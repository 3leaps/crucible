---
title: "Windows ARM64 Gaps in the TypeScript Stack"
description: "Native binary availability gaps for Biome, Rollup/Vitest, and other Rust/C++ tools on Windows ARM64"
author: "Claude Opus 4.6"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-02-09"
last_updated: "2026-02-09"
updated_in: "kitfly v0.1.1 CI bring-up"
status: "draft"
tags: ["typescript", "windows", "arm64", "biome", "vitest", "rollup", "cross-platform", "cicd"]
---

# Windows ARM64 Gaps in the TypeScript Stack

Bun, Biome, Vitest/Rollup, and other tools in the modern TypeScript stack ship platform-specific native binaries. Several of these tools do not publish `win32-arm64` packages, causing failures on Windows ARM64 runners and developer machines.

This document tracks the current state and recommended CI workarounds.

Scope note:

- This page covers TypeScript ecosystem package availability gaps.
- For runner-level behavior (shell defaults, `.exe`, path/rename semantics), see [Windows Runner Gotchas](../../cicd/github-actions/windows-runners.md).
- For Bun binary release design, see [Bun-Compiled TypeScript Binaries](bun-compiled-binaries.md).

## Status Matrix

| Tool           | Package Expected                  | Available                    | Workaround                                |
| -------------- | --------------------------------- | ---------------------------- | ----------------------------------------- |
| **Bun**        | (single binary)                   | x64 only, runs via emulation | Works transparently                       |
| **Biome**      | `@biomejs/cli-win32-arm64`        | No                           | Skip lint step                            |
| **Rollup**     | `@rollup/rollup-win32-arm64-msvc` | No                           | Skip test step (Vitest depends on Rollup) |
| **TypeScript** | (pure JS)                         | Yes                          | Works natively                            |
| **esbuild**    | `@esbuild/win32-arm64`            | Yes (since v0.21)            | Works natively                            |

**Last verified**: 2026-02-09

## How It Manifests

### Biome

```
Error: Cannot find module '@biomejs/cli-win32-arm64/biome.exe'
```

Biome publishes platform-specific optional dependencies. On Windows ARM64, `bun install` cannot resolve the ARM64 variant, and x64 emulation does not help because npm/bun resolves the package name based on `os.arch()` which reports `arm64`.

### Rollup (via Vitest)

```
Error: Cannot find module @rollup/rollup-win32-arm64-msvc
```

Vitest depends on Vite, which depends on Rollup. Rollup uses native binaries for performance. The same `os.arch()` resolution issue applies — even though Bun itself runs under x64 emulation, Node.js module resolution asks for the arm64-native package.

## Why x64 Emulation Doesn't Help

Windows ARM64 runs x64 binaries via transparent emulation (Windows on ARM / WoA). Bun itself runs fine this way. However, npm/bun package resolution uses `process.arch` (which reports `arm64`) to select optional dependency variants **at install time**, not at runtime. So the package manager tries to install `win32-arm64` packages even though x64 packages would work at runtime.

This is a fundamental design issue in how npm optional dependencies handle architecture detection — the install-time arch check doesn't account for emulation.

## Recommended CI Pattern

Split `check-all` into individual steps and use matrix flags to skip unavailable tools:

```yaml
strategy:
  fail-fast: false
  matrix:
    include:
      - os: ubuntu-latest
        name: linux-x64
      - os: macos-15
        name: darwin-arm64
      - os: windows-latest
        name: windows-x64
      - os: windows-latest-arm64-s
        name: windows-arm64
        skip-lint: true # Biome: no win32-arm64 binary
        skip-test: true # Rollup/Vitest: no win32-arm64 binary

steps:
  - name: Lint
    if: matrix.skip-lint != true
    run: make lint

  - name: Typecheck
    run: make typecheck

  - name: Test
    if: matrix.skip-test != true
    run: make test

  - name: Build
    run: make build
```

### What Windows ARM64 Still Validates

Even with lint and test skipped, the ARM64 runner proves:

