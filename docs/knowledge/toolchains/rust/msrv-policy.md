---
title: "Rust MSRV Policy"
description: "Minimum Supported Rust Version guidance for Rust projects"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["rust", "msrv", "versioning", "toolchains"]
---

# Rust MSRV Policy

Guidance for managing Minimum Supported Rust Version (MSRV) in Rust projects.

## What is MSRV?

MSRV defines the oldest Rust version that can compile your project. It's specified in `Cargo.toml`:

```toml
[package]
name = "my-crate"
version = "0.1.0"
rust-version = "1.75"
```

## Why MSRV Matters

1. **Distribution compatibility** - Linux distros ship older Rust
2. **Enterprise adoption** - Organizations may not be on latest stable
3. **Dependency compatibility** - Your dependents need to compile too
4. **CI verification** - Proves your claim is accurate

## Recommended Policy

### For Libraries (crates.io)

| Library Type    | MSRV Lag     | Example (if stable = 1.82) |
| --------------- | ------------ | -------------------------- |
| Foundational    | 6+ versions  | 1.75                       |
| General-purpose | 3-4 versions | 1.78                       |
| Bleeding-edge   | 0-2 versions | 1.80                       |

**Rationale**: Libraries need broader compatibility. Core crates like `serde` and `tokio` maintain longer MSRV windows.

### For Applications (binaries)

| Application Type | MSRV Lag     | Notes                      |
| ---------------- | ------------ | -------------------------- |
| Internal tools   | Latest       | No external consumers      |
| Distributed CLI  | 2-3 versions | Balance features/compat    |
| System packages  | 4-6 versions | Match distro Rust versions |

## Setting MSRV

### In Cargo.toml

```toml
[package]
rust-version = "1.75"
```

### In rust-toolchain.toml (for contributors)

```toml
[toolchain]
channel = "1.82"
# This is the version for development
# MSRV is in Cargo.toml
```

## Verifying MSRV in CI

### GitHub Actions

```yaml
jobs:
  msrv:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Get MSRV
        id: msrv
        run: |
          msrv=$(grep rust-version Cargo.toml | sed 's/.*"\(.*\)"/\1/')
          echo "msrv=$msrv" >> $GITHUB_OUTPUT

      - name: Install MSRV toolchain
        uses: dtolnay/rust-toolchain@master
        with:
          toolchain: ${{ steps.msrv.outputs.msrv }}

      - name: Build with MSRV
        run: cargo build --all-features
```

### Using cargo-msrv

```bash
# Install
cargo install cargo-msrv

# Find minimum version that compiles
cargo msrv find

# Verify declared MSRV
cargo msrv verify

# Show currently declared MSRV
cargo msrv show
```

## Bumping MSRV

### When to Bump

- Using a new language feature (let-else, async-trait, etc.)
- Dependency requires newer MSRV
- Compiler fix needed for soundness
- Significant ergonomics improvement

### How to Bump

1. Update `rust-version` in Cargo.toml
2. Document in CHANGELOG.md
3. Consider major version bump if library

```markdown
## [0.3.0] - 2026-01-29

### Changed

- **BREAKING**: MSRV bumped to 1.78 (was 1.75)
```

### SemVer and MSRV

| Change Type | Recommended    |
| ----------- | -------------- |
| Minor bump  | Patch version  |
| Major bump  | Minor version  |
| Large bump  | Minor or Major |

There's no universal consensus. Document your policy.

## Common MSRV Pinning Issues

### Problem: Cargo.lock pins newer dependencies

```bash
# Regenerate with MSRV-compatible deps
rm Cargo.lock
cargo +1.75 generate-lockfile
```

### Problem: Feature requires newer Rust

```rust
// Use cfg for conditional compilation
#[cfg(feature = "nightly")]
fn use_nightly_feature() { ... }
```

### Problem: Dependency bumped MSRV

Check before updating:

```bash
cargo update --dry-run
# Review MSRV changes in dependency changelogs
```

## Rust Release Schedule

| Channel | Release Cycle |
| ------- | ------------- |
| Stable  | Every 6 weeks |
| Beta    | 6 weeks ahead |
| Nightly | Daily         |

Current stable (as of early 2026): ~1.82

## Quick Reference

```bash
# Check current stable
rustc --version

# Install specific version
rustup install 1.75

# Build with specific version
rustup run 1.75 cargo build

# Set project default
rustup override set 1.75

# Find MSRV automatically
cargo msrv find
```
