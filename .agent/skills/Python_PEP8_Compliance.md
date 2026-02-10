---
name: Python PEP 8 Compliance
description: Enforce Python coding standards based on PEP 8, with project-specific overrides.
---

# Python PEP 8 Compliance

This skill defines the coding standards for Python code within this project. Follow these guidelines to ensure code quality and consistency.

## Core Principles (PEP 8)

### 1. Indentation
- Use **4 spaces** per indentation level.
- Do **NOT** use tabs.

### 2. Line Length
- Limit all lines to a maximum of **88 characters** (compatible with `black` formatter defaults).
- For long lines, use parentheses `()` to wrap expressions rather than backslashes `\`.

### 3. Imports
- Imports should be grouped in the following order:
    1.  Standard library imports.
    2.  Related third-party imports.
    3.  Local application/library specific imports.
- Put a blank line between each group of imports.
- Use absolute imports (e.g., `from services.edinet_service import EdinetClient`) over relative imports where possible.

### 4. Whitespace
- Avoid extraneous whitespace in the following situations:
    - Immediately inside parentheses, brackets or braces.
    - Immediately before a comma, semicolon, or colon.
- Surround top-level function and class definitions with **two blank lines**.
- Method definitions inside a class are surrounded by a **single blank line**.

### 5. Naming Conventions
- **Functions/Variables**: `snake_case`
- **Classes**: `CapWords` (PascalCase)
- **Constants**: `UPPER_CASE_WITH_UNDERSCORES`
- **Private Members**: Use a leading underscore `_variable_name` for non-public methods and instance variables.

## Project-Specific Overrides (User Rules)

### 6. Comments & Documentation
> [!IMPORTANT]
> **Code comments MUST be written in Japanese.**
> コードに記述するコメントは日本語にしてください。

- **Docstrings**: All public modules, functions, classes, and methods should have docstrings.
    - Format: Google Style or NumPy Style is preferred.
    - Content: Description, Arguments, Returns, Raises.
    - Language: **Japanese**.
- **Block Comments**: Use `#` for block comments. Explain *why* code is doing something, not just *what* it is doing.
- **Inline Comments**: Use sparingly. Separate from code by at least two spaces.

## Tooling

### Recommended Linters & Formatters
- **Formatter**: `black` (uncompromising code formatter)
- **Linter**: `flake8` (style guide enforcement)
- **Import Sorter**: `isort`

## Example

```python
import os
import sys

from typing import List, Optional

class DataProcessor:
    """
    データ処理を行うクラス。
    """

    TIMEOUT_SECONDS = 30

    def __init__(self, data_source: str):
        self.data_source = data_source
        self._cache = {}

    def process_items(self, items: List[str]) -> List[str]:
        """
        アイテムのリストを処理して返します。

        Args:
            items (List[str]): 処理対象のアイテムリスト

        Returns:
            List[str]: 処理後のアイテムリスト
        """
        results = []
        for item in items:
            # アイテムが空の場合はスキップ
            if not item:
                continue
            
            processed = self._transform(item)
            results.append(processed)
        
        return results

    def _transform(self, item: str) -> str:
        return item.strip().lower()
```
