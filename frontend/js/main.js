const weatherLabels = {
    clear: '맑음',
    rain: '폭우',
    fog: '안개',
};

const timeLabels = {
    day: '주간',
    rush_hour: '출퇴근 시간',
};

const formatSimTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
};

window.uiBridge = {
    showToast(message, severity = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${severity}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3200);
    },

    applySimulationState(state) {
        if (!state) return;
        const prev = this._mergedState;
        if (prev && state.snapshot === 'tick') {
            state = {
                ...prev,
                ...state,
                event_catalog: state.event_catalog || prev.event_catalog,
                rescue_catalog: state.rescue_catalog || prev.rescue_catalog,
                cargo_catalog: state.cargo_catalog || prev.cargo_catalog,
                analytics: {
                    ...(prev.analytics || {}),
                    ...(state.analytics || {}),
                    series: state.analytics?.series || prev.analytics?.series || [],
                },
                player: state.player || prev.player,
            };
        }
        this._mergedState = state;
        try {
            window.canvasRenderer?.render(state);
            window.uiController?.setPreviewState(state);
            this.updateDashboard(state);
            this.updateEvents(state);
            window.uiController?.updateAccidentStatus?.(state);
            window.analyticsPanel?.update(state);
            window.engagementPanel?.update(state);

            if (state.event_catalog && !window.uiController?.catalogRendered) {
                window.uiController.renderEventButtons(state.event_catalog);
                window.uiController.catalogRendered = true;
            }
        } catch (err) {
            console.error('state render failed', err);
        }
    },

    async refreshSimulationState() {
        try {
            const res = await fetch('/api/state');
            if (!res.ok) return;
            const state = await res.json();
            this.applySimulationState(state);
        } catch {
            /* ignore */
        }
    },

    updateDashboard(state) {
        const stats = state.stats || {};
        document.getElementById('activeVehicles').textContent = stats.active_vehicles ?? 0;
        document.getElementById('totalCompleted').textContent = stats.total_completed ?? 0;
        document.getElementById('roadCount').textContent = stats.road_count ?? 0;
        document.getElementById('activeEvents').textContent = stats.active_events ?? 0;
        document.getElementById('simTimeLabel').textContent = formatSimTime(stats.sim_time || 0);
        document.getElementById('weatherLabel').textContent = weatherLabels[state.weather] || '맑음';
        document.getElementById('timeLabel').textContent = timeLabels[state.time_of_day] || '주간';

        const congestion = Math.round((stats.congestion_level || 0) * 100);
        document.getElementById('congestionValue').textContent = `${congestion}%`;
        document.getElementById('congestionFill').style.width = `${congestion}%`;

        document.getElementById('pauseBtn').textContent = stats.is_paused ? '▶ 재개' : '⏸ 일시정지';
        const autoSpawn = document.getElementById('autoSpawnToggle');
        if (autoSpawn && typeof stats.auto_spawn_enabled === 'boolean') {
            autoSpawn.checked = stats.auto_spawn_enabled;
        }
        document.getElementById('statusLine').textContent = stats.is_paused
            ? '시뮬레이션이 일시정지되었습니다.'
            : `실시간 운행 중 · 차량 ${stats.active_vehicles ?? 0}대`;
    },

    updateEvents(state) {
        const activeList = document.getElementById('activeEventList');
        const events = state.events || [];

        if (!events.length) {
            activeList.innerHTML = '<li class="event-empty">현재 이벤트 없음</li>';
        } else {
            activeList.innerHTML = events.map((event) => `
                <li class="severity-${event.severity}">
                    ${event.icon} <strong>${event.label}</strong><br>
                    ${event.message}<br>
                    <span style="color:#94a3b8">남은 시간 ${event.remaining}s</span>
                </li>
            `).join('');
        }

        const log = document.getElementById('eventLog');
        const entries = state.event_log || [];
        if (!entries.length) {
            log.innerHTML = '<li class="event-empty">아직 기록된 이벤트가 없습니다</li>';
        } else {
            log.innerHTML = entries.map((entry) => `
                <li class="severity-${entry.severity}">
                    ${entry.icon} ${entry.message}
                </li>
            `).join('');
        }
    },
};

let wsReconnectTimer = null;

const connectSimulationSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    const socket = new WebSocket(wsUrl);
    window.simulationSocket = socket;

    socket.addEventListener('open', () => {
        window.uiBridge.showToast('CityFlow 서버에 연결되었습니다.', 'info');
        document.getElementById('statusLine').textContent = '서버 연결 완료';
        if (wsReconnectTimer) {
            clearTimeout(wsReconnectTimer);
            wsReconnectTimer = null;
        }
    });

    socket.addEventListener('message', (event) => {
        let payload;
        try {
            payload = JSON.parse(event.data);
        } catch {
            return;
        }

        if (payload.type === 'error') {
            window.uiBridge.showToast(payload.data?.message || '연결 오류', 'warning');
            return;
        }

        if (payload.type === 'state') {
            window.uiBridge.applySimulationState(payload.data);
        }

        if (payload.type === 'action_result' && payload.data?.message) {
            const severity = payload.data.ok ? 'info' : 'warning';
            window.uiBridge.showToast(payload.data.message, severity);
            if (payload.data.player) {
                window.engagementPanel?.applyPlayer(payload.data.player);
            }
        }
    });

    socket.addEventListener('close', () => {
        window.uiBridge.showToast('실시간 연결이 끊어졌습니다. REST로 동기화합니다.', 'warning');
        wsReconnectTimer = setTimeout(connectSimulationSocket, 3000);
        window.uiBridge.refreshSimulationState();
    });

    socket.addEventListener('error', () => {
        window.uiBridge.showToast('WebSocket 연결 오류 — REST 모드', 'warning');
    });
};

window.addEventListener('DOMContentLoaded', () => {
    window.uiBridge.refreshSimulationState();
    connectSimulationSocket();
    setInterval(() => {
        if (!window.simulationSocket || window.simulationSocket.readyState !== WebSocket.OPEN) {
            window.uiBridge.refreshSimulationState();
        }
    }, 2000);
});
