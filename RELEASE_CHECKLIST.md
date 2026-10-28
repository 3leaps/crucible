# Release Checklist (3leaps/crucible)

3leaps/crucible is a standards repository: releases are **signed git tags** (`vX.Y.Z`) that mark
stable snapshots of documentation, schemas, and configuration. No binaries are shipped.

## Variables (Quick Reference)

Three groups. Set **Required** on every tag step. Set **Optional** only for
the behavior that line names. Every **Refused** name must be unset.

Required:

- `THREELEAPS_CRUCIBLE_RELEASE_TAG`: the release tag (e.g., `v0.2.1`), for every tag step
  (guard, tag, verify, push). Never derived from `VERSION`, `git describe`, or the branch.
- `THREELEAPS_CRUCIBLE_DECERNOR_BIN`: absolute path to the checker, decernor 0.1.8
  or newer, for every step that reads a committed pin or anchor (tag, verify, push,
  `release-check-anchors`). The version guard does not need it. Must be a regular,
  executable, non-symlink file; there is no `PATH` fallback.
  See [`docs/security/README.md`](docs/security/README.md).
- `THREELEAPS_CRUCIBLE_GPG_HOMEDIR`: the signing keyring, for `release-tag`. An
  absolute path to a dedicated, non-symlink directory. The default GPG keyring is
  never used: an unset value, a path that resolves to the default keyring, or an
  inherited `GNUPGHOME` naming a different directory is refused. The default
  keyring is resolved two ways, compared as physical paths: `gpgconf`'s homedir
  and the `.gnupg` under the account home from the user database (`dscl` on
  macOS, `getent` elsewhere), not from `HOME`. If either cannot be resolved,
  the step stops. Use a throwaway keyring holding only the signing key, and
  remove it afterwards.

Optional:

- `THREELEAPS_CRUCIBLE_PGP_KEY_ID`: key id/email/fingerprint for signing
- `THREELEAPS_CRUCIBLE_TAGGER_NAME`: tagger name stamped on signed tag objects
- `THREELEAPS_CRUCIBLE_TAGGER_EMAIL`: tagger email stamped on signed tag objects
- `THREELEAPS_CRUCIBLE_ALLOW_NON_MAIN`: set to `1` to allow tagging from non-main branch

Refused (unset every one of these; if any is set, even empty, every tag step
fails before it signs or pushes):

- `RELEASE_TAG`
- `THREELEAPS_CRUCIBLE_REQUIRE_TAG`
- `DECERNOR_BIN`
- Retired unprefixed aliases: `CRUCIBLE_RELEASE_TAG`, `CRUCIBLE_GPG_HOMEDIR`,
  `CRUCIBLE_PGP_KEY_ID`, `CRUCIBLE_TAGGER_NAME`, `CRUCIBLE_TAGGER_EMAIL`,
  `CRUCIBLE_ALLOW_NON_MAIN`, `CRUCIBLE_REQUIRE_TAG`, `CRUCIBLE_DECERNOR_BIN`

There is no precedence among these names. A refused name does not fall through
to a required one
([PDR-0008](docs/decisions/PDR-0008-release-public-identity-in-tree.md) §2.4).

The `THREELEAPS_CRUCIBLE_` prefix is the name of this repository's release
environment. These variables are not secrets and typically are not stored in
encrypted env bundles.

Install the checker from the digest pin rather than pointing at a copy found on `PATH`
(use `darwin_arm64` or `linux_amd64` to match the host; both are pinned):

```bash
decernor_dir="$(mktemp -d)"
export THREELEAPS_CRUCIBLE_DECERNOR_BIN="$(./scripts/release-fetch-decernor.sh darwin_arm64 "$decernor_dir")"
export THREELEAPS_CRUCIBLE_RELEASE_TAG="vX.Y.Z"   # type the intended tag
```

Type the tag rather than computing it: the guard then checks the stated intent against `VERSION`.

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
      release administration), and record the result. The release workflow
      cannot see bypass actors, so this run is the bypass-actors check:
  ```bash
  make release-guard-tag-ruleset
  ```
  If this step, or `make release-tag`, reports that it could not read the
  ruleset from GitHub, the credential `gh` is using was rejected or lacks
  access; the ruleset itself was not checked. `gh` uses `GH_TOKEN` or
  `GITHUB_TOKEN` when either is set, and its stored login otherwise. A token
  can be set without your noticing, for example by a per-directory environment
  such as a direnv `.envrc`. Check with `gh auth status` in the same
  environment. To use the stored login for one
  command without changing your shell:
  ```bash
  env -u GH_TOKEN -u GITHUB_TOKEN make release-guard-tag-ruleset
  ```
