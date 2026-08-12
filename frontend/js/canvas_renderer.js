window.canvasRenderer = {
    lastState: null,
    animationPhase: 0,
    _didInitialFit: false,

    resize() {
        const canvas = document.getElementById('simulationCanvas');
        const stage = canvas.parentElement;
        canvas.width = stage.clientWidth;
        canvas.height = stage.clientHeight;
        if (!this._didInitialFit) {
            window.simulationCamera.reset(canvas);
        }
        if (this.lastState) {
            this.render(this.lastState);
        }
    },

    render(state) {
        if (!state) return;
        this.lastState = state;
        const canvas = document.getElementById('simulationCanvas');
        if (!canvas) return;
        if (canvas.width < 2 || canvas.height < 2) {
            this.resize();
        }
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        const camera = window.simulationCamera;
        this.animationPhase += 0.04;

        if (!this._didInitialFit && (state.roads?.length || 0) > 0) {
            camera.fitToState(state, canvas);
            this._didInitialFit = true;
        }

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        this._drawBackground(ctx, canvas, state);
        this._drawWeather(ctx, canvas, state.weather);

        ctx.save();
        camera.applyTransform(ctx, canvas);
        this._drawWorldGrid(ctx, canvas, camera);

        const roads = state.roads || [];
        const nodes = state.nodes || [];
        const vehicles = state.vehicles || [];
        const events = state.events || [];

        roads.forEach((road) => this._drawRoad(ctx, road));
        this._drawNetworkNodes(ctx, nodes, roads);
        (state.bus_stops || []).forEach((stop) => this._drawBusStop(ctx, stop));
        (state.traffic_lights || []).forEach((light) => this._drawTrafficLight(ctx, light));
        events.forEach((event) => this._drawEvent(ctx, roads, event));
        vehicles.forEach((vehicle) => this._drawVehicle(ctx, vehicle, state.time_of_day));
        ctx.restore();

        this._drawHud(ctx, canvas, camera);
        this._drawGoldenBanner(ctx, canvas, state);
    },

    _drawBusStop(ctx, stop) {
        const x = stop.x;
        const y = stop.y;
        ctx.save();
        ctx.translate(x, y);
        ctx.fillStyle = '#0ea5e9';
        ctx.strokeStyle = '#e0f2fe';
        ctx.lineWidth = 2;
        ctx.beginPath();
        if (ctx.roundRect) {
            ctx.roundRect(-8, -6, 16, 12, 3);
        } else {
            ctx.rect(-8, -6, 16, 12);
        }
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 8px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('BUS', 0, 3);
        ctx.restore();
    },

    _drawGoldenBanner(ctx, canvas, state) {
        const gh = state.golden_hour;
        if (!gh?.active) return;
        ctx.save();
        ctx.fillStyle = 'rgba(251, 191, 36, 0.92)';
        ctx.fillRect(12, 12, 210, 28);
        ctx.fillStyle = '#422006';
        ctx.font = '600 12px Inter, sans-serif';
        ctx.fillText(`골든 아워 ${Math.floor(gh.streak_seconds)}s · 평균 ${gh.avg_speed}`, 20, 30);
        ctx.restore();
    },

    _drawWorldGrid(ctx, canvas, camera) {
        const step = 40;
        const topLeft = camera.screenToWorld(0, 0, canvas);
        const bottomRight = camera.screenToWorld(canvas.width, canvas.height, canvas);
        const startX = Math.floor(topLeft.x / step) * step;
        const startY = Math.floor(topLeft.y / step) * step;
        ctx.save();
        ctx.strokeStyle = 'rgba(148, 163, 184, 0.08)';
        ctx.lineWidth = 1 / camera.zoom;
        for (let x = startX; x <= bottomRight.x; x += step) {
            ctx.beginPath();
            ctx.moveTo(x, topLeft.y);
            ctx.lineTo(x, bottomRight.y);
            ctx.stroke();
        }
        for (let y = startY; y <= bottomRight.y; y += step) {
            ctx.beginPath();
            ctx.moveTo(topLeft.x, y);
            ctx.lineTo(bottomRight.x, y);
            ctx.stroke();
        }
        ctx.restore();
    },

    _drawHud(ctx, canvas, camera) {
        ctx.save();
        ctx.fillStyle = 'rgba(15, 23, 42, 0.75)';
        ctx.strokeStyle = 'rgba(148, 163, 184, 0.25)';
        ctx.lineWidth = 1;
        const label = `줌 ${Math.round(camera.zoom * 100)}% · 휠 확대/축소 · 우클릭/관찰 모드 드래그 이동`;
        ctx.font = '12px Inter, sans-serif';
        const pad = 10;
        const w = ctx.measureText(label).width + pad * 2;
        ctx.beginPath();
        this._roundRect(ctx, 12, canvas.height - 36, w, 24, 8);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = '#94a3b8';
        ctx.fillText(label, 12 + pad, canvas.height - 19);
        ctx.restore();
    },

    _drawBackground(ctx, canvas, state) {
        const cosmetic = state.player?.active_cosmetic || 'default';
        const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
        if (cosmetic === 'sunset') {
            gradient.addColorStop(0, '#4a1942');
            gradient.addColorStop(1, '#1a0f2e');
        } else if (cosmetic === 'neon') {
            gradient.addColorStop(0, '#0a1628');
            gradient.addColorStop(1, '#050510');
        } else if (state.time_of_day === 'rush_hour') {
            gradient.addColorStop(0, '#1e1b4b');
            gradient.addColorStop(1, '#0f172a');
        } else if (state.weather === 'rain') {
            gradient.addColorStop(0, '#0f172a');
            gradient.addColorStop(1, '#111827');
        } else {
            gradient.addColorStop(0, '#13203d');
            gradient.addColorStop(1, '#0b1020');
        }
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    },

    _drawWeather(ctx, canvas, weather) {
        if (weather !== 'rain' && weather !== 'fog') return;

        ctx.save();
        if (weather === 'rain') {
            ctx.strokeStyle = 'rgba(147, 197, 253, 0.25)';
            ctx.lineWidth = 1;
            for (let i = 0; i < 80; i += 1) {
                const x = (i * 97 + this.animationPhase * 120) % canvas.width;
                const y = (i * 53 + this.animationPhase * 220) % canvas.height;
                ctx.beginPath();
                ctx.moveTo(x, y);
                ctx.lineTo(x - 4, y + 12);
                ctx.stroke();
            }
        } else {
            const fog = ctx.createRadialGradient(
                canvas.width / 2,
                canvas.height / 2,
                20,
                canvas.width / 2,
                canvas.height / 2,
                canvas.width / 1.2,
            );
            fog.addColorStop(0, 'rgba(148, 163, 184, 0.02)');
            fog.addColorStop(1, 'rgba(148, 163, 184, 0.18)');
            ctx.fillStyle = fog;
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        }
        ctx.restore();
    },

    _drawRoad(ctx, road) {
        const width = road.width || 18;
        ctx.save();
        ctx.lineCap = 'round';

        ctx.beginPath();
        ctx.moveTo(road.start[0], road.start[1]);
        ctx.lineTo(road.end[0], road.end[1]);
        ctx.strokeStyle = 'rgba(15, 23, 42, 0.85)';
        ctx.lineWidth = width + 8;
        ctx.stroke();

        const roadGradient = ctx.createLinearGradient(
            road.start[0], road.start[1], road.end[0], road.end[1],
        );
        roadGradient.addColorStop(0, '#334155');
        roadGradient.addColorStop(0.5, '#475569');
        roadGradient.addColorStop(1, '#334155');
        const cosmetic = this.lastState?.player?.active_cosmetic;
        if (cosmetic === 'neon') {
            roadGradient.addColorStop(0, '#1e3a5f');
            roadGradient.addColorStop(0.5, '#22d3ee');
            roadGradient.addColorStop(1, '#1e3a5f');
        } else if (cosmetic === 'sunset') {
            roadGradient.addColorStop(0, '#78350f');
            roadGradient.addColorStop(0.5, '#ea580c');
            roadGradient.addColorStop(1, '#78350f');
        }

        ctx.beginPath();
        ctx.moveTo(road.start[0], road.start[1]);
        ctx.lineTo(road.end[0], road.end[1]);
        ctx.strokeStyle = roadGradient;
        ctx.lineWidth = width;
        ctx.stroke();

        const dx = road.end[0] - road.start[0];
        const dy = road.end[1] - road.start[1];
        const length = Math.hypot(dx, dy);
        if (length < 1) {
            ctx.restore();
            return;
        }

        const nx = -dy / length;
        const ny = dx / length;
        const laneOffset = width * 0.18;

        ctx.setLineDash([10, 14]);
        ctx.strokeStyle = 'rgba(250, 204, 21, 0.85)';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(road.start[0], road.start[1]);
        ctx.lineTo(road.end[0], road.end[1]);
        ctx.stroke();

        if ((road.lanes || 1) >= 2) {
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.55)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(road.start[0] + nx * laneOffset, road.start[1] + ny * laneOffset);
            ctx.lineTo(road.end[0] + nx * laneOffset, road.end[1] + ny * laneOffset);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(road.start[0] - nx * laneOffset, road.start[1] - ny * laneOffset);
            ctx.lineTo(road.end[0] - nx * laneOffset, road.end[1] - ny * laneOffset);
            ctx.stroke();
        }

        ctx.setLineDash([]);
        ctx.restore();
    },

    _drawTrafficLight(ctx, light) {
        const colors = {
            green: '#22c55e',
            yellow: '#eab308',
            red: '#ef4444',
        };
        const fill = colors[light.state] || colors.red;
        ctx.save();
        ctx.beginPath();
        ctx.arc(light.x, light.y - 16, 7, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
        ctx.fill();
        ctx.strokeStyle = 'rgba(148, 163, 184, 0.6)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(light.x, light.y - 16, 4.5, 0, Math.PI * 2);
        ctx.fillStyle = fill;
        ctx.shadowColor = fill;
        ctx.shadowBlur = light.state === 'green' ? 10 : 4;
        ctx.fill();
        ctx.restore();
    },

    _drawNetworkNodes(ctx, nodes, roads) {
        if (nodes.length > 0) {
            nodes.forEach((node) => {
                const degree = roads.filter(
                    (r) => r.start_node_id === node.id || r.end_node_id === node.id,
                ).length;
                if (degree < 2) return;
                ctx.save();
                ctx.beginPath();
                ctx.arc(node.x, node.y, 10, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(250, 204, 21, 0.2)';
                ctx.fill();
                ctx.strokeStyle = 'rgba(250, 204, 21, 0.55)';
                ctx.lineWidth = 2;
                ctx.stroke();
                ctx.restore();
            });
            return;
        }
        this._drawIntersections(ctx, roads);
    },

    _drawIntersections(ctx, roads) {
        const points = {};
        roads.forEach((road) => {
            ['start', 'end'].forEach((key) => {
                const point = road[key];
                const id = `${Math.round(point[0])},${Math.round(point[1])}`;
                points[id] = (points[id] || 0) + 1;
            });
        });

        Object.entries(points).forEach(([key, count]) => {
            if (count < 2) return;
            const [x, y] = key.split(',').map(Number);
            ctx.save();
            ctx.beginPath();
            ctx.arc(x, y, 12, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(250, 204, 21, 0.18)';
            ctx.fill();
            ctx.strokeStyle = 'rgba(250, 204, 21, 0.45)';
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.restore();
        });
    },

    _roadPoint(road, progress) {
        return [
            road.start[0] + (road.end[0] - road.start[0]) * progress,
            road.start[1] + (road.end[1] - road.start[1]) * progress,
        ];
    },

    _drawEvent(ctx, roads, event) {
        const road = roads.find((item) => item.id === event.road_id);
        if (!road) return;

        const [x, y] = this._roadPoint(road, event.progress || 0.5);
        const pulse = 0.65 + Math.sin(this.animationPhase * 2) * 0.15;

        ctx.save();
        if (event.severity === 'critical') {
            ctx.fillStyle = `rgba(239, 68, 68, ${0.18 * pulse})`;
            ctx.strokeStyle = 'rgba(239, 68, 68, 0.85)';
        } else if (event.severity === 'warning') {
            ctx.fillStyle = `rgba(245, 158, 11, ${0.16 * pulse})`;
            ctx.strokeStyle = 'rgba(245, 158, 11, 0.85)';
        } else if (event.severity === 'premium') {
            ctx.fillStyle = `rgba(251, 191, 36, ${0.18 * pulse})`;
            ctx.strokeStyle = 'rgba(251, 191, 36, 0.9)';
        } else {
            ctx.fillStyle = `rgba(91, 140, 255, ${0.14 * pulse})`;
            ctx.strokeStyle = 'rgba(91, 140, 255, 0.85)';
        }

        ctx.beginPath();
        ctx.arc(x, y, 18 * pulse, 0, Math.PI * 2);
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.font = '16px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#fff';
        ctx.fillText(event.icon || '⚠️', x, y);
        ctx.restore();
    },

    _drawVehicle(ctx, vehicle, timeOfDay) {
        const length = vehicle.length || 14;
        const width = vehicle.width || 8;
        const angle = vehicle.angle || 0;

        ctx.save();
        ctx.translate(vehicle.x, vehicle.y);
        ctx.rotate(angle);

        ctx.fillStyle = 'rgba(0, 0, 0, 0.25)';
        ctx.fillRect(-length / 2 + 2, -width / 2 + 3, length, width);

        const body = ctx.createLinearGradient(-length / 2, 0, length / 2, 0);
        body.addColorStop(0, this._shadeColor(vehicle.color, -18));
        body.addColorStop(1, vehicle.color || '#ffffff');
        ctx.fillStyle = body;
        this._roundRect(ctx, -length / 2, -width / 2, length, width, 3);
        ctx.fill();

        ctx.fillStyle = 'rgba(191, 219, 254, 0.85)';
        const windowLength = Math.max(4, length * 0.28);
        this._roundRect(ctx, -length * 0.08, -width * 0.34, windowLength, width * 0.68, 2);
        ctx.fill();

        if (vehicle.type === 'truck') {
            ctx.fillStyle = this._shadeColor(vehicle.color, -28);
            ctx.fillRect(length * 0.08, -width / 2, length * 0.35, width);
            if (vehicle.cargo_type && vehicle.cargo_type !== 'unclassified') {
                ctx.fillStyle = '#fef3c7';
                ctx.font = '7px sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText(String(vehicle.cargo_type).slice(0, 4), 0, width + 8);
            } else if (vehicle.cargo_classified === false) {
                ctx.fillStyle = '#f87171';
                ctx.font = '7px sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText('?', 0, width + 8);
            }
        }

        if (vehicle.type === 'bus') {
            ctx.fillStyle = 'rgba(255,255,255,0.25)';
            for (let i = -0.2; i <= 0.25; i += 0.18) {
                ctx.fillRect(length * i, -width * 0.32, length * 0.08, width * 0.64);
            }
        }

        if (vehicle.emergency_flash && Math.sin(this.animationPhase * 4) > 0) {
            ctx.fillStyle = '#ef4444';
            ctx.fillRect(-length * 0.35, -width * 0.45, length * 0.18, width * 0.25);
            ctx.fillStyle = '#3b82f6';
            ctx.fillRect(-length * 0.35, width * 0.2, length * 0.18, width * 0.25);
        }

        if (timeOfDay === 'rush_hour') {
            ctx.fillStyle = 'rgba(254, 240, 138, 0.95)';
            ctx.beginPath();
            ctx.arc(length / 2 - 1, -width * 0.18, 2, 0, Math.PI * 2);
            ctx.arc(length / 2 - 1, width * 0.18, 2, 0, Math.PI * 2);
            ctx.fill();
        }

        if (vehicle.state === 'braking') {
            ctx.fillStyle = '#ef4444';
            ctx.fillRect(-length / 2 + 1, -width * 0.18, 2.5, 2.5);
            ctx.fillRect(-length / 2 + 1, width * 0.18 - 2.5, 2.5, 2.5);
        }

        if (vehicle.in_accident || vehicle.state === 'accident') {
            ctx.strokeStyle = vehicle.rescue_state === 'police' || vehicle.rescue_state === 'towing'
                ? '#38bdf8'
                : '#ef4444';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(0, 0, Math.max(length, width), 0, Math.PI * 2);
            ctx.stroke();
            ctx.fillStyle = '#f8fafc';
            ctx.font = '7px Inter, sans-serif';
            ctx.textAlign = 'center';
            const tons = ((vehicle.mass_kg || 1000) / 1000).toFixed(1);
            ctx.fillText(`${tons}t`, 0, -width - 4);
            if (vehicle.rescue_state === 'police') {
                ctx.fillText('🚓', 0, width + 10);
            } else if (vehicle.rescue_state === 'towing') {
                ctx.fillText('🚛', 0, width + 10);
            }
        }

        if (vehicle.turn_signal === 'left' || vehicle.turn_signal === 'right') {
            const blink = Math.sin(this.animationPhase * 6) > 0;
            if (blink) {
                ctx.fillStyle = '#fbbf24';
                const side = vehicle.turn_signal === 'left' ? -1 : 1;
                ctx.fillRect(side * length * 0.22, -width * 0.42, length * 0.12, width * 0.22);
            }
        }

        ctx.restore();
    },

    _roundRect(ctx, x, y, width, height, radius) {
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.lineTo(x + width - radius, y);
        ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
        ctx.lineTo(x + width, y + height - radius);
        ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
        ctx.lineTo(x + radius, y + height);
        ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
        ctx.lineTo(x, y + radius);
        ctx.quadraticCurveTo(x, y, x + radius, y);
        ctx.closePath();
    },

    _shadeColor(hex, amount) {
        if (!hex || !hex.startsWith('#')) return hex || '#ffffff';
        const num = parseInt(hex.slice(1), 16);
        const r = Math.min(255, Math.max(0, ((num >> 16) & 255) + amount));
        const g = Math.min(255, Math.max(0, ((num >> 8) & 255) + amount));
        const b = Math.min(255, Math.max(0, (num & 255) + amount));
        return `rgb(${r}, ${g}, ${b})`;
    },
};

window.addEventListener('resize', () => window.canvasRenderer.resize());

const scheduleCanvasResize = () => {
    requestAnimationFrame(() => {
        window.canvasRenderer.resize();
        requestAnimationFrame(() => window.canvasRenderer.resize());
    });
};

scheduleCanvasResize();

const simStage = document.querySelector('.simulation-stage');
if (simStage && typeof ResizeObserver !== 'undefined') {
    const ro = new ResizeObserver(() => window.canvasRenderer.resize());
    ro.observe(simStage);
}
