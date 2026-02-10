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
        const wrappers = document.querySelectorAll('.chart-wrapper');
        wrappers.forEach((wrapper) => {
            if (wrapper.dataset.chartInitialized === 'true') return;
            wrapper.dataset.chartInitialized = 'true';

            const payloadScript = wrapper.querySelector('#chart-payload-json');
            const colors = getColors();
            const canvas = wrapper.querySelector('.candle-canvas');
            const tooltip = wrapper.querySelector('.chart-tooltip');
            // Element is outside wrapper, in the card header
            const card = wrapper.closest('.chart-card');
            const smaLegend = card ? card.querySelector('.sma-legend') : null;

            if (!payloadScript || !canvas || !tooltip) return;

            let payload;
            try {
                payload = JSON.parse(payloadScript.textContent);
            } catch (_) {
                return;
            }
            const allPoints = payload.points || [];
            const levels = payload.support_levels || [];

            // Identify SMA keys dynamically & Sort
            // Scan last 5 points to ensure keys exist even if recent data is partial
            const samplePoints = allPoints.slice(-5);
            const allKeys = new Set();
            samplePoints.forEach(p => Object.keys(p).forEach(k => allKeys.add(k)));
            const smaKeys = Array.from(allKeys).filter(k => k.startsWith('SMA'));

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
                'SMA60': '#3b82f6',
                'SMA12': '#f59e0b', // Monthly Short
                'SMA24': '#8b5cf6', // Monthly Medium
                'SMA60': '#3b82f6'  // Monthly Long (Redundant key but safe)
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

            function updateMainLegend(point) {
                const sub = document.querySelector('.chart-sub');
                if (!sub || !point) return;

                const o = fmtPrice(point.open);
                const h = fmtPrice(point.high);
                const l = fmtPrice(point.low);
                const c = fmtPrice(point.close);
                const v = fmtVolume(point.volume);
                const t = point.label; // e.g. '2025/12/19'

                let html = '';
                html += `<span class="l-item"><span class="l-label">始値</span><span class="l-val">${o}</span></span>`;
                html += `<span class="l-item"><span class="l-label">高値</span><span class="l-val">${h}</span></span>`;
                html += `<span class="l-item"><span class="l-label">安値</span><span class="l-val">${l}</span></span>`;
                html += `<span class="l-item"><span class="l-label">終値</span><span class="l-val">${c}</span></span>`;
                // html += `<span class="l-item"><span class="l-label">出来高</span><span class="l-val">${v}</span></span>`;
                // html += `<span class="l-item" style="color:var(--muted); font-size:0.9rem;">${t}</span>`;

                sub.innerHTML = html;
            }

            function updateLegend(point) {

                if (!smaLegend) return;
                if (!sortedSmaKeys.length) {
                    smaLegend.innerHTML = '';
                    return;
                }

                // Map keys to Japanese labels
                // Determine interval unit
                const select = document.querySelector('select[name="interval"]');
                const interval = select ? select.value : '1d';
                let unit = '日';
                if (interval.includes('wk') || interval === 'weekly') unit = '週';
                if (interval.includes('mo') || interval === 'monthly') unit = 'ヶ月';

                let html = '';
                sortedSmaKeys.forEach((k, index) => {
                    const val = point ? point[k] : null;
                    const color = smaColors[k] || colors.text;
                    const valStr = fmtPrice(val);

                    // Dynamic Label Generation
                    // Extract number from key (e.g., 'SMA25' -> 25)
                    const numMatch = k.match(/\d+/);
                    const num = numMatch ? parseInt(numMatch[0], 10) : '';

                    // Determine role based on sorted order (Short/Med/Long)
                    // Assuming standard 3 lines. If not, fallback to Key.
                    let role = '';
                    if (sortedSmaKeys.length === 3) {
                        if (index === 0) role = '短期';
                        if (index === 1) role = '中期';
                        if (index === 2) role = '長期';
                    } else if (sortedSmaKeys.length === 2) {
                        if (index === 0) role = '短期';
                        if (index === 1) role = '長期';
                    }

                    const label = (role && num) ? `${role}(${num}${unit})` : k.toUpperCase();

                    html += `<span class="sma-item" style="color:${color}"><span style="opacity:0.8">${label}</span> <span style="font-weight:700">${valStr}</span></span>`;
                });
                smaLegend.innerHTML = html;
            }

            // Init Legend with latest data
            if (allPoints.length > 0) {
                const last = allPoints[allPoints.length - 1];
                updateLegend(last);
                updateMainLegend(last);
            }


            // Viewport State
            let viewCount = Math.min(allPoints.length, 100);
            let viewIndex = Math.max(0, allPoints.length - viewCount);
            let isDragging = false;
            let lastX = 0;
            let dpr = window.devicePixelRatio || 1;
            let width, height;
            let yScale = null;
            let selectedDataIdx = null; // Sticky tooltip state
            let selectedCrossIdx = null; // Sticky cross tooltip state

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
                    yScale = null;
                    ctx.clearRect(0, 0, width * dpr, height * dpr);
                    ctx.fillStyle = colors.muted;
                    ctx.font = '14px "Segoe UI", sans-serif';
                    ctx.fillText('データがありません', 20, 30);
                    return;
                }

                ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
                ctx.clearRect(0, 0, width, height);

                // Check Layout
                // Adjust layout to prevent overlap and add bottom margin for X-axis
                const topMargin = 40; // Increased to prevent legend overlap
                const bottomMargin = 20; // Space for X-axis dates
                const availableHeight = height - topMargin - bottomMargin;

                // Price Area: Top 60% of available
                const priceAreaHeight = availableHeight * 0.60;
                const priceTop = topMargin;
                const priceBottom = priceTop + priceAreaHeight;

                // Volume Area: Bottom 25% of available
                const volumeHeight = availableHeight * 0.25;
                // Gap is roughly 15%
                const volumeTop = height - bottomMargin - volumeHeight;
                const volumeBottom = height - bottomMargin;

                const chartLeft = 50;
                const chartRight = width - 50; // Extra right space for Volume Axis
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

                yScale = (val) => priceBottom - ((val - yMin) / (yMax - yMin)) * (priceAreaHeight);
                const getX = (i) => chartLeft + i * step + step / 2;

                // --- Draw Axis Labels ---
                ctx.fillStyle = colors.muted;
                ctx.font = '11px "Segoe UI", sans-serif';
                ctx.textAlign = 'right';
                ctx.textBaseline = 'bottom';
                ctx.fillText('株価', chartLeft - 8, priceTop - 15);

                // Volume Label (Left side)
                ctx.textAlign = 'right';
                ctx.fillText('出来高', chartLeft - 8, volumeTop - 4);

                ctx.textAlign = 'right';
                ctx.textBaseline = 'top';
                ctx.fillText('日付', chartRight, height - 14); // Bottom right

                // --- Grid & Y Axis (Price) ---
                ctx.lineWidth = 1;
                ctx.font = '11px "Segoe UI", sans-serif';
                ctx.textAlign = 'right';
                ctx.textBaseline = 'middle';
                const ticks = 5;
                for (let i = 0; i <= ticks; i++) {
                    const value = yMin + ((yMax - yMin) * i) / ticks;
                    const y = priceBottom - (i / ticks) * priceAreaHeight;
                    ctx.strokeStyle = colors.chartGrid;
                    ctx.setLineDash([4, 4]);
                    ctx.beginPath(); ctx.moveTo(chartLeft, y); ctx.lineTo(chartRight, y); ctx.stroke();
                    ctx.setLineDash([]);
                    ctx.fillStyle = colors.muted;
                    ctx.fillText(value.toFixed(0), chartLeft - 6, y);
                }

                // --- Volume Axis (Left) ---
                const maxVolume = Math.max(...points.map(p => p.volume || 0)) || 1;
                const volTicks = 3;
                ctx.textAlign = 'right';
                for (let i = 0; i <= volTicks; i++) {
                    const volVal = (maxVolume * i) / volTicks;
                    const y = volumeBottom - (i / volTicks) * volumeHeight; // Bottom-up

                    ctx.fillStyle = colors.muted;
                    // Format volume (K/M)
                    let volStr = volVal >= 1000000 ? (volVal / 1000000).toFixed(1) + 'M' :
                        volVal >= 1000 ? (volVal / 1000).toFixed(1) + 'K' : volVal.toFixed(0);
                    ctx.fillText(volStr, chartLeft - 6, y);
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
                    ctx.beginPath(); ctx.moveTo(x, priceTop); ctx.lineTo(x, volumeBottom); ctx.stroke(); // Full height grid
                    ctx.setLineDash([]);
                    ctx.fillStyle = colors.muted;
                    // Ensure label text doesn't overlap volume bars (draw below volume area)
                    ctx.fillText(label, x, volumeBottom + 4);
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
                    if (c.index >= viewIndex && c.index < viewIndex + viewCount) {
                        const i = c.index - viewIndex;
                        const x = getX(i);

                        // Draw Vertical Line (UP to Icon)
                        ctx.strokeStyle = c.type === 'golden' ? '#eab308' : '#3b82f6';
                        ctx.lineWidth = 2.0;
                        ctx.beginPath();
                        ctx.moveTo(x, yScale(c.price));
                        ctx.lineTo(x, priceTop); // Draw line UP to the icon
                        ctx.stroke();

                        // Draw Dot
                        ctx.fillStyle = c.type === 'golden' ? '#eab308' : '#3b82f6';
                        ctx.beginPath();
                        ctx.arc(x, yScale(c.price), 4, 0, Math.PI * 2);
                        ctx.fill();

                        // Icon & Label logic
                        ctx.font = '16px "Segoe UI Emoji"';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'bottom';
                        const icon = c.type === 'golden' ? '☀' : '☠';
                        ctx.fillStyle = colors.panel;
                        ctx.fillStyle = c.type === 'golden' ? '#eab308' : '#3b82f6';
                        ctx.fillText(icon, x, priceTop - 2);

                        // Removed Text Label (GC/DC) as requested
                    }
                });

                // --- Separator Line (Price vs Volume) ---
                // --- Separator Line (Price vs Volume) ---
                ctx.strokeStyle = '#4b5563'; // Brighter gray
                ctx.lineWidth = 1; // Thicker?
                ctx.beginPath();
                // Draw line between price area and volume area. Center in the gap.
                const separatorY = priceBottom + (volumeTop - priceBottom) / 2;
                ctx.moveTo(chartLeft, separatorY);
                ctx.lineTo(chartRight, separatorY);
                ctx.stroke();
                ctx.lineTo(chartRight, separatorY);
                ctx.stroke();

                // --- Volume Bars ---
                const vGradient = ctx.createLinearGradient(0, volumeTop, 0, volumeBottom);
                vGradient.addColorStop(0, colors.gradientFrom);
                vGradient.addColorStop(1, colors.gradientTo);

                points.forEach((p, i) => {
                    const val = p.volume || 0;
                    // Scale volume relative to max calculated above
                    const barHeight = (val / maxVolume) * volumeHeight;
                    const xCenter = getX(i);
                    // Base color + Gradient overlay (Changed to #FFD700 Gold)
                    ctx.fillStyle = '#FFD700';
                    ctx.globalAlpha = 0.3;
                    ctx.fillRect(xCenter - candleWidth / 2, volumeBottom - barHeight, candleWidth, Math.max(1, barHeight));

                    ctx.fillStyle = vGradient;
                    ctx.globalAlpha = 0.4;
                    ctx.fillRect(xCenter - candleWidth / 2, volumeBottom - barHeight, candleWidth, Math.max(1, barHeight));
                    ctx.globalAlpha = 1.0;
                });

                // Sticky Tooltip Rendering
                if (selectedDataIdx !== null && yScale) {
                    if (selectedDataIdx >= viewIndex && selectedDataIdx < viewIndex + viewCount) {
                        const i = selectedDataIdx - viewIndex;
                        const x = getX(i);
                        const point = allPoints[selectedDataIdx];
                        const rect = canvas.getBoundingClientRect();
                        const virtualY = rect.top + yScale(point.close);
                        showTooltip(point, x, virtualY, rect);
                    } else {
                        tooltip.style.display = 'none';
                    }
                }

                // Sticky Cross Tooltip Rendering
                if (selectedCrossIdx !== null) {
                    const cross = crosses.find(c => c.index === selectedCrossIdx);
                    if (cross && cross.index >= viewIndex && cross.index < viewIndex + viewCount) {
                        const i = cross.index - viewIndex;
                        const x = chartLeft + i * (chartWidth / viewCount) + (chartWidth / viewCount) / 2;
                        const rect = canvas.getBoundingClientRect();
                        const my = 40; // priceTop
                        showCrossTooltip(cross, x, my, rect);
                    } else if (selectedDataIdx === null) {
                        tooltip.style.display = 'none';
                    }
                }
            }

            // ... interactions ...

            // Tooltip & Drag & Scroll
            canvas.style.cursor = 'grab'; // Indicate draggable

            // --- Interaction: Click (Sticky Tooltip) ---
            canvas.addEventListener('click', (e) => {
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const my = e.clientY - rect.top;

                const chartLeft = 50;
                const chartRight = width - 50;
                const chartWidth = chartRight - chartLeft;
                const step = chartWidth / viewCount;

                // Check for Cross Icon Click
                const priceTop = 40;
                let clickedCross = null;
                for (const c of crosses) {
                    if (c.index >= viewIndex && c.index < viewIndex + viewCount) {
                        const i = c.index - viewIndex;
                        const cx = chartLeft + i * step + step / 2;
                        const iconTop = priceTop - 25;
                        const iconBottom = priceTop + 5;

                        if (Math.abs(x - cx) < 20 && my >= iconTop && my <= iconBottom) {
                            clickedCross = c;
                            break;
                        }
                    }
                }

                if (clickedCross) {
                    selectedCrossIdx = clickedCross.index;
                    selectedDataIdx = null; // Clear candle sticky
                    draw();
                    return;
                }

                const idxInView = Math.floor((x - chartLeft) / step);
                const dataIdx = Math.floor(viewIndex + idxInView);

                if (dataIdx >= 0 && dataIdx < allPoints.length) {
                    if (!yScale) { selectedDataIdx = null; selectedCrossIdx = null; draw(); return; }

                    const point = allPoints[dataIdx];
                    const cHigh = yScale(point.high);
                    const cLow = yScale(point.low);
                    const buffer = 10;

                    if (my >= cHigh - buffer && my <= cLow + buffer) {
                        selectedDataIdx = dataIdx;
                        selectedCrossIdx = null; // Clear cross sticky
                    } else {
                        selectedDataIdx = null;
                        selectedCrossIdx = null;
                    }
                    draw();
                } else {
                    selectedDataIdx = null;
                    selectedCrossIdx = null;
                    draw();
                }
            });

            canvas.addEventListener('mousedown', (e) => {
                isDragging = true;
                lastX = e.clientX;
                canvas.style.cursor = 'grabbing';
                tooltip.style.display = 'none'; // Hide tooltip while dragging
            });

            const stopDrag = () => {
                isDragging = false;
                canvas.style.cursor = 'grab';
            };
            canvas.addEventListener('mouseup', stopDrag);
            canvas.addEventListener('mouseleave', () => {
                stopDrag();
                tooltip.style.display = 'none';
                draw();
                if (allPoints.length > 0) updateLegend(allPoints[allPoints.length - 1]);
            });

            function showTooltip(point, x, clientY, rect) {
                // Construct Content
                // Format Date: 2025/12/19 -> 2025-12-19
                const formattedDate = (point.label || '').replace(/\//g, '-');
                const volInWan = point.volume != null ? (point.volume / 10000).toLocaleString('ja-JP', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '万株' : 'N/A';

                let html = `<div class="tooltip-header">${formattedDate}</div>`;
                html += `<div class="tooltip-row"><span class="t-label">出来高</span><span class="t-val">${volInWan}</span></div>`;
                html += `<div class="tooltip-divider"></div>`;
                html += `<div class="tooltip-row"><span class="t-label">始値</span><span class="t-val">${fmtPrice(point.open)}</span></div>`;
                html += `<div class="tooltip-row"><span class="t-label">高値</span><span class="t-val">${fmtPrice(point.high)}</span></div>`;
                html += `<div class="tooltip-row"><span class="t-label">安値</span><span class="t-val">${fmtPrice(point.low)}</span></div>`;
                html += `<div class="tooltip-row"><span class="t-label">終値</span><span class="t-val">${fmtPrice(point.close)}</span></div>`;

                if (point.candle_name && point.candle_type) {
                    html += `<div class="tooltip-divider"></div>`;
                    html += `<div class="tooltip-row"><span class="t-label">形</span><span class="t-val">${point.candle_type}</span></div>`;

                    // Pattern Name Link
                    let patternNameHtml = point.candle_name;
                    if (payload.candle_patterns) {
                        const pattern = payload.candle_patterns.find(p => p.name === point.candle_name);
                        if (pattern) {
                            patternNameHtml = `<a href="javascript:void(0)" class="t-pattern-link" onclick="window.showPatternCardModal('${pattern.id}')">${point.candle_name}</a>`;
                        }
                    }
                    html += `<div class="tooltip-row"><span class="t-label">種類</span><span class="t-val">${patternNameHtml}</span></div>`;
                }

                tooltip.innerHTML = html;
                tooltip.style.display = 'block';
                tooltip.style.pointerEvents = 'auto'; // Enable clicks inside tooltip

                // Position
                const tWidth = tooltip.offsetWidth || 180;
                const tHeight = tooltip.offsetHeight || 120;
                let left = x + 20;
                let top = (clientY - rect.top) - 20;

                // Boundary Logic
                if (left + tWidth > width) left = x - tWidth - 20;
                if (top + tHeight > height) top = height - tHeight - 10;
                if (top < 0) top = 10;

                tooltip.style.left = `${left}px`;
                tooltip.style.top = `${top}px`;
                tooltip.style.transform = 'none';
            }

            function showCrossTooltip(cross, x, my, rect) {
                const point = allPoints[cross.index];
                const prevPoint = cross.index > 0 ? allPoints[cross.index - 1] : null;

                const isGolden = cross.type === 'golden';
                const crossTitle = isGolden ? 'ゴールデンクロス' : 'デッドクロス';
                const crossColor = isGolden ? '#eab308' : '#3b82f6';

                const shortKey = sortedSmaKeys[0] || '短期MA';
                const longKey = sortedSmaKeys[1] || '長期MA';
                const shortNum = shortKey.match(/\d+/) ? shortKey.match(/\d+/)[0] : '';
                const longNum = longKey.match(/\d+/) ? longKey.match(/\d+/)[0] : '';

                const isConfirmed = cross.index < allPoints.length - 1;
                const res = calculateCrossConfidence(cross, prevPoint, point, shortKey, longKey);

                // 1. Date
                const formattedDate = (point.label || '').replace(/\//g, '-');
                let html = `<div class="tooltip-header" style="border:none; padding-bottom:0;">${formattedDate}</div>`;

                // 2. Status (Enhanced with color and icon)
                const statusText = isConfirmed ? '確定' : '未確定';
                const statusClass = isConfirmed ? 'status-confirmed' : 'status-unconfirmed';
                const statusIcon = isConfirmed ? '✅' : '⏳';
                html += `<div class="tooltip-row"><span class="t-label">状態</span><span class="t-val ${statusClass}"><span class="status-icon">${statusIcon}</span>${statusText}</span></div>`;

                // 3. Line Type
                html += `<div class="tooltip-row"><span class="t-label">線種</span><span class="t-val" style="color:${crossColor}; font-weight:700;">${crossTitle}</span></div>`;

                // 4. Condition
                const op = isGolden ? '>' : '<';
                html += `<div class="tooltip-row"><span class="t-label">条件</span><span class="t-val" style="font-size:0.75rem;">短期(${shortNum}) ${op} 長期(${longNum})</span></div>`;

                // 5. Confidence
                const badgeContent = res.level + (res.icon ? ' ' + res.icon : '');
                // Include cross type for the modal symbol
                const resJson = JSON.stringify({ ...res, type: cross.type }).replace(/"/g, '&quot;');
                html += `<div class="tooltip-row">
                    <span class="t-label">信頼度評価 <span class="conf-help-icon" onclick="window.showCrossHelpModal(event, ${resJson})">?</span></span>
                    <span class="conf-badge ${res.colorClass}">${badgeContent}</span>
                </div>`;

                // (Reason is now displayed only in the modal)

                // 7. Short MA
                html += `<div class="tooltip-row"><span class="t-label">短期(${shortNum})</span><span class="t-val">${fmtPrice(point[shortKey])}</span></div>`;

                // 8. Long MA
                html += `<div class="tooltip-row"><span class="t-label">長期(${longNum})</span><span class="t-val">${fmtPrice(point[longKey])}</span></div>`;

                // 9. Close
                html += `<div class="tooltip-row"><span class="t-label">終値</span><span class="t-val">${fmtPrice(point.close)}</span></div>`;

                tooltip.innerHTML = html;
                tooltip.style.display = 'block';
                tooltip.style.pointerEvents = 'auto';

                const tWidth = tooltip.offsetWidth || 200;
                const tHeight = tooltip.offsetHeight || 250;
                let left = x + 20;
                let top = my - (tHeight / 2);
                if (left + tWidth > width) left = x - tWidth - 20;
                if (top + tHeight > height) top = height - tHeight - 10;
                if (top < 0) top = 10;

                tooltip.style.left = `${left}px`;
                tooltip.style.top = `${top}px`;
                tooltip.style.transform = 'none';
            }

            // Confidence Scoring for GC/DC
            function calculateCrossConfidence(cross, prevPoint, currPoint, shortKey, longKey) {
                if (!prevPoint || !currPoint) return { level: '未確定', icon: '', reason: 'データ不足', colorClass: 'conf-unconfirmed' };

                const slope = currPoint[longKey] - prevPoint[longKey];
                const isGC = cross.type === 'golden';
                const close = currPoint.close;
                const longMa = currPoint[longKey];

                const isConfirmed = cross.index < allPoints.length - 1;

                if (!isConfirmed) {
                    const trendMatches = isGC ? (slope > 0) : (slope < 0);
                    const priceDominant = isGC ? (close > longMa) : (close < longMa);
                    let tempReason = '';
                    if (trendMatches && priceDominant) {
                        tempReason = isGC ? '長期MAが上昇、終値が長期MAの上' : '長期MAが下降、終値が長期MAの下';
                    } else if (!trendMatches && !priceDominant) {
                        tempReason = isGC ? '長期MAが下降、終値が長期MAの下' : '長期MAが上昇、終値が長期MAの上';
                    } else if (trendMatches && !priceDominant) {
                        tempReason = isGC ? '長期MAは上昇しているが、終値が長期MAの下' : '長期MAは下降しているが、終値が長期MAの上';
                    } else {
                        tempReason = isGC ? '終値は長期MAの上にあるが、長期MAが下降中' : '終値は長期MAの下にあるが、長期MAが上昇中';
                    }
                    return { level: '未確定', icon: '', reason: `未確定足のため。（暫定状態：${tempReason}）`, colorClass: 'conf-unconfirmed' };
                }

                // Trend matching direction
                const trendMatches = isGC ? (slope > 0) : (slope < 0);
                // Price position in favorable side
                const priceDominant = isGC ? (close > longMa) : (close < longMa);

                let level, icon, reason, colorClass;

                if (trendMatches && priceDominant) {
                    level = '高'; icon = '◎'; colorClass = 'conf-high';
                    reason = isGC ? '長期MAが上昇、終値が長期MAの上' : '長期MAが下降、終値が長期MAの下';
                } else if (!trendMatches && !priceDominant) {
                    level = '低'; icon = '△'; colorClass = 'conf-low';
                    reason = isGC ? '長期MAが下降、終値が長期MAの下' : '長期MAが上昇、終値が長期MAの上';
                } else {
                    level = '中'; icon = '〇'; colorClass = 'conf-medium';
                    if (trendMatches && !priceDominant) {
                        reason = isGC ? '長期MAは上昇しているが、終値が長期MAの下' : '長期MAは下降しているが、終値が長期MAの上';
                    } else {
                        reason = isGC ? '終値は長期MAの上にあるが、長期MAが下降中' : '終値は長期MAの下にあるが、長期MAが上昇中';
                    }
                }

                return { level, icon, reason, colorClass };
            }



            canvas.addEventListener('mousemove', (e) => {
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;

                // Dragging Logic
                if (isDragging) {
                    const deltaX = e.clientX - lastX;
                    lastX = e.clientX;

                    const chartLeft = 50;
                    const chartRight = width - 50;
                    const chartWidth = chartRight - chartLeft;
                    const step = chartWidth / viewCount;

                    const barsMoved = deltaX / step;
                    viewIndex -= barsMoved;

                    const maxIndex = Math.max(0, allPoints.length - viewCount);
                    viewIndex = Math.max(0, Math.min(viewIndex, maxIndex));

                    draw();
                    return;
                }

                const chartLeft = 50;
                const chartRight = width - 50;
                const chartWidth = chartRight - chartLeft;

                if (x < chartLeft || x > chartRight) {
                    tooltip.style.display = 'none';
                    draw();
                    if (allPoints.length > 0) {
                        const last = allPoints[allPoints.length - 1];
                        updateLegend(last);
                        updateMainLegend(last);
                    }
                    return;
                }

                // Check Cross Icon Hover
                let hoveredCross = null;
                const my = e.clientY - rect.top;
                const topMargin = 40;
                const priceTop = topMargin;

                for (const c of crosses) {
                    if (c.index >= viewIndex && c.index < viewIndex + viewCount) {
                        const i = c.index - viewIndex;
                        const cx = chartLeft + i * (chartWidth / viewCount) + (chartWidth / viewCount) / 2;
                        const iconTop = priceTop - 25;
                        const iconBottom = priceTop + 5;

                        if (Math.abs(x - cx) < 20 && my >= iconTop && my <= iconBottom) {
                            hoveredCross = c;
                            break;
                        }
                    }
                }

                if (hoveredCross) {
                    canvas.style.cursor = 'help';
                    const cx = chartLeft + (hoveredCross.index - viewIndex) * (chartWidth / viewCount) + (chartWidth / viewCount) / 2;
                    if (selectedCrossIdx === null) {
                        showCrossTooltip(hoveredCross, cx, my, rect);
                    }
                    return;
                }

                const step = chartWidth / viewCount;
                const idxInView = Math.floor((x - chartLeft) / step);
                const dataIdx = Math.floor(viewIndex + idxInView);

                if (dataIdx >= 0 && dataIdx < allPoints.length) {
                    const point = allPoints[dataIdx];
                    draw();

                    // Crosshair
                    const centerX = chartLeft + idxInView * step + step / 2;
                    ctx.strokeStyle = colors.chartCrosshair;
                    ctx.setLineDash([5, 5]);
                    ctx.beginPath(); ctx.moveTo(centerX, 0); ctx.lineTo(centerX, height); ctx.stroke();
                    ctx.setLineDash([]);

                    updateLegend(point);
                    updateMainLegend(point);

                    // Cursor & Tooltip
                    if (yScale) {
                        const yMouse = e.clientY - rect.top;
                        const cHigh = yScale(point.high);
                        const cLow = yScale(point.low);
                        const buffer = 4;
                        const isHoveringCandle = (yMouse >= cHigh - buffer && yMouse <= cLow + buffer);

                        if (isHoveringCandle) {
                            canvas.style.cursor = 'pointer';
                        } else {
                            canvas.style.cursor = isDragging ? 'grabbing' : 'grab';
                        }

                        if (selectedDataIdx === null) {
                            showTooltip(point, centerX, e.clientY, rect);
                        }
                    }
                } else {
                    tooltip.style.display = 'none';
                }
            });

            // Wheel Scroll Logic
            canvas.addEventListener('wheel', (e) => {
                e.preventDefault(); // Prevent page scroll
                const delta = e.deltaX || e.deltaY; // Support both axis

                // Sensitivity
                const speed = 0.5; // Bars per pixel roughly
                const barsMoved = (delta / 50) * speed * viewCount * 0.1; // adjust scaling

                // Mouse Wheel Down (Positive) -> Move Forward in Time (Pan Right) -> Increase Index
                viewIndex += (delta > 0 ? 1 : -1) * Math.max(1, Math.abs(delta) / 10);

                // Clamp
                const maxIndex = Math.max(0, allPoints.length - viewCount);
                viewIndex = Math.floor(viewIndex);
                viewIndex = Math.max(0, Math.min(viewIndex, maxIndex));

                draw();
                if (allPoints.length > 0) updateLegend(allPoints[Math.min(allPoints.length - 1, Math.floor(viewIndex + viewCount - 1))]);
            }, { passive: false });

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


    function initPatternPage() {
        initPatternTabs();
        initPatternModal();
    }

    /* Removed animateCountBadges function to prevent count fluctuation */

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
                // animateCountBadges(); // Removed
            });
        });
        // animateCountBadges(); // Removed
    }

    function initPatternModal() {
        const overlay = document.querySelector('[data-modal-overlay]');
        if (!overlay) return;
        const closeBtn = overlay.querySelector('[data-close-modal]');
        const imgEl = overlay.querySelector('[data-modal-image]');
        const nameEl = overlay.querySelector('[data-modal-name]');
        const actionEl = overlay.querySelector('[data-modal-action]');
        const descLeadEl = overlay.querySelector('[data-modal-desc-lead]');
        const descBodyEl = overlay.querySelector('[data-modal-desc-body]');
        const detailEl = overlay.querySelector('[data-modal-detail]');
        const sceneEl = overlay.querySelector('[data-modal-scene]');
        const howtoEl = overlay.querySelector('[data-modal-howto]');
        const tipsEl = overlay.querySelector('[data-modal-tips]');
        const detailWrapper = overlay.querySelector('[data-modal-detail-wrapper]');

        let lastFocus = null;

        const close = () => {
            overlay.classList.remove('is-open');
            overlay.hidden = true;
            if (lastFocus) {
                try { lastFocus.focus(); } catch (e) { }
            }
        };

        const open = (data, isFull = true) => {
            overlay.hidden = false;
            overlay.classList.add('is-open');

            nameEl.textContent = data.name || '';
            actionEl.textContent = data.action || data.catch || '';
            descLeadEl.textContent = data.descLead || '';
            descBodyEl.textContent = data.descBody || '';

            if (data.svg) {
                imgEl.src = data.svg.startsWith('/') ? data.svg : '/static/' + data.svg;
                imgEl.alt = data.name || '';
            }

            if (isFull) {
                if (detailWrapper) detailWrapper.hidden = false;
                detailEl.textContent = data.detail || '';
                sceneEl.textContent = data.scene || '';
                howtoEl.textContent = data.howto || '';
                tipsEl.innerHTML = '';
                const tipsSource = data.tips || data.notes || '';
                const tips = (typeof tipsSource === 'string') ? tipsSource.split('||').filter(Boolean) : (Array.isArray(tipsSource) ? tipsSource : []);
                tips.forEach((t) => {
                    const li = document.createElement('li');
                    li.textContent = t;
                    tipsEl.appendChild(li);
                });
            } else {
                if (detailWrapper) detailWrapper.hidden = true;
            }
        };

        // Export for Tooltip reference
        window.showPatternCardModal = (patternId) => {
            const chartWrappers = document.querySelectorAll('.chart-wrapper');
            let pattern = null;
            for (const wrap of chartWrappers) {
                const script = wrap.querySelector('#chart-payload-json');
                if (script) {
                    try {
                        const payload = JSON.parse(script.textContent);
                        if (payload.candle_patterns) {
                            pattern = payload.candle_patterns.find(p => p.id === patternId);
                        }
                    } catch (e) { }
                }
                if (pattern) break;
            }

            if (pattern) {
                // Map fields to match the 'open' function expectations (dataset naming)
                const data = {
                    name: pattern.name,
                    action: pattern.action,
                    descLead: pattern.desc_lead,
                    descBody: pattern.desc_body,
                    svg: pattern.svg
                };
                open(data, false); // Card style only
            }
        };

        document.querySelectorAll('.pattern-detail-trigger').forEach((btn) => {
            btn.addEventListener('click', () => {
                lastFocus = btn;
                open(btn.dataset, true);
            });
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

    function initCrossModal() {
        const overlay = document.querySelector('[data-modal-cross-overlay]');
        if (!overlay) return;
        const closeBtn = overlay.querySelector('[data-modal-cross-close]');
        const detailsSection = document.getElementById('cross-details-section');
        const badge = document.getElementById('modal-cross-badge');
        const reason = document.getElementById('modal-cross-reason');
        const visual = document.getElementById('modal-cross-visual');

        const close = () => {
            overlay.classList.remove('is-open');
            setTimeout(() => { if (!overlay.classList.contains('is-open')) overlay.hidden = true; }, 300);
        };
        const open = (data) => {
            if (data && data.level) {
                if (detailsSection) detailsSection.style.display = 'block';
                if (badge) {
                    badge.className = `conf-badge ${data.colorClass}`;
                    badge.textContent = data.level + (data.icon ? ' ' + data.icon : '');
                }
                if (reason) reason.textContent = data.reason;
                if (visual) {
                    // Support both 'golden'/'dead' and 'gc'/'dc'
                    const isGolden = data.type === 'golden' || data.type === 'gc';
                    const isDead = data.type === 'dead' || data.type === 'dc';

                    if (isGolden) {
                        visual.textContent = '☀';
                        visual.style.color = '#eab308';
                    } else if (isDead) {
                        visual.textContent = '☠';
                        visual.style.color = '#3b82f6';
                    } else {
                        visual.textContent = '📈';
                        visual.style.color = 'var(--accent)';
                    }
                }
            } else {
                if (detailsSection) detailsSection.style.display = 'none';
                if (visual) {
                    visual.textContent = '📊';
                    visual.style.color = 'var(--accent)';
                }
            }
            overlay.hidden = false;
            // Force reflow
            overlay.offsetHeight;
            overlay.classList.add('is-open');
        };

        window.showCrossHelpModal = (e, data) => {
            if (e) {
                e.preventDefault();
                e.stopPropagation();
            }
            open(data);
        };

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

    function initBackToTop() {
        const btn = document.getElementById('backToTop');
        if (!btn) return;

        const updateVisibility = () => {
            const viewportHeight = window.innerHeight;
            if (window.scrollY > viewportHeight) {
                btn.removeAttribute('hidden');
                btn.classList.add('is-visible');
            } else {
                btn.classList.remove('is-visible');
                // Optional: set hidden after transition
                // setTimeout(() => { if(!btn.classList.contains('is-visible')) btn.setAttribute('hidden', ''); }, 300);
            }
        };

        window.addEventListener('scroll', updateVisibility, { passive: true });

        btn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
            // Also blur button after click for better focus management (optional)
            btn.blur();
        });

        // Initial check
        updateVisibility();
    }

    // --- Init & HTMX Support ---
    bindTabButtons();
    renderCandleCharts();
    initPatternModal();
    initCrossModal();
    initBackToTop();

    window.initCharts = () => {
        bindTabButtons();
        renderCandleCharts();
        initBackToTop();
    };

    document.body.addEventListener('htmx:afterSwap', () => {
        window.initCharts();
    });

})();
