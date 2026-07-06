---
title: "Manual Signing Handoff for Draft Releases"
description: "Operator workflow for downloading draft assets, signing locally, verifying, and re-uploading"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-02-10"
last_updated: "2026-02-10"
status: "draft"
tags: ["github-actions", "release", "signing", "checksums", "operations"]
---

# Manual Signing Handoff for Draft Releases

Many teams intentionally split release generation and signing:

- CI produces draft release assets
- Operator performs signing on a trusted local machine
- Operator uploads signed manifests/keys and publishes release

This document captures that operator workflow.

## Workflow Overview

1. CI builds release assets and creates a **draft** GitHub release.
2. Operator downloads assets locally.
3. Operator recomputes and verifies checksums.
4. Operator signs checksum manifests.
5. Operator verifies signatures and exports public key material.
6. Operator updates release notes and uploads modified assets.
7. Operator undrafts the release.

## Why This Pattern

- Keeps private signing keys off CI runners
- Supports hardware-backed key workflows
- Adds a final operator verification gate before publish
- Preserves fallback paths (local rebuild + upload-all) for recovery

## Asset Classes

Typical release assets:

- Platform binary archives (`linux`, `darwin`, `windows`; optional `windows-arm64`)
- npm/package tarball (if distributed alongside binaries)
- Checksum manifests: `SHA256SUMS`, `SHA512SUMS`
- Signature and key artifacts generated locally

## Operational Rules

1. Download all candidate assets from draft release before signing.
2. Recompute checksums locally from downloaded assets.
3. Sign checksum manifests locally.
4. Verify signatures locally before upload.
5. Upload only changed assets when possible (checksums/signatures/keys/notes).
6. Use full upload-all path only for recovery or intentional local rebuilds.

## Optional Platform Assets (Windows ARM64)

If `windows-arm64` is built in a manual/native workflow:

- Include it in checksums when present.
- Do not block release if policy marks it optional and build was skipped.
- Ensure release notes state whether the optional asset is included.

## Suggested Command Sequence

Project-local targets often follow this shape:

```bash
make release-clean
make release-download
make release-checksums
make release-sign
make release-verify-signatures
make release-export-keys
make release-notes
make release-upload          # selective upload
# or make release-upload-all # full replacement path
```

Use project-specific names if needed, but keep the order stable.

## Consistency Checks Before Undraft

1. Draft release asset list matches expected required set.
2. Checksum manifests include every distributable present.
3. Signature verification passes for both SHA256 and SHA512 manifests.
4. Public key export files are attached (if policy requires).
5. Release notes mention optional assets and any omitted lanes.

## Failure and Recovery

If inconsistencies are found:

- Keep release in draft.
- Delete/re-upload incorrect checksum/signature assets.
- Regenerate and re-verify locally before upload.

If workflow-level errors invalidate provenance, follow:

- [Release Rollback Procedure](release-rollback.md)

## Related

- [Artifact Handling Patterns](artifact-handling.md)
- [Release Verification Checklist](release-verification-checklist.md)
- [Release Rollback Procedure](release-rollback.md)
