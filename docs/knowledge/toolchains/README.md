---
title: "Toolchain Knowledge"
description: "Language and platform toolchain knowledge, workarounds, and best practices"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["toolchains", "languages", "knowledge"]
---

# Toolchain Knowledge

Language and platform toolchain knowledge accumulated across 3leaps projects.

## Languages

| Language   | Directory                  | Topics                                 |
| ---------- | -------------------------- | -------------------------------------- |
| Rust       | [rust/](rust/)             | cargo-deny, cargo-audit, MSRV policy   |
| TypeScript | [typescript/](typescript/) | napi-rs, Node.js versions              |
| Python     | [python/](python/)         | uv, ruff, pytest                       |
| Go         | [go/](go/)                 | CGO, static linking, module versioning |

## What Belongs Here

- **Toolchain quirks** - Unexpected behaviors, edge cases
- **Workarounds** - Fixes for known issues pending upstream resolution
- **Version policies** - MSRV, Node.js LTS, Go version support
- **Build patterns** - Cross-compilation, static linking, prebuilds
- **Ecosystem gotchas** - Registry publishing, dependency management

## What Doesn't Belong Here

- **Coding standards** - See `docs/coding/`
- **Testing patterns** - See `docs/knowledge/testing/`
- **Architecture decisions** - See `docs/decisions/`

## Cross-References

Knowledge here often relates to:

- [CI/CD Knowledge](../cicd/) - Build and publish automation
- [Coding Baseline](../../coding/baseline.md) - Language-agnostic coding standard
