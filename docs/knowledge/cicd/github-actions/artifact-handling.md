---
title: "Artifact Handling Patterns in GitHub Actions"
description: "When to use (and avoid) upload-artifact/download-artifact in release workflows"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-02-10"
last_updated: "2026-02-10"
status: "draft"
tags: ["github-actions", "artifacts", "release-engineering", "cicd", "troubleshooting"]
---

# Artifact Handling Patterns in GitHub Actions

This document defines release artifact patterns for GitHub Actions, with emphasis on avoiding unnecessary artifact store complexity.

## Core Principle

Use the artifact store only for cross-job transfer. If all release outputs can be built in one job, keep them in the workspace and publish directly.

## Preferred Pattern: Single-Job Release Assembly

In one job:

1. Checkout and setup toolchain
2. Build binaries/tarballs
3. Generate checksums
4. Create draft release and upload assets

Benefits:

- No artifact round-trip
- Fewer API calls
- Simpler provenance reasoning (single execution context)
- Simpler debugging

## When Multi-Job Artifacts Are Justified

Use artifact transfer between jobs only when required:

- Matrix builds on platform-specific runners
- Heavy builds where parallelization materially reduces runtime
- Trust boundary or permissions separation between build and publish stages
- Native-only targets that cannot be cross-compiled in your main job

If you must use multi-job artifacts:

- Give each artifact a deterministic name
- Include OS/arch in artifact names
- Validate expected artifact count before publish

## Rate-Limit and Reliability Considerations

Artifact download flows can hit:

- Secondary API rate limiting
- Transient network failures
- Missing artifacts from partial matrix completion

Mitigations:

- Prefer single-job release assembly when possible
- If downloading artifacts, add bounded retries with backoff
- Fail closed when expected artifacts are missing

## Checksums: Scope and Ordering

Generate checksums only after all intended release assets are finalized in one directory.

Include all shipping artifacts:

- Platform binary archives (`.tar.gz`, `.zip`)
- Package tarball(s) if shipped in release assets

Do not:

- Generate checksums per job and merge later unless unavoidable
- Upload checksums before manual signing/verification is complete

## Optional Lanes and Partial Asset Sets

Some targets may be optional (for example, `windows-arm64` built on native runners).

Pattern:

- Required asset set gates release readiness
- Optional lane assets are included when present
- Checksums must reflect exactly the final uploaded asset set

This keeps releases deterministic while allowing practical platform exceptions.

## Minimal Validation Script Pattern

Before publishing/undrafting, verify:

1. Required files exist.
2. Optional files are allowed to be absent.
3. Checksum manifests reference all present distributables.

Fail if any required file is missing or checksum manifest is stale.

## Recommended Related Docs

- [Release Rollback Procedure](release-rollback.md)
- [Manual Signing Handoff](manual-signing-handoff.md)
- [Release Verification Checklist](release-verification-checklist.md)
- [Cross-Platform Asset Selection](cross-platform-asset-selection.md)
