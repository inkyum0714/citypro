const weatherKey = {
    clear: 'weather.clear',
    rain: 'weather.rain',
    fog: 'weather.fog',
};

const timeKey = {
    day: 'time.day',
    rush_hour: 'time.rush_hour',
};

const eventLabel = (event) => window.t(`event.${event.type}.label`, event.label || '');

const eventMessage = (event) => {
    const label = eventLabel(event);
    const raw = event.message || '';
    if (raw.includes('수동') || /triggered/i.test(raw)) return window.t('events.manual', { label });
    return window.t('events.occurred', { label });
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
        window.clientSim?.ingest(state);
        const merged = window.clientSim?.getState?.() || state;
        this._mergedState = merged;
        try {
            if (!window.clientSim) {
                window.canvasRenderer?.render(merged);
            }
            window.uiController?.setPreviewState(merged);
            this.updateDashboard(merged);
            this.updateEvents(merged);
            window.uiController?.updateAccidentStatus?.(merged);
            window.analyticsPanel?.update(merged);
            window.engagementPanel?.update(merged);

            if (merged.event_catalog && !window.uiController?.catalogRendered) {
                window.uiController.renderEventButtons(merged.event_catalog);
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
        document.getElementById('weatherLabel').textContent = window.t(weatherKey[state.weather] || 'weather.clear');
        document.getElementById('timeLabel').textContent = window.t(timeKey[state.time_of_day] || 'time.day');

        const congestion = Math.round((stats.congestion_level || 0) * 100);
        document.getElementById('congestionValue').textContent = `${congestion}%`;
        document.getElementById('congestionFill').style.width = `${congestion}%`;

        document.getElementById('pauseBtn').textContent = stats.is_paused
            ? window.t('nav.resume')
            : window.t('nav.pause');
        const autoSpawn = document.getElementById('autoSpawnToggle');
        if (autoSpawn && typeof stats.auto_spawn_enabled === 'boolean') {
            autoSpawn.checked = stats.auto_spawn_enabled;
        }
        document.getElementById('statusLine').textContent = stats.is_paused
            ? window.t('status.paused')
            : window.t('status.running', { n: stats.active_vehicles ?? 0 });
    },

    updateEvents(state) {
        const activeList = document.getElementById('activeEventList');
        const events = state.events || [];

        if (!events.length) {
            activeList.innerHTML = `<li class="event-empty">${window.t('events.empty')}</li>`;
        } else {
            activeList.innerHTML = events.map((event) => `
                <li class="severity-${event.severity}">
                    ${event.icon} <strong>${eventLabel(event)}</strong><br>
                    ${eventMessage(event)}<br>
                    <span style="color:#94a3b8">${window.t('events.remaining', { s: event.remaining })}</span>
                </li>
            `).join('');
        }

        const log = document.getElementById('eventLog');
        const entries = state.event_log || [];
        if (!entries.length) {
            log.innerHTML = `<li class="event-empty">${window.t('events.none_logged')}</li>`;
        } else {
            log.innerHTML = entries.map((entry) => `
                <li class="severity-${entry.severity}">
                    ${entry.icon} ${eventMessage(entry)}
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
        window.uiBridge.showToast(window.t('toast.connected'), 'info');
        document.getElementById('statusLine').textContent = window.t('status.connected');
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
            window.uiBridge.showToast(payload.data?.message || window.t('toast.conn_error'), 'warning');
            return;
        }

        if (payload.type === 'state') {
            window.uiBridge.applySimulationState(payload.data);
        }

        if (payload.type === 'action_result' && payload.data?.message && !payload.data.silent) {
            const severity = payload.data.ok ? 'info' : 'warning';
            window.uiBridge.showToast(payload.data.message, severity);
            if (payload.data.player) {
                window.engagementPanel?.applyPlayer(payload.data.player);
            }
        }
    });

    socket.addEventListener('close', () => {
        window.uiBridge.showToast(window.t('toast.ws_lost'), 'warning');
        wsReconnectTimer = setTimeout(connectSimulationSocket, 3000);
        window.uiBridge.refreshSimulationState();
    });

    socket.addEventListener('error', () => {
        window.uiBridge.showToast(window.t('toast.ws_error'), 'warning');
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
