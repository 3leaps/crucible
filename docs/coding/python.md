---
title: "Python Coding Standards"
description: "Python-specific coding standards including type safety, Pydantic patterns, logging, and testing"
author: "devlead"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["standards", "coding", "python", "pydantic", "type-safety", "testing"]
upstream_source: "fulmenhq/crucible docs/standards/coding/python.md"
---

# Python Coding Standards

## Overview

Python-specific coding standards ensuring consistency, quality, and type safety. These standards apply to 3leaps Python projects.

**Core Principle**: Write idiomatic Python code that is simple, readable, and maintainable, with strict type safety and clean output.

**Foundation**: This guide builds upon [Coding Baseline](baseline.md) which establishes:

- Output hygiene (STDERR for logs, STDOUT for data)
- RFC3339 timestamps
- CLI exit codes
- Error handling patterns
- Security practices

Read the baseline first, then apply Python-specific patterns below.

---

## 1. Critical Rules (Zero-Tolerance)

### 1.1 Python Version

**Minimum**: Python 3.12+

**Why**:

- Type system improvements (PEP 695 - Type Parameter Syntax)
- ~5% faster than 3.11
- Better error messages
- Modern f-string improvements

```toml
# pyproject.toml
requires-python = ">=3.12"
```

### 1.2 Avoid `Any` at Boundaries

```python
from typing import Any

from pydantic import BaseModel

# Avoid `Any` in internal code. Prefer specific types or `TypedDict`.
# Accept `Any` only at system boundaries (parsing JSON, reading env/config), then validate.


class ConfigModel(BaseModel):
    host: str


def process_data(data: Any) -> str:
    config = ConfigModel.model_validate(data)
    return config.host

# Better: Define specific types
from typing import TypedDict

class Config(TypedDict):
    port: int
    host: str
```

### 1.3 Type Hints Required

**Rule**: All public functions and methods must have complete type hints.

```python
# WRONG - Missing type hints
def process_file(filename, options):
    return result

# CORRECT - Complete type hints
def process_file(filename: str, options: dict[str, Any]) -> ProcessResult:
    return ProcessResult(...)
```

### 1.4 Output Hygiene

**Rule**: Output streams must remain clean for structured output.

**DO**: Use logging for all diagnostic output

```python
import logging

logger = logging.getLogger(__name__)

# Correct logging (to stderr)
logger.debug("Processing %d files", file_count)
logger.info("Operation completed in %.2fs: %d issues found", duration, issue_count)
logger.error("Failed to process: %s", error)
logger.warning("Config not found, using defaults")
```

**DO NOT**: Write to stdout/stderr directly for diagnostics

```python
# Avoid direct writes: use logging.
print(f"DEBUG: Processing {filename}")
print("Status:", status)
sys.stderr.write("Error message\n")
```

---

## 2. Standard Libraries

### 2.1 Data Modeling: Pydantic

**Preferred** for validated data models.

```python
from pydantic import BaseModel, Field, ConfigDict

class Config(BaseModel):
    model_config = ConfigDict(frozen=True)  # Immutable

    host: str = Field(default="localhost")
    port: int = Field(ge=1, le=65535)
```

**Use Cases**:

- Configuration models
- API request/response schemas
- Data transfer objects
- Settings management

**Do NOT use**: dataclasses for validated models, attrs, marshmallow

### 2.2 CLI Framework: Click

**Default choice** for CLI applications.

```python
import click

@click.command()
@click.option("--config", "-c", type=click.Path(exists=True))
@click.option("--verbose", "-v", is_flag=True)
def main(config: str | None, verbose: bool) -> None:
    """Process files with optional configuration."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    # ...

if __name__ == "__main__":
    main()
```

### 2.3 HTTP Client: httpx

**Preferred** for HTTP operations.

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(url, timeout=30.0)
    response.raise_for_status()
