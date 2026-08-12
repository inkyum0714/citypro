const canvas = document.getElementById('simulationCanvas');
const previewCtx = canvas.getContext('2d');

let isDrawing = false;
let startWorld = { x: 0, y: 0 };
let currentWorld = { x: 0, y: 0 };
let activeTool = 'road';
let previewState = null;

const getWorldPoint = (clientX, clientY) => {
    const rect = canvas.getBoundingClientRect();
    const screenX = clientX - rect.left;
    const screenY = clientY - rect.top;
    return window.simulationCamera.screenToWorld(screenX, screenY, canvas);
};

const sendAction = async (payload) => {
    if (window.simulationSocket && window.simulationSocket.readyState === WebSocket.OPEN) {
        window.simulationSocket.send(JSON.stringify(payload));
        return true;
    }
    try {
        const res = await fetch('/api/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (data.message) {
            window.uiBridge?.showToast(data.message, data.ok ? 'info' : 'warning');
        }
        if (data.player) {
            window.engagementPanel?.applyPlayer(data.player);
        }
        if (data.ok && window.uiBridge?.refreshSimulationState) {
            await window.uiBridge.refreshSimulationState();
        }
        return data.ok;
    } catch {
        window.uiBridge?.showToast('서버와 연결되지 않았습니다.', 'warning');
        return false;
    }
};

const drawPreview = () => {
    if (!previewState || !isDrawing) return;
    window.canvasRenderer.render(previewState);

    previewCtx.save();
    window.simulationCamera.applyTransform(previewCtx, canvas);
    previewCtx.setLineDash([8, 8]);
    previewCtx.lineCap = 'round';
    previewCtx.strokeStyle = 'rgba(91, 140, 255, 0.85)';
    previewCtx.lineWidth = 18 / window.simulationCamera.zoom;
    previewCtx.beginPath();
    previewCtx.moveTo(startWorld.x, startWorld.y);
    previewCtx.lineTo(currentWorld.x, currentWorld.y);
    previewCtx.stroke();
    previewCtx.restore();
};

document.querySelectorAll('.tool-btn').forEach((button) => {
    button.addEventListener('click', () => {
        document.querySelectorAll('.tool-btn').forEach((item) => item.classList.remove('active'));
        button.classList.add('active');
        activeTool = button.dataset.tool;
        const roadOptions = document.getElementById('roadOptions');
        if (roadOptions) {
            roadOptions.hidden = activeTool !== 'road';
        }
        if (activeTool === 'road' || activeTool === 'bus_stop') {
            canvas.style.cursor = 'crosshair';
        } else if (activeTool === 'spawn') {
            canvas.style.cursor = 'copy';
        } else {
            canvas.style.cursor = 'grab';
        }
        document.getElementById('cargoPanel').hidden = true;
    });
});

let selectedTruckId = null;

const getSpawnVehicleType = () => {
    const value = document.getElementById('spawnVehicleType')?.value || 'random';
    return value === 'random' ? undefined : value;
};

const showCargoPanel = (vehicle, catalog) => {
    const panel = document.getElementById('cargoPanel');
    const buttons = document.getElementById('cargoButtons');
    if (!panel || !buttons) return;
    selectedTruckId = vehicle.id;
    panel.hidden = false;
    const items = catalog || [
        { id: 'food', label: '식품' },
        { id: 'construction', label: '건설자재' },
        { id: 'fuel', label: '연료' },
        { id: 'general', label: '일반화물' },
    ];
    buttons.innerHTML = items.map((c) =>
        `<button type="button" class="btn btn-ghost btn-sm cargo-btn" data-cargo="${c.id}">${c.icon || ''} ${c.label}</button>`
    ).join('');
    buttons.querySelectorAll('.cargo-btn').forEach((btn) => {
        btn.onclick = async () => {
            await sendAction({
                action: 'classify_cargo',
                vehicle_id: selectedTruckId,
                cargo_type: btn.dataset.cargo,
            });
            panel.hidden = true;
        };
    });
};

