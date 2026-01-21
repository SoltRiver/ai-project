---
description: Test procedure for checking regressions in Stock Chart logic
---

# Regression Testing Procedure

Before notifying the user of completion, ANY changes to `static/js/app.js` or chart-related logic MUST be verified against this checklist using the `browser_subagent`.

## 1. Visual Load Check
- [ ] Navigate to a stock detail page (e.g., `/stocks/7203`).
- [ ] **Verify Chart Exists**: Ensure the canvas element is visible and not blank/white.
- [ ] **Verify No Spinner**: Ensure the loading spinner (if any) has disappeared.
- [ ] **Verify No Console Errors**: Capture logs and confirm clean output.

## 2. Interactive Features Check
- [ ] **Horizontal Scroll**:
    - Drag the chart horizontally (mousedown -> move -> mouseup).
    - Take a screenshot during/after drag to verify the candles moved (change in data view).
- [ ] **Tooltip & Cursor**:
    - Hover over candles. Cursor should change to `pointer`. Tooltip should appear.
    - Hover over background. Cursor should be `grab`.
- [ ] **Timeframe Switch**:
    - Click a different interval tab (e.g., "週足" or "Weekly").
    - **Verify Persistence**: After swap, try dragging or hovering again. Features MUST still work (HTMX re-init check).

## 3. Cross Indicators (If applicable)
- [ ] Hover over a Golden/Dead Cross icon (Sun/Skull).
- [ ] Verify specific tooltip ("ゴールデンクロス" etc.) appears.

## 4. Crash Check
- [ ] Reload the page and ensure it renders cleanly every time.

## Automation Helper (Copy-Paste for Browser Subagent)
```text
Navigate to http://localhost:8000/stocks/7203.
1. Check for console errors.
2. Verify canvas is visible and drawn (not blank).
3. Drag chart to test scroll.
4. Click 'Weekly' tab (or similar) to test HTMX swap.
5. Drag chart again to verify re-init.
6. Return summary of pass/fail.
```
