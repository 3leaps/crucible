---
title: "Bun-Compiled TypeScript Binaries"
description: "Patterns and caveats for shipping standalone TypeScript CLI binaries with bun build --compile"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-02-10"
last_updated: "2026-02-10"
status: "draft"
tags: ["typescript", "bun", "binaries", "release-engineering", "cross-platform"]
---

# Bun-Compiled TypeScript Binaries

`bun build --compile` produces standalone CLI binaries from TypeScript. This page covers practical cross-platform release patterns.

## When to Use

Use Bun-compiled binaries when you need:

- Fast startup for CLI tools
- No runtime Node/Bun requirement for end users
- Simple release assets (`.tar.gz`, `.zip`, `.exe`)

Use npm-only publishing when:

- The project is primarily a library
- Users are expected to run via package managers
- Cross-platform native binary support is incomplete for your matrix

## Baseline Build Pattern

Build four mainstream targets from Linux:

```bash
bun build src/cli.ts --compile --target=bun-linux-x64 --outfile dist/release/tool-linux-x64
bun build src/cli.ts --compile --target=bun-linux-arm64 --outfile dist/release/tool-linux-arm64
bun build src/cli.ts --compile --target=bun-darwin-arm64 --outfile dist/release/tool-darwin-arm64
bun build src/cli.ts --compile --target=bun-windows-x64 --outfile dist/release/tool-windows-x64.exe
```

### Windows ARM64

Bun cannot cross-compile to `windows-arm64`. If you need it:

- Build via a native Windows ARM64 runner
- Run as a separate optional workflow
- Treat absence of the asset as valid unless your release policy requires it

## Version Injection

Inject version metadata at build time:

```bash
bun build src/cli.ts \
  --compile \
  --define VERSION_OVERRIDE='\"0.1.1\"' \
  --outfile dist/release/tool-linux-x64
```

In code, use a deterministic dev fallback:

- `VERSION_OVERRIDE` at compile time for release binaries
- `VERSION` file read at runtime for local/dev execution

This prevents drift between binary output and tag version.

## Asset Naming Conventions

Use explicit OS/arch tokens in every filename:

- `tool-v0.1.1-linux-x64.tar.gz`
- `tool-v0.1.1-linux-arm64.tar.gz`
- `tool-v0.1.1-darwin-arm64.tar.gz`
- `tool-v0.1.1-windows-x64.zip`
- `tool-v0.1.1-windows-arm64.zip` (optional/manual lane)

Naming rules:

- Include full OS names (`windows`, not `win`)
- Include architecture token (`x64`, `arm64`)
- Preserve `.exe` inside Windows archives

See [Cross-Platform Asset Selection](../../cicd/github-actions/cross-platform-asset-selection.md) for boundary-safe matching.

## Packaging Pattern

Recommended:

- Linux/macOS: `.tar.gz`
- Windows: `.zip`
- npm tarball: include as separate asset if publishing to npm

Keep packaging deterministic:

- One staging directory (`dist/release/`)
- One checksum pass after all assets are present
- No mutation after checksums are generated (except appending signature files)

## Checksums and Signatures

Generate checksum manifests for all distributables:

- `SHA256SUMS`
- `SHA512SUMS`

Then sign manifests and publish signature material.

Operator model:

1. Download draft assets locally.
2. Recompute and verify checksums.
3. Sign checksums.
4. Verify signatures.
5. Upload updated checksum/signature assets.
6. Undraft release.

See [Manual Signing Handoff](../../cicd/github-actions/manual-signing-handoff.md).

## Workflow Shape: Prefer Single-Job Assembly

For moderate asset counts, prefer one release job:

- Avoid `upload-artifact`/`download-artifact` round-trips
- Reduce GitHub API pressure
- Keep provenance and checksums in one execution context

Use multi-job only when:

- You need isolated build environments per target
- Native target constraints force split jobs (for example, `windows-arm64`)

See [Artifact Handling Patterns](../../cicd/github-actions/artifact-handling.md).

## Minimum Validation

Before publishing:

1. Required assets exist per release policy.
2. Checksums include all shipped asset types.
3. Windows assets contain `.exe` binaries where expected.
4. Signature verification passes locally.
5. Release notes match the final asset set.

## Related

- [Modern TypeScript Stack](modern-typescript-stack.md)
- [Windows ARM64 Gaps](windows-arm64-gaps.md)
- [Windows Runner Gotchas](../../cicd/github-actions/windows-runners.md)
- [Release Verification Checklist](../../cicd/github-actions/release-verification-checklist.md)
- [Release Rollback Procedure](../../cicd/github-actions/release-rollback.md)
