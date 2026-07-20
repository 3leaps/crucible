# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file starts at v0.1.17, the first public release baseline.

---

## v0.1.21 (2026-07-20)

**Signed publication-policy attestation.**

### Highlights

- **Complete pre-tag validation** — the release script checks the configured
  version-tag policy before creating a tag
- **Signed policy fingerprint** — annotated release tags carry the canonical
  publication-policy fingerprint
- **Publication verification** — CI checks the read-only policy view and the
  signed fingerprint after pinned-key signature verification

### Changes

| Area        | Change                                                                                  |
| ----------- | --------------------------------------------------------------------------------------- |
| **Release** | Add complete/read-only ruleset modes and signed policy-attestation handling             |
| **CI**      | Verify the read-only policy view and signed fingerprint after pinned-key verification   |
| **Tests**   | Cover validation modes and missing or incorrect attestations                            |
| **Docs**    | Update the release gate decision and operator checklist                                 |
| **Build**   | Version 0.1.20 → 0.1.21; package metadata, README badge, and changelog links are synced |

**Full release notes**: [docs/releases/v0.1.21.md](docs/releases/v0.1.21.md)

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

[View complete changelog →](CHANGELOG.md)
