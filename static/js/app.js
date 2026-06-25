(function () {
    // Theme is now handled by Alpine.js in base.html
    // Tabs are now handled by Alpine.js in detail.html

    const getColors = () => {
        const styles = getComputedStyle(document.documentElement);
        const isDark = document.documentElement.classList.contains('dark');
        return {
            text: styles.getPropertyValue('--text').trim() || (isDark ? '#e5e7eb' : '#1f2937'),
            muted: styles.getPropertyValue('--muted').trim() || '#9ca3af',
            positive: styles.getPropertyValue('--positive').trim() || '#22c55e',
            negative: styles.getPropertyValue('--negative').trim() || '#ef4444',
            neutral: styles.getPropertyValue('--neutral').trim() || '#94a3b8',
            border: styles.getPropertyValue('--border').trim() || (isDark ? '#1f2937' : '#e5e7eb'),
            panel: styles.getPropertyValue('--panel').trim() || (isDark ? '#111827' : '#ffffff'),
            chartGrid: styles.getPropertyValue('--chart-grid').trim() || (isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.05)'),
            chartCrosshair: styles.getPropertyValue('--chart-crosshair').trim() || 'rgba(14, 165, 233, 0.3)',
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
            const card = wrapper.closest('.chart-card');
            const smaLegend = card ? card.querySelector('.sma-legend') : null;

            if (!payloadScript || !canvas || !tooltip) {
                return;
            }

            let payload;
            try {
                payload = JSON.parse(payloadScript.textContent);
            } catch (_) {
                return;
            }
            const allPoints = payload.points || [];
            if (!allPoints.length) return;

            const samplePoints = allPoints.slice(-5);
            const allKeys = new Set();
            samplePoints.forEach(p => Object.keys(p).forEach(k => allKeys.add(k)));
            const smaKeys = Array.from(allKeys).filter(k => k.startsWith('SMA'));
            const smaNums = smaKeys.map(k => ({ key: k, num: parseInt(k.replace('SMA', ''), 10) }))
                .sort((a, b) => a.num - b.num);
            const sortedSmaKeys = smaNums.map(o => o.key);

            let crossPair = null;
            if (sortedSmaKeys.length >= 2) {
                crossPair = { short: sortedSmaKeys[0], long: sortedSmaKeys[1] };
            }

            const smaColors = {
                'SMA25': '#f59e0b', 'SMA75': '#8b5cf6', 'SMA200': '#3b82f6',
                'SMA13': '#f59e0b', 'SMA26': '#8b5cf6', 'SMA52': '#3b82f6',
                'SMA5': '#ef4444', 'SMA20': '#f59e0b', 'SMA60': '#3b82f6',
                'SMA12': '#f59e0b', 'SMA24': '#8b5cf6', 'SMA60': '#3b82f6'
            };

            const crosses = [];
            if (crossPair) {
                const k1 = crossPair.short, k2 = crossPair.long;
                for (let i = 1; i < allPoints.length; i++) {
                    const prev1 = allPoints[i - 1][k1], prev2 = allPoints[i - 1][k2];
                    const curr1 = allPoints[i][k1], curr2 = allPoints[i][k2];
                    if (prev1 != null && prev2 != null && curr1 != null && curr2 != null) {
                        if (prev1 < prev2 && curr1 >= curr2) crosses.push({ index: i, type: 'golden', price: curr1, label: 'GC' });
                        else if (prev1 > prev2 && curr1 <= curr2) crosses.push({ index: i, type: 'dead', price: curr1, label: 'DC' });
                    }
                }
            }

            function updateMainLegend(point) {
                const sub = document.querySelector('.chart-sub');
                if (!sub || !point) return;
                const o = fmtPrice(point.open), h = fmtPrice(point.high), l = fmtPrice(point.low), c = fmtPrice(point.close);
                // 使用 Unicode 轉義序列以避免編碼問題 (\u59CB\u5024=始値, \u9AD8\u5024=高値, \u5B89\u5024=安値, \u7D42\u5024=終値)
                sub.innerHTML = `<span class="l-item"><span class="l-label">\u59CB\u5024</span><span class="l-val">${o}</span></span><span class="l-item"><span class="l-label">\u9AD8\u5024</span><span class="l-val">${h}</span></span><span class="l-item"><span class="l-label">\u5B89\u5024</span><span class="l-val">${l}</span></span><span class="l-item"><span class="l-label">\u7D42\u5024</span><span class="l-val">${c}</span></span>`;
            }

            function updateLegend(point) {
                if (!smaLegend) return;
                const select = document.querySelector('select[name="interval"]'), interval = select ? select.value : '1d';
                let unit = interval.includes('wk') || interval === 'weekly' ? '週' : interval.includes('mo') || interval === 'monthly' ? 'ヶ月' : '日';
                let html = '';
                sortedSmaKeys.forEach((k, index) => {
                    const val = point ? point[k] : null, color = smaColors[k] || colors.text, valStr = fmtPrice(val);
                    const numMatch = k.match(/\d+/), num = numMatch ? numMatch[0] : '';
                    let role = sortedSmaKeys.length === 3 ? (index === 0 ? '短期' : index === 1 ? '中期' : '長期') : (sortedSmaKeys.length === 2 ? (index === 0 ? '短期' : '長期') : '');
                    const label = (role && num) ? `${role}(${num}${unit})` : k.toUpperCase();
                    html += `<span class="sma-item" style="color:${color}"><span style="opacity:0.8">${label}</span> <span style="font-weight:700">${valStr}</span></span>`;
                });
                smaLegend.innerHTML = html;
            }

            if (allPoints.length > 0) {
                const last = allPoints[allPoints.length - 1];
                updateLegend(last);
                updateMainLegend(last);
            }

            let viewCount = Math.min(allPoints.length, 100), viewIndex = Math.max(0, allPoints.length - viewCount);
            let isDragging = false, lastX = 0, dpr = window.devicePixelRatio || 1, width, height, yScale = null, selectedDataIdx = null, selectedCrossIdx = null, isSticky = false;
            // イベントハンドラーから参照できるよう、draw()内のレイアウト変数をスコープ外で宣言
            let chartLeft = 75, chartRight = 0, priceTop = 40, volumeBottom = 0;

            function updateDimensions() {
                const rect = wrapper.getBoundingClientRect();
                width = Math.max(100, rect.width - 32);
                height = parseInt(canvas.getAttribute('height'), 10) || 420;
                canvas.width = width * dpr; canvas.height = height * dpr;
                canvas.style.width = `${width}px`; canvas.style.height = `${height}px`;
            }
            updateDimensions();
            // canvasの幅が0の場合は複数回リトライしてチャートを初期化する
            if (width <= 100) {
                let retryCount = 0;
                const maxRetries = 5;
                const retryInterval = setInterval(() => {
                    retryCount++;
                    updateDimensions();
                    if (width > 100 || retryCount >= maxRetries) {
                        clearInterval(retryInterval);
                        draw();
                    }
                }, 150);
            }
            let ctx = canvas.getContext('2d');

            // ツールチップ表示関数（レキシカルスコープの変数にアクセス可能にするため内部に移動）
            function showTooltip(point, x, clientY, rect) {
                // コンテンツ構築
                // 日付フォーマット: 2025/12/19 -> 2025-12-19
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

                    // パターン名リンク：名前とカテゴリ（陽線/陰線）の両方で一致させる
                    let patternNameHtml = point.candle_name;
                    if (payload.candle_patterns) {
                        // まず名前＋カテゴリで完全一致を試行
                        let pattern = payload.candle_patterns.find(p => p.name === point.candle_name && p.category === point.candle_type);
                        // 見つからなければ名前のみで検索（十字線・コマ等のカテゴリ「迷い」用）
                        if (!pattern) {
                            pattern = payload.candle_patterns.find(p => p.name === point.candle_name);
                        }
                        if (pattern) {
                            patternNameHtml = `<a href="javascript:void(0)" class="t-pattern-link" onclick="window.showPatternCardModal('${pattern.id}')">${point.candle_name}</a>`;
                        }
                    }
                    html += `<div class="tooltip-row"><span class="t-label">種類</span><span class="t-val">${patternNameHtml}</span></div>`;
                }

                tooltip.innerHTML = html;
                tooltip.style.display = 'block';
                tooltip.style.pointerEvents = 'auto'; // ツールチップ内でのクリックを有効化

                // 表示位置の設定
                const tWidth = tooltip.offsetWidth || 180;
                const tHeight = tooltip.offsetHeight || 120;
                let left = x + 20;
                let top = (clientY - rect.top) - 20;

                // 境界判定ロジック
                if (left + tWidth > width) left = x - tWidth - 20;
                if (top + tHeight > height) top = height - tHeight - 10;
                if (top < 0) top = 10;

                tooltip.style.left = `${left}px`;
                tooltip.style.top = `${top}px`;
                tooltip.style.transform = 'none';
            }

            // GC/DCの信頼度スコアを計算する関数（allPointsにアクセスできるよう内部に定義）
            function calculateCrossConfidence(cross, prevPoint, currPoint, shortKey, longKey) {
                if (!prevPoint || !currPoint) return { level: '未確定', icon: '', reason: 'データ不足', colorClass: 'conf-unconfirmed' };

                const slope = currPoint[longKey] - prevPoint[longKey];
                const isGC = cross.type === 'golden';
                const close = currPoint.close;
                const longMa = currPoint[longKey];

                // 最新足かどうかで確定/未確定を判断
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

                // トレンド方向の一致チェック
                const trendMatches = isGC ? (slope > 0) : (slope < 0);
                // 終値が有利なサイドにあるかチェック
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

            // DC/GC用のツールチップ表示関数
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

                // 1. 日付
                const formattedDate = (point.label || '').replace(/\//g, '-');
                let html = `<div class="tooltip-header" style="border:none; padding-bottom:0;">${formattedDate}</div>`;

                // 2. 状態（色とアイコンで強調）
                const statusText = isConfirmed ? '確定' : '未確定';
                const statusClass = isConfirmed ? 'status-confirmed' : 'status-unconfirmed';
                const statusIcon = isConfirmed ? '✅' : '⏳';
                html += `<div class="tooltip-row"><span class="t-label">状態</span><span class="t-val ${statusClass}"><span class="status-icon">${statusIcon}</span>${statusText}</span></div>`;

                // 3. 線種
                html += `<div class="tooltip-row"><span class="t-label">線種</span><span class="t-val" style="color:${crossColor}; font-weight:700;">${crossTitle}</span></div>`;

                // 4. 条件
                const op = isGolden ? '>' : '<';
                html += `<div class="tooltip-row"><span class="t-label">条件</span><span class="t-val" style="font-size:0.75rem;">短期(${shortNum}) ${op} 長期(${longNum})</span></div>`;

                // 5. 信頼度評価
                const badgeContent = res.level + (res.icon ? ' ' + res.icon : '');
                const resJson = JSON.stringify({ ...res, type: cross.type }).replace(/"/g, '&quot;');
                html += `<div class="tooltip-row">
                            <span class="t-label">信頼度評価 <span class="conf-help-icon" onclick="window.showCrossHelpModal(event, ${resJson})">?</span></span>
                            <span class="conf-badge ${res.colorClass}">${badgeContent}</span>
                        </div>`;

                // 7. 短期移動平均
                html += `<div class="tooltip-row"><span class="t-label">短期(${shortNum})</span><span class="t-val">${fmtPrice(point[shortKey])}</span></div>`;

                // 8. 長期移動平均
                html += `<div class="tooltip-row"><span class="t-label">長期(${longNum})</span><span class="t-val">${fmtPrice(point[longKey])}</span></div>`;

                // 9. 終値
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

            function draw() {
                if (!ctx) {
                    return;
                }
                const points = allPoints.slice(viewIndex, viewIndex + viewCount);
                if (!points.length) {
                    ctx.clearRect(0, 0, width * dpr, height * dpr);
                    ctx.fillStyle = colors.muted; ctx.font = '14px sans-serif'; ctx.textAlign = 'center';
                    ctx.fillText('\u30C7\u30FC\u30BF\u304C\u3042\u308A\u307E\u305B\u3093', (width / 2) * dpr, (height / 2) * dpr); // データがありません
                    return;
                }
                ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
                ctx.clearRect(0, 0, width, height);

                const topMargin = 40, bottomMargin = 20, availableHeight = height - topMargin - bottomMargin;
                const priceAreaHeight = availableHeight * 0.60, priceBottom = priceTop + priceAreaHeight;
                const volumeHeight = availableHeight * 0.25, volumeTop = height - bottomMargin - volumeHeight;
                // レイアウト変数を更新（イベントハンドラーから参照するため外部スコープ変数に代入）
                chartLeft = 75; chartRight = width - 40; priceTop = topMargin; volumeBottom = height - bottomMargin;
                const chartWidth = chartRight - chartLeft;
                const step = chartWidth / Math.max(1, points.length), candleWidth = Math.max(1, step * 0.65);

                const highs = points.map(p => p.high), lows = points.map(p => p.low);
                sortedSmaKeys.forEach(k => points.forEach(p => { if (p[k] != null) { highs.push(p[k]); lows.push(p[k]); } }));
                const yMin = Math.min(...lows) * 0.99, yMax = Math.max(...highs) * 1.01;
                yScale = (val) => priceBottom - ((val - yMin) / (yMax - yMin)) * priceAreaHeight;
                const getX = (i) => chartLeft + i * step + step / 2;

                // Axis Labels
                ctx.fillStyle = colors.muted; ctx.font = '11px sans-serif';
                ctx.textAlign = 'right'; ctx.fillText('株価', chartLeft - 8, priceTop - 15);
                ctx.fillText('出来高', chartLeft - 8, volumeTop - 4);

                // Grid (Price)
                const ticks = 5;
                for (let i = 0; i <= ticks; i++) {
                    const val = yMin + ((yMax - yMin) * i) / ticks, y = priceBottom - (i / ticks) * priceAreaHeight;
                    ctx.strokeStyle = colors.chartGrid; ctx.setLineDash([4, 4]);
                    ctx.beginPath(); ctx.moveTo(chartLeft, y); ctx.lineTo(chartRight, y); ctx.stroke();
                    ctx.setLineDash([]); ctx.fillStyle = colors.muted; ctx.fillText(val.toFixed(0), chartLeft - 6, y);
                }

                // Volume Labels (Simplified)
                const maxVol = Math.max(...points.map(p => p.volume || 0)) || 1;
                ctx.fillText(fmtVolume(maxVol), chartLeft - 6, volumeTop + 10);

                // Candles
                points.forEach((p, i) => {
                    const xCenter = getX(i), x = xCenter - candleWidth / 2, isUp = p.close >= p.open;
                    const isHovered = (selectedDataIdx !== null && (viewIndex + i) === selectedDataIdx);

                    // ホバー時のハイライト縦帯
                    if (isHovered) {
                        const step = (chartRight - chartLeft) / viewCount;
                        ctx.fillStyle = colors.chartCrosshair;
                        ctx.fillRect(xCenter - step / 2, priceTop, step, volumeBottom - priceTop);
                    }

                    ctx.fillStyle = isUp ? colors.positive : colors.negative;
                    ctx.beginPath(); ctx.strokeStyle = ctx.fillStyle; ctx.lineWidth = Math.max(1, 1 * dpr);
                    ctx.moveTo(xCenter, yScale(p.high)); ctx.lineTo(xCenter, yScale(p.low)); ctx.stroke();
                    const yHigh = yScale(Math.max(p.open, p.close)), yLow = yScale(Math.min(p.open, p.close));
                    // ホバー時はローソク足の幅を少し太くする
                    const drawWidth = isHovered ? Math.min(candleWidth * 1.5, step) : candleWidth;
                    const drawX = xCenter - drawWidth / 2;
                    ctx.fillRect(drawX, yHigh, drawWidth, Math.max(1, yLow - yHigh));
                });

                // SMAs
                sortedSmaKeys.forEach(k => {
                    ctx.strokeStyle = smaColors[k] || '#fff'; ctx.lineWidth = 1.5; ctx.beginPath();
                    let started = false;
                    for (let i = 0; i < points.length; i++) {
                        const val = points[i][k]; if (val == null) { started = false; continue; }
                        const x = getX(i), y = yScale(val);
                        if (!started) { ctx.moveTo(x, y); started = true; } else { ctx.lineTo(x, y); }
                    }
                    ctx.stroke();
                });

                // Volume Bars
                const vGrad = ctx.createLinearGradient(0, volumeTop, 0, volumeBottom);
                vGrad.addColorStop(0, colors.gradientFrom); vGrad.addColorStop(1, colors.gradientTo);
                points.forEach((p, i) => {
                    const h = (p.volume / maxVol) * volumeHeight, x = getX(i) - candleWidth / 2;
                    const isHovered = (selectedDataIdx !== null && (viewIndex + i) === selectedDataIdx);
                    ctx.fillStyle = '#FFD700'; ctx.globalAlpha = isHovered ? 0.8 : 0.3;
                    ctx.fillRect(x, volumeBottom - h, candleWidth, Math.max(1, h));
                    ctx.fillStyle = vGrad; ctx.globalAlpha = isHovered ? 0.9 : 0.4;
                    ctx.fillRect(x, volumeBottom - h, candleWidth, Math.max(1, h));
                    ctx.globalAlpha = 1.0;
                });

                // Cross Events
                crosses.forEach(c => {
                    if (c.index >= viewIndex && c.index < viewIndex + viewCount) {
                        const i = c.index - viewIndex, x = getX(i);
                        ctx.strokeStyle = c.type === 'golden' ? '#eab308' : '#3b82f6'; ctx.lineWidth = 2;
                        ctx.beginPath(); ctx.moveTo(x, yScale(c.price)); ctx.lineTo(x, priceTop); ctx.stroke();
                        ctx.fillStyle = ctx.strokeStyle; ctx.beginPath(); ctx.arc(x, yScale(c.price), 4, 0, Math.PI * 2); ctx.fill();
                        ctx.font = '16px sans-serif'; ctx.textAlign = 'center'; ctx.fillText(c.type === 'golden' ? '☀' : '☠', x, priceTop - 2);
                    }
                });

                if (selectedDataIdx !== null && selectedDataIdx >= viewIndex && selectedDataIdx < viewIndex + viewCount) {
                    const i = selectedDataIdx - viewIndex, x = getX(i);
                    showTooltip(allPoints[selectedDataIdx], x, canvas.getBoundingClientRect().top + yScale(allPoints[selectedDataIdx].close), canvas.getBoundingClientRect());
                }
                if (selectedCrossIdx !== null) {
                    const c = crosses.find(x => x.index === selectedCrossIdx);
                    if (c && c.index >= viewIndex && c.index < viewIndex + viewCount) {
                        showCrossTooltip(c, getX(c.index - viewIndex), priceTop, canvas.getBoundingClientRect());
                    }
                }
            }

            canvas.addEventListener('click', (e) => {
                const rect = canvas.getBoundingClientRect(), x = e.clientX - rect.left, y = e.clientY - rect.top;
                const step = (chartRight - chartLeft) / viewCount;

                // すでに固定状態（isSticky）である場合、どこをクリックしても固定を解除して消す
                if (isSticky) {
                    isSticky = false;
                    selectedDataIdx = null;
                    selectedCrossIdx = null;
                    tooltip.style.display = 'none';
                    draw();
                    return;
                }

                // DC/GC の判定（固定されていない場合のみ新規で固定する）
                let clickedCross = crosses.find(c => {
                    if (c.index < viewIndex || c.index >= viewIndex + viewCount) return false;
                    const cx = chartLeft + (c.index - viewIndex) * step + step / 2;
                    const cyCircle = yScale(c.price);
                    const cyLabel = priceTop - 10;
                    return Math.abs(x - cx) < 15 && (Math.abs(y - cyCircle) < 15 || Math.abs(y - cyLabel) < 20);
                });

                if (clickedCross) {
                    isSticky = true;
                    selectedCrossIdx = clickedCross.index;
                    selectedDataIdx = null;
                    draw();
                    return;
                }

                // ローソク足・出来高バーの判定
                const idx = Math.floor((x - chartLeft) / step) + viewIndex;
                if (idx >= viewIndex && idx < viewIndex + viewCount && idx < allPoints.length) {
                    isSticky = true;
                    selectedDataIdx = idx;
                    selectedCrossIdx = null;
                    draw();
                } else {
                    isSticky = false;
                    selectedDataIdx = null;
                    selectedCrossIdx = null;
                    tooltip.style.display = 'none';
                    draw();
                }
            });

            canvas.addEventListener('mousedown', (e) => { isDragging = true; lastX = e.clientX; canvas.style.cursor = 'grabbing'; });
            window.addEventListener('mouseup', () => { isDragging = false; if (canvas) canvas.style.cursor = 'grab'; });
            canvas.addEventListener('mousemove', (e) => {
                const rect = canvas.getBoundingClientRect(), x = e.clientX - rect.left, y = e.clientY - rect.top;
                const step = (chartRight - chartLeft) / viewCount;

                if (isDragging) {
                    const deltaX = e.clientX - lastX; lastX = e.clientX;
                    viewIndex = Math.max(0, Math.min(viewIndex - deltaX / ((chartRight - chartLeft) / viewCount), allPoints.length - viewCount));
                    draw(); return;
                }

                // DC/GC のホバー判定（crossesが存在すれば判定する）
                let hoveredCross = null;
                if (crosses.length > 0) {
                    hoveredCross = crosses.find(c => {
                        if (c.index < viewIndex || c.index >= viewIndex + viewCount) return false;
                        const cx = chartLeft + (c.index - viewIndex) * step + step / 2;
                        const cyCircle = yScale(c.price);
                        const cyLabel = priceTop - 10;
                        return Math.abs(x - cx) < 15 && (Math.abs(y - cyCircle) < 15 || Math.abs(y - cyLabel) < 20);
                    });
                }

                if (hoveredCross) {
                    canvas.style.cursor = 'pointer';
                    if (!isSticky) {
                        selectedCrossIdx = hoveredCross.index;
                        selectedDataIdx = null;
                        draw();
                    }
                    return;
                }

                // ローソク足または出来高バーのホバー判定
                const idx = Math.floor((x - chartLeft) / step) + viewIndex;
                if (idx >= viewIndex && idx < viewIndex + viewCount && idx < allPoints.length && y >= priceTop && y <= volumeBottom) {
                    canvas.style.cursor = 'pointer';
                    if (!isSticky) {
                        selectedDataIdx = idx;
                        selectedCrossIdx = null;
                        updateLegend(allPoints[idx]);
                        updateMainLegend(allPoints[idx]);
                        draw();
                    } else {
                        updateLegend(allPoints[idx]);
                        updateMainLegend(allPoints[idx]);
                    }
                } else {
                    canvas.style.cursor = 'grab';
                    if (!isSticky) {
                        selectedDataIdx = null;
                        selectedCrossIdx = null;
                        tooltip.style.display = 'none';
                        draw();
                    }
                }
            });

            canvas.addEventListener('mouseleave', () => {
                if (!isSticky) {
                    selectedDataIdx = null;
                    selectedCrossIdx = null;
                    tooltip.style.display = 'none';
                    if (allPoints.length > 0) {
                        const last = allPoints[allPoints.length - 1];
                        updateLegend(last);
                        updateMainLegend(last);
                    }
                    draw();
                }
            });

            canvas.addEventListener('wheel', (e) => {
                e.preventDefault();
                viewIndex = Math.max(0, Math.min(viewIndex + (e.deltaY > 0 ? 5 : -5), allPoints.length - viewCount));
                draw();
            }, { passive: false });

            draw();
        });
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

    // --- 初期化 & HTMX連携 ---
    renderCandleCharts();
    initPatternModal();
    initCrossModal();
    initBackToTop();

    window.initCharts = () => {
        renderCandleCharts();
        initBackToTop();
    };

    window.renderCandleCharts = renderCandleCharts;

    // HTMXのスワップ完了後にチャートを初期化する
    // afterSwap: DOMへの挿入直後（レイアウトが確定する前の場合もある）
    document.body.addEventListener('htmx:afterSwap', () => {
        window.initCharts();
    });

    // afterSettle: すべての遷移が完了した後（こちらのほうが確実）
    document.body.addEventListener('htmx:afterSettle', () => {
        // チャートが初期化済みでない場合のみ再実行する
        const uninitializedWrappers = document.querySelectorAll('.chart-wrapper:not([data-chart-initialized="true"])');
        if (uninitializedWrappers.length > 0) {
            renderCandleCharts();
        }
    });

})();
