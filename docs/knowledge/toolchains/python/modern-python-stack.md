---
title: "Modern Python Stack (2026)"
description: "The modern Python development stack: uv, ruff, pytest, and Python 3.12+"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["python", "uv", "ruff", "pytest", "toolchains"]
upstream_source: "fulmenhq/crucible docs/standards/repository-structure/python/README.md"
---

# Modern Python Stack (2026)

The Python ecosystem has consolidated around a new generation of Rust-based tools that dramatically improve developer experience. This document covers the recommended stack for new Python projects in 2026.

## The Stack

| Tool   | Purpose              | Replaces                               |
| ------ | -------------------- | -------------------------------------- |
| uv     | Package management   | pip, pip-tools, pipenv, poetry         |
| ruff   | Linting + formatting | black, flake8, isort, pylint, autopep8 |
| pytest | Testing              | unittest                               |

All three are mature, fast, and well-maintained.

## uv: Package Management

### Why uv

- **Speed**: 10-100x faster than pip (Rust-based)
- **Unified**: Single tool for deps, venv, version management
- **Lock files**: Reproducible builds via `uv.lock`
- **Python management**: Built-in Python version management

### Installation

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Essential Commands

```bash
# Initialize new project
uv init --lib my-package

# Add dependencies
uv add requests pydantic

# Add dev dependencies
uv add --dev pytest ruff mypy

# Install from lock file
uv sync

# Run commands in virtual environment
uv run pytest
uv run python my_script.py

# Update lock file
uv lock
```

### Project Structure

```
project/
├── .python-version          # Python version pin (3.12)
├── pyproject.toml           # Project metadata
├── ruff.toml                # Linting config
├── uv.lock                  # Locked dependencies (commit this!)
├── src/
│   └── package_name/
│       └── __init__.py
└── tests/
    └── __init__.py
```

### pyproject.toml Example

```toml
[project]
name = "my-package"
version = "0.1.0"
description = "Brief description"
requires-python = ">=3.12"

dependencies = [
    "pydantic>=2.0.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## ruff: Linting and Formatting

### Why ruff

- **Speed**: Extremely fast (Rust-based)
- **Unified**: Replaces flake8, black, isort, pydocstyle
- **Comprehensive**: 800+ rules from popular linters

### Configuration (ruff.toml)

```toml
line-length = 120
indent-width = 4
target-version = "py312"

[format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false

[lint]
select = ["E4", "E7", "E9", "F", "B"]
ignore = []
fixable = ["ALL"]
unfixable = []

[lint.per-file-ignores]
"__init__.py" = ["E402"]
"tests/*" = ["E402"]
```

### Essential Commands

```bash
# Check for issues
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

## pytest: Testing

### Why pytest

- **Industry standard**: Rich plugin ecosystem
- **Fixtures**: Powerful dependency injection
- **Clear syntax**: Readable test code

### Configuration (in pyproject.toml)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "--cov=src --cov-report=term-missing"
```

### Test Structure

```
tests/
├── __init__.py
├── unit/
│   ├── test_core.py
│   └── test_utils.py
├── integration/
│   └── test_api.py
└── fixtures/
    └── sample_data.json
```

### Example Test

```python
import pytest
from my_package.core import process_data

@pytest.fixture
def sample_input():
    return {"key": "value"}

def test_process_data_success(sample_input):
    result = process_data(sample_input)
    assert result.success is True
    assert "key" in result.data

def test_process_data_empty():
    with pytest.raises(ValueError, match="empty input"):
        process_data({})
```

## Python Version: 3.12+

### Why Python 3.12

- Type system improvements (PEP 695)
- ~5% faster than 3.11
- Better error messages
- Modern f-string improvements

### Version Pinning

```bash
# .python-version
3.12
```

```toml
# pyproject.toml
[project]
requires-python = ">=3.12"
```

## Type Checking (Optional but Recommended)

### mypy Configuration

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
disallow_untyped_defs = true
```

### Typed Package Marker

For libraries, include `py.typed` marker:

```
src/package_name/
├── __init__.py
└── py.typed          # Empty file, signals typed package
```

## Common Makefile

```makefile
.PHONY: install test lint format clean

install:  ## Install dependencies
	uv sync

test:  ## Run tests
	uv run pytest

lint:  ## Run linting
	uv run ruff check .

format:  ## Format code
	uv run ruff format .

check:  ## Run all checks
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest

clean:  ## Clean build artifacts
	rm -rf dist/ build/ .pytest_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
```

## GitHub Actions

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync

      - name: Lint
        run: uv run ruff check .

      - name: Test
        run: uv run pytest
```

## Migration from Legacy Tools

### From pip/pip-tools to uv

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create pyproject.toml from requirements.txt
uv init --lib my-package
uv add $(cat requirements.txt)
uv add --dev $(cat requirements-dev.txt)

# Remove old files
rm requirements.txt requirements-dev.txt setup.py
```

### From black/flake8 to ruff

```bash
# Remove old tools
uv remove black flake8 isort

# Add ruff
uv add --dev ruff

# Run initial format
uv run ruff format .
uv run ruff check --fix .
```

## Attribution

Adapted from [FulmenHQ Crucible](https://github.com/fulmenhq/crucible) Python standards.
