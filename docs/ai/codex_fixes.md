# Codex Review Fixes Log

This document tracks bugs, errors, and improvement suggestions identified by Codex reviews, along with the applied fixes.

## Date: 2026-01-20

### 1. HTML Duplication in `_tab_fundamental.html`
- **Issue**: `replace_file_content` duplicated the `tab-panel` structure (lines 1-18 duplicated at 22-39).
- **Fix**: Manually removed the duplicate block and corrected the `{% for group %}` loop structure.
- **Learnings**: Use strict `StartLine`/`EndLine` or `multi_replace_file_content` when replacing large blocks to avoid regex mismatches.

### 2. Candlestick Analysis Robustness (`analyzer.py`)
- **Issue**: `analyze_candlestick` could return runtime errors if `open`, `close`, `high`, or `low` were `None` or `NaN`.
- **Fix**: Added explicit checks: `if open_price is None or ...` and `if math.isnan(open_price) ...` to return default `{'name': '-', 'type': '-'}`.
- **Learnings**: Always validate financial data inputs for `None` and `NaN` before mathematical operations.

### 3. Tooltip CSS Missing
- **Issue**: Frontend logic added classes `.tooltip-header`, `.t-label`, `.t-val` but styles were missing in `theme.css`.
- **Fix**: Added corresponding CSS classes to `theme.css` during the implementation phase (caught by self-verification/Codex hint).