- [ ] No retired release variable is exported in the release shell (any one, even
      empty, fails every tag step):
  ```bash
  env | grep -E '^(RELEASE_TAG|DECERNOR_BIN|CRUCIBLE_[A-Z_]+|THREELEAPS_CRUCIBLE_REQUIRE_TAG)=' \
    && echo "unset the variables above" || echo "[ok] no retired variables"
  ```
- [ ] The committed anchors match the committed public exports under the checker:
  ```bash
  make release-check-anchors
  ```
- [ ] Guard: the explicit tag matches `VERSION`:
  ```bash
  make release-guard-tag-version   # requires THREELEAPS_CRUCIBLE_RELEASE_TAG
  ```
- [ ] Dry ceremony, before anything is signed. Run each command below. Each
      command must **fail**, and the failure text must include the quoted
      string on that line. If a command succeeds, stop. That success is a
      defect:
  ```bash
  env -u THREELEAPS_CRUCIBLE_RELEASE_TAG make release-tag        # "THREELEAPS_CRUCIBLE_RELEASE_TAG is required"
  RELEASE_TAG="${THREELEAPS_CRUCIBLE_RELEASE_TAG}" make release-tag   # "retired or unprefixed release variable set"
  THREELEAPS_CRUCIBLE_DECERNOR_BIN=decernor make release-tag    # "must be an absolute path"
  ```

### Release surfaces

The aggregated notes, the detailed note, and the changelog are hand-maintained
and can each fall behind `VERSION` without any other check failing. This guard
asserts they moved together, and runs as part of `make check`:

```bash
make release-guard-release-surfaces
```

It checks that `RELEASE_NOTES.md` leads with the current version, that
`docs/releases/vX.Y.Z.md` exists, and that `CHANGELOG.md` carries the version's
section, defines its compare link, and points `[unreleased]` at it.

What stays a manual review: **which** entries `RELEASE_NOTES.md` retains, and the
content of what is kept. The guard asserts the surface is current, not that its
contents are right.

## Tagging (Signed Tag Required)

### 1. Set up GPG environment

```bash
# Enable pinentry prompts
export GPG_TTY="$(tty)"
gpg-connect-agent updatestartuptty /bye

# Point to the dedicated signing keyring (required; never the default keyring)
export THREELEAPS_CRUCIBLE_GPG_HOMEDIR="/absolute/path/to/throwaway-signing-keyring"
export THREELEAPS_CRUCIBLE_PGP_KEY_ID="your-key-id"

# Verify key is available
GNUPGHOME="${THREELEAPS_CRUCIBLE_GPG_HOMEDIR}" gpg --list-secret-keys --keyid-format=long
```

### 2. Create the signed tag (with safety checks)

```bash
make release-tag
```

The script performs these safety checks before creating the tag:

- Explicit inputs: `THREELEAPS_CRUCIBLE_RELEASE_TAG` and `THREELEAPS_CRUCIBLE_DECERNOR_BIN` are
  set and valid, the tag matches `VERSION`, and no retired variable is set
- The signing keyring is dedicated (see Variables)
- Signing uses OpenPGP through the `gpg` on `PATH`: a configured `gpg.format`,
  `gpg.program` or `gpg.openpgp.program` naming anything else stops the step,
  and the signing command pins all three
- The committed pins at `HEAD` match their anchors under the designated checker
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
git tag -v "${THREELEAPS_CRUCIBLE_RELEASE_TAG}"
```

Expected output includes:

- `gpg: Signature made ...`
- `gpg: Good signature from ...`

The annotated tag must also carry the policy fingerprint produced by the full
pre-tag guard:

```bash
git cat-file tag "${THREELEAPS_CRUCIBLE_RELEASE_TAG}" | grep '^Tag-Publish-Policy-SHA256: '
```

### 4. Push

The release commit is already on `main`. Push only the tag:

```bash
make release-push-tag
```

This verifies the local signature, requires the tagged commit to be on `main`
and the remote tag to be absent, pushes the tag ref, and confirms the remote tag
object (and GitHub's verified flag, when `gh` is available).

**Transport.** Every remote call (fetch, tag check, push, confirm) uses
`https://github.com/3leaps/crucible.git`, never `origin`, so the tag ref lands
under the identity CI verifies. The only credential is the `GH_TOKEN` that
direnv loads from the `.envrc` above the repository, passed through
`gh auth git-credential`; every other credential helper is cleared, and an
inherited `GH_TOKEN` or `GITHUB_TOKEN` is dropped first. git runs with an empty
home directory and no global or system configuration, so a `.netrc`, a stored
credential or a global username is never sent. The push stops before
contacting GitHub when no `.envrc` above the repository loads, when it sets no
token, or when the remaining configuration (repository, or `GIT_CONFIG_*` in
the environment) carries a `url.*.insteadOf`, `url.*.pushInsteadOf`,
`http.*.extraHeader`, `http.*.cookieFile`, `http.*.proxy` or
`credential.*.username` setting; the refusal names only the kind of setting
and its scope. A failed fetch or remote read is an error. Do not retry over
`origin`, SSH or a stored `gh` login.

