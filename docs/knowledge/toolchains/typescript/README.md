---
title: "TypeScript Toolchain Knowledge"
description: "TypeScript and Node.js ecosystem knowledge and workarounds"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-02-10"
status: "draft"
tags: ["typescript", "bun", "biome", "vitest", "toolchains"]
---

# TypeScript Toolchain Knowledge

Knowledge and workarounds for the TypeScript/Node.js ecosystem.

## Contents

| Document                                              | Description                                   | Status |
| ----------------------------------------------------- | --------------------------------------------- | ------ |
| [Modern TypeScript Stack](modern-typescript-stack.md) | bun, biome, vitest - 2026 baseline            | Draft  |
| [Bun-Compiled Binaries](bun-compiled-binaries.md)     | Shipping standalone TS CLI binaries with Bun  | Draft  |
| [Windows ARM64 Gaps](windows-arm64-gaps.md)           | Native binary gaps for Biome, Rollup on arm64 | Draft  |

## Planned

| Document               | Description                        |
| ---------------------- | ---------------------------------- |
| napi-rs-prebuilds.md   | Cross-platform native addon builds |
| node-version-policy.md | Node.js LTS version guidance       |

## Common Patterns

### napi-rs Cross-Compilation

For native Node.js addons with Rust:

- Use zig for Linux cross-compilation
- Build platform packages separately
- Publish as optionalDependencies

See [npm OIDC](../../cicd/registry/npm-oidc.md) for publishing patterns.

### Node.js Version Policy

- Target current LTS versions
- Specify in `engines.node` in package.json
- Test matrix should include oldest supported LTS

## Related

- [GitHub Actions Knowledge](../../cicd/github-actions/) - Release workflow patterns
- [CI/CD Registry: npm](../../cicd/registry/npm-oidc.md) - npm publishing
- [Coding Baseline](../../../coding/baseline.md) - Language-agnostic coding standard
- [TypeScript Coding Standards](../../../coding/typescript.md) - Normative TypeScript standard
