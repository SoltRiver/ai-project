---
description: Perform an architectural review on a set of files using the Architect skill.
---

# Architect Review Workflow

1.  **Preparation**
    -   Identify the files to be reviewed.
    -   Read `docs/architecture/coding_standards.md` to refresh memory on principles.
    -   Read `.agent/skills/Architect.md` to adopt the persona.

2.  **Analysis**
    -   For each file:
        -   Read the file content using `view_file`.
        -   Look for:
            -   Repeated logic (DRY violation)
            -   Deeply nested conditionals (KISS violation)
            -   Mixed responsibilities (e.g., SQL in a router) (Separation of Concerns violation)
            -   Hardcoded strings/magic numbers (Commonization opportunity)
            -   English comments (Violation of Project Rule)

3.  **Reporting**
    -   Create a summary report in the chat (or a temporary markdown file).
    -   Format:
        ```markdown
        ## File: [filename]
        - [Score]: 1-5 (5 is best)
        - [Issues]: List of violations
        - [Suggestions]: Concrete refactoring steps
        ```

4.  **Action (Optional)**
    -   If the user approves, proceed to refactor the code based on the suggestions.
