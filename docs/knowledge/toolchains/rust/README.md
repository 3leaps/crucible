---
title: "Rust Toolchain Knowledge"
description: "Rust ecosystem knowledge, cargo tooling, and workarounds"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["rust", "cargo", "toolchains"]
---

# Rust Toolchain Knowledge

Knowledge and workarounds for the Rust ecosystem.

## Contents

| Document                                                          | Description                             |
| ----------------------------------------------------------------- | --------------------------------------- |
| [FFI Bindings Setup](ffi-bindings-setup.md)                       | Adding Go/TypeScript bindings to Rust   |
| [CI Parity and Generated Tools](ci-parity-and-generated-tools.md) | Keeping local checks aligned with CI    |
| [MSRV Policy](msrv-policy.md)                                     | Minimum Supported Rust Version guidance |
| [cargo-audit vs cargo-deny](cargo-audit-vs-deny.md)               | Security tool comparison                |
| [cargo-deny CVSS 4.0](cargo-deny-cvss4.md)                        | CVSS 4.0 parsing workaround             |
| [cargo subcommand gotchas](cargo-subcommand-gotchas.md)           | Binary vs subcommand invocation         |

## Common Tools

### cargo-deny

License and advisory checking. See [cargo-deny-cvss4.md](cargo-deny-cvss4.md) for current issues.

```bash
cargo deny check                    # Full check (may fail on CVSS 4.0)
cargo deny check bans licenses sources  # Skip advisories (workaround)
```

### cargo-audit

Security vulnerability scanning. Alternative to cargo-deny's advisory checking.

```bash
cargo audit                         # Scan for vulnerabilities
```

### MSRV Policy

See [MSRV Policy](msrv-policy.md) for detailed guidance.

Quick reference:

- Check `rust-version` in `Cargo.toml` for per-project MSRV
- Test with: `rustup run <version> cargo build`
- CI should verify MSRV builds

## Related

- [CI/CD GitHub Actions](../../cicd/github-actions/) - Rust in CI
- [Coding Baseline](../../../coding/baseline.md) - Language-agnostic coding standard
- [Rust Coding Standards](../../../coding/rust.md) - Normative Rust standard
