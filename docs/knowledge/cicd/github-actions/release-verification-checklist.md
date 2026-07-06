---
title: "Release Verification Checklist"
description: "Pre-publish checklist for draft release assets, checksums, signatures, and notes"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-02-10"
last_updated: "2026-02-10"
status: "draft"
tags: ["github-actions", "release", "checklist", "signing", "operations"]
---

# Release Verification Checklist

Use this checklist before undrafting a release.

## Asset Set

1. Required platform assets are present.
2. Optional assets are either present or explicitly marked omitted in release notes.
3. Asset filenames use explicit OS/arch tokens.
4. Windows archives contain `.exe` binaries where expected.
5. npm/package tarball is present if part of release policy.

## Integrity

1. `SHA256SUMS` exists and includes every shipped distributable.
2. `SHA512SUMS` exists and includes every shipped distributable.
3. Checksum manifests were generated after the final asset set was staged.
4. No asset changed after checksum generation.

## Signatures and Keys

1. Checksum manifests are signed per project policy.
2. Signature verification succeeds locally.
3. Public key export artifacts are attached if policy requires them.
4. Signature files correspond to the current checksum files (no stale signatures).

## Release Metadata

1. Release is still draft until verification is complete.
2. Release notes reflect the final uploaded assets.
3. Notes call out optional lanes (for example, `windows-arm64`) when omitted.
4. Version and tag metadata match binary `--version` output.

## Publish Gate

Undraft only when all sections above are complete.

If any item fails:

- Keep the release in draft.
- Regenerate and re-verify affected artifacts.
- Re-upload only corrected files.

## Related

- [Manual Signing Handoff](manual-signing-handoff.md)
- [Artifact Handling Patterns](artifact-handling.md)
- [Release Rollback Procedure](release-rollback.md)
