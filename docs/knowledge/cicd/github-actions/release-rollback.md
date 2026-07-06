---
title: "Release Rollback Procedure"
description: "How to rollback and re-execute a GitHub release when issues are discovered"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-30"
last_updated: "2026-02-09"
status: "approved"
tags: ["cicd", "release", "rollback", "github-actions"]
---

# Release Rollback Procedure

When a release workflow fails or produces incorrect artifacts, follow this procedure to rollback and re-execute cleanly.

## When to Use

- Release workflow failed after tag push
- Discovered missing files in tagged commit (e.g., package-lock.json)
- Need to include additional fixes in the release
- Provenance mismatch between release artifacts and published packages

## Order of Operations

The order matters to prevent inconsistent state:

```
1. Delete GitHub release (gh release delete)
2. Delete remote tags (git push origin --delete)
3. Push fixes to main
4. Re-create and push tags
5. Wait for release workflow
6. Manual signing (if applicable)
7. Undraft release
8. Trigger downstream workflows (npm publish, etc.)
```

### Rationale

Deleting tags before pushing main prevents any window where published tags reference commits that differ from what main will eventually be tagged with.

## Step-by-Step

### 1. Delete the GitHub Release

```bash
gh release delete v0.1.8 --yes
```

### 2. Delete Tags (Local and Remote)

```bash
# Delete local tags
git tag -d v0.1.8
git tag -d bindings/go/sysprims/v0.1.8  # if applicable

# Delete remote tags
git push origin --delete v0.1.8 bindings/go/sysprims/v0.1.8 --no-verify
```

Note: `--no-verify` is acceptable for tag deletion as no code is being pushed.

### 3. Apply Fixes and Push Main

```bash
# Make necessary fixes
git add <files>
git commit -m "fix: description of fix"

# Push to main
git push origin main
```

### 4. Re-Create Tags

```bash
VERSION=$(cat VERSION)

# Create annotated tags
git tag -a "v${VERSION}" -m "v${VERSION}: release description"
git tag -a "bindings/go/sysprims/v${VERSION}" -m "Go bindings v${VERSION}"

# Push tags to trigger release workflow
git push origin "v${VERSION}" "bindings/go/sysprims/v${VERSION}" --no-verify
```

### 5. Monitor Release Workflow

```bash
# Find the workflow run
gh run list --workflow=release.yml --limit=1

# Watch it
gh run watch <run-id> --exit-status
```

### 6. Manual Signing (if applicable)

Follow your project's signing runbook. Typically:

```bash
make release-clean
make release-download
make release-checksums
make release-sign
make release-verify-signatures    # Verify minisign + PGP before upload
make release-export-keys
make release-notes
make release-upload               # Or: make release-upload-provenance (signatures/keys only)
```

### 7. Undraft the Release

If your upload script doesn't undraft automatically:

```bash
gh release edit v0.1.8 --draft=false
```

### 8. Trigger Downstream Workflows

```bash
# Example: npm publish
gh workflow run "TypeScript npm Publish" --ref main
```

## Common Pitfalls

### Provenance Mismatch

If a publish workflow checks out `main` instead of the tag, you'll publish from a different commit than the signed release. Ensure publish workflows:

1. Fetch tags: `fetch-tags: true` in checkout
2. Checkout the tag explicitly before building

```yaml
- name: Checkout release tag
  run: |
    git checkout "${{ env.tag }}"
```

### Missing package-lock.json

`npm ci` requires `package-lock.json` to exist. Ensure it's:

- Not gitignored
- Committed before tagging

### Upload Script Fails on Missing Signatures

If `make release-upload` runs before `make release-sign`, signature files don't exist. If the upload script uses literal paths in an array (not globs), `nullglob` won't help — literal paths survive shell expansion and get passed to `gh release upload` as nonexistent files.

**Solution**: Use glob patterns for signature candidates, then filter by file existence:

```bash
SIG_CANDIDATES=("$DIR"/SHA256SUMS.* "$DIR"/SHA512SUMS.* "$DIR"/*-minisign.pub)
SIGNATURES=()
for f in "${SIG_CANDIDATES[@]}"; do
    [ -f "$f" ] && SIGNATURES+=("$f")
done
if [ ${#SIGNATURES[@]} -eq 0 ]; then
    echo "error: No signature files found. Did you run 'make release-sign' first?" >&2
    exit 1
fi
```

**Key insight**: Bash `nullglob` only affects glob patterns — literal paths like `"$DIR/SHA256SUMS.minisig"` are never removed by nullglob, even when the file doesn't exist.

### Upload Script Not Undrafting

Some upload scripts only upload assets without publishing. Verify your script includes:

```bash
gh release edit "$TAG" --draft=false
```

Or run it manually after upload.

## Verification

After rollback completion:

```bash
# Verify release is published (not draft)
gh release view v0.1.8 --json isDraft

# Verify assets
gh release view v0.1.8 --json assets --jq '.assets[].name'

# Verify downstream packages (e.g., npm)
npm view @yourorg/package@0.1.8 version
```

## Related

- [Manual Signing Handoff](manual-signing-handoff.md)
- [Artifact Handling Patterns](artifact-handling.md)
- [Release Verification Checklist](release-verification-checklist.md)
- [npm OIDC Publishing](../registry/npm-oidc.md)
- Project-specific: `RELEASE_CHECKLIST.md`