**Expect a bypass notice.** After `make release-push-tag`, read the output
before you treat the tag as pushed.

The notice is present when the push output reports bypassed rule violations
for the tag ref ("creations being restricted"). Tag creation is restricted by
the `Tag Publish Protection` ruleset. The maintainer
push uses the organization-admin bypass
([PDR-0004](docs/decisions/PDR-0004-release-publication-gate.md)), so the
notice is the expected result.

The notice is absent when the push prints no bypass line. The ruleset did
not apply. Stop, and check the ruleset before the release proceeds.

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
      attestation both passed. The read-only check reports bypass actors as
      not visible and not checked; the Pre-Release full check is the record
      for them.
- [ ] Verify the release is **published, not draft**, and — for a stable release
      — carries the **Latest** flag:
  ```bash
  gh release view "${THREELEAPS_CRUCIBLE_RELEASE_TAG}" --json isDraft,isPrerelease,url
  gh api repos/3leaps/crucible/releases/latest --jq .tag_name
  ```
  Expected for a stable release: `isDraft: false`, and `releases/latest` names this tag.
  Expected for a prerelease: `isDraft: false`, `isPrerelease: true`, and `releases/latest`
  still names the previous stable tag.
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
git tag -v "${THREELEAPS_CRUCIBLE_RELEASE_TAG}"
# needs THREELEAPS_CRUCIBLE_DECERNOR_BIN (see Variables)
./scripts/verify-pinned-tag.sh "${THREELEAPS_CRUCIBLE_RELEASE_TAG}"
```

Tags up to and including `v0.2.0` predate the current pin layout; verify one of
those with the `scripts/verify-pinned-tag.sh` from that tag's own commit.

**GitHub API** (CI-friendly):

```bash
TAG_SHA=$(gh api "repos/3leaps/crucible/git/ref/tags/${THREELEAPS_CRUCIBLE_RELEASE_TAG}" --jq .object.sha)
gh api repos/3leaps/crucible/git/tags/$TAG_SHA --jq .verification
```

**GitHub Web UI note**: A green "Verified" badge only appears if:

1. The signing public key is uploaded to the GitHub account
2. The tagger email matches a verified email on that account

Otherwise GitHub may show "Unverified" even though `git tag -v` succeeds locally.

## Release-key rotation

CI publishes only tags that `scripts/verify-pinned-tag.sh` accepts (PDR-0004 §2,
PDR-0008). It reads these files from the tagged commit, not the working tree, and
verifies the anchors with the digest-pinned designated checker:

| File | Holds |
| --- | --- |
| `docs/security/release-signing-keys.asc` | Public primary plus exactly one signing subkey |
| `docs/security/crucible-minisign.pub` | Minisign public pin (shared 3leaps key; signs no crucible asset today) |
| `keys/expected-fingerprints.txt` | `gpg <primary fingerprint>` then `minisign <sha256 of key blob>` |
| `keys/expected-fingerprints.ndjson` | The checker's fingerprint records for the same two keys |
| `config/release/tagger-identity.txt` | Required tagger name and email |
| `config/release/decernor-ci-sha256.txt` | Digest of each checker archive CI or the ceremony downloads |

The tag must carry one good, unexpired signature by the pinned signing subkey.
`make release-verify-tag` runs the same check locally. The key exports are the
same bytes across 3leaps repositories; copy them from a sibling rather than
re-exporting. The anchors are never copied or typed: derive them from the
committed exports with the checker. When the release key rotates:

- [ ] Replace the exports, delete both anchor files, and re-derive them with
      `./scripts/release-derive-anchors.sh --write` (it derives twice and refuses
      to overwrite), all in one reviewed PR merged **before** pushing the first
      tag signed by the new key (a stale pin fails closed: the release stays
      unpublished and `verify-signature` is red)
- [ ] Upload the new public key to the maintainer GitHub account (keeps the
      secondary account-linkage assertion and the Verified badge green)
- [ ] The verifier accepts exactly one signing subkey, so the pin switches
      in the same PR; tags already pushed under the old key are unaffected
- [ ] Keep the retired minisign pin committed under a retired name with the tag
      range it signed (PDR-0008 §2.8)

### Checker upgrade

The checker archive is pinned by digest in `config/release/decernor-ci-sha256.txt`,
one line per platform. To move to a newer decernor release, verify the release's
`SHA256SUMS` with its minisign signature against `docs/security/crucible-minisign.pub`,
then replace the lines (same version on every line) in a reviewed PR.
`scripts/release-fetch-decernor.sh` installs exactly one pinned archive per
platform and refuses any digest mismatch before extraction
(`scripts/test-release-fetch-decernor.sh` proves it, offline, in `make test`).

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
git push origin --delete "${THREELEAPS_CRUCIBLE_RELEASE_TAG}"

# Delete local tag
git tag -d "${THREELEAPS_CRUCIBLE_RELEASE_TAG}"

# If VERSION file needs revert
git revert <commit-hash>
```

