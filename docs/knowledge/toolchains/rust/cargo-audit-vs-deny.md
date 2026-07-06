---
title: "cargo-audit vs cargo-deny"
description: "Comparison of Rust security scanning tools and when to use each"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["rust", "cargo-deny", "cargo-audit", "security", "toolchains"]
---

# cargo-audit vs cargo-deny

Both tools scan for security vulnerabilities in Rust dependencies, but they serve different purposes and have different tradeoffs.

## Quick Comparison

| Feature             | cargo-audit | cargo-deny      |
| ------------------- | ----------- | --------------- |
| Primary purpose     | Security    | Policy/Security |
| RustSec database    | Yes         | Yes             |
| License checking    | No          | Yes             |
| Duplicate detection | No          | Yes             |
| Source verification | No          | Yes             |
| Ban specific crates | No          | Yes             |
| Configuration       | Simple      | Rich            |
| CVSS 4.0 support    | Yes         | Partial\*       |
| Output formats      | Text/JSON   | Text/JSON/SARIF |
| GitHub Advisory DB  | Optional    | No              |

\*See [cargo-deny-cvss4.md](cargo-deny-cvss4.md) for current issues.

## When to Use cargo-audit

**Best for**: Simple security scanning, quick CI checks, broad compatibility.

```bash
# Install
cargo install cargo-audit

# Basic scan
cargo audit

# JSON output for parsing
cargo audit --json

# Use GitHub Advisory Database
cargo audit --db https://github.com/rustsec/advisory-db
```

### Strengths

- **Simpler** - No configuration needed
- **Focused** - Does one thing well
- **CVSS 4.0** - Full support for new advisory format
- **GitHub integration** - Can use GitHub Advisory Database

### Configuration

Minimal config in `.cargo/audit.toml`:

```toml
[advisories]
ignore = ["RUSTSEC-2024-XXXX"]  # With justification

[output]
format = "json"
```

## When to Use cargo-deny

**Best for**: Policy enforcement, license compliance, comprehensive dependency governance.

```bash
# Install
cargo install cargo-deny

# Full check
cargo deny check

# Skip advisories (workaround for CVSS 4.0 issues)
cargo deny check bans licenses sources
```

### Strengths

- **Policy enforcement** - License, sources, duplicates
- **Ban specific crates** - Block known-bad dependencies
- **Duplicate detection** - Catch multiple versions of same crate
- **Rich configuration** - Fine-grained control

### Configuration (deny.toml)

```toml
[advisories]
vulnerability = "deny"
unmaintained = "warn"
yanked = "deny"
ignore = []

[licenses]
allow = [
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
]
copyleft = "deny"

[bans]
multiple-versions = "warn"
deny = [
    { name = "openssl" },  # Prefer rustls
]

[sources]
allow-git = []
allow-registry = ["https://github.com/rust-lang/crates.io-index"]
```

## Recommended CI Strategy

### Use Both Tools

```yaml
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # cargo-audit for security (handles CVSS 4.0)
      - name: Security audit
        run: cargo audit

      # cargo-deny for policy (skip advisories if CVSS 4.0 issues)
      - name: Policy check
        run: cargo deny check bans licenses sources
```

### Why Both?

1. **cargo-audit**: Best-in-class security scanning with full CVSS 4.0 support
2. **cargo-deny**: License and policy enforcement (until CVSS 4.0 fully supported)

This approach gives you:

- Reliable vulnerability detection (cargo-audit)
- License compliance checking (cargo-deny licenses)
- Source verification (cargo-deny sources)
- Ban enforcement (cargo-deny bans)

## Common Workflows

### Quick Security Check (Local Dev)

```bash
cargo audit
```

### Full Policy Check (Pre-Commit)

```bash
cargo deny check
```

### CI with CVSS 4.0 Workaround

```bash
# Security
cargo audit

# Policy (excluding advisories due to CVSS 4.0)
cargo deny check bans licenses sources
```

## Output Formats

### cargo-audit

```bash
# Human readable (default)
cargo audit

# JSON for parsing
cargo audit --json

# Markdown for GitHub issues
cargo audit --format markdown
```

### cargo-deny

```bash
# Human readable (default)
cargo deny check

# JSON
cargo deny --format json check

# SARIF (for GitHub Code Scanning)
cargo deny --format sarif check
```

## Ignoring Advisories

### cargo-audit

```toml
# .cargo/audit.toml
[advisories]
ignore = [
    "RUSTSEC-2024-XXXX",  # Reason: not exploitable in our context
]
```

### cargo-deny

```toml
# deny.toml
[advisories]
ignore = [
    "RUSTSEC-2024-XXXX",  # Reason
]
```

## Known Issues

### cargo-deny CVSS 4.0 (Current)

See [cargo-deny-cvss4.md](cargo-deny-cvss4.md) for workaround.

**Status**: Tracked at https://github.com/EmbarkStudios/cargo-deny/issues/XXX

### Advisory Database Sync

Both tools pull from RustSec. Run periodically to get updates:

```bash
cargo audit fetch
```

## Decision Matrix

| Scenario                 | Recommendation        |
| ------------------------ | --------------------- |
| Quick security scan      | cargo-audit           |
| CI security gate         | cargo-audit           |
| License compliance       | cargo-deny            |
| Block specific crates    | cargo-deny            |
| Enterprise policy        | Both                  |
| Minimal setup            | cargo-audit           |
| Comprehensive governance | cargo-deny (full)     |
| CVSS 4.0 advisories      | cargo-audit (for now) |
