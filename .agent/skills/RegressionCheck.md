---
name: Regression Check
description: Check for regressions in existing features before running Codex review.
---

# Regression Check Skill

Before running the `codex` command or requesting a review, you must explicitly check if your changes have negatively impacted existing functionality.

## Steps

1.  **Identify Affected Areas**:
    -   List the features you modified.
    -   List the features that might be indirectly affected (e.g., shared components, global styles, event listeners).

2.  **Verify Existing Features**:
    -   **Navigation**: Do tabs still switch correctly?
    -   **Layout**: Are headers, footers, and sidebars still aligned?
    -   **Interactions**: Do tooltips, buttons, and scrolls still work as expected?
    -   **Data**: Is data still loading for other symbols/pages?

3.  **Browser Verification**:
    -   Use the `browser_subagent` to verify specifically that *old* features still work.
    -   Example: If you changed the chart, verify the fundamental tab still loads.

4.  **Codex Pre-Flight**:
    -   Only after verifying no regressions, proceed to run `codex`.
    -   If regressions are found, fix them *before* running `codex`.
