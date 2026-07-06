---
title: "Python Toolchain Knowledge"
description: "Python ecosystem knowledge, modern tooling, and workarounds"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["python", "uv", "ruff", "pytest", "toolchains"]
---

# Python Toolchain Knowledge

Knowledge and workarounds for the Python toolchain ecosystem.

## Contents

| Document                                      | Description                          |
| --------------------------------------------- | ------------------------------------ |
| [Modern Python Stack](modern-python-stack.md) | uv, ruff, pytest - the 2026 baseline |

## The Modern Stack

The Python ecosystem has consolidated around fast, Rust-based tools:

| Tool   | Purpose              | Replaces                     |
| ------ | -------------------- | ---------------------------- |
| uv     | Package management   | pip, pipenv, poetry          |
| ruff   | Linting + formatting | black, flake8, isort, pylint |
| pytest | Testing              | unittest                     |

See [Modern Python Stack](modern-python-stack.md) for details.

## Quick Reference

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create new project
uv init --lib my-package

# Add dependencies
uv add requests pydantic
uv add --dev pytest ruff

# Run tests
uv run pytest

# Lint and format
uv run ruff check .
uv run ruff format .
```

## Related

- [Testing Patterns](../../testing/) - HTTP and integration testing
- [CI Baseline](../../../operations/ci-baseline.md) - CI/CD patterns
- [Coding Baseline](../../../coding/baseline.md) - Language-agnostic coding standard
- [Python Coding Standards](../../../coding/python.md) - Normative Python standard
