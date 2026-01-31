---
name: UI/UX Guidelines
description: Standard checklist for UI/UX design, gaze flow, and visual integrity.
---

# UI/UX Guidelines Skill

When performing any frontend work, you must adopt the persona of a **UI/UX Specialist** and verify the following points.

## 1. UI/UX Consideration
-   **Usability**: Is the feature intuitive? Can a new user understand it without explanation?
-   **Feedback**: Does the system provide immediate feedback for actions (hover states, click effects, loading spinners)?
-   **Consistency**: Do the new elements match the existing design language (colors, spacing, typography)?

## 2. Gaze Flow (Visual Hierarchy)
-   **Natural Flow**: Does the eye move naturally from the most important elements (Headers/Titles) to Control Elements (Search/Buttons) and then to Data?
-   **Grouping**: Are related controls (e.g., Search Box and Action Buttons) grouped together?
    -   *Bad*: Search on left, Buttons far right.
    -   *Good*: Search and Buttons adjacent.
-   **Proximity**: Are related labels and inputs close to each other?

## 3. Visual Integrity
-   **No Overlaps**: Ensure elements do not overlap, especially on smaller screens or when content is dynamic.
    -   *Action*: Resize browser window to mobile width (~375px) and verify header/card layouts.
-   **Spacing**: Maintain sufficient whitespace (padding/margin) between major sections (e.g., Header vs Content). Avoid "cramped" layouts.
-   **Alignment**: Are text and interactions property aligned?

## 4. Component Functionality
-   **Interactivity**: Do buttons/inputs work as expected?
-   **Responsiveness**: Does the layout break on window resize? Use `flex-wrap` where appropriate.
-   **Edge Cases**: What happens with long text, empty states, or zero data?

## 5. General Best Practices (Heuristics)
-   **Visibility of System Status**: Always keep users informed about what is going on (e.g., "Saving...", "Loading...").
-   **Error Prevention & Recovery**:
    -   Ask for confirmation before destructive actions (e.g., Delete).
    -   Provide clear, human-readable error messages (not just "Error 500").
-   **Accessibility (A11y)**:
    -   **Contrast**: Ensure text has sufficient contrast against background (Target WCAG AA, ~4.5:1).
        -   *Action*: Check dark mode specifically. Background `#1a1b26` needs text brighter than `#94a3b8` (Slate-400).
    -   **Keyboard Support**: Can the user navigate via Tab?
    -   **Labels**: Use `aria-label` or `<label>` for inputs.
-   **Fitts's Law (Clickability)**: Make interactive elements large enough to click easily (add padding to buttons/links).
-   **Aesthetic & Minimalist Design**: Do not overwhelm the user with irrelevant information. Remove "chartjunk" or redundant text.

## Implementation Checklist
-   [ ] **Design Review**: Before implementation, plan the layout to satisfy Gaze Flow.
-   [ ] **Code Implementation**: Use flexible layouts (`flexbox`, `grid`, `gap`, `box-sizing: border-box`) to prevent overlaps.
-   [ ] **Browser Verification**: Explicitly check for Overlaps, Gaze Flow, and Functionality using the `browser_subagent`.
