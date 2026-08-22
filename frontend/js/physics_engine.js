/**
 * 클라이언트 2D 물리 — 충돌 검출·작용반작용·겹침 정리.
 * 인텔 9세대급(i5-9400 / UHD 630)에서 수백 대까지 메인 스레드 예산 안에 돌도록
 * 격자 해시 + 프레임 예산으로 O(n²)를 피합니다.
 */
window.CityFlowPhysics = (() => {
    const DEFAULTS = {
        collision_radius_scale: 0.55,
        collision_min_closing_speed: 2.0,
        collision_velocity_damp: 0.35,
        collision_restitution: 0.25,
        avoidance_scan_radius: 55.0,
        cell_size: 64,
        max_pairs_per_frame: 80,
        settle_iterations: 3,
        road_snap: true,
        lateral_friction: 0.72,
    };

    let cfg = { ...DEFAULTS };

    const configure = (next) => {
        if (!next || typeof next !== 'object') return cfg;
        cfg = { ...cfg, ...next };
        if (!cfg.cell_size || cfg.cell_size < 16) cfg.cell_size = 64;
        return cfg;
    };

    const hypot = Math.hypot;
    const cellKey = (cx, cy) => (cx + 32768) * 65536 + (cy + 32768);

    const collisionRadius = (vehicle) => {
        const scale = cfg.collision_radius_scale;
        const occupancy = vehicle.space_occupancy || 1;
        const base = hypot(vehicle.length || 14, vehicle.width || 8) * scale;
        return Math.max(4, base * Math.sqrt(Math.max(0.5, occupancy)));
    };

    const velocityOf = (vehicle) => {
        const vx = vehicle.vx;
        const vy = vehicle.vy;
        if (typeof vx === 'number' && typeof vy === 'number') return [vx, vy];
        const speed = vehicle.speed || vehicle.current_speed || 0;
        const angle = vehicle.angle || 0;
        return [speed * Math.cos(angle), speed * Math.sin(angle)];
    };

    const syncSpeedFromVelocity = (vehicle) => {
        const speed = hypot(vehicle.vx || 0, vehicle.vy || 0);
        vehicle.speed = speed;
        vehicle.current_speed = speed;
        if (speed > 0.05) vehicle.angle = Math.atan2(vehicle.vy, vehicle.vx);
    };

    const closingSpeed = (ego, other) => {
        const dx = other.x - ego.x;
        const dy = other.y - ego.y;
        const dist = hypot(dx, dy);
        if (dist < 1e-6) return Math.max(ego.speed || 0, other.speed || 0);
        const nx = dx / dist;
        const ny = dy / dist;
        const [v1x, v1y] = velocityOf(ego);
        const [v2x, v2y] = velocityOf(other);
        return (v1x - v2x) * nx + (v1y - v2y) * ny;
    };

    const detectPair = (a, b) => {
        if (!a || !b || a.id === b.id || a.finished || b.finished) return false;
        if (a.in_accident || b.in_accident) return false;
        const dist = hypot(a.x - b.x, a.y - b.y);
        const minSep = collisionRadius(a) + collisionRadius(b);
        if (dist >= minSep) return false;
        return closingSpeed(a, b) > cfg.collision_min_closing_speed || dist < minSep * 0.65;
    };

    const resolveImpulse = (a, b) => {
        const m1 = Math.max(1, a.mass_kg || 1000);
        const m2 = Math.max(1, b.mass_kg || 1000);
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        let dist = hypot(dx, dy);
        let nx;
        let ny;
        if (dist < 1e-6) {
            nx = Math.cos(a.angle || 0);
            ny = Math.sin(a.angle || 0);
            dist = 1e-6;
        } else {
            nx = dx / dist;
            ny = dy / dist;
        }

        const [v1x, v1y] = velocityOf(a);
        const [v2x, v2y] = velocityOf(b);
        const velAlongN = (v2x - v1x) * nx + (v2y - v1y) * ny;
        const e = cfg.collision_restitution;
        if (velAlongN > 0) {
            return { impulse: 0, mass_a: m1, mass_b: m2 };
        }

        const invM1 = 1 / m1;
        const invM2 = 1 / m2;
        const denom = invM1 + invM2;
        const j = denom > 0 ? -(1 + e) * velAlongN / denom : 0;
        const impulse = Math.abs(j);

        a.vx = v1x - j * invM1 * nx;
        a.vy = v1y - j * invM1 * ny;
        b.vx = v2x + j * invM2 * nx;
        b.vy = v2y + j * invM2 * ny;

        const damp = cfg.collision_velocity_damp;
        a.vx *= damp;
        a.vy *= damp;
        b.vx *= damp;
        b.vy *= damp;
        syncSpeedFromVelocity(a);
        syncSpeedFromVelocity(b);

        const overlap = (collisionRadius(a) + collisionRadius(b)) - dist;
        if (overlap > 0) {
            const sep = overlap / denom;
            a.x -= nx * sep * invM1;
            a.y -= ny * sep * invM1;
            b.x += nx * sep * invM2;
            b.y += ny * sep * invM2;
        }

        a.last_impulse = impulse;
        b.last_impulse = impulse;
        a.collision_partner_id = b.id;
        b.collision_partner_id = a.id;
        return { impulse, mass_a: m1, mass_b: m2, id_a: a.id, id_b: b.id };
    };

    const buildHash = (vehicles) => {
        const cell = cfg.cell_size;
        const grid = new Map();
        for (let i = 0; i < vehicles.length; i += 1) {
            const v = vehicles[i];
            if (v.finished) continue;
            const cx = Math.floor(v.x / cell);
            const cy = Math.floor(v.y / cell);
            const key = cellKey(cx, cy);
            let bucket = grid.get(key);
            if (!bucket) {
                bucket = [];
                grid.set(key, bucket);
            }
            bucket.push(v);
        }
        return grid;
    };

    const forNeighborPairs = (vehicles, visit) => {
        const cell = cfg.cell_size;
        const grid = buildHash(vehicles);
        const seen = new Set();
        const offsets = [];
        for (let ox = -1; ox <= 1; ox += 1) {
            for (let oy = -1; oy <= 1; oy += 1) offsets.push([ox, oy]);
        }

        for (let i = 0; i < vehicles.length; i += 1) {
            const a = vehicles[i];
            if (a.finished || a.in_accident) continue;
            const cx = Math.floor(a.x / cell);
            const cy = Math.floor(a.y / cell);
            for (let o = 0; o < offsets.length; o += 1) {
                const bucket = grid.get(cellKey(cx + offsets[o][0], cy + offsets[o][1]));
                if (!bucket) continue;
                for (let k = 0; k < bucket.length; k += 1) {
                    const b = bucket[k];
                    if (b.id <= a.id || b.finished || b.in_accident) continue;
                    const pairKey = a.id < b.id ? `${a.id}:${b.id}` : `${b.id}:${a.id}`;
                    if (seen.has(pairKey)) continue;
                    seen.add(pairKey);
                    if (visit(a, b) === false) return;
                }
            }
        }
    };

    /**
     * 겹침 해소 + 신규 충돌. budgetMs를 넘기면 나머지 쌍은 다음 프레임.
     * @returns {{pairs: object[], checked: number}}
     */
    const settle = (vehicles, options = {}) => {
        const iterations = Math.max(1, options.iterations ?? cfg.settle_iterations);
        const maxPairs = options.maxPairs ?? cfg.max_pairs_per_frame;
        const pairs = [];
        let checked = 0;
        const handled = options.handledPairs || new Set();

        for (let iter = 0; iter < iterations; iter += 1) {
            let hitBudget = false;
            forNeighborPairs(vehicles, (a, b) => {
                checked += 1;
                if (!detectPair(a, b)) return true;
                const key = a.id < b.id ? `${a.id}:${b.id}` : `${b.id}:${a.id}`;
                if (handled.has(key)) {
                    resolveImpulse(a, b);
                    return true;
                }
                if (pairs.length >= maxPairs) {
                    hitBudget = true;
                    return false;
                }
                const physics = resolveImpulse(a, b);
                if (physics.impulse > 0 || hypot(a.x - b.x, a.y - b.y) < collisionRadius(a) + collisionRadius(b)) {
                    handled.add(key);
                    pairs.push({
                        id_a: a.id,
                        id_b: b.id,
                        impulse: physics.impulse,
                        mass_a: physics.mass_a,
                        mass_b: physics.mass_b,
                    });
                    a.in_accident = true;
                    b.in_accident = true;
                    a.state = 'accident';
                    b.state = 'accident';
                    a.accident_timer = 0;
                    b.accident_timer = 0;
                }
                return true;
            });
            if (hitBudget) break;
        }
        return { pairs, checked };
    };

    const constrainToRoad = (vehicle, roads, dt) => {
        if (!cfg.road_snap || !roads || !roads.length) return;
        const rid = vehicle.road_id;
        let road = null;
        for (let i = 0; i < roads.length; i += 1) {
            if (roads[i].id === rid) {
                road = roads[i];
                break;
            }
        }
        if (!road || !road.start || !road.end) return;
        const dx = road.end[0] - road.start[0];
        const dy = road.end[1] - road.start[1];
        const len = hypot(dx, dy);
        if (len < 1) return;
        const tx = dx / len;
        const ty = dy / len;
        const speed = hypot(vehicle.vx || 0, vehicle.vy || 0);
        const along = (vehicle.vx || 0) * tx + (vehicle.vy || 0) * ty;
        const friction = cfg.lateral_friction == null ? 0.72 : cfg.lateral_friction;
        const keep = Math.max(0.15, 1 - friction * Math.min(1, dt * 8));
        const latVx = (vehicle.vx || 0) - along * tx;
        const latVy = (vehicle.vy || 0) - along * ty;
        vehicle.vx = along * tx + latVx * keep;
        vehicle.vy = along * ty + latVy * keep;
        if (speed > 0.4) vehicle.angle = Math.atan2(ty * Math.sign(along || 1) || ty, tx * Math.sign(along || 1) || tx);
        if (vehicle.waiting_at_signal) {
            vehicle.vx *= 0.55;
            vehicle.vy *= 0.55;
        }
    };

    const dampAccident = (vehicle, dt) => {
        if (!vehicle.in_accident) return;
        vehicle.accident_timer = (vehicle.accident_timer || 0) + dt;
        vehicle.vx = (vehicle.vx || 0) * 0.85;
        vehicle.vy = (vehicle.vy || 0) * 0.85;
        const speed = hypot(vehicle.vx, vehicle.vy);
        if (speed < 0.8 || vehicle.accident_timer > 1.2) {
            vehicle.vx = 0;
            vehicle.vy = 0;
            vehicle.speed = 0;
            vehicle.current_speed = 0;
        } else {
            vehicle.speed = speed;
            vehicle.current_speed = speed;
            vehicle.x += vehicle.vx * dt;
            vehicle.y += vehicle.vy * dt;
        }
        vehicle.acceleration = 0;
        vehicle.state = 'accident';
    };

    const qualityPreset = (level) => {
        if (level === 'low') {
            return { iterations: 1, maxPairs: 16, rain: 0, gradients: false, grid: false };
        }
        if (level === 'medium') {
            return { iterations: 1, maxPairs: 32, rain: 36, gradients: false, grid: true };
        }
        return { iterations: 3, maxPairs: 80, rain: 80, gradients: true, grid: true };
    };

    return {
        configure,
        collisionRadius,
        detectPair,
        resolveImpulse,
        settle,
        dampAccident,
        constrainToRoad,
        qualityPreset,
        getConfig: () => cfg,
    };
})();
