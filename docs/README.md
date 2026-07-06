# 3leaps Standards Documentation

Lightweight, practical standards for 3leaps open source tools.

**New here?** Start with [Getting Started](getting-started.md).

## Categories

### [Coding](coding/)

Language-agnostic coding standards covering output hygiene, error handling, exit codes, and timestamps.

- [baseline.md](coding/baseline.md) - Core conventions all tools must follow

### [Repository](repository/)

Repository structure, automation, and collaboration patterns.

- [makefile-minimum.md](repository/makefile-minimum.md) - Required make targets
- [commit-style.md](repository/commit-style.md) - Commit message format
- [secure-commits.md](repository/secure-commits.md) - Security-sensitive commit policy
- [frontmatter.md](repository/frontmatter.md) - Document frontmatter metadata
- [agents.md](repository/agents.md) - AI agent collaboration
- [agent-identity.md](repository/agent-identity.md) - AI contribution attribution

### [Observability](observability/)

Logging, metrics, and operational visibility.

- [logging-baseline.md](observability/logging-baseline.md) - Logging fundamentals

### [Operations](operations/)

Operational guides for maintainers and implementers.

- [ci-baseline.md](operations/ci-baseline.md) - CI/CD patterns and gotchas
- [upstream-sync-guide.md](operations/upstream-sync-guide.md) - Vendoring crucible content

### [SOP](sop/)

Standard operating procedures - mandatory policies.

- [stream-output.md](sop/stream-output.md) - stdout/stderr discipline for tool chainability

### [Standards](standards/)

Cross-cutting classification standards for data and artifacts, plus contract standards shared across tools.

- [auth-session-artifact.md](standards/auth-session-artifact.md) - Non-secret auth session metadata contract (acquirer ⇄ inspector)
- [classifiers-framework.md](standards/classifiers-framework.md) - How the classifiers system fits together (docs + config + schemas)
- [data-artifact-contract.md](standards/data-artifact-contract.md) - Portable artifact, representation, catalog, provenance, and protection contract
- [data-artifact-contract-examples.md](standards/data-artifact-contract-examples.md) - Source-neutral stress cases and producer adoption preview template
- [data-sensitivity-classification.md](standards/data-sensitivity-classification.md) - Sensitivity levels (UNKNOWN, 0-6)
- [volatility-classification.md](standards/volatility-classification.md) - Update cadence (static → streaming)
- [access-tier-classification.md](standards/access-tier-classification.md) - Distribution control (public → eyes-only)
- [retention-lifecycle-classification.md](standards/retention-lifecycle-classification.md) - Retention periods
- [schema-stability-classification.md](standards/schema-stability-classification.md) - Schema evolution
- [volume-tier-classification.md](standards/volume-tier-classification.md) - Data scale (tiny → massive)
- [velocity-mode-classification.md](standards/velocity-mode-classification.md) - Processing patterns (batch/streaming)

**Domain-scoped (opt-in, not universal baseline):**

- [data-engineering/data-pipeline-principles.md](standards/data-engineering/data-pipeline-principles.md) - Durable data-pipeline engineering principles (28 across 5 axes; EPR-class)

### [Decisions](decisions/)

Decision and governance records (ADR / PDR / …) — see the [decisions index](decisions/README.md) and the [`*DR` family standard](repository/decision-records.md).

- [ADR-0001](decisions/ADR-0001-schema-config-versioning.md) - Schema and config versioning
- [ADR-0002](decisions/ADR-0002-keymaterial-fingerprint-portable-contract.md) - Key-material fingerprint contract as a portable schema (proposed)
- [ADR-0003](decisions/ADR-0003-decision-record-taxonomy.md) - Decision & governance record taxonomy (the \*DR family)
- [PDR-0001](decisions/PDR-0001-adopt-data-pipeline-principles.md) - Adopt the data-pipeline engineering principles

### [Catalog](catalog/)

Reusable templates and reference materials.

- [roles/](catalog/roles/) - Baseline role prompts for AI agent sessions
- [classifiers/](catalog/classifiers/) - Index of classifier dimensions and sources

### [Releases](releases/)

Current release documentation.

- [v0.1.17.md](releases/v0.1.17.md) - Baseline release, data artifact metadata hardening, and repository guidance alignment

## Design Principles

1. **Minimal** - Only what's needed, nothing more
2. **Practical** - Real patterns from real projects
3. **Reference-friendly** - Easy to link, easy to clone
4. **Extensible** - Baseline patterns can be adopted or extended locally

## Canonical URLs

> The hosted docs site is **planned** (targeted v0.1.x). Today, the canonical source is
> this repository (GitHub). The planned canonical web paths are:

| Document                 | URL                                                                       |
| ------------------------ | ------------------------------------------------------------------------- |
| Getting Started          | `crucible.3leaps.dev/getting-started`                                     |
| Coding Baseline          | `crucible.3leaps.dev/coding/baseline`                                     |
| Makefile Minimum         | `crucible.3leaps.dev/repository/makefile-minimum`                         |
| Commit Style             | `crucible.3leaps.dev/repository/commit-style`                             |
| Secure Commits           | `crucible.3leaps.dev/repository/secure-commits`                           |
| Frontmatter              | `crucible.3leaps.dev/repository/frontmatter`                              |
| Agents                   | `crucible.3leaps.dev/repository/agents`                                   |
| AI Attribution           | `crucible.3leaps.dev/repository/agent-identity`                           |
| Logging Baseline         | `crucible.3leaps.dev/observability/logging-baseline`                      |
| CI/CD Baseline           | `crucible.3leaps.dev/operations/ci-baseline`                              |
| Stream Output            | `crucible.3leaps.dev/sop/stream-output`                                   |
| Auth Session Artifact    | `crucible.3leaps.dev/standards/auth-session-artifact`                     |
| Data Sensitivity         | `crucible.3leaps.dev/standards/data-sensitivity-classification`           |
| Classifiers Framework    | `crucible.3leaps.dev/standards/classifiers-framework`                     |
| Volatility               | `crucible.3leaps.dev/standards/volatility-classification`                 |
| Access Tier              | `crucible.3leaps.dev/standards/access-tier-classification`                |
| Retention Lifecycle      | `crucible.3leaps.dev/standards/retention-lifecycle-classification`        |
| Schema Stability         | `crucible.3leaps.dev/standards/schema-stability-classification`           |
| Volume Tier              | `crucible.3leaps.dev/standards/volume-tier-classification`                |
| Velocity Mode            | `crucible.3leaps.dev/standards/velocity-mode-classification`              |
| Data Pipeline Principles | `crucible.3leaps.dev/standards/data-engineering/data-pipeline-principles` |
| Role Catalog             | `crucible.3leaps.dev/catalog/roles`                                       |
| Classifiers Catalog      | `crucible.3leaps.dev/catalog/classifiers`                                 |
