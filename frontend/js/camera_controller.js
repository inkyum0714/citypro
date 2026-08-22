/** Phase 5: 월드 좌표 ↔ 화면 변환 및 카메라 조작. */
window.simulationCamera = {
    x: 480,
    y: 320,
    zoom: 1,
    minZoom: 0.15,
    maxZoom: 4,
    isPanning: false,
    panStartScreen: { x: 0, y: 0 },
    panStartCamera: { x: 0, y: 0 },

    clampZoom(value) {
        return Math.max(this.minZoom, Math.min(this.maxZoom, value));
    },

    screenToWorld(screenX, screenY, canvas) {
        return {
            x: (screenX - canvas.width / 2) / this.zoom + this.x,
            y: (screenY - canvas.height / 2) / this.zoom + this.y,
        };
    },

    worldToScreen(worldX, worldY, canvas) {
        return {
            x: (worldX - this.x) * this.zoom + canvas.width / 2,
            y: (worldY - this.y) * this.zoom + canvas.height / 2,
        };
    },

    worldBounds(canvas, pad = 48) {
        const topLeft = this.screenToWorld(-pad, -pad, canvas);
        const bottomRight = this.screenToWorld(canvas.width + pad, canvas.height + pad, canvas);
        return {
            minX: Math.min(topLeft.x, bottomRight.x),
            maxX: Math.max(topLeft.x, bottomRight.x),
            minY: Math.min(topLeft.y, bottomRight.y),
            maxY: Math.max(topLeft.y, bottomRight.y),
        };
    },

    applyTransform(ctx, canvas) {
        ctx.translate(canvas.width / 2, canvas.height / 2);
        ctx.scale(this.zoom, this.zoom);
        ctx.translate(-this.x, -this.y);
    },

    zoomAt(screenX, screenY, canvas, factor) {
        const before = this.screenToWorld(screenX, screenY, canvas);
        this.zoom = this.clampZoom(this.zoom * factor);
        const after = this.screenToWorld(screenX, screenY, canvas);
        this.x += before.x - after.x;
        this.y += before.y - after.y;
    },

    fitToState(state, canvas) {
        const roads = state?.roads || [];
        const nodes = state?.nodes || [];
        let minX = Infinity;
        let minY = Infinity;
        let maxX = -Infinity;
        let maxY = -Infinity;

        const include = (x, y) => {
            minX = Math.min(minX, x);
            minY = Math.min(minY, y);
            maxX = Math.max(maxX, x);
            maxY = Math.max(maxY, y);
        };

        roads.forEach((road) => {
            include(road.start[0], road.start[1]);
            include(road.end[0], road.end[1]);
        });
        nodes.forEach((node) => include(node.x, node.y));

        if (!Number.isFinite(minX)) {
            this.x = canvas.width / 2;
            this.y = canvas.height / 2;
            this.zoom = 1;
            return;
        }

        const pad = 80;
        minX -= pad;
        minY -= pad;
        maxX += pad;
        maxY += pad;
        const worldW = Math.max(maxX - minX, 120);
        const worldH = Math.max(maxY - minY, 120);
        this.x = (minX + maxX) / 2;
        this.y = (minY + maxY) / 2;
        this.zoom = this.clampZoom(
            Math.min(canvas.width / worldW, canvas.height / worldH) * 0.92,
        );
    },

    reset(canvas) {
        this.x = canvas.width / 2;
        this.y = canvas.height / 2;
        this.zoom = 1;
    },

    bind(canvas) {
        canvas.addEventListener(
            'wheel',
            (event) => {
                event.preventDefault();
                const rect = canvas.getBoundingClientRect();
                const sx = event.clientX - rect.left;
                const sy = event.clientY - rect.top;
                const factor = event.deltaY > 0 ? 0.9 : 1.1;
                this.zoomAt(sx, sy, canvas, factor);
            },
            { passive: false },
        );

        const startPan = (event) => {
            const panButton = event.button === 1 || event.button === 2;
            const inspectPan = event.button === 0 && window.uiController?.getActiveTool?.() === 'inspect';
            if (!panButton && !inspectPan) return;
            if (event.button === 0 && window.uiController?.getActiveTool?.() === 'road') return;
            event.preventDefault();
            this.isPanning = true;
            const rect = canvas.getBoundingClientRect();
            this.panStartScreen = { x: event.clientX - rect.left, y: event.clientY - rect.top };
            this.panStartCamera = { x: this.x, y: this.y };
            canvas.style.cursor = 'grabbing';
        };

        const movePan = (event) => {
            if (!this.isPanning) return;
            const rect = canvas.getBoundingClientRect();
            const sx = event.clientX - rect.left;
            const sy = event.clientY - rect.top;
            const dx = sx - this.panStartScreen.x;
            const dy = sy - this.panStartScreen.y;
            this.x = this.panStartCamera.x - dx / this.zoom;
            this.y = this.panStartCamera.y - dy / this.zoom;
        };

        const endPan = () => {
            if (!this.isPanning) return;
            this.isPanning = false;
            const tool = window.uiController?.getActiveTool?.() || 'road';
            if (tool === 'road') canvas.style.cursor = 'crosshair';
            else if (tool === 'spawn') canvas.style.cursor = 'copy';
            else canvas.style.cursor = 'grab';
        };

        canvas.addEventListener('mousedown', startPan);
        window.addEventListener('mousemove', movePan);
        window.addEventListener('mouseup', endPan);
        canvas.addEventListener('contextmenu', (e) => e.preventDefault());
    },
};
