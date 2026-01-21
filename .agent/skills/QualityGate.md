---
name: Quality Gate
description: Enforce quality assurance steps before git commit.
---

# Quality Gate Skill

This skill acts as your "Quality Keeper". You must follow this checklist strictly before committing any code changes to the repository.

## Workflow

1.  **Implementation Complete**
    -   Verify the code satisfies the User's request.
    -   Ensure implementation plan is up to date (`implementation_plan.md`).

2.  **Regression Check**
    -   Run the `RegressionCheck` skill or manually check critical paths:
        -   Tab Switching (Fundamental <-> Chart)
        -   Data Loading (Interval changes)
        -   Interactivity (Tooltips, Drag, Scroll)
    -   **Use Browser Subagent** to verify these.

3.  **Codex Review**
    -   Run the `codex` command: `codex "Review my changes in [files] for logic, security, and regression risks."`
    -   **Constraint**: If `codex` CLI is unavailable or unresponsive, act as the reviewer yourself ("Simulated Codex Review") and scrutinize the diffs.
    -   **Note**: If the `codex` command prompts for input, select the first option (usually "Yes, proceed").

4.  **Fix Issues**
    -   Address *all* critical or high-severity issues found by Codex or yourself.
    -   If fixes require complex changes, restart from Step 1.

5.  **Documentation**
    -   Log the review results in `docs/ai/codex_fixes.md` (Date, Status, Findings, Actions).
    -   Update `walkthrough.md` with verification results (Screenshots/Logs).

6.  **Git Commit & Push**
    -   Only proceed if Steps 1-5 are **Done** and **Passed**.
    -   Command: `git commit -m "Type: Description (Verified)"`
    -   Push: `git push`

## Checklist Template

Use this mental (or scratchpad) checklist:

- [ ] Implementation Verified
- [ ] Regression Test Passed (Browser Verified)
- [ ] Codex Review Run (or Simulated)
- [ ] Issues Fixed & Verified
- [ ] Documentation Updated (`codex_fixes.md` + `walkthrough.md`)
- [ ] Ready to Commit