## Release Tooling Reference

### Make Targets

| Target                                | Purpose                                          |
| ------------------------------------- | ------------------------------------------------ |
| `make release-tag`                    | Create signed git tag with all safety checks     |
| `make release-verify-tag`             | Verify an existing signed tag and its anchors    |
| `make release-push-tag`               | Verify, push and confirm the signed version tag  |
| `make release-check-anchors`          | Re-derive anchors with the checker and compare   |
| `make release-guard-tag-version`      | Verify the explicit tag matches VERSION          |
| `make test-release-identity`          | End-to-end identity controls (gpg + checker)     |
| `make release-guard-tag-ruleset`      | Verify live version-tag publication policy       |
| `make release-guard-release-surfaces` | Verify release notes and changelog match VERSION |

### Scripts

All scripts are in `scripts/` and can be run directly if needed.

**`scripts/release-tag.sh`** - The primary release script. Safety checks:

1. Refuses retired variables; requires the explicit tag and checker
2. Validates tag format (`vMAJOR.MINOR.PATCH`) and that it matches `VERSION`
3. Ensures working tree is clean (no uncommitted changes)
4. Ensures on `main` branch (override with `THREELEAPS_CRUCIBLE_ALLOW_NON_MAIN=1`)
5. Ensures tag doesn't already exist
6. Verifies the committed pins at `HEAD` against their anchors with the checker
7. Validates the complete live ruleset, including bypass actors
8. Embeds the canonical policy fingerprint in the tag message
9. Verifies GPG signing key is available
10. Creates signed annotated tag
11. Automatically verifies signature after creation

**`scripts/release-guard-tag-version.sh`** - Version consistency check:

- Requires `THREELEAPS_CRUCIBLE_RELEASE_TAG` and compares it against the `VERSION` file
- Never falls back to `git describe`; a missing tag is an error
- Exits 0 if match, exits 1 if mismatch

**`scripts/release-env.sh`** - Explicit release inputs, sourced by every tag step:

- Refuses retired and unprefixed variables
- Requires the canonical tag from `THREELEAPS_CRUCIBLE_RELEASE_TAG`
- Binds the checker from `THREELEAPS_CRUCIBLE_DECERNOR_BIN` with identity and
  minimum-version checks; no `PATH` fallback
- Requires a dedicated signing keyring, refusing the default keyring by
  either resolution
- Refuses a non-OpenPGP or non-`gpg` signing configuration
- Runs each push-step remote call against the explicit URL with only the org
  token (see Push)

**`scripts/release-guard-tag-ruleset.sh`** - Publication-boundary check:

- Resolves `Tag Publish Protection` by name through the GitHub API
- Requires an active repository ruleset covering only `refs/tags/v*`
- Requires creation, update, deletion, and non-fast-forward protection
- Default mode requires the sole bypass to be organization administrators in
  `always` mode
- `--print-attestation` performs the full check and emits the canonical policy
  fingerprint for the signed tag
- `--read-only` checks the fields a read-only credential can see (name,
  repository, target, enforcement, ref conditions, rules). A bypass list that
  is null or empty is reported as not visible and not checked, never as a
  match; a visible list must be exactly the expected one, and only then is a
  match reported
- `--verify-tag-attestation` requires the signed tag object to carry the exact
  expected full-policy fingerprint
- Fails closed on missing, duplicate, malformed, or unexpected policy data
- Full mode requires authenticated `gh` access sufficient for complete ruleset
  validation; read-only mode requires repository metadata access

**`scripts/release-verify-tag.sh`** - Signature verification:

- Runs the pinned-key and anchor check (`scripts/verify-pinned-tag.sh`) on
  `THREELEAPS_CRUCIBLE_RELEASE_TAG`
- Imports only the committed pin into a throwaway keyring; never reads the
  default keyring or an ambient `GNUPGHOME`

---

_Adapted from established release-process patterns._
