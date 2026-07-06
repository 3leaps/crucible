# Release Checklist (3leaps/crucible)

3leaps/crucible is a standards repository: releases are **signed git tags** (`vX.Y.Z`) that mark
stable snapshots of documentation, schemas, and configuration. No binaries are shipped.

## Variables (Quick Reference)

- `THREELEAPS_CRUCIBLE_RELEASE_TAG`: optional override tag (e.g., `v0.1.3`)
- `THREELEAPS_CRUCIBLE_GPG_HOMEDIR`: dedicated signing keyring directory (recommended)
- `THREELEAPS_CRUCIBLE_PGP_KEY_ID`: key id/email/fingerprint for signing
- `THREELEAPS_CRUCIBLE_TAGGER_NAME`: tagger name stamped on signed tag objects
- `THREELEAPS_CRUCIBLE_TAGGER_EMAIL`: tagger email stamped on signed tag objects
- `THREELEAPS_CRUCIBLE_ALLOW_NON_MAIN`: set to `1` to allow tagging from non-main branch

Legacy aliases (still supported):

- `CRUCIBLE_RELEASE_TAG`, `CRUCIBLE_GPG_HOMEDIR`, `CRUCIBLE_PGP_KEY_ID`, `CRUCIBLE_ALLOW_NON_MAIN`

> **Why `THREELEAPS_CRUCIBLE_`?** The prefix disambiguates this repository's release environment from other Crucible-style repositories and avoids generic environment variable names.

Note: These are not secrets and typically aren't stored in encrypted env bundles.

## Pre-Release

- [ ] `git status` is clean
- [ ] Quality gates pass: `make check`
- [ ] `CHANGELOG.md` updated (Unreleased → new section with date)
- [ ] CHANGELOG footer links synced (`make version-set V=X.Y.Z` updates `[unreleased]` and adds `[X.Y.Z]`)
- [ ] `docs/releases/vX.Y.Z.md` created
- [ ] `RELEASE_NOTES.md` updated (keep only latest 3 entries)
- [ ] `VERSION` matches the intended tag
- [ ] README version badge updated to match VERSION
- [ ] All changes committed and pushed to main
- [ ] CI passes on main branch
- [ ] Guard: ensure tag/version match:
  ```bash
  make release-guard-tag-version
  ```

## Tagging (Signed Tag Required)

### 1. Set up GPG environment

```bash
# Enable pinentry prompts
export GPG_TTY="$(tty)"
gpg-connect-agent updatestartuptty /bye

# Point to dedicated signing keyring (recommended)
export THREELEAPS_CRUCIBLE_GPG_HOMEDIR="/path/to/signing-keyring"
export THREELEAPS_CRUCIBLE_PGP_KEY_ID="your-key-id"

# Verify key is available
GNUPGHOME="${THREELEAPS_CRUCIBLE_GPG_HOMEDIR}" gpg --list-secret-keys --keyid-format=long
```

### 2. Create the signed tag (with safety checks)

```bash
make release-tag
```

The script performs these safety checks before creating the tag:

- Tag format validation (`vMAJOR.MINOR.PATCH`)
- Clean working tree required
- Must be on `main` branch (set `THREELEAPS_CRUCIBLE_ALLOW_NON_MAIN=1` to override)
- Tag must not already exist
- GPG signing key availability verified
- Automatic signature verification after creation

### 3. Verify the signed tag (optional manual check)

```bash
make release-verify-tag
# or:
git tag -v v$(cat VERSION)
```

Expected output includes:

- `gpg: Signature made ...`
- `gpg: Good signature from ...`

### 4. Push

```bash
git push origin main
git push origin v$(cat VERSION)
```

## Post-Release

- [ ] Verify tag appears on GitHub: https://github.com/3leaps/crucible/tags
- [ ] Verify release.yml workflow runs and creates GitHub Release
- [ ] Spot-check release notes render correctly

### Verify tag signature (optional)

**Local git** (most reliable):

```bash
git fetch --tags origin
git tag -v v$(cat VERSION)
```

**GitHub API** (CI-friendly):

```bash
TAG_SHA=$(gh api repos/3leaps/crucible/git/ref/tags/v$(cat VERSION) --jq .object.sha)
gh api repos/3leaps/crucible/git/tags/$TAG_SHA --jq .verification
```

**GitHub Web UI note**: A green "Verified" badge only appears if:

1. The signing public key is uploaded to the GitHub account
2. The tagger email matches a verified email on that account

Otherwise GitHub may show "Unverified" even though `git tag -v` succeeds locally.

## Rollback

If issues are discovered after release:

```bash
# Delete remote tag
git push origin --delete v<VERSION>

# Delete local tag
git tag -d v<VERSION>

# If VERSION file needs revert
git revert <commit-hash>
```

## Release Tooling Reference

### Make Targets

| Target                           | Purpose                                       |
| -------------------------------- | --------------------------------------------- |
| `make release-tag`               | Create signed git tag with all safety checks  |
| `make release-verify-tag`        | Verify an existing signed tag                 |
| `make release-guard-tag-version` | Verify tag matches VERSION file (CI-friendly) |

### Scripts

All scripts are in `scripts/` and can be run directly if needed.

**`scripts/release-tag.sh`** - The primary release script. Safety checks:

1. Validates tag format (`vMAJOR.MINOR.PATCH`)
2. Ensures working tree is clean (no uncommitted changes)
3. Ensures on `main` branch (override with `THREELEAPS_CRUCIBLE_ALLOW_NON_MAIN=1`)
4. Ensures tag doesn't already exist
5. Verifies GPG signing key is available
6. Creates signed annotated tag
7. Automatically verifies signature after creation

**`scripts/release-guard-tag-version.sh`** - Version consistency check:

- Compares current git tag (or `THREELEAPS_CRUCIBLE_RELEASE_TAG` env var) against `VERSION` file
- Use in CI with `THREELEAPS_CRUCIBLE_REQUIRE_TAG=1` to enforce tag presence
- Exits 0 if match, exits 1 if mismatch

**`scripts/release-verify-tag.sh`** - Signature verification:

- Verifies GPG signature on the tag for `VERSION` (or `THREELEAPS_CRUCIBLE_RELEASE_TAG`)
- Respects `THREELEAPS_CRUCIBLE_GPG_HOMEDIR` for dedicated keyrings

---

_Adapted from established release-process patterns._
