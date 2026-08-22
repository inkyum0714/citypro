/**
 * 서버 스냅샷을 받아 로컬에서 보간·충돌 정리를 돌립니다.
 * 렌더는 이 루프가 담당하고, WebSocket 수신은 상태만 갱신합니다.
 */
window.clientSim = (() => {
    const PHYSICS_HZ = 30;
    const STEP = 1 / PHYSICS_HZ;
    const MAX_FRAME_DT = 0.08;
    const BLEND = 8.5;
    const REPORT_MS = 180;

    let serverState = null;
    let vehicles = new Map();
    let handledPairs = new Set();
    let running = false;
    let rafId = 0;
    let lastTs = 0;
    let acc = 0;
    let quality = 'high';
    let frameMsEma = 16;
    let pendingReports = [];
    let lastReportAt = 0;
    let paused = false;
    let clientPhysics = true;

    const cloneVehicle = (src) => ({
        id: src.id,
        x: src.x,
        y: src.y,
        sx: src.x,
        sy: src.y,
        vx: src.vx || (src.speed || 0) * Math.cos(src.angle || 0),
        vy: src.vy || (src.speed || 0) * Math.sin(src.angle || 0),
        speed: src.speed || 0,
        current_speed: src.speed || 0,
        angle: src.angle || 0,
        color: src.color,
        type: src.type,
        length: src.length,
        width: src.width,
        mass_kg: src.mass_kg || 1000,
        space_occupancy: src.space_occupancy || 1,
        road_id: src.road_id,
        lane_index: src.lane_index,
        turn_signal: src.turn_signal,
        state: src.state,
        cargo_type: src.cargo_type,
        cargo_classified: src.cargo_classified,
        bus_dwell_remaining: src.bus_dwell_remaining,
        in_accident: !!src.in_accident,
        rescue_state: src.rescue_state,
        emergency_flash: src.emergency_flash,
        accident_timer: 0,
        waiting_at_signal: !!src.waiting_at_signal,
        finished: false,
        last_impulse: src.last_impulse || 0,
        collision_partner_id: src.collision_partner_id,
        _serverCrash: !!src.in_accident,
    });

    const applyServerVehicle = (local, src) => {
        local.sx = src.x;
        local.sy = src.y;
        if (typeof src.vx === 'number') local.vx = src.vx;
        if (typeof src.vy === 'number') local.vy = src.vy;
        local.speed = src.speed;
        local.current_speed = src.speed;
        local.angle = src.angle;
        local.color = src.color;
        local.type = src.type;
        local.length = src.length;
        local.width = src.width;
        local.mass_kg = src.mass_kg || local.mass_kg;
        local.space_occupancy = src.space_occupancy || local.space_occupancy;
        local.road_id = src.road_id;
        local.lane_index = src.lane_index;
        local.turn_signal = src.turn_signal;
        local.cargo_type = src.cargo_type;
        local.cargo_classified = src.cargo_classified;
        local.bus_dwell_remaining = src.bus_dwell_remaining;
        local.waiting_at_signal = !!src.waiting_at_signal;
        local.rescue_state = src.rescue_state;
        local.emergency_flash = src.emergency_flash;
        if (src.in_accident) {
            local.in_accident = true;
            local.state = 'accident';
            local._serverCrash = true;
        } else if (local.in_accident && !local._serverCrash && (local.accident_timer || 0) > 0.9) {
            local.in_accident = false;
            local.state = src.state;
            local.x = src.x;
            local.y = src.y;
            if (local.collision_partner_id) {
                const key = local.id < local.collision_partner_id
                    ? `${local.id}:${local.collision_partner_id}`
                    : `${local.collision_partner_id}:${local.id}`;
                handledPairs.delete(key);
            }
            local.collision_partner_id = null;
        } else if (!local.in_accident) {
            local.state = src.state;
        }
        if (!clientPhysics) {
            local.x = src.x;
            local.y = src.y;
        }
        if (src.collision_partner_id != null && local.collision_partner_id == null) {
            local.collision_partner_id = src.collision_partner_id;
        }
    };

    const ingest = (state) => {
        if (!state) return;
        if (state.physics) {
            window.CityFlowPhysics?.configure(state.physics);
            if (typeof state.physics.client_physics === 'boolean') {
                clientPhysics = state.physics.client_physics;
            }
        }
        paused = !!state.stats?.is_paused;
        const prev = serverState;
        if (prev && state.snapshot === 'tick') {
            state = {
                ...prev,
                ...state,
                event_catalog: state.event_catalog || prev.event_catalog,
                rescue_catalog: state.rescue_catalog || prev.rescue_catalog,
                cargo_catalog: state.cargo_catalog || prev.cargo_catalog,
                roads: state.roads || prev.roads,
                nodes: state.nodes || prev.nodes,
                physics: state.physics || prev.physics,
                analytics: {
                    ...(prev.analytics || {}),
                    ...(state.analytics || {}),
                    series: state.analytics?.series || prev.analytics?.series || [],
                },
                player: state.player || prev.player,
            };
        }
        serverState = state;

        const incoming = state.vehicles || [];
        const seen = new Set();
        for (let i = 0; i < incoming.length; i += 1) {
            const src = incoming[i];
            seen.add(src.id);
            const local = vehicles.get(src.id);
            if (!local) {
                vehicles.set(src.id, cloneVehicle(src));
            } else {
                applyServerVehicle(local, src);
            }
        }
        for (const id of vehicles.keys()) {
            if (!seen.has(id)) vehicles.delete(id);
        }

        const live = new Set();
        vehicles.forEach((v) => live.add(v.id));
        for (const key of handledPairs) {
            const [a, b] = key.split(':').map(Number);
            if (!live.has(a) || !live.has(b)) handledPairs.delete(key);
        }
        start();
    };

    const stepPhysics = (dt) => {
        if (!clientPhysics || paused) return;
        const list = [];
        vehicles.forEach((v) => list.push(v));
        const alpha = 1 - Math.exp(-BLEND * dt);

        for (let i = 0; i < list.length; i += 1) {
            const v = list[i];
            if (v.in_accident) {
                window.CityFlowPhysics.dampAccident(v, dt);
                continue;
            }
            v.x += v.vx * dt;
            v.y += v.vy * dt;
            v.x += (v.sx - v.x) * alpha;
            v.y += (v.sy - v.y) * alpha;
            window.CityFlowPhysics.constrainToRoad(v, serverState?.roads, dt);
        }

        const preset = window.CityFlowPhysics.qualityPreset(quality);
        const result = window.CityFlowPhysics.settle(list, {
            iterations: preset.iterations,
            maxPairs: preset.maxPairs,
            handledPairs,
        });
        if (result.pairs.length) {
            pendingReports.push(...result.pairs);
        }
    };

    const flushReports = (now) => {
        if (!pendingReports.length || now - lastReportAt < REPORT_MS) return;
        if (!window.simulationSocket || window.simulationSocket.readyState !== WebSocket.OPEN) {
            pendingReports = [];
            return;
        }
        const pairs = pendingReports.splice(0, 12);
        lastReportAt = now;
        window.simulationSocket.send(JSON.stringify({
            action: 'report_collisions',
            pairs,
        }));
    };

    const adaptQuality = (frameMs) => {
        frameMsEma = frameMsEma * 0.9 + frameMs * 0.1;
        if (frameMsEma > 33) quality = 'low';
        else if (frameMsEma > 22) quality = 'medium';
        else quality = 'high';
    };

    const renderState = () => {
        if (!serverState) return null;
        const list = [];
        vehicles.forEach((v) => list.push(v));
        const state = serverState;
        state.vehicles = list;
        state.client_quality = quality;
        return state;
    };

    const tick = (ts) => {
        rafId = requestAnimationFrame(tick);
        if (!serverState) return;
        const now = ts;
        const rawDt = lastTs ? (now - lastTs) / 1000 : STEP;
        lastTs = now;
        const dt = Math.min(MAX_FRAME_DT, Math.max(0, rawDt));
        acc += dt;
        let steps = 0;
        while (acc >= STEP && steps < 3) {
            stepPhysics(STEP);
            acc -= STEP;
            steps += 1;
        }
        const state = renderState();
        if (state) {
            window.canvasRenderer.render(state);
            window.uiController?.paintPreview?.();
        }
        flushReports(now);
        adaptQuality(dt * 1000);
    };

    const start = () => {
        if (running) return;
        running = true;
        lastTs = 0;
        acc = 0;
        rafId = requestAnimationFrame(tick);
    };

    const stop = () => {
        running = false;
        if (rafId) cancelAnimationFrame(rafId);
        rafId = 0;
    };

    const reset = () => {
        vehicles.clear();
        handledPairs.clear();
        pendingReports = [];
        serverState = null;
    };

    return {
        ingest,
        start,
        stop,
        reset,
        getQuality: () => quality,
        getState: () => serverState,
        usesClientPhysics: () => clientPhysics,
    };
})();
