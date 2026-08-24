---
title: "cargo-deny CVSS 4.0 Advisory Parsing Workaround"
description: "Workaround for cargo-deny failing to parse CVSS 4.0 scores in RustSec advisories"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-28"
last_updated: "2026-01-29"
status: "draft"
tags: ["rust", "cargo-deny", "cvss", "workaround", "security"]
---

# cargo-deny CVSS 4.0 Advisory Parsing Workaround

## Problem

cargo-deny fails to load the RustSec advisory database when advisories contain CVSS 4.0 scores:

```
error: failed to load advisory database: parse error:
error parsing .../crates/cmov/RUSTSEC-2026-0003.md:
TOML parse error at line 7, column 8
cvss = "CVSS:4.0/AV:N/AC:H/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:H/SI:N/SA:N"
unsupported CVSS version: 4.0
```

This blocks the entire `cargo deny check` command, even for projects that don't depend on the affected crate.

## Root Cause

- RustSec advisory database added CVSS 4.0 scores to some advisories
- cargo-deny's `rustsec` dependency doesn't fully support CVSS 4.0 parsing
- Issue tracked at: https://github.com/EmbarkStudios/cargo-deny/issues/804
- A fix was merged (rustsec 0.31) but new advisories with different CVSS 4.0 formats still break

## Affected Versions

- cargo-deny 0.19.0 and earlier
- Any project when RustSec database contains CVSS 4.0 advisories

## Workaround

Change Makefile `deny` target to skip advisories check:

```makefile
# Before
cargo deny check

# After
cargo deny check bans licenses sources
```

This runs license policy enforcement and ban checks but skips vulnerability advisories.

## What Still Works

- **License checks**: All GPL/LGPL detection still enforced
- **Ban checks**: Explicit crate bans still enforced
- **Source checks**: Registry validation still works

## What's Temporarily Disabled

- **Advisory checks**: Vulnerability scanning against RustSec database

## Compensating Control

Use `cargo-audit` for vulnerability scanning while cargo-deny advisories are disabled:

```makefile
audit: ## Run cargo-audit security scan
    cargo audit
```

cargo-audit may have better CVSS 4.0 support and can run alongside cargo-deny.

## Follow-up Required

1. **Monitor upstream**: Watch cargo-deny releases for CVSS 4.0 fix
   - Check: `cargo search cargo-deny` periodically

2. **Re-enable when fixed**: Update Makefile to use full `cargo deny check`

3. **Test before re-enabling**:
   ```bash
   cargo deny check  # Will fail until upstream fixes CVSS 4.0
   ```

## Affected Projects

Projects that may need this workaround:

- Any Rust project using cargo-deny for license/advisory checking
- docprims (applied 2026-01-28)
- sysprims (not currently affected - dependencies don't trigger the issue)

## References

- [cargo-deny issue #804](https://github.com/EmbarkStudios/cargo-deny/issues/804)
- [RustSec Advisory Database](https://rustsec.org/)
- [CVSS 4.0 Specification](https://www.first.org/cvss/v4.0/specification-document)