canvas.addEventListener('click', (event) => {
    if (event.button !== 0) return;
    const point = getWorldPoint(event.clientX, event.clientY);

    if (activeTool === 'spawn') {
        sendAction({
            action: 'spawn_vehicle',
            vehicle_type: getSpawnVehicleType(),
            world: { x: point.x, y: point.y },
        });
        return;
    }

    if (activeTool === 'bus_stop') {
        sendAction({
            action: 'add_bus_stop',
            world: { x: point.x, y: point.y },
        });
        return;
    }

    if (activeTool === 'inspect') {
        const state = window.canvasRenderer?.lastState;
        const vehicles = state?.vehicles || [];
        let nearest = null;
        let best = 36 / (window.simulationCamera?.zoom || 1);
        vehicles.forEach((v) => {
            const d = Math.hypot(v.x - point.x, v.y - point.y);
            if (d < best) {
                best = d;
                nearest = v;
            }
        });
        const panel = document.getElementById('inspectInfo');
        if (nearest) {
            const tons = ((nearest.mass_kg || 1000) / 1000).toFixed(1);
            const vol = Math.round(nearest.volume || 0);
            const occ = Number(nearest.space_occupancy || 1).toFixed(1);
            let extra = '';
            if (nearest.type === 'truck') {
                extra = nearest.cargo_classified === false
                    ? ' · 화물 미분류'
                    : ` · 화물 ${nearest.cargo_type || '-'}`;
            }
            if (nearest.type === 'bus' && nearest.bus_dwell_remaining > 0) {
                extra = ' · 정류장 정차중';
            }
            const text = `#${nearest.id} ${nearest.type || 'car'} · ${nearest.speed} · ${tons}t · 부피 ${vol} · 점유 ${occ}${extra}`;
            window.uiBridge?.showToast(text, 'info');
            if (panel) {
                panel.hidden = false;
                panel.textContent = text;
            }
            if (nearest.type === 'truck' && nearest.cargo_classified === false) {
                showCargoPanel(nearest, state.cargo_catalog);
            } else {
                document.getElementById('cargoPanel').hidden = true;
            }
        } else if (panel) {
            panel.hidden = true;
            panel.textContent = '';
            document.getElementById('cargoPanel').hidden = true;
        }
    }
});

canvas.addEventListener('mousedown', (event) => {
    if (activeTool !== 'road' || event.button !== 0) return;
    const point = getWorldPoint(event.clientX, event.clientY);
    isDrawing = true;
    startWorld = point;
    currentWorld = point;
});

canvas.addEventListener('mousemove', (event) => {
    if (!isDrawing) return;
    currentWorld = getWorldPoint(event.clientX, event.clientY);
    drawPreview();
});

canvas.addEventListener('mouseup', (event) => {
    if (!isDrawing || activeTool !== 'road' || event.button !== 0) return;

    const endWorld = getWorldPoint(event.clientX, event.clientY);
    isDrawing = false;

    const distance = Math.hypot(endWorld.x - startWorld.x, endWorld.y - startWorld.y);
    if (distance < 24) {
        // 의도치 않은 짧은 클릭은 조용히 무시 (드래그 시작만 한 경우)
        if (distance > 6) {
            window.uiBridge?.showToast('도로가 너무 짧습니다. 조금 더 길게 드래그하세요.', 'warning');
        }
        return;
    }

    const lanesEl = document.getElementById('roadLanes');
    const bidirEl = document.getElementById('roadBidirectional');
    const lanes = Number(lanesEl?.value || 2);
    const bidirectional = Boolean(bidirEl?.checked);

    sendAction({
        action: 'add_road',
        data: {
            start: [startWorld.x, startWorld.y],
            end: [endWorld.x, endWorld.y],
            lanes,
            bidirectional,
        },
    });

    document.getElementById('canvasHint').style.display = 'none';
});

