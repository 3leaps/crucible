# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file starts at v0.1.17, the first public release baseline.

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
