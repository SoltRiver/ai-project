(function() {
    const root = document.documentElement;
    const saved = localStorage.getItem('theme');
    if (saved) {
        root.setAttribute('data-theme', saved);
    }
    const toggle = document.querySelector('[data-action="toggle-theme"]');
    const apply = (theme) => {
        root.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    };
    if (toggle) {
        toggle.addEventListener('click', () => {
            const current = root.getAttribute('data-theme') || 'light';
            apply(current === 'light' ? 'dark' : 'light');
        });
    }

    function renderMiniCandles() {
        const canvases = document.querySelectorAll('.mini-candle-chart');
        canvases.forEach((canvas) => {
            const ctx = canvas.getContext('2d');
            const dataRaw = canvas.getAttribute('data-points');
            if (!ctx || !dataRaw) return;
            let points = [];
            try { points = JSON.parse(dataRaw); } catch (e) { return; }
            if (!points.length) return;

            const width = canvas.width;
            const height = canvas.height;
            ctx.clearRect(0, 0, width, height);

            const lows = points.map(p => p.low_raw);
            const highs = points.map(p => p.high_raw);
            const minVal = Math.min(...lows);
            const maxVal = Math.max(...highs);
            const pad = 10;
            const range = (maxVal - minVal) || 1;
            const step = width / points.length;
            const candleWidth = Math.max(4, step * 0.6);

            const yScale = (val) => {
                return height - pad - ((val - minVal) / range) * (height - pad * 2);
            };

            points.forEach((p, idx) => {
                const xCenter = idx * step + step / 2;
                const openY = yScale(p.open_raw);
                const closeY = yScale(p.close_raw);
                const highY = yScale(p.high_raw);
                const lowY = yScale(p.low_raw);
                const isUp = p.close_raw >= p.open_raw;
                ctx.strokeStyle = isUp ? '#22c55e' : '#ef4444';
                ctx.fillStyle = isUp ? '#22c55e' : '#ef4444';

                // wick
                ctx.beginPath();
                ctx.moveTo(xCenter, highY);
                ctx.lineTo(xCenter, lowY);
                ctx.stroke();

                // body
                const bodyTop = Math.min(openY, closeY);
                const bodyHeight = Math.max(2, Math.abs(closeY - openY));
                ctx.fillRect(xCenter - candleWidth / 2, bodyTop, candleWidth, bodyHeight);
            });
        });
    }

    document.addEventListener('DOMContentLoaded', renderMiniCandles);
    document.addEventListener('htmx:afterSwap', renderMiniCandles);
})();
