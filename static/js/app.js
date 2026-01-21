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
                html += `<span class="l-item" style="color:var(--muted); font-size:0.9rem;">${t}</span>`;

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
                    const isUp = p.close >= p.open;

                    // Base color + Gradient overlay
                    ctx.fillStyle = isUp ? colors.positive : colors.negative;
                    ctx.globalAlpha = 0.3;
                    ctx.fillRect(xCenter - candleWidth / 2, volumeBottom - barHeight, candleWidth, Math.max(1, barHeight));

                    ctx.fillStyle = vGradient;
                    ctx.globalAlpha = 0.4;
                    ctx.fillRect(xCenter - candleWidth / 2, volumeBottom - barHeight, candleWidth, Math.max(1, barHeight));
                    ctx.globalAlpha = 1.0;
                });

                // Sticky Tooltip Rendering
                if (selectedDataIdx !== null && yScale) {
                    // Check if in view
                    if (selectedDataIdx >= viewIndex && selectedDataIdx < viewIndex + viewCount) {
                        const i = selectedDataIdx - viewIndex;
                        const x = getX(i);
                        const point = allPoints[selectedDataIdx];
                        // If sticky, where to position? slightly offset from candle center?
                        // Or reuse mouse position? Mouse position is not available in draw().
                        // Pin it relative to candle top/bottom or fixed.
                        // Let's mimic "top right of candle".
                        const rect = canvas.getBoundingClientRect();
                        const virtualY = rect.top + yScale(point.close); // Approximate Y
                        showTooltip(point, x, virtualY, rect);
                    } else {
                        // Off screen
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

                const chartLeft = 50;
                const chartRight = width - 50;
                const chartWidth = chartRight - chartLeft;
                const step = chartWidth / viewCount;
                const idxInView = Math.floor((x - chartLeft) / step);
                const dataIdx = Math.floor(viewIndex + idxInView);

                if (dataIdx >= 0 && dataIdx < allPoints.length) {
                    // Strict Check: Did we click CANDLE?
                    // Sticky only locks if clicking the candle itself (or very close)
                    // If clicking empty space (bg/volume/top), resets.

                    if (!yScale) { selectedDataIdx = null; draw(); return; }

                    const point = allPoints[dataIdx];
                    const cHigh = yScale(point.high);
                    const cLow = yScale(point.low);
                    const yClick = e.clientY - rect.top;
                    const buffer = 10; // Generous buffer

                    if (yClick >= cHigh - buffer && yClick <= cLow + buffer) {
                        if (selectedDataIdx === dataIdx) {
                            // Same clicked -> Do nothing
                        } else {
                            selectedDataIdx = dataIdx;
                        }
                    } else {
                        // Clicked inside column but NOT on candle -> Reset
                        selectedDataIdx = null;
                    }
                    draw();
                } else {
                    selectedDataIdx = null; // Click outside
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
                // Check Y-Axis Hover for Tooltip (Only for Hover, strict check)
                // For pinned tooltip (selectedDataIdx !== null), we might skip strict Y check or keep it?
                // Request says: "Display tooltip for that candle". Usually implies ignoring Y position for pinned.
                // But let's reuse logic. If pinned, we pass a dummy 'force' flag? 

                // Construct Content
                let html = `<div class="tooltip-header">${point.label}</div>`;
                html += `<div class="tooltip-row"><span class="t-label">始値</span><span class="t-val">${fmtPrice(point.open)}</span></div>`;
                html += `<div class="tooltip-row"><span class="t-label">高値</span><span class="t-val">${fmtPrice(point.high)}</span></div>`;
                html += `<div class="tooltip-row"><span class="t-label">安値</span><span class="t-val">${fmtPrice(point.low)}</span></div>`;
                html += `<div class="tooltip-row"><span class="t-label">終値</span><span class="t-val">${fmtPrice(point.close)}</span></div>`;

                if (point.candle_name && point.candle_type) {
                    html += `<div class="tooltip-divider"></div>`;
                    html += `<div class="tooltip-row"><span class="t-label">形</span><span class="t-val">${point.candle_type}</span></div>`;
                    html += `<div class="tooltip-row"><span class="t-label">種類</span><span class="t-val">${point.candle_name}</span></div>`;
                }

                tooltip.innerHTML = html;
                tooltip.style.display = 'block';
                tooltip.style.pointerEvents = 'none';

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



            canvas.addEventListener('mousemove', (e) => {
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;

                // Dragging Logic
                if (isDragging) {
                    const deltaX = e.clientX - lastX;
                    lastX = e.clientX;

                    // Calculate sensitivity (pixels per bar)
                    const chartLeft = 50;
                    const chartRight = width - 50;
                    const chartWidth = chartRight - chartLeft;
                    const step = chartWidth / viewCount;

                    // Move viewIndex based on drag distance
                    // Drag Right -> Move View Left (Earlier) -> Decrease Index
                    const barsMoved = deltaX / step;
                    viewIndex -= barsMoved;

                    const maxIndex = Math.max(0, allPoints.length - viewCount);
                    viewIndex = Math.max(0, Math.min(viewIndex, maxIndex));

                    draw();
                    // Force cursor check after drag
                    // Simply resetting to grab is fine, but if we stop dragging over a candle, 
                    // we want to know. However, dragging usually implies movement.
                    return;
                }

                // Tooltip Logic
                // Recalculate layout metrics for hit testing
                const chartLeft = 50;
                const chartRight = width - 50;
                const chartWidth = chartRight - chartLeft;

                if (x < chartLeft || x > chartRight) {
                    tooltip.style.display = 'none'; draw();
                    if (allPoints.length > 0) {
                        const last = allPoints[allPoints.length - 1];
                        updateLegend(last);
                        updateMainLegend(last);
                    }
                    return;
                }


                // Check Cross Icon Hover FIRST (Higher priority for details?)
                // Or maybe transient?
                let hoveredCross = null;
                const my = e.clientY - rect.top;

                // Recalculate layout scope for hitbox
                const topMargin = 40; // Match draw()
                const priceTop = topMargin;

                // Visible Crosses
                for (const c of crosses) {
                    if (c.index >= viewIndex && c.index < viewIndex + viewCount) {
                        const i = c.index - viewIndex;
                        const cx = chartLeft + i * (chartWidth / viewCount) + (chartWidth / viewCount) / 2;
                        // Icon Position: cx, priceTop - 2 (bottom baseline). Size approx 16px.
                        // Hit box: +/- 20px X, priceTop - 25 to priceTop + 5 Y.
                        const iconTop = priceTop - 25;
                        const iconBottom = priceTop + 5;

                        if (Math.abs(x - cx) < 20 && my >= iconTop && my <= iconBottom) {
                            hoveredCross = c;
                            break;
                        }
                    }
                }

                if (hoveredCross) {
                    // Show Cross Tooltip
                    canvas.style.cursor = 'help'; // Indicate info

                    const p = allPoints[hoveredCross.index];
                    const label = hoveredCross.type === 'golden' ? 'ゴールデンクロス' : 'デッドクロス';
                    const color = hoveredCross.type === 'golden' ? '#eab308' : '#3b82f6';

                    let html = `<div class="tooltip-header" style="color:${color}">${label}</div>`;
                    html += `<div class="tooltip-time">${p.label}</div>`;
                    html += `<div class="tooltip-divider"></div>`;

                    // Add SMA Values involved
                    // We need to know which SMAs crossed. 
                    // 'sortedSmaKeys' has the order. Pair is sortedSmaKeys[0] vs [1].
                    if (sortedSmaKeys.length >= 2) {
                        const shortKey = sortedSmaKeys[0];
                        const longKey = sortedSmaKeys[1];
                        const shortVal = p[shortKey];
                        const longVal = p[longKey];

                        // Get nice labels (Short/Med/Long)
                        // We can reuse logic or just use keys
                        html += `<div class="tooltip-row"><span class="t-label">${shortKey}</span><span class="t-val">${fmtPrice(shortVal)}</span></div>`;
                        html += `<div class="tooltip-row"><span class="t-label">${longKey}</span><span class="t-val">${fmtPrice(longVal)}</span></div>`;
                    }

                    tooltip.innerHTML = html;
                    tooltip.style.display = 'block';

                    // Position
                    const tWidth = tooltip.offsetWidth || 180;
                    const tHeight = tooltip.offsetHeight || 100;
                    let left = x + 20;
                    let top = my + 20;
                    if (left + tWidth > width) left = x - tWidth - 20;
                    if (top + tHeight > height) top = height - tHeight - 10;

                    tooltip.style.left = `${left}px`;
                    tooltip.style.top = `${top}px`;
                    tooltip.style.transform = 'none';
                    return;
                }

                // If not hovering Cross, continue to Candle logic

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

                    // --- Sticky Tooltip Check ---

                    if (selectedDataIdx !== null) {
                        if (yScale) {
                            const yMouse = e.clientY - rect.top;
                            const cHigh = yScale(point.high);
                            const cLow = yScale(point.low);
                            const buffer = 4;
                            if (yMouse >= cHigh - buffer && yMouse <= cLow + buffer) {
                                canvas.style.cursor = 'pointer';
                            } else {
                                canvas.style.cursor = isDragging ? 'grabbing' : 'grab';
                            }
                        }
                    } else {
                        // Normal Hover: Show Tooltip (Relaxed logic)
                        if (!yScale) {
                            tooltip.style.display = 'none';
                            return;
                        }

                        const yMouse = e.clientY - rect.top;
                        const cHigh = yScale(point.high);
                        const cLow = yScale(point.low);
                        const buffer = 4;
                        const isHoveringCandle = (yMouse >= cHigh - buffer && yMouse <= cLow + buffer);

                        // Cursor indicates clickable (sticky) if on candle
                        if (isHoveringCandle) {
                            canvas.style.cursor = 'pointer';
                        } else {
                            canvas.style.cursor = isDragging ? 'grabbing' : 'grab';
                        }

                        // Tooltip Restriction (Round 8): Only show if hovering strict candle area
                        if (isHoveringCandle) {
                            const rectBox = canvas.getBoundingClientRect();
                            const virtualY = rectBox.top + yScale(point.close);
                            const xCenter = chartLeft + idxInView * step + step / 2;
                            showTooltip(point, xCenter, virtualY, rectBox);
                        } else {
                            tooltip.style.display = 'none';
                        }
                    }
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

    // --- Init & HTMX Support ---
    bindTabButtons();
    renderCandleCharts();
    initPatternModal();

    window.initCharts = () => {
        bindTabButtons();
        renderCandleCharts();
    };

    document.body.addEventListener('htmx:afterSwap', () => {
        window.initCharts();
    });

})();
