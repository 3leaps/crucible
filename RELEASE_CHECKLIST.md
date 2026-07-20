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
- [ ] The live version-tag ruleset matches the **full** publication policy,
      including bypass actors (run with the maintainer credential used for
      release administration):
  ```bash
  make release-guard-tag-ruleset
  ```
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

- Live `Tag Publish Protection` ruleset matches the required policy
- Canonical publication-policy fingerprint is embedded in the signed tag
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

The annotated tag must also carry the policy fingerprint produced by the full
pre-tag guard:

```bash
git cat-file tag "v$(cat VERSION)" | grep '^Tag-Publish-Policy-SHA256: '
```

### 4. Push

```bash
git push origin main
git push origin v$(cat VERSION)
```

## Post-Release

Pushing the signed tag is the last manual act. `release.yml` verifies the
signature and publishes the release; see
[PDR-0004](docs/decisions/PDR-0004-release-publication-gate.md). Nothing below
requires a click — these items confirm CI did its job.

**Verify the release is published, not merely created.** A release object that
exists but is still a draft is a failure, not a completed release: it is
invisible to every consumer while the repository looks healthy.

- [ ] Verify tag appears on GitHub: https://github.com/3leaps/crucible/tags
- [ ] Verify the `release.yml` workflow succeeded (a failed `verify-signature`
      job means publication was refused — investigate, do not publish by hand)
- [ ] Verify the workflow's read-only ruleset check and signed policy
      attestation both passed.
- [ ] Verify the release is **published, not draft**, and — for a stable release
      — carries the **Latest** flag:
  ```bash
  gh release view "v$(cat VERSION)" --json isDraft,isLatest,isPrerelease,url
  ```
  Expected for a stable release: `isDraft: false`, `isLatest: true`.
  Expected for a prerelease: `isDraft: false`, `isPrerelease: true`, `isLatest: false`.
- [ ] Verify the published release is reachable and its notes render correctly:
      https://github.com/3leaps/crucible/releases/latest

> If a release is sitting in draft, that is a defect in the publication path —
> the fix is to repair the workflow, not to undraft it manually and move on.

### Verify tag signature (optional manual check)

CI already asserts this before publishing; these commands are for local
diagnosis.

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

## Release-key rotation

CI publishes only tags signed by a key in the committed pin file
`docs/security/release-signing-keys.asc` (PDR-0004 §2). When the release key
rotates:

- [ ] Update `docs/security/release-signing-keys.asc` by reviewed PR **before**
      pushing the first tag signed by the new key (a stale pin fails closed:
      the release stays unpublished and `verify-signature` is red)
- [ ] Upload the new public key to the maintainer GitHub account (keeps the
      secondary account-linkage assertion and the Verified badge green)
- [ ] Remove the retired key from the pin file once no in-flight tag depends
      on it

**Expiry is rotation you did not schedule.** A pinned key that passes its
expiration date fails verification exactly as a missing pin does — the release
stays unpublished and the job is red — but nothing prompts it first. Check the
remaining life of the pinned material periodically, and refresh the pin before
it lapses rather than after a release blocks:

```bash
gpg --show-keys docs/security/release-signing-keys.asc | grep -E "^(pub|sub)"
```

Each line ends with `[expires: YYYY-MM-DD]` where an expiry is set. The signing
subkey — the one marked `[S]` — is what gates publication.

## Rollback

Version tags are protected against deletion and update. Prefer a corrective
release. If exceptional removal is required, an organization administrator must
explicitly exercise the protected-tag bypass before running the remote-tag
deletion below:

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
| `make release-guard-tag-ruleset` | Verify live version-tag publication policy    |

### Scripts

All scripts are in `scripts/` and can be run directly if needed.

**`scripts/release-tag.sh`** - The primary release script. Safety checks:

1. Validates tag format (`vMAJOR.MINOR.PATCH`)
2. Ensures working tree is clean (no uncommitted changes)
3. Ensures on `main` branch (override with `THREELEAPS_CRUCIBLE_ALLOW_NON_MAIN=1`)
4. Ensures tag doesn't already exist
5. Validates the complete live ruleset, including bypass actors
6. Embeds the canonical policy fingerprint in the tag message
7. Verifies GPG signing key is available
8. Creates signed annotated tag
9. Automatically verifies signature after creation

**`scripts/release-guard-tag-version.sh`** - Version consistency check:

- Compares current git tag (or `THREELEAPS_CRUCIBLE_RELEASE_TAG` env var) against `VERSION` file
- Use in CI with `THREELEAPS_CRUCIBLE_REQUIRE_TAG=1` to enforce tag presence
- Exits 0 if match, exits 1 if mismatch

**`scripts/release-guard-tag-ruleset.sh`** - Publication-boundary check:

- Resolves `Tag Publish Protection` by name through the GitHub API
- Requires an active repository ruleset covering only `refs/tags/v*`
- Requires creation, update, deletion, and non-fast-forward protection
- Default mode requires the sole bypass to be organization administrators in
  `always` mode
- `--print-attestation` performs the full check and emits the canonical policy
  fingerprint for the signed tag
- `--read-only` checks the read-only policy view; unavailable bypass data is
  accepted, while unexpected visible actors still fail
- `--verify-tag-attestation` requires the signed tag object to carry the exact
  expected full-policy fingerprint
- Fails closed on missing, duplicate, malformed, or unexpected policy data
- Full mode requires authenticated `gh` access sufficient for complete ruleset
  validation; read-only mode requires repository metadata access

**`scripts/release-verify-tag.sh`** - Signature verification:

- Verifies GPG signature on the tag for `VERSION` (or `THREELEAPS_CRUCIBLE_RELEASE_TAG`)
- Respects `THREELEAPS_CRUCIBLE_GPG_HOMEDIR` for dedicated keyrings

---

_Adapted from established release-process patterns._
