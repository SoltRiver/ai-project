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

5.  **Run Codex Review**:
    -   Start `codex` (if not running) or resume it.
    -   Send the command: `/review` (or "Review my changes...").
    -   **Important**: Explicitly ask Codex to check for:
        -   Potential bugs/regressions.
        -   Security issues.
        -   Code style/consistency.
    -   If Codex asks for permission to read files, grant it (`y`).

6.  **Record Findings**:
    -   Review the Codex output.
    -   If issues are found, fix them.
    -   **Mandatory**: Record the review findings and any fixes in `docs/ai/codex_fixes.md`.
    -   Format: Date, Scope, Findings, Actions Taken.

7.  **Finalize & Push**:
    -   **If Findings Existed**: Ensure `codex_fixes.md` is updated FIRST. Then run `git add .`, `git commit -m "Refactor: [Description] (w/ Fixes)"`, `git push`.
    -   **If No Findings**: Run `git add .`, `git commit -m "Refactor: [Description] (Verified)"`, `git push` immediately after review completion.
