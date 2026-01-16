(function() {
    const root = document.documentElement;
    const saved = localStorage.getItem('theme');
    if (saved) {
        root.setAttribute('data-theme', saved);
    }
    const toggle = document.querySelector('[data-action="toggle-theme"]');
    const applyTheme = (theme) => {
        root.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    };
    if (toggle) {
        toggle.addEventListener('click', () => {
            const current = root.getAttribute('data-theme') || 'light';
            applyTheme(current === 'light' ? 'dark' : 'light');
            renderCandleCharts();
        });
    }

    function bindTabButtons() {
        const tabs = document.querySelectorAll('.tab-button[data-tab-name]');
        if (!tabs.length) return;
        tabs.forEach((btn) => {
            if (btn.dataset.bound === 'true') return;
            btn.dataset.bound = 'true';
            btn.addEventListener('click', () => {
                tabs.forEach((b) => {
                    b.classList.remove('is-active');
                    b.setAttribute('aria-pressed', 'false');
                });
                btn.classList.add('is-active');
                btn.setAttribute('aria-pressed', 'true');
            });
        });
    }

    const getColors = () => {
        const styles = getComputedStyle(document.documentElement);
        return {
            text: styles.getPropertyValue('--text').trim() || '#e5e7eb',
            muted: styles.getPropertyValue('--muted').trim() || '#9ca3af',
            positive: styles.getPropertyValue('--positive').trim() || '#22c55e',
            negative: styles.getPropertyValue('--negative').trim() || '#ef4444',
            neutral: styles.getPropertyValue('--neutral').trim() || '#94a3b8',
            border: styles.getPropertyValue('--border').trim() || '#1f2937',
            panel: styles.getPropertyValue('--panel').trim() || '#111827',
            chartGrid: styles.getPropertyValue('--chart-grid').trim() || 'rgba(255, 255, 255, 0.08)',
            chartCrosshair: styles.getPropertyValue('--chart-crosshair').trim() || 'rgba(255, 255, 255, 0.3)',
            gradientFrom: styles.getPropertyValue('--chart-gradient-from').trim() || 'rgba(14, 165, 233, 0.15)',
            gradientTo: styles.getPropertyValue('--chart-gradient-to').trim() || 'rgba(14, 165, 233, 0.0)',
        };
    };

    const fmtPrice = (val) => {
        if (val === null || val === undefined || isNaN(val)) return 'N/A';
        return `¥${Number(val).toLocaleString('ja-JP', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`;
    };
    const fmtVolume = (val) => (val === null || val === undefined || isNaN(val) ? 'N/A' : Number(val).toLocaleString('ja-JP'));

    function renderCandleCharts() {
        const wrappers = document.querySelectorAll('[data-chart-payload]');
        wrappers.forEach((wrapper) => {
            const payloadRaw = wrapper.getAttribute('data-chart-payload');
            const colors = getColors();
            const canvas = wrapper.querySelector('.candle-canvas');
            const tooltip = wrapper.querySelector('.chart-tooltip');
            if (!payloadRaw || !canvas || !tooltip) return;

            let payload;
            try {
                payload = JSON.parse(payloadRaw);
            } catch (_) {
                return;
            }
            const points = payload.points || [];
            const levels = payload.support_levels || [];
            const dpr = window.devicePixelRatio || 1;
            const displayWidth = wrapper.clientWidth - 16;
            const displayHeight = parseInt(canvas.getAttribute('height'), 10) || 420;
            const width = displayWidth;
            const height = displayHeight;
            canvas.width = width * dpr;
            canvas.height = height * dpr;
            canvas.style.width = `${width}px`;
            canvas.style.height = `${height}px`;
            const ctx = canvas.getContext('2d');
            if (!ctx) return;
            ctx.scale(dpr, dpr);
            ctx.clearRect(0, 0, width, height);

            if (!points.length) {
                ctx.fillStyle = colors.muted;
                ctx.font = '14px "Segoe UI", sans-serif';
                ctx.fillText('チャートデータがありません', 12, 24);
                return;
            }

            const highs = points.map((p) => p.high);
            const lows = points.map((p) => p.low);
            const volumes = points.map((p) => p.volume || 0);
            const maxHigh = Math.max(...highs);
            const minLow = Math.min(...lows);
            const pad = Math.max(1, (maxHigh - minLow) * 0.05);
            const yMin = minLow - pad;
            const yMax = maxHigh + pad;
            const priceAreaHeight = height * 0.7;
            const priceTop = 8;
            const priceBottom = priceTop + priceAreaHeight;
            const volumeAreaHeight = height * 0.22;
            const volumeTop = priceBottom + 6;
            const chartLeft = 50;
            const chartRight = width - 12;
            const chartWidth = chartRight - chartLeft;
            const barCount = points.length;
            const step = chartWidth / barCount;
            const candleWidth = Math.max(4, step * 0.6);

            const yScale = (val) => {
                const ratio = (val - yMin) / (yMax - yMin);
                return priceBottom - ratio * (priceAreaHeight - 16);
            };

            ctx.strokeStyle = colors.border;
            ctx.lineWidth = 1;
            ctx.font = '12px "Segoe UI", sans-serif';
            ctx.fillStyle = colors.text;

            // Y axis ticks
            // Grid & Ticks
            const ticks = 5;
            ctx.textAlign = 'left';
            ctx.textBaseline = 'middle';
            
            for (let i = 0; i <= ticks; i++) {
                const value = yMin + ((yMax - yMin) * i) / ticks;
                const y = priceBottom - ((priceAreaHeight - 16) * i) / ticks;

                // Grid line
                ctx.strokeStyle = colors.chartGrid;
                ctx.setLineDash([4, 4]);
                ctx.beginPath();
                ctx.moveTo(chartLeft, y);
                ctx.lineTo(chartRight, y);
                ctx.stroke();
                ctx.setLineDash([]);

                // Tick label
                ctx.fillStyle = colors.muted;
                ctx.fillText(value.toFixed(1), 4, y);
            }

            // X axis ticks
            // X axis ticks
            const xTicks = Math.min(6, barCount);
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';

            for (let i = 0; i < xTicks; i++) {
                const idx = Math.floor((barCount - 1) * (i / (xTicks - 1 || 1)));
                const point = points[idx];
                const x = chartLeft + idx * step + step / 2;
                
                // Grid line
                ctx.strokeStyle = colors.chartGrid;
                ctx.setLineDash([4, 4]);
                ctx.beginPath();
                ctx.moveTo(x, priceTop);
                ctx.lineTo(x, priceBottom);
                ctx.stroke();
                ctx.setLineDash([]);

                ctx.fillStyle = colors.muted;
                ctx.fillText(point.label, x, height - 20);
            }

            // Support / resistance lines
            levels.forEach((lvl) => {
                const y = yScale(lvl.value);
                ctx.setLineDash([6, 4]);
                ctx.strokeStyle = lvl.type === 'support' ? colors.positive : lvl.type === 'resistance' ? colors.negative : colors.neutral;
                ctx.beginPath();
                ctx.moveTo(chartLeft, y);
                ctx.lineTo(chartRight, y);
                ctx.stroke();
                ctx.setLineDash([]);
            });

            // Candles
            points.forEach((p, idx) => {
                const xCenter = chartLeft + idx * step + step / 2;
                const openY = yScale(p.open);
                const closeY = yScale(p.close);
                const highY = yScale(p.high);
                const lowY = yScale(p.low);
                const isUp = p.close >= p.open;
                ctx.strokeStyle = isUp ? colors.positive : colors.negative;
                ctx.fillStyle = isUp ? colors.positive : colors.negative;

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

            // Volume bars
            // Volume bars
            const maxVolume = Math.max(...volumes) || 1;
            
            // Gradient for volume
            const vGradient = ctx.createLinearGradient(0, volumeTop, 0, volumeTop + volumeAreaHeight);
            vGradient.addColorStop(0, colors.gradientFrom);
            vGradient.addColorStop(1, colors.gradientTo);
            
            points.forEach((p, idx) => {
                const xCenter = chartLeft + idx * step + step / 2;
                const barHeight = ((p.volume || 0) / maxVolume) * volumeAreaHeight;
                const isUp = p.close >= p.open;
                
                ctx.fillStyle = isUp ? colors.positive : colors.negative;
                ctx.globalAlpha = 0.2; // base opacity
                ctx.fillRect(xCenter - candleWidth / 2, volumeTop + (volumeAreaHeight - barHeight), candleWidth, Math.max(2, barHeight));
                
                // Gradient overlay
                ctx.fillStyle = vGradient;
                ctx.globalAlpha = 0.3;
                ctx.fillRect(xCenter - candleWidth / 2, volumeTop + (volumeAreaHeight - barHeight), candleWidth, Math.max(2, barHeight));
                
                ctx.globalAlpha = 1;
            });

            function showTooltip(evt) {
                const rect = canvas.getBoundingClientRect();
                const x = (evt.clientX - rect.left) * (width / rect.width);
                const y = (evt.clientY - rect.top) * (height / rect.height);
                
                const idx = Math.min(points.length - 1, Math.max(0, Math.floor((x - chartLeft) / step)));
                const point = points[idx];
                if (!point) return;
                
                // ... Tooltip Content Generation ...
                const nearLevels = (levels || []).filter((lvl) => Math.abs(point.close - lvl.value) <= (yMax - yMin) * 0.01);
                let html = '';
                html += `<div class="row"><span>譎る俣</span><span>${point.label}</span></div>`;
                html += `<div class="row"><span>蟋句€､</span><span>${fmtPrice(point.open)}</span></div>`;
                html += `<div class="row"><span>鬮伜€､</span><span>${fmtPrice(point.high)}</span></div>`;
                html += `<div class="row"><span>螳牙€､</span><span>${fmtPrice(point.low)}</span></div>`;
                html += `<div class="row"><span>邨ょ€､</span><span>${fmtPrice(point.close)}</span></div>`;
                html += `<div class="row"><span>蜃ｺ譚･鬮・/span><span>${fmtVolume(point.volume)}</span></div>`;
                if (point.pattern) html += `<div class="row"><span>雜ｳ繝代ち繝ｼ繝ｳ</span><span>${point.pattern}</span></div>`;
                
                 nearLevels.forEach((lvl) => {
                    html += `<div class="row"><span>${lvl.label}</span><span>¥${Number(lvl.value).toLocaleString('ja-JP', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} / ${lvl.note}</span></div>`;
                });

                tooltip.innerHTML = html;
                tooltip.style.display = 'block';
                
                // Smart Positioning
                const wrapRect = wrapper.getBoundingClientRect();
                const tWidth = tooltip.offsetWidth || 220;
                const tHeight = tooltip.offsetHeight || 160;
                
                // Default: Top Left fixed if not obscuring
                // Or follow mouse but flip if too close to edge
                
                let left = evt.clientX - wrapRect.left + 20;
                let top = evt.clientY - wrapRect.top + 20;
                
                if (left + tWidth > wrapRect.width) left = evt.clientX - wrapRect.left - tWidth - 20;
                if (top + tHeight > wrapRect.height) top = evt.clientY - wrapRect.top - tHeight - 20;
                
                // Clamp
                left = Math.max(10, Math.min(left, wrapRect.width - tWidth - 10));
                top = Math.max(10, Math.min(top, wrapRect.height - tHeight - 10));
                
                tooltip.style.transform = `translate(${left}px, ${top}px)`;
            }

            function hideTooltip() {
                tooltip.style.display = 'none';
            }

            canvas.onmousemove = showTooltip;
            canvas.onmouseleave = hideTooltip;
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        bindTabButtons();
        renderCandleCharts();
        initPatternPage();
    });
    document.addEventListener('htmx:afterSwap', () => {
        bindTabButtons();
        renderCandleCharts();
        initPatternPage();
    });
})(); 

function initPatternPage() {
    initPatternTabs();
    initPatternModal();
}

function animateCountBadges(scope = document) {
    const badges = scope.querySelectorAll('.count-badge[data-count-target]');
    badges.forEach((badge) => {
        const target = Number.parseInt(badge.dataset.countTarget || '0', 10);
        if (Number.isNaN(target)) return;
        const duration = 450;
        const start = performance.now();
        badge.textContent = '0';
        const tick = (now) => {
            const progress = Math.min((now - start) / duration, 1);
            const value = Math.floor(target * progress);
            badge.textContent = String(value);
            if (progress < 1) {
                requestAnimationFrame(tick);
            } else {
                badge.textContent = String(target);
            }
        };
        requestAnimationFrame(tick);
    });
}

function initPatternTabs() {
    const tabs = document.querySelectorAll('.pattern-tab');
    if (!tabs.length) return;
    const setActive = (active) => {
        tabs.forEach((tab) => {
            const isActive = tab === active;
            tab.classList.toggle('is-active', isActive);
            tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
            tab.setAttribute('tabindex', isActive ? '0' : '-1');
        });
    };
    tabs.forEach((tab) => {
        if (tab.dataset.bound === 'true') return;
        tab.dataset.bound = 'true';
        tab.addEventListener('click', () => {
            setActive(tab);
            animateCountBadges();
        });
    });
    animateCountBadges();
}

function initPatternModal() {
    const overlay = document.querySelector('[data-modal-overlay]');
    if (!overlay) return;
    const modal = overlay.querySelector('.pattern-modal');
    const closeBtn = overlay.querySelector('[data-close-modal]');
    const imgEl = overlay.querySelector('[data-modal-image]');
    const nameEl = overlay.querySelector('[data-modal-name]');
    const catchEl = overlay.querySelector('[data-modal-catch]');
    const descLeadEl = overlay.querySelector('[data-modal-desc-lead]');
    const descBodyEl = overlay.querySelector('[data-modal-desc-body]');
    const detailEl = overlay.querySelector('[data-modal-detail]');
    const sceneEl = overlay.querySelector('[data-modal-scene]');
    const howtoEl = overlay.querySelector('[data-modal-howto]');
    const notesEl = overlay.querySelector('[data-modal-notes]');

    let lastFocus = null;

    const close = () => {
        overlay.classList.remove('is-open');
        overlay.hidden = true;
        if (lastFocus) lastFocus.focus();
    };

    const open = (btn) => {
        lastFocus = btn;
        overlay.hidden = false;
        overlay.classList.add('is-open');
        nameEl.textContent = btn.dataset.name || '';
        catchEl.textContent = btn.dataset.catch || '';
        descLeadEl.textContent = btn.dataset.descLead || '';
        descBodyEl.textContent = btn.dataset.descBody || '';
        detailEl.textContent = btn.dataset.detail || '';
        sceneEl.textContent = btn.dataset.scene || '';
        howtoEl.textContent = btn.dataset.howto || '';
        if (btn.dataset.svg) {
            imgEl.src = btn.dataset.svg;
            imgEl.alt = btn.dataset.name || '';
        }
        notesEl.innerHTML = '';
        const notes = (btn.dataset.notes || '').split('||').filter(Boolean);
        notes.forEach((n) => {
            const li = document.createElement('li');
            li.textContent = n;
            notesEl.appendChild(li);
        });
    };

    document.querySelectorAll('.pattern-detail-trigger').forEach((btn) => {
        btn.addEventListener('click', () => open(btn));
    });
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) close();
    });
    if (closeBtn) closeBtn.addEventListener('click', close);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && overlay.classList.contains('is-open')) {
            close();
        }
    });
}
