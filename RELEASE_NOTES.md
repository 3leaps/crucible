# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file starts at v0.1.17, the first public release baseline.

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

## v0.1.17 (2026-07-06)

**Baseline release, data artifact metadata hardening, and repository guidance alignment.**

### Highlights

- **Physical file metadata is content** — boundary-crossing columnar
  representations must suppress, make opaque, or omit restricted-class
  row-group/page statistics, page-index bounds, and membership-oracle structures
  such as per-column Bloom filters
- **Data artifact validator coverage** — validators now check physical metadata
  suppression declarations for restricted-class columns in boundary-crossing
  columnar representations
- **Review-loop fold** — physical-file-metadata handling is folded into Metadata
  Is Content; format-specific mechanics remain producer-profile details
- **Reference producer citation** — examples intentionally cite
  `fulmenhq/sumpter` as a public, non-normative reference producer
- **Public repository guidance** — contributor-agent, AI attribution, and
  repository docs are aligned for public standards use

### Changes

| Area           | Change                                                                                  |
| -------------- | --------------------------------------------------------------------------------------- |
| **Standards**  | Treat physical columnar metadata and membership-oracle structures as content            |
| **Examples**   | Add deliberate `fulmenhq/sumpter` reference-producer citation                           |
| **Validation** | Add validator coverage for physical metadata suppression in columnar representations    |
| **Docs**       | Align repository-facing guidance for public standards use                               |
| **Decisions**  | Retitle ADR-0002 around portable schema contract framing                                |
| **Build**      | Version 0.1.16 → 0.1.17; package metadata, README badge, and changelog links are synced |

**Full release notes**: [docs/releases/v0.1.17.md](docs/releases/v0.1.17.md)

---

[View complete changelog →](CHANGELOG.md)
