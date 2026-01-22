---
name: Reusable Components
description: Guidelines for creating and using reusable components to improve code quality and maintainability.
---

# Reusable Components Skill

To maintain high code quality and reduce technical debt, you must prioritize creating and using reusable components over ad-hoc implementations.

## When to Apply
-   **New Features**: When designing a new UI element or logic flow.
-   **Refactoring**: When modifying existing code and noticing duplication (Rule of Three).
-   **Review**: When Codex or a reviewer flags duplicate code.

## Guidelines by Technology

### 1. HTML / Templates (Jinja2)
-   **Partials**: If a block of HTML is used in more than one place (e.g., a card, a specific button style, a modal), extract it to a partial `_segment.html`.
-   **Macros**: Use Jinja2 macros for repetitive elements with varying data (e.g., rendering a status badge with different colors/text).
    ```jinja2
    {% macro status_badge(label, color='gray') %}
    <span class="badge badge-{{ color }}">{{ label }}</span>
    {% endmacro %}
    ```

### 2. CSS / Styling
-   **Utility Classes**: Avoid writing deep nested selectors for one-off elements. Use or create utility classes in `theme.css`.
-   **Variables**: Always use CSS variables (`var(--primary-color)`) for colors, spacing, and fonts. Do not hardcode magic numbers.
-   **Modules**: Group related styles (e.g., `.card`, `.btn`) together. If a style block grows too large, consider splitting the CSS file (if the framework supports it) or clearly sequestering it with comments.

### 3. JavaScript
-   **Utility Functions**: Extract logic that transforms data (e.g., date formatting, number formatting, API fetch wrappers) into pure functions.
-   **Classes/Modules**: Encapsulate complex logic (e.g., specific Chart interactions) into Classes or Modules rather than leaving them in the global scope or a massive single function.
-   **No Magic values**: Define constants for configuration values (e.g., `maxItems`, `refreshInterval`).

## Implementation Checklist
1.  **Search**: Before implementing, search the codebase (`grep_search`) for similar existing implementations.
2.  **Extract**: If duplication is found, refactor the common logic into a shared component *first*.
3.  **Implement**: Use the new shared component for your task.
4.  **Document**: Add a brief comment (JSDoc or standard code comment) explaining the input/output of the reproducible component.
