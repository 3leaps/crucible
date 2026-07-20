# Decisions

This directory is **this repo's chosen home** for decision and governance records.
The record types, naming, and lifecycle are defined by the shared standard —
[Decision & Governance Records: the `*DR` family](../repository/decision-records.md),
ratified by [ADR-0003](ADR-0003-decision-record-taxonomy.md). The standard mandates
**no** storage location; `docs/decisions/` is simply the home this repo picked.

## Decision Types

The normative type set lives in the [`*DR` family standard](../repository/decision-records.md):
the full vocabulary is `{ADR, DDR, SecDR, PDR, EPR}`. The types in active use in
this lane:

| Prefix | Type                          | Scope                                                              |
| ------ | ----------------------------- | ------------------------------------------------------------------ |
| ADR    | Architecture Decision Record  | System architecture, patterns, structure                           |
| DDR    | Design / Data Decision Record | API design, schema design, interface choices                       |
| SecDR  | Security Decision Record      | Security controls, threat mitigations                              |
| PDR    | Process Decision Record       | Ways-of-working, governance, standard-set adoption                 |
| EPR    | Engineering Principle Record  | Durable engineering principles that arbitrate a standing trade-off |

## Naming Convention

`<TYPE>-<NNNN>-<kebab-slug>.md` — 4-digit, zero-padded, **per type** (each type numbers
independently, repo-global per type). See the standard for the full rule.

Examples:

- `ADR-0001-schema-config-versioning.md`
- `DDR-0001-classifier-dimension-schema.md`
- `SecDR-0001-secrets-handling.md`

## Status Values

- **proposed** - Under discussion
- **accepted** - Approved and in effect
- **superseded** - Replaced by a later record (see its `Superseded-by:`)
- **rejected** - Considered but not adopted
- **withdrawn** - Pulled by its author before acceptance

## Index

| ID                                                                | Title                                                              | Status   | Date       |
| ----------------------------------------------------------------- | ------------------------------------------------------------------ | -------- | ---------- |
| [ADR-0001](ADR-0001-schema-config-versioning.md)                  | Schema and Config Versioning with v0 and SemVer                    | accepted | 2026-01-22 |
| [ADR-0002](ADR-0002-keymaterial-fingerprint-portable-contract.md) | Key-Material Fingerprint Contract as a Portable Schema             | proposed | 2026-06-09 |
| [ADR-0003](ADR-0003-decision-record-taxonomy.md)                  | Decision & Governance Record Taxonomy (the \*DR family)            | accepted | 2026-06-29 |
| [ADR-0004](ADR-0004-coverage-attestation-contract.md)             | Coverage Attestation as a Companion Portable Contract              | proposed | 2026-07-02 |
| [ADR-0005](ADR-0005-operation-record-classification.md)           | Operation-Record Classification Standard                           | proposed | 2026-07-02 |
| [ADR-0006](ADR-0006-process-run-contract.md)                      | Local Process Telemetry & Control as a Companion Portable Contract | proposed | 2026-07-06 |
| [PDR-0001](PDR-0001-adopt-data-pipeline-principles.md)            | Adopt the Data-Pipeline Engineering Principles                     | accepted | 2026-06-29 |
| [PDR-0002](PDR-0002-worktree-per-task.md)                         | One git worktree per concurrent task                               | accepted | 2026-06-29 |
| [PDR-0003](PDR-0003-role-portfolio-tiering.md)                    | Role portfolio tiering: core, supplemental, deprecated             | accepted | 2026-06-29 |
| [PDR-0004](PDR-0004-release-publication-gate.md)                  | The signed tag authorizes publication; CI verifies and publishes   | accepted | 2026-07-17 |
| [EPR-0001](EPR-0001-published-artifact-dependency-integrity.md)   | Published Artifacts Carry an Integral Dependency Graph             | proposed | 2026-07-17 |
| [EPR-0002](EPR-0002-verification-gate-integrity.md)               | Gates Assert on Resolved State and Are Proven Able to Fail         | accepted | 2026-07-20 |
