---
title: "Cargo Subcommand Gotchas"
description: "Common issues with cargo subcommands vs binary names"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["rust", "cargo", "gotchas", "ci"]
---

# Cargo Subcommand Gotchas

## Binary Name vs Subcommand

Cargo extensions can be invoked two ways:

```bash
# As cargo subcommand (for building)
cargo zigbuild --release --target x86_64-unknown-linux-gnu

# As binary directly (for version checks, help)
cargo-zigbuild --version
```

**Common mistake in CI:**

```yaml
# WRONG - subcommand doesn't accept --version
- run: cargo zigbuild --version

# CORRECT - use binary name for version check
- run: cargo-zigbuild --version
```

## Affected Tools

| Tool           | Subcommand       | Binary           |
| -------------- | ---------------- | ---------------- |
| cargo-zigbuild | `cargo zigbuild` | `cargo-zigbuild` |
| cargo-deny     | `cargo deny`     | `cargo-deny`     |
| cargo-audit    | `cargo audit`    | `cargo-audit`    |
| cargo-nextest  | `cargo nextest`  | `cargo-nextest`  |

## Why This Happens

When you run `cargo <subcommand>`, cargo looks for a binary named `cargo-<subcommand>` in PATH and executes it, passing arguments. The binary receives different argv depending on invocation:

- `cargo zigbuild --version` → binary sees `["cargo-zigbuild", "zigbuild", "--version"]`
- `cargo-zigbuild --version` → binary sees `["cargo-zigbuild", "--version"]`

Most cargo extensions don't handle the extra `zigbuild` argument when `--version` is passed.

## Best Practice

```yaml
# Install
- run: cargo install cargo-zigbuild

# Verify installation (use binary name)
- run: cargo-zigbuild --version

# Build (use subcommand)
- run: cargo zigbuild --release --target ${{ matrix.target }}
```