window.uiController = {
    getActiveTool() {
        return activeTool;
    },

    setPreviewState(state) {
        previewState = state;
        if (isDrawing) {
            drawPreview();
        }
    },

    bindControls() {
        document.getElementById('pauseBtn').addEventListener('click', () => {
            sendAction({ action: 'toggle_pause' });
        });

        document.getElementById('resetBtn').addEventListener('click', () => {
            if (window.confirm('도로와 차량, 이벤트를 모두 초기화할까요?')) {
                sendAction({ action: 'reset_simulation' });
                document.getElementById('canvasHint').style.display = 'block';
                window.canvasRenderer._didInitialFit = false;
                window.simulationCamera.reset(canvas);
            }
        });

        document.getElementById('clearEventsBtn').addEventListener('click', () => {
            sendAction({ action: 'clear_events' });
        });

        document.getElementById('spawnRate').addEventListener('input', (event) => {
            sendAction({ action: 'set_spawn_rate', rate: Number(event.target.value) / 100 });
        });

        document.getElementById('autoSpawnToggle')?.addEventListener('change', (event) => {
            sendAction({ action: 'set_auto_spawn', enabled: event.target.checked });
        });

        document.getElementById('spawnVehicleBtn')?.addEventListener('click', () => {
            sendAction({ action: 'spawn_vehicle', vehicle_type: getSpawnVehicleType() });
        });

        document.getElementById('logoutBtn')?.addEventListener('click', async () => {
            await fetch('/api/auth/logout', { method: 'POST' });
            window.location.href = '/login';
        });

        document.getElementById('cameraFitBtn')?.addEventListener('click', () => {
            if (window.canvasRenderer.lastState) {
                window.simulationCamera.fitToState(window.canvasRenderer.lastState, canvas);
                window.canvasRenderer.render(window.canvasRenderer.lastState);
            }
        });

        document.getElementById('cameraResetBtn')?.addEventListener('click', () => {
            window.simulationCamera.reset(canvas);
            if (window.canvasRenderer.lastState) {
                window.canvasRenderer.render(window.canvasRenderer.lastState);
            }
        });

        document.getElementById('cameraZoomInBtn')?.addEventListener('click', () => {
            window.simulationCamera.zoomAt(canvas.width / 2, canvas.height / 2, canvas, 1.15);
            if (window.canvasRenderer.lastState) {
                window.canvasRenderer.render(window.canvasRenderer.lastState);
            }
        });

        document.getElementById('cameraZoomOutBtn')?.addEventListener('click', () => {
            window.simulationCamera.zoomAt(canvas.width / 2, canvas.height / 2, canvas, 0.87);
            if (window.canvasRenderer.lastState) {
                window.canvasRenderer.render(window.canvasRenderer.lastState);
            }
        });

        document.getElementById('dispatchPoliceBtn')?.addEventListener('click', () => {
            sendAction({ action: 'dispatch_police' });
        });
        document.getElementById('dispatchTowBtn')?.addEventListener('click', () => {
            sendAction({ action: 'dispatch_tow' });
        });
        document.getElementById('clearAccidentsBtn')?.addEventListener('click', () => {
            sendAction({ action: 'clear_accidents' });
        });
    },

    renderEventButtons(catalog) {
        const container = document.getElementById('eventButtons');
        container.innerHTML = '';

        catalog.forEach((item) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = `event-btn${item.severity === 'premium' ? ' premium' : ''}`;
            button.textContent = `${item.icon} ${item.label}`;
            button.addEventListener('click', () => {
                sendAction({
                    action: 'trigger_event',
                    event_type: item.type,
                    message: `${item.label} 수동 발생`,
                });
            });
            container.appendChild(button);
        });
    },

    updateAccidentStatus(state) {
        const el = document.getElementById('accidentStatus');
        if (!el) return;
        const open = state.stats?.open_accidents ?? state.accidents?.open_accidents ?? 0;
        const queue = state.accidents?.rescue_queue || [];
        let extra = '';
        if (queue.length) {
            const job = queue[0];
            const label = job.mode === 'tow' ? '견인' : '경찰';
            extra = ` · ${label} ETA ${job.eta}s`;
        }
        el.textContent = `사고 현장: ${open}건${extra}`;
        el.classList.toggle('has-accident', open > 0);
    },
};

window.uiController.bindControls();
window.simulationCamera.bind(canvas);
