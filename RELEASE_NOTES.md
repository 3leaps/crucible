# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file keeps the latest three releases. Earlier releases, back to
> v0.1.17 (the first public baseline), are in [CHANGELOG.md](CHANGELOG.md) and
> [docs/releases/](docs/releases/).

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

---

## v0.2.0 (2026-10-22)

**Four proposed contract families (recurrence rules, durable records with use
restrictions, durable indexes and data acquisition) and a release-identity
process decision.**

- **Recurrence rules (proposed)**: `recurrence/v0` publishes a canonical JSON
  form of an RFC 5545 RRULE subset with normative expansion semantics. DST-gap
  times are skipped as non-slots without consuming `COUNT`, overlaps resolve to
  the first instant, and a conformance corpus is pinned to IANA tzdb 2026e.
  Promotion requires two independent implementations to pass it.
- **Durable records with use restrictions (proposed, experimental)**:
  `durable-record/v1` adds holds that block serving, export and reuse while
  keeping records readable for audit. It is a new major contract version; v0 is
  unchanged, and there is no automatic migration.
- **Durable indexes (proposed, experimental)**: `durable-index/v0` describes
  object-inventory snapshots as a segmented-snapshot profile, with an
  independent TypeScript reader. Evidence is logical only.
- **Data acquisition (proposed)**: `data-acquisition/v0` covers source policy,
  acquisition scope and shared-capacity registration with exact-byte pins.
- **Decisions and charter**: PDR-0008 (proposed) sets controls for committed
  release public identity; PDR-0006 names the validation interpreters
  (Python >= 3.9, Node.js >= 22.6).
- **Schema revision**: the segmented-snapshot manifest gains an optional
  `profile_metadata` binding; readers that do not implement it must refuse it.
- **Toolchain**: goneat v0.6.5 and the glibc tools runner v0.5.12 (biome
  2.5.15). The release guards no longer fail spuriously on a large changelog.

See [docs/releases/v0.2.0.md](docs/releases/v0.2.0.md).