```

**Do NOT use**: requests (no async), urllib (low-level)

---

## 3. Code Organization

### 3.1 Project Structure

```
project/
├── src/
│   └── package_name/
│       ├── __init__.py
│       ├── cli.py           # Click commands
│       ├── core.py          # Business logic
│       ├── config.py        # Pydantic models
│       └── py.typed         # Type marker
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml
├── ruff.toml
└── uv.lock
```

### 3.2 Import Organization

```python
# Standard library
import os
from pathlib import Path

# Third-party
import click
from pydantic import BaseModel

# Local
from .config import Config
from .core import process
```

---

## 4. Error Handling

### 4.1 Custom Exceptions

```python
class ProcessingError(Exception):
    """Base exception for processing errors."""
    pass

class ConfigurationError(ProcessingError):
    """Configuration-related errors."""
    pass

class ValidationError(ProcessingError):
    """Input validation errors."""
    pass
```

### 4.2 Exception Chaining

```python
try:
    config = load_config(path)
except FileNotFoundError as e:
    raise ConfigurationError(f"Config not found: {path}") from e
```

### 4.3 Context Managers

```python
from contextlib import contextmanager

@contextmanager
def temporary_directory():
    path = Path(tempfile.mkdtemp())
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
```

---

## 5. Testing Standards

### 5.1 pytest Patterns

```python
import pytest
from package_name.core import process

@pytest.fixture
def sample_config():
    return Config(host="localhost", port=8080)

def test_process_success(sample_config):
    result = process(sample_config)
    assert result.success is True

def test_process_invalid_input():
    with pytest.raises(ValidationError, match="invalid input"):
        process(None)

@pytest.mark.parametrize("port,expected", [
    (80, True),
    (0, False),
    (65536, False),
])
def test_port_validation(port, expected):
    if expected:
        Config(host="localhost", port=port)
    else:
        with pytest.raises(ValueError):
            Config(host="localhost", port=port)
```

### 5.2 Async Testing

```python
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    result = await fetch_data()
    assert result is not None
```

---

## 6. Type Checking

### 6.1 mypy Configuration

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
disallow_untyped_defs = true
```

### 6.2 Type Marker for Libraries

Include `py.typed` marker:

```
src/package_name/
├── __init__.py
└── py.typed          # Empty file
```

---

## 7. Common Anti-Patterns

### 7.1 Output Contamination

```python
# NEVER
print(f"DEBUG: Processing {filename}")

# ALWAYS
logger.debug("Processing %s", filename)
```

### 7.2 Mutable Default Arguments

```python
# WRONG - Shared mutable default
def process(items: list = []):
    items.append("new")
    return items

# CORRECT
def process(items: list | None = None):
    if items is None:
        items = []
    items.append("new")
    return items
```

### 7.3 Bare Exceptions

```python
# WRONG
try:
    risky_operation()
except:
    pass

# CORRECT
try:
    risky_operation()
except SpecificError as e:
    logger.error("Operation failed: %s", e)
    raise
```

---

## 8. Code Review Checklist

Before submitting Python code, verify:

- [ ] No print statements in library code
- [ ] All public functions have type hints
- [ ] Pydantic models for validated data
- [ ] Logging used for diagnostics
- [ ] Tests with pytest
- [ ] Custom exceptions with chaining
- [ ] `ruff check` passes
- [ ] `mypy` passes (if enabled)

---

## 9. Tools

### Required

- `uv` - Package management
- `ruff` - Linting and formatting
- `pytest` - Testing

### Recommended

- `mypy` - Type checking
- `pytest-cov` - Coverage

---

## Related

- [Coding Baseline](baseline.md) - Language-agnostic standards
- [Modern Python Stack](../knowledge/toolchains/python/modern-python-stack.md) - uv, ruff, pytest setup

## Attribution

Adapted from [FulmenHQ Crucible](https://github.com/fulmenhq/crucible) Python coding standards.
