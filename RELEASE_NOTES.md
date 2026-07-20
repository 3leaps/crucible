# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file starts at v0.1.17, the first public release baseline.

---

## v0.1.20 (2026-07-19)

**Governance records: dependency-graph integrity, and the release process that publishes them.**

### Highlights

- **EPR-0001 (proposed)** — this lane's first Engineering Principle Record:
  every artifact built from a resolved dependency graph ships that graph
  pinned in-repo, enforced at build, continuously audited, and held at parity
  across all distribution surfaces of the same release. Obligations are fixed;
  tooling is deliberately left to adopting repositories
- **PDR-0004 (accepted)** — the signed tag authorizes publication. Signing
  creates the tag and the push triggers the workflow, so the tag is already
  signed when CI runs; a draft awaiting a signature guarded a condition that
  could not occur
- **Releases publish from CI** — the workflow asserts a verified tag signature,
  binds authorization to the exact annotated tag object, then publishes
  directly, setting `Latest` explicitly for stable versions; prereleases
  publish as prereleases and do not take `Latest`
- **Unverified tags fail closed** — no release is created, making an
  unpublished release a failure signal rather than a normal waiting state
- **Version-tag policy is executable** — release tagging and publication verify
  the live ruleset protects `refs/tags/v*` with only the
  organization-administrator bypass; workflow actions are pinned to immutable
  commits

### Changes

| Area           | Change                                                                                        |
| -------------- | --------------------------------------------------------------------------------------------- |
| **Governance** | Add EPR-0001 (proposed) and PDR-0004 (accepted); `EPR` listed in active use; index completed  |
| **CI**         | Release workflow verifies the exact tag object, publishes non-draft, pins third-party actions |
| **Process**    | Checklist, tagging, and publication verify the live version-tag ruleset                       |
| **Build**      | Version 0.1.19 → 0.1.20; package metadata, README badge, and changelog links are synced       |

**Full release notes**: [docs/releases/v0.1.20.md](docs/releases/v0.1.20.md)

---

## v0.1.19 (2026-07-09)

**Data artifact contract alignment: fully-withheld catalogs and optional grain catalogs.**

### Highlights

- **Fully-withheld field catalogs** — `fields: []` is valid when
  `withheld_field_count >= 1`, matching the protection model that already
  allows disclosing only a withheld count when field names are sensitive
- **Optional grain catalog refs** — raw archival grains that are not queryable
  or renderable may omit `field_catalog_ref`; queryable/renderable enforcement
  stays in Validation Requirements
- **Golden fixtures** — positive descriptors for both shapes; empty fields
  without a positive count fail closed

### Changes

| Area          | Change                                                                                          |
| ------------- | ----------------------------------------------------------------------------------------------- |
| **Standards** | Align field-catalog and grain catalog prose with fully-withheld and archival-optional semantics |
| **Schemas**   | Loosen `data-artifact/v0` constraints for empty catalogs and optional grain `field_catalog_ref` |
| **Examples**  | Add fully-withheld and raw-archival golden descriptors                                          |
| **Build**     | Version 0.1.18 → 0.1.19; package metadata, README badge, and changelog links are synced         |

**Full release notes**: [docs/releases/v0.1.19.md](docs/releases/v0.1.19.md)

---

## v0.1.18 (2026-07-06)

**Companion contract for local process telemetry and control.**

### Highlights

- **Process Run Contract (proposed)** — add `process-run/v0`, a source-neutral
  contract for observing and steering local long-running processes: an
  append-only NDJSON event stream and a token-gated local control channel, at a
  deliberately minimal complexity floor (files and a local socket,
  schema-versioned)
- **Sibling to `data-artifact/v0`** — that contract governs _what was produced_;
  this one governs _the producing process_, and terminal events bridge a run to
  its output artifacts
- **ADR-0006** — ratifies `process-run/v0` as a proposed companion contract;
  graduates to accepted on a downstream conforming implementation
- **Validation coverage** — `make check` now exercises the process-run schemas,
  golden examples (including per-line NDJSON events), and the contract manifest

### Changes

| Area           | Change                                                                                    |
| -------------- | ----------------------------------------------------------------------------------------- |
| **Standards**  | Add the `process-run/v0` local process telemetry and control contract (draft)             |
| **Schemas**    | Add `process-run/v0` schema family, `contract.json` manifest, README, and golden examples |
| **Decisions**  | Add ADR-0006 ratifying `process-run/v0` as a proposed companion contract                  |
| **Validation** | `make check` now validates the process-run examples and contract manifest                 |
| **Build**      | Version 0.1.17 → 0.1.18; package metadata, README badge, and changelog links are synced   |

**Full release notes**: [docs/releases/v0.1.18.md](docs/releases/v0.1.18.md)

---

[View complete changelog →](CHANGELOG.md)
