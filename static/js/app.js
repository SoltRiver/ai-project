(function () {
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
            if (wrapper.dataset.chartInitialized === 'true') return;
            wrapper.dataset.chartInitialized = 'true';

            const payloadRaw = wrapper.getAttribute('data-chart-payload');
            const colors = getColors();
            const canvas = wrapper.querySelector('.candle-canvas');
            const tooltip = wrapper.querySelector('.chart-tooltip');
            const smaLegend = wrapper.querySelector('.sma-legend'); // New Legend Container

            if (!payloadRaw || !canvas || !tooltip) return;

            let payload;
            try {
                payload = JSON.parse(payloadRaw);
            } catch (_) {
                return;
            }
            const allPoints = payload.points || [];
            const levels = payload.support_levels || [];

            // Identify SMA keys dynamically & Sort
            const smaKeys = allPoints.length > 0
                ? Object.keys(allPoints[0]).filter(k => k.startsWith('SMA'))
                : [];

            // Sort SMAs to determine Short/Long for Crossovers
            // Extract number: SMA25 -> 25
            const smaNums = smaKeys.map(k => ({ key: k, num: parseInt(k.replace('SMA', ''), 10) }))
                .sort((a, b) => a.num - b.num);
            const sortedSmaKeys = smaNums.map(o => o.key);

            // Determine crossover pair (Short vs Med/Long)
            // Rule: Smallest vs Second Smallest (e.g. 25 vs 75, or 13 vs 26)
            let crossPair = null;
            if (sortedSmaKeys.length >= 2) {
                crossPair = { short: sortedSmaKeys[0], long: sortedSmaKeys[1] };
            }

            // SMA Colors (Reuse existing map)
            const smaColors = {
                'SMA25': '#f59e0b', // Amber
                'SMA75': '#8b5cf6', // Violet
                'SMA200': '#3b82f6', // Blue
                'SMA13': '#f59e0b',
                'SMA26': '#8b5cf6',
                'SMA52': '#3b82f6',
                'SMA5': '#ef4444',
                'SMA20': '#f59e0b',
                'SMA60': '#3b82f6'
            };

            // Pre-calculate Crosses
            const crosses = [];
            if (crossPair) {
                const k1 = crossPair.short;
                const k2 = crossPair.long;
                for (let i = 1; i < allPoints.length; i++) {
                    const prev1 = allPoints[i - 1][k1];
                    const prev2 = allPoints[i - 1][k2];
                    const curr1 = allPoints[i][k1];
                    const curr2 = allPoints[i][k2];

                    if (prev1 != null && prev2 != null && curr1 != null && curr2 != null) {
                        if (prev1 < prev2 && curr1 >= curr2) {
                            crosses.push({ index: i, type: 'golden', price: curr1, label: 'GC' });
                        } else if (prev1 > prev2 && curr1 <= curr2) {
                            crosses.push({ index: i, type: 'dead', price: curr1, label: 'DC' });
                        }
                    }
                }
            }

            function updateLegend(point) {
                if (!smaLegend) return;
                if (!sortedSmaKeys.length) {
                    smaLegend.innerHTML = '';
                    return;
                }

                let html = '';
                sortedSmaKeys.forEach(k => {
                    const val = point ? point[k] : null;
                    const color = smaColors[k] || colors.text;
                    const valStr = fmtPrice(val);
                    html += `<span class="sma-item" style="color:${color}"><span style="opacity:0.8">${k}</span> <span style="font-weight:700">${valStr}</span></span>`;
                });
                smaLegend.innerHTML = html;
            }

            // Init Legend with latest data
            if (allPoints.length > 0) {
                updateLegend(allPoints[allPoints.length - 1]);
            }

            // Viewport State
            let viewCount = Math.min(allPoints.length, 100);
            let viewIndex = Math.max(0, allPoints.length - viewCount);
            let isDragging = false;
            let lastX = 0;
            let dpr = window.devicePixelRatio || 1;
            let width, height;

            function updateDimensions() {
                const rect = wrapper.getBoundingClientRect();
                width = rect.width - 32;
                const attrHeight = parseInt(canvas.getAttribute('height'), 10) || 420;
                height = attrHeight;
                canvas.width = width * dpr;
                canvas.height = height * dpr;
                canvas.style.width = `${width}px`;
                canvas.style.height = `${height}px`;
            }
            updateDimensions();
            let ctx = canvas.getContext('2d');

            function draw() {
                if (!ctx) return;
                const endIndex = Math.min(allPoints.length, viewIndex + viewCount);
                const points = allPoints.slice(viewIndex, endIndex);

                if (!points.length) { // ... Empty handling ... 
                    ctx.clearRect(0, 0, width * dpr, height * dpr);
                    ctx.fillStyle = colors.muted;
                    ctx.font = '14px "Segoe UI", sans-serif';
                    ctx.fillText('データがありません', 20, 30);
                    return;
                }

                ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
                ctx.clearRect(0, 0, width, height);

                // Check Layout
                const priceAreaHeight = height * 0.7;
                const priceTop = 24; // Extra space for top icons
                const priceBottom = priceTop + priceAreaHeight;
                const volumeAreaHeight = height * 0.22;
                const volumeTop = priceBottom + 6;
                const chartLeft = 50;
                const chartRight = width - 12;
                const chartWidth = chartRight - chartLeft;
                const barCount = points.length;
                const step = chartWidth / Math.max(1, barCount);
                const candleWidth = Math.max(1, step * 0.65);

                const highs = points.map((p) => p.high);
                const lows = points.map((p) => p.low);
                sortedSmaKeys.forEach(key => {
                    points.forEach(p => { if (p[key] != null) { highs.push(p[key]); lows.push(p[key]); } });
                });

                const maxHigh = Math.max(...highs);
                const minLow = Math.min(...lows);
                const range = maxHigh - minLow;
                const pad = Math.max(1, range * 0.05);
                const yMin = minLow - pad;
                const yMax = maxHigh + pad;

                const yScale = (val) => priceBottom - ((val - yMin) / (yMax - yMin)) * (priceAreaHeight);
                const getX = (i) => chartLeft + i * step + step / 2;

                // --- Draw Axis Labels ---
                ctx.fillStyle = colors.muted;
                ctx.font = '11px "Segoe UI", sans-serif';
                ctx.textAlign = 'right';
                ctx.textBaseline = 'bottom';
                ctx.fillText('株価', chartLeft - 8, priceTop - 4);
                ctx.textBaseline = 'top';
                ctx.fillText('日付', chartRight, height - 14);

                // --- Grid & Y Axis ---
                ctx.lineWidth = 1;
                ctx.font = '11px "Segoe UI", sans-serif';
                ctx.textAlign = 'right';
                ctx.textBaseline = 'middle';
                const ticks = 5;
                for (let i = 0; i <= ticks; i++) {
                    const value = yMin + ((yMax - yMin) * i) / ticks;
                    const y = priceBottom - (i / ticks) * priceAreaHeight; // Corrected calc
                    ctx.strokeStyle = colors.chartGrid;
                    ctx.setLineDash([4, 4]);
                    ctx.beginPath(); ctx.moveTo(chartLeft, y); ctx.lineTo(chartRight, y); ctx.stroke();
                    ctx.setLineDash([]);
                    ctx.fillStyle = colors.muted;
                    ctx.fillText(value.toFixed(0), chartLeft - 6, y);
                }

                // --- X Axis ---
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';
                const tickStep = Math.ceil(barCount / 5);
                for (let i = 0; i < barCount; i += tickStep) {
                    const x = getX(i);
                    const label = points[i].label;
                    ctx.strokeStyle = colors.chartGrid;
                    ctx.setLineDash([4, 4]);
                    ctx.beginPath(); ctx.moveTo(x, priceTop); ctx.lineTo(x, priceBottom); ctx.stroke();
                    ctx.setLineDash([]);
                    ctx.fillStyle = colors.muted;
                    ctx.fillText(label, x, height - 16);
                }

                // --- Candles ---
                points.forEach((p, i) => {
                    const xCenter = getX(i);
                    const openY = yScale(p.open);
                    const closeY = yScale(p.close);
                    const highY = yScale(p.high);
                    const lowY = yScale(p.low);
                    const isUp = p.close >= p.open;
                    ctx.strokeStyle = isUp ? colors.positive : colors.negative;
                    ctx.fillStyle = isUp ? colors.positive : colors.negative;
                    ctx.beginPath(); ctx.moveTo(xCenter, highY); ctx.lineTo(xCenter, lowY); ctx.stroke();
                    const bodyTop = Math.min(openY, closeY);
                    const bodyHeight = Math.max(1, Math.abs(closeY - openY));
                    ctx.fillRect(xCenter - candleWidth / 2, bodyTop, candleWidth, bodyHeight);
                });

                // --- SMAs ---
                sortedSmaKeys.forEach(key => {
                    ctx.strokeStyle = smaColors[key] || '#ffffff';
                    ctx.lineWidth = 1.5;
                    ctx.beginPath();
                    let started = false;
                    for (let i = 0; i < points.length; i++) {
                        const val = points[i][key];
                        if (val == null) { started = false; continue; }
                        const x = getX(i);
                        const y = yScale(val);
                        if (!started) { ctx.moveTo(x, y); started = true; } else { ctx.lineTo(x, y); }
                    }
                    ctx.stroke();
                });

                // --- Cross Events (Golden/Dead) ---
                crosses.forEach(c => {
                    // Check if index is in view
                    if (c.index >= viewIndex && c.index < viewIndex + viewCount) {
                        const i = c.index - viewIndex;
                        const x = getX(i);

                        // Draw Vertical Line
                        ctx.strokeStyle = c.type === 'golden' ? '#eab308' : '#3b82f6'; // Gold / Blue
                        ctx.setLineDash([3, 3]);
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.moveTo(x, priceTop);
                        ctx.lineTo(x, priceBottom);
                        ctx.stroke();
                        ctx.setLineDash([]);

                        // Draw Icon
                        ctx.font = '16px "Segoe UI Emoji"';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'bottom';
                        // Golden: ☀, Dead: ☠ or ❄
                        const icon = c.type === 'golden' ? '☀' : '☠';

                        // Background for icon for visibility
                        ctx.fillStyle = colors.panel; // clear bg behind icon
                        // ctx.beginPath(); ctx.arc(x, priceTop - 10, 10, 0, Math.PI*2); ctx.fill(); 

                        ctx.fillStyle = c.type === 'golden' ? '#eab308' : '#3b82f6';
                        ctx.fillText(icon, x, priceTop - 2);

                        // Label (GC/DC)
                        ctx.font = '10px "Segoe UI", sans-serif';
                        ctx.fillText(c.label, x, priceTop + 12);
                    }
                });

                // --- Volume ---
                const maxVolume = Math.max(...points.map(p => p.volume || 0)) || 1;
                const vGradient = ctx.createLinearGradient(0, volumeTop, 0, volumeTop + volumeAreaHeight);
                vGradient.addColorStop(0, colors.gradientFrom);
                vGradient.addColorStop(1, colors.gradientTo);
                points.forEach((p, i) => {
                    const val = p.volume || 0;
                    const barHeight = (val / maxVolume) * volumeAreaHeight;
                    const xCenter = getX(i);
                    const isUp = p.close >= p.open;
                    ctx.fillStyle = isUp ? colors.positive : colors.negative;
                    ctx.globalAlpha = 0.2;
                    ctx.fillRect(xCenter - candleWidth / 2, volumeTop + (volumeAreaHeight - barHeight), candleWidth, Math.max(1, barHeight));
                    ctx.fillStyle = vGradient;
                    ctx.globalAlpha = 0.3;
                    ctx.fillRect(xCenter - candleWidth / 2, volumeTop + (volumeAreaHeight - barHeight), candleWidth, Math.max(1, barHeight));
                    ctx.globalAlpha = 1.0;
                });
            }

            // --- Interactions ---
            const onMouseDown = (e) => { isDragging = true; lastX = e.clientX; canvas.style.cursor = 'grabbing'; };
            canvas.addEventListener('mousedown', onMouseDown);
            const onMouseMoveGlobal = (e) => {
                if (!isDragging) return;
                const dx = e.clientX - lastX;
                if (dx === 0) return;
                const sensitivity = viewCount / width;
                const deltaIndex = Math.round(-dx * sensitivity * 1.5);
                if (deltaIndex !== 0) {
                    viewIndex = Math.max(0, Math.min(allPoints.length - viewCount, viewIndex + deltaIndex));
                    lastX = e.clientX;
                    requestAnimationFrame(draw);
                    // Update legend to latest visible if dragging? No, keep cursor logic or default to last visible.
                    // If simply dragging, we don't have a cursor over chart, so maybe update to "center of view" or last. 
                    // Let's stick to cursor hover for update.
                }
            };
            window.addEventListener('mousemove', onMouseMoveGlobal);
            const onMouseUpGlobal = () => { isDragging = false; canvas.style.cursor = 'crosshair'; };
            window.addEventListener('mouseup', onMouseUpGlobal);
            canvas.addEventListener('wheel', (e) => {
                e.preventDefault();
                if (e.ctrlKey || Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
                    const zoomDir = Math.sign(e.deltaY);
                    const deltaCount = Math.round(viewCount * 0.1 * zoomDir);
                    const newCount = Math.max(10, Math.min(allPoints.length, viewCount + deltaCount));
                    if (newCount !== viewCount) {
                        const centerRatio = 0.5;
                        const added = newCount - viewCount;
                        viewIndex = Math.max(0, Math.min(allPoints.length - newCount, viewIndex - Math.round(added * centerRatio)));
                        viewCount = newCount;
                        requestAnimationFrame(draw);
                    }
                } else {
                    const panDir = Math.sign(e.deltaX || e.deltaY);
                    viewIndex = Math.max(0, Math.min(allPoints.length - viewCount, viewIndex + Math.round(viewCount * 0.05 * panDir)));
                    requestAnimationFrame(draw);
                }
            }, { passive: false });

            // Tooltip
            canvas.addEventListener('mousemove', (e) => {
                if (isDragging) { tooltip.style.display = 'none'; return; }
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const chartLeft = 50; const chartRight = width - 12; const chartWidth = chartRight - chartLeft;
                if (x < chartLeft || x > chartRight) {
                    tooltip.style.display = 'none'; draw();
                    if (allPoints.length > 0) updateLegend(allPoints[allPoints.length - 1]); // Reset legend
                    return;
                }
                const step = chartWidth / viewCount;
                const idxInView = Math.floor((x - chartLeft) / step);
                const dataIdx = viewIndex + idxInView;
                if (dataIdx >= 0 && dataIdx < allPoints.length) {
                    const point = allPoints[dataIdx];
                    draw(); // redraw
                    // Crosshair
                    const centerX = chartLeft + idxInView * step + step / 2;
                    ctx.strokeStyle = colors.chartCrosshair;
                    ctx.setLineDash([5, 5]);
                    ctx.beginPath(); ctx.moveTo(centerX, 0); ctx.lineTo(centerX, height); ctx.stroke();
                    ctx.setLineDash([]);

                    // Update SMA Legend (Live)
                    updateLegend(point);

                    // Tooltip
                    let html = `<div class="row"><span>日時</span><span>${point.label}</span></div>`;
                    html += `<div class="row"><span>始値</span><span>${fmtPrice(point.open)}</span></div>`;
                    html += `<div class="row"><span>高値</span><span>${fmtPrice(point.high)}</span></div>`;
                    html += `<div class="row"><span>安値</span><span>${fmtPrice(point.low)}</span></div>`;
                    html += `<div class="row"><span>終値</span><span>${fmtPrice(point.close)}</span></div>`;

                    tooltip.innerHTML = html;
                    tooltip.style.display = 'block';
                    const tWidth = tooltip.offsetWidth || 180; const tHeight = tooltip.offsetHeight || 120;
                    let left = e.clientX - rect.left + 15; let top = e.clientY - rect.top + 15;
                    if (left + tWidth > width) left = e.clientX - rect.left - tWidth - 15;
                    if (top + tHeight > height) top = e.clientY - rect.top - tHeight - 15;
                    tooltip.style.transform = `translate(${left}px, ${top}px)`;
                }
            });
            canvas.addEventListener('mouseleave', () => {
                tooltip.style.display = 'none'; draw();
                if (allPoints.length > 0) updateLegend(allPoints[allPoints.length - 1]);
            });

            draw();
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
