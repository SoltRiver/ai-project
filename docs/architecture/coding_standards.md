# Coding Standards & Best Practices

This document outlines the architectural principles and coding standards for the project. The "Architect" agent will use this as a reference to enforce quality.

## Core Principles

### 1. DRY (Don't Repeat Yourself)
- **Definition**: Every piece of knowledge must have a single, unambiguous, authoritative representation within a system.
- **Application**:
    - Extract repeated logic into helper functions or services.
    - Use partials/macros for shared HTML/Jinja2 templates.
    - If you copy-paste code more than once (Rule of Three), refactor it immediately.

### 2. KISS (Keep It Simple, Stupid)
- **Definition**: Systems work best if they are kept simple rather than made complicated.
- **Application**:
    - Avoid over-engineering pre-maturely.
    - Write code that is easy to read and understand.
    - Prefer explicit code over implicit "magic".

### 3. YAGNI (You Aren't Gonna Need It)
- **Definition**: Always implement things when you actually need them, never when you just foresee that you need them.
- **Application**:
    - Do not add features or abstractions "just in case".
    - Focus on the current requirements.

### 4. SOLID Principles
- **S - Single Responsibility Principle**: A class or module should have one, and only one, reason to change.
- **O - Open/Closed Principle**: Software entities should be open for extension, but closed for modification.
- **L - Liskov Substitution Principle**: Objects of a superclass shall be replaceable with objects of its subclasses.
- **I - Interface Segregation Principle**: Many client-specific interfaces are better than one general-purpose interface.
- **D - Dependency Inversion Principle**: Depend upon abstractions, not concretions.

## Architecture & Design

### Separation of Concerns
- **UI Layer**: `templates/`, `static/`. Handles presentation only. No business logic.
- **API Layer**: `routers/`. Handles HTTP requests/responses, validation. Delegates logic to Services.
- **Service Layer**: `services/`. Contains the core business logic.
- **Data Layer**: `models/`, `utils/`. Handles data access and storage.

### Modularization
- Organize code by feature or domain where possible.
- Avoid "God Objects" or massive files (e.g., if `app.py` gets too big, split routes into `routers/`).

### Abstraction
- Hide implementation details behind clear interfaces (functions/classes).
- When using external APIs, create a wrapper service (e.g., `StockService`) so the rest of the app doesn't know the specifics of the HTTP calls.

## Project Specific Rules

### 1. Comments & Documentation
- **Language**: Comments MUST be written in **Japanese**.
- **Clarity**: Write comments that explain *why*, not just *what*.
- **Docstrings**: All public functions and classes should have docstrings.

### 2. Error Handling
- Never silence errors implicitly.
- If a value cannot be retrieved, return `-` or `None` explicitly as appropriate for the context, but do not crash.
- Log errors where necessary.

### 3. UI/UX Verification
- Any visual change must be verified in the browser.
- Use `verify_indices_browser.py` or similar scripts to ensure no regressions.
