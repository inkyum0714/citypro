window.analyticsPanel = {
    update(state) {
        const analytics = state.analytics || {};
        const latest = analytics.latest || {};
        const summary = analytics.summary || {};

        const tp = document.getElementById('analyticsThroughput');
        const wait = document.getElementById('analyticsWait');
        const peak = document.getElementById('analyticsPeakCongestion');
        if (tp) tp.textContent = latest.throughput_per_min ?? '—';
        if (wait) wait.textContent = latest.avg_wait_seconds ?? '—';
        if (peak) peak.textContent = summary.peak_congestion ?? '—';

        this._drawChart(analytics.series || []);
    },

    _drawChart(series) {
        const canvas = document.getElementById('analyticsChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);
        if (!series.length) {
            ctx.fillStyle = '#64748b';
            ctx.font = '12px Inter, sans-serif';
            ctx.fillText(window.t('chart.collecting'), 12, h / 2);
            return;
        }

        const values = series.map((s) => s.throughput_per_min || 0);
        const maxV = Math.max(...values, 1);
        ctx.strokeStyle = 'rgba(91, 140, 255, 0.9)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        series.forEach((point, i) => {
            const x = 8 + (i / Math.max(series.length - 1, 1)) * (w - 16);
            const y = h - 8 - ((point.throughput_per_min || 0) / maxV) * (h - 16);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
    },
};
