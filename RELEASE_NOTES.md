# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file keeps the latest three releases. Earlier releases, back to
> v0.1.17 (the first public baseline), are in [CHANGELOG.md](CHANGELOG.md) and
> [docs/releases/](docs/releases/).

---

## v0.2.3 (2026-10-27)

**Durable-record/v1 gains continuation streams and restriction review.**

- **Continuation streams (durable-record/v1, additive)**: a stream that
  re-records another stream's content declares `continues` and marks imports
  with `imported_from`. A `restrictions_reviewed` entry binds the reviewed
  source cut, the effective source restrictions and the destination's applied
  restrictions. Serving, export and reuse fail closed as `restrictions_pending`
  until a current review exists. Existing v1 records and journals are
  unchanged. The logical controls qualify no store.
- **Repository classes (draft 0.1.1)**: C5 requires a `version` subcommand
  and settles JSON-only and artifact-output verbs; C3 counts test variables;
  C4 points host-tool ceremonies at `make doctor`; P1 settles npm and PyPI
  reservation.

See [docs/releases/v0.2.3.md](docs/releases/v0.2.3.md).

---

## v0.2.2 (2026-10-25)

**Repository classes drafted; durable-record/v1 amended before adoption.**

- **Repository classes (draft)**: pick a repo's class by its primary caller
  (prims, bolts, wits, voys; pressers adjacent), with per-class MUST checks, a
  repo declaration and a new-repo template. ADR-0018 records the prims
  multi-language commitment and sibling-dependency rules.
- **Durable-record/v1 (not additive)**: records move to envelope `v: 1` with an
  optional `produced_at`, so every v1 digest and pin changes; every v1 instant
  has one canonical spelling; `retired` gains an optional key and receipt;
  `commit_strategy` is a closed set. Amended on 2026-10-25 with no v1
  adopters; v0 is unchanged.
- **Release tooling**: PDR-0008 accepted; the default GPG keyring is never used;
  failed GitHub reads are reported as such; `release-tag-push` is removed.
- **Fixed**: the durable-queue reference model keeps a fractional
  `clock_start`.

See [docs/releases/v0.2.2.md](docs/releases/v0.2.2.md).

---

## v0.2.1 (2026-10-23)

**Release tooling adopts PDR-0008; PDR-0010 proposed.**

- **Release identity (PDR-0008)**: decernor derives and verifies the
  release fingerprint anchors, read from the tagged commit, with no second
  parser. Every tag step needs `THREELEAPS_CRUCIBLE_RELEASE_TAG` (and the
  checker path where it reads pins); retired names are refused. CI pins the
  checker by digest. This release's tag is the first under that ceremony.
- **Verifiers**: the minisign pin is renamed
  `docs/security/crucible-minisign.pub` (same key). Releases are signed tags
  only; there are no checksum files.
- **Immutable release publication (PDR-0010, proposed)**: verify staged assets
  before immutable publication. No workflow change here.
- **CI baseline**: digest- and commit-pinned examples and new supply-chain
  guidance.

See [docs/releases/v0.2.1.md](docs/releases/v0.2.1.md).