- **Bootstrap chain works**: sfetch, goneat, foundation tools install correctly
- **TypeScript compiles**: `tsc --noEmit` runs natively (TypeScript is pure JS)
- **Build succeeds**: Static site generation, file I/O, and path handling work
- **Bun works under emulation**: Package install, script execution, module resolution

### Coverage Summary

| Check           | linux-x64 | linux-arm64 | darwin-arm64 | windows-x64 | windows-arm64 |
| --------------- | --------- | ----------- | ------------ | ----------- | ------------- |
| Lint (Biome)    | Full      | Full        | Full         | Full        | Skipped       |
| Typecheck (tsc) | Full      | Full        | Full         | Full        | Full          |
| Test (Vitest)   | Full      | Full        | Full         | Full        | Skipped       |
| Build           | Full      | Full        | Full         | Full        | Full          |

Windows x64 provides full coverage for all Windows-specific behavior. The ARM64 target validates the deployment pipeline and compilation, which is the primary risk surface for ARM64.

## Cross-Platform Path Handling

A related issue discovered during Windows CI bring-up: Node.js `path.join()` and `path.resolve()` produce `\` separators on Windows. Code that constructs or compares paths must use `path.sep` and `path.resolve()` rather than hardcoded `/`.

### Production Code Pattern

```typescript
import { resolve, sep } from "node:path";

// WRONG: hardcoded forward slash
if (!resolved.startsWith(`${root}/`)) { ... }

// RIGHT: OS-native separator with normalized root
const normalizedRoot = resolve(root);
if (!resolved.startsWith(`${normalizedRoot}${sep}`)) { ... }
```

### URL Paths vs Filesystem Paths

URL paths always use `/`. When converting filesystem paths to URL paths, normalize:

```typescript
export function toUrlPath(root: string, resolvedPath: string): string {
  const normalizedRoot = resolve(root);
  if (resolvedPath.startsWith(`${normalizedRoot}${sep}`)) {
    return resolvedPath.slice(normalizedRoot.length + 1).replaceAll("\\", "/");
  }
  return resolvedPath;
}
```

### Test Assertions

Use `path.join()`, `path.resolve()`, `path.isAbsolute()`, `path.dirname()`, and `path.sep` in test assertions — never hardcoded path strings:

```typescript
// WRONG: hardcoded Unix paths
expect(result).toBe("/home/user/project/docs/guide.md");
expect(parentDir).toBe(logPath.slice(0, logPath.lastIndexOf("/")));
expect(kitflyHome.startsWith("/")).toBe(true);

// RIGHT: platform-agnostic
expect(result).toBe(resolve("/home/user/project", "docs", "guide.md"));
expect(dirname(logPath)).toBe(logsDir);
expect(isAbsolute(kitflyHome)).toBe(true);
```

## CRLF Line Endings

Git on Windows converts LF to CRLF on checkout. This causes format checkers (Biome, Prettier) to flag every file. Fix with `.gitattributes`:

```
# Force LF line endings on all platforms
* text=auto eol=lf
```

This must be committed **before** format checks run in CI. After adding `.gitattributes`, existing clones need `git checkout -- .` or a fresh clone to pick up the change.

## Monitoring and Future

Track these upstream issues for ARM64 binary availability:

- **Biome**: Watch for `@biomejs/cli-win32-arm64` package on npm
- **Rollup**: Watch for `@rollup/rollup-win32-arm64-msvc` package on npm
- **Vite/Vitest**: Will work automatically once Rollup ships ARM64

When binaries become available, remove the `skip-lint` and `skip-test` matrix flags and verify full CI passes.

## Related

- [Windows Runner Gotchas](../../cicd/github-actions/windows-runners.md) - General Windows CI issues
- [Modern TypeScript Stack](modern-typescript-stack.md) - The bun/biome/vitest baseline
- [Bun-Compiled TypeScript Binaries](bun-compiled-binaries.md) - Standalone CLI binary release patterns
- [Cross-Platform Asset Selection](../../cicd/github-actions/cross-platform-asset-selection.md) - Asset naming for multi-platform releases
