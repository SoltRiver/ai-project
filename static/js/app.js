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
            // Check if already initialized to avoid double binding
            if (wrapper.dataset.chartInitialized === 'true') return;
            wrapper.dataset.chartInitialized = 'true';

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
            const allPoints = payload.points || [];
            const levels = payload.support_levels || [];

            // Identify SMA keys dynamically
            const smaKeys = allPoints.length > 0
                ? Object.keys(allPoints[0]).filter(k => k.startsWith('SMA'))
                : [];

            // SMA Colors
            const smaColors = {
                'SMA25': '#f59e0b', // Amber
                'SMA75': '#8b5cf6', // Violet
                'SMA200': '#3b82f6', // Blue
                'SMA13': '#f59e0b',
                'SMA26': '#8b5cf6',
                'SMA52': '#3b82f6',
                'SMA12': '#f59e0b',
                'SMA24': '#8b5cf6',
                'SMA60': '#3b82f6',
            };

            // Viewport State
            let viewCount = Math.min(allPoints.length, 100); // Default zoom level
            let viewIndex = Math.max(0, allPoints.length - viewCount); // Start at newest data

            // Interaction State
            let isDragging = false;
            let lastX = 0;
            let dpr = window.devicePixelRatio || 1;

            // Dimensions (updated on resize/draw)
            let width, height;

            function updateDimensions() {
                const rect = wrapper.getBoundingClientRect();
                width = rect.width - 32; // padding
                const attrHeight = parseInt(canvas.getAttribute('height'), 10) || 420;
                height = attrHeight;

                // Canvas resolution
                canvas.width = width * dpr;
                canvas.height = height * dpr;

                // CSS size
                canvas.style.width = `${width}px`;
                canvas.style.height = `${height}px`;
            }

            // Init dimensions
            updateDimensions();
            // Re-get context after resize
            let ctx = canvas.getContext('2d');

            function draw() {
                if (!ctx) return;

                // Visible subset
                const endIndex = Math.min(allPoints.length, viewIndex + viewCount);
                const points = allPoints.slice(viewIndex, endIndex);

                if (!points.length) {
                    ctx.clearRect(0, 0, width * dpr, height * dpr);
                    ctx.fillStyle = colors.muted;
                    ctx.font = '14px "Segoe UI", sans-serif';
                    ctx.fillText('データがありません', 20, 30);
                    return;
                }

                // Reset canvas
                ctx.setTransform(dpr, 0, 0, dpr, 0, 0); // Reset scale
                ctx.clearRect(0, 0, width, height);

                // Calculate Layout
                const priceAreaHeight = height * 0.7;
                const priceTop = 8;
                const priceBottom = priceTop + priceAreaHeight;
                const volumeAreaHeight = height * 0.22;
                const volumeTop = priceBottom + 6;
                const chartLeft = 50;
                const chartRight = width - 12;
                const chartWidth = chartRight - chartLeft;

                const barCount = points.length;
                const step = chartWidth / Math.max(1, barCount);
                const candleWidth = Math.max(1, step * 0.65);

                // Calculate Y Range (Price) considering SMAs
                const highs = points.map((p) => p.high);
                const lows = points.map((p) => p.low);

                // Add visible SMAs to min/max
                smaKeys.forEach(key => {
                    points.forEach(p => {
                        if (p[key] != null) {
                            highs.push(p[key]);
                            lows.push(p[key]);
                        }
                    });
                });

                const maxHigh = Math.max(...highs);
                const minLow = Math.min(...lows);
                const range = maxHigh - minLow;
                const pad = Math.max(1, range * 0.05); // 5% padding
                const yMin = minLow - pad;
                const yMax = maxHigh + pad;

                const yScale = (val) => {
                    const ratio = (val - yMin) / (yMax - yMin);
                    return priceBottom - ratio * (priceAreaHeight - 16);
                };

                // Helper: Get X coordinate for index relative to CURRENT VIEW
                const getX = (i) => chartLeft + i * step + step / 2;

                // --- Draw Axis Labels ---
                ctx.fillStyle = colors.muted;
                ctx.font = '11px "Segoe UI", sans-serif';
                ctx.textAlign = 'right';

                // Y-Axis "Stock Price"
                ctx.textBaseline = 'bottom';
                ctx.fillText('株価', chartLeft - 8, priceTop - 4);

                // X-Axis "Date"
                ctx.textBaseline = 'top';
                ctx.fillText('日付', chartRight, height - 14);

                // --- Draw Grid & Y Axis ---
                ctx.lineWidth = 1;
                ctx.font = '11px "Segoe UI", sans-serif';
                ctx.textAlign = 'right';
                ctx.textBaseline = 'middle';

                const ticks = 5;
                for (let i = 0; i <= ticks; i++) {
                    const value = yMin + ((yMax - yMin) * i) / ticks;
                    const y = priceBottom - ((priceAreaHeight - 16) * i) / ticks;

                    // Grid
                    ctx.strokeStyle = colors.chartGrid;
                    ctx.setLineDash([4, 4]);
                    ctx.beginPath();
                    ctx.moveTo(chartLeft, y);
                    ctx.lineTo(chartRight, y);
                    ctx.stroke();
                    ctx.setLineDash([]);

                    // Label
                    ctx.fillStyle = colors.muted;
                    ctx.fillText(value.toFixed(0), chartLeft - 6, y);
                }

                // --- Draw X Axis (Time) ---
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';
                const tickStep = Math.ceil(barCount / 5);

                for (let i = 0; i < barCount; i += tickStep) {
                    const x = getX(i);
                    const label = points[i].label;

                    // Grid
                    ctx.strokeStyle = colors.chartGrid;
                    ctx.setLineDash([4, 4]);
                    ctx.beginPath();
                    ctx.moveTo(x, priceTop);
                    ctx.lineTo(x, priceBottom);
                    ctx.stroke();
                    ctx.setLineDash([]);

                    ctx.fillStyle = colors.muted;
                    ctx.fillText(label, x, height - 16);
                }

                // --- Draw Support/Resistance ---
                levels.forEach((lvl) => {
                    const y = yScale(lvl.value);
                    if (y < priceTop || y > priceBottom) return; // Out of view

                    ctx.setLineDash([6, 4]);
                    ctx.strokeStyle = lvl.type === 'support' ? colors.positive : lvl.type === 'resistance' ? colors.negative : colors.neutral;
                    ctx.beginPath();
                    ctx.moveTo(chartLeft, y);
                    ctx.lineTo(chartRight, y);
                    ctx.stroke();
                    ctx.setLineDash([]);
                });

                // --- Draw Candles ---
                points.forEach((p, i) => {
                    const xCenter = getX(i);
                    const openY = yScale(p.open);
                    const closeY = yScale(p.close);
                    const highY = yScale(p.high);
                    const lowY = yScale(p.low);
                    const isUp = p.close >= p.open;

                    ctx.strokeStyle = isUp ? colors.positive : colors.negative;
                    ctx.fillStyle = isUp ? colors.positive : colors.negative;

                    // Wick
                    ctx.beginPath();
                    ctx.moveTo(xCenter, highY);
                    ctx.lineTo(xCenter, lowY);
                    ctx.stroke();

                    // Body
                    const bodyTop = Math.min(openY, closeY);
                    const bodyHeight = Math.max(1, Math.abs(closeY - openY));
                    ctx.fillRect(xCenter - candleWidth / 2, bodyTop, candleWidth, bodyHeight);
                });

                // --- Draw SMAs ---
                smaKeys.forEach(key => {
                    ctx.strokeStyle = smaColors[key] || '#ffffff';
                    ctx.lineWidth = 1.5;
                    ctx.beginPath();

                    let started = false;
                    for (let i = 0; i < points.length; i++) {
                        const val = points[i][key];
                        if (val == null) {
                            started = false; // break line on null
                            continue;
                        }
                        const x = getX(i);
                        const y = yScale(val);

                        // Clip Y (though usually fine)
                        if (!started) {
                            ctx.moveTo(x, y);
                            started = true;
                        } else {
                            ctx.lineTo(x, y);
                        }
                    }
                    ctx.stroke();
                });

                // --- Draw Volume ---
                const maxVolume = Math.max(...points.map(p => p.volume || 0)) || 1;
                // Volume Gradient
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

            // Pan logic
            const onMouseDown = (e) => {
                isDragging = true;
                lastX = e.clientX;
                canvas.style.cursor = 'grabbing';
            };
            canvas.addEventListener('mousedown', onMouseDown);

            const onMouseMoveGlobal = (e) => {
                if (!isDragging) return;
                const dx = e.clientX - lastX;
                if (dx === 0) return;

                // Move viewIndex
                // Sensitivity: 1 pixel drag ~= 1 candle * sensitivity
                const sensitivity = viewCount / width;
                const deltaIndex = Math.round(-dx * sensitivity * 1.5);

                if (deltaIndex !== 0) {
                    const newIndex = viewIndex + deltaIndex;
                    // Clamp
                    viewIndex = Math.max(0, Math.min(allPoints.length - viewCount, newIndex));
                    lastX = e.clientX;
                    requestAnimationFrame(draw);
                }
            };
            window.addEventListener('mousemove', onMouseMoveGlobal);

            const onMouseUpGlobal = () => {
                isDragging = false;
                canvas.style.cursor = 'crosshair';
            };
            window.addEventListener('mouseup', onMouseUpGlobal);

            // Zoom logic (Wheel)
            canvas.addEventListener('wheel', (e) => {
                e.preventDefault();

                // Detect scroll vs zoom
                if (e.ctrlKey || Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
                    // Zoom
                    const zoomDir = Math.sign(e.deltaY);
                    const zoomFactor = 0.1;
                    const deltaCount = Math.round(viewCount * zoomFactor * zoomDir);

                    const newCount = Math.max(10, Math.min(allPoints.length, viewCount + deltaCount));
                    if (newCount !== viewCount) {
                        const centerRatio = 0.5;
                        const added = newCount - viewCount;
                        viewIndex = Math.max(0, Math.min(allPoints.length - newCount, viewIndex - Math.round(added * centerRatio)));
                        viewCount = newCount;
                        requestAnimationFrame(draw);
                    }
                } else {
                    // Pan (horizontal scroll)
                    const panDir = Math.sign(e.deltaX || e.deltaY);
                    const shift = Math.round(viewCount * 0.05 * panDir);
                    viewIndex = Math.max(0, Math.min(allPoints.length - viewCount, viewIndex + shift));
                    requestAnimationFrame(draw);
                }
            }, { passive: false });

            // Tooltip (Mouse Move without Drag)
            canvas.addEventListener('mousemove', (e) => {
                if (isDragging) {
                    tooltip.style.display = 'none';
                    return;
                }

                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const chartLeft = 50;
                const chartRight = width - 12;
                const chartWidth = chartRight - chartLeft;

                if (x < chartLeft || x > chartRight) {
                    tooltip.style.display = 'none';
                    draw(); // clear crosshair
                    return;
                }

                const step = chartWidth / viewCount;
                const relX = x - chartLeft;
                const idxInView = Math.floor(relX / step);
                const dataIdx = viewIndex + idxInView;

                if (dataIdx >= 0 && dataIdx < allPoints.length) {
                    const point = allPoints[dataIdx];
                    // Redraw to show crosshair (optional, but good)
                    draw();

                    // Simple Crosshair on top
                    const centerX = chartLeft + idxInView * step + step / 2;
                    ctx.strokeStyle = colors.chartCrosshair;
                    ctx.setLineDash([5, 5]);
                    ctx.beginPath();
                    ctx.moveTo(centerX, 0);
                    ctx.lineTo(centerX, height);
                    ctx.stroke();
                    ctx.setLineDash([]);

                    // Show Tooltip
                    let html = '';
                    html += `<div class="row"><span>日時</span><span>${point.label}</span></div>`;
                    html += `<div class="row"><span>始値</span><span>${fmtPrice(point.open)}</span></div>`;
                    html += `<div class="row"><span>高値</span><span>${fmtPrice(point.high)}</span></div>`;
                    html += `<div class="row"><span>安値</span><span>${fmtPrice(point.low)}</span></div>`;
                    html += `<div class="row"><span>終値</span><span>${fmtPrice(point.close)}</span></div>`;
                    // SMAs in Tooltip
                    smaKeys.forEach(k => {
                        if (point[k] != null) {
                            html += `<div class="row"><span style="color:${smaColors[k]}">${k}</span><span>${fmtPrice(point[k])}</span></div>`;
                        }
                    });

                    tooltip.innerHTML = html;
                    tooltip.style.display = 'block';

                    // Position Tooltip
                    const tWidth = tooltip.offsetWidth || 180;
                    const tHeight = tooltip.offsetHeight || 120;
                    let left = e.clientX - rect.left + 15;
                    let top = e.clientY - rect.top + 15;

                    if (left + tWidth > width) left = e.clientX - rect.left - tWidth - 15;
                    if (top + tHeight > height) top = e.clientY - rect.top - tHeight - 15;

                    tooltip.style.transform = `translate(${left}px, ${top}px)`;
                }
            });

            canvas.addEventListener('mouseleave', () => {
                tooltip.style.display = 'none';
                draw(); // clear crosshair
            });

            // Initial Draw
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
