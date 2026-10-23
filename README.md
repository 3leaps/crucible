# 3leaps Crucible

![Version: 0.2.1](https://img.shields.io/badge/version-0.2.1-blue)
![Lifecycle: Beta](https://img.shields.io/badge/lifecycle-beta-blue)
![License: MIT + CC0](https://img.shields.io/badge/license-MIT%20%2B%20CC0-blue)
![Check](https://github.com/3leaps/crucible/actions/workflows/check.yml/badge.svg)

**The common ground for uncommon tools.**

> **Beta**: Crucible's standards are stable enough to reference and adopt. Individual schemas are versioned independently and may still sit at `v0/` (see [Schemas](#schemas)) — those can change; pin to a commit if you need stability. Feedback and issues welcome.

Standards that scale down as gracefully as they scale up. Crucible is the lightweight baseline for 3leaps open source—practical conventions for coding, commits, observability, and AI-assisted development that work for solo projects and multi-repo ecosystems alike.

---

## What is Crucible?

A crucible is a vessel for transformation—where raw materials become refined output. In the 3leaps ecosystem, Crucible holds the foundational standards that shape consistent, high-quality tooling across all projects.

This repository is the **Single Source of Truth (SSOT)** for technical standards shared across:

- **3leaps tools** - CLI utilities, libraries, and applications
- **Adopting repositories** - Projects that extend or adopt 3leaps standards

Intentionally lightweight—no sync machinery, no runtime code. Just clear standards you can reference or clone.

## Quick Start

### Canonical source (GitHub)

The canonical home for all standards is this repository:

```
https://github.com/3leaps/crucible/  (browse or raw files)
```

> A hosted docs site at `crucible.3leaps.dev` is **planned**.
> Until it's live, use GitHub as the canonical source.

### Local Fallback

When network access is unavailable, clone
[`3leaps/crucible`](https://github.com/3leaps/crucible) as a sibling of the
consuming repository:

```bash
# From the consuming repository
git clone https://github.com/3leaps/crucible.git ../crucible

# Reference via relative path
../crucible/docs/coding/baseline.md
```

This catalog is `3leaps/crucible`. Other GitHub organizations also publish a
repository named `crucible` (for example
[`fulmenhq/crucible`](https://github.com/fulmenhq/crucible)). Use the
org-qualified URL above so the sibling named `crucible` is this catalog.

**Convention**: 3leaps tools check for `../crucible/` as a fallback when GitHub is unreachable.

### Access Priority

| Priority  | Source                       | Use Case                           |
| --------- | ---------------------------- | ---------------------------------- |
| 1         | `github.com/3leaps/crucible` | Canonical source (web + raw files) |
| 2         | `../crucible/`               | Local sibling (offline)            |
| (planned) | `crucible.3leaps.dev`        | Hosted docs site                   |

This is a **reference-based model**—we don't sync standards into repositories. For artifacts your code or CI depends on at runtime (schemas, config templates), create local copies with documented provenance. See [Getting Started](docs/getting-started.md) for details.

## Repository Structure

```
3leaps/crucible/
├── config/                    # Configuration data (YAML/JSON, schema-validated)
│   ├── agentic/
│   │   └── roles/             # AI agent role prompts (20 definitions)
│   ├── classifiers/
│   │   └── dimensions/        # Classifier dimension definitions (11 dimensions)
│   └── release/               # Tagger identity and decernor archive digest
├── docs/                      # Standards documentation
│   ├── catalog/               # Reusable templates and indexes
│   │   ├── classifiers/       # Classifier dimension catalog
│   │   └── roles/             # Role prompt documentation
│   ├── coding/
│   │   ├── baseline.md        # Output hygiene, exit codes, timestamps, errors
│   │   ├── go.md              # Go coding standards
│   │   ├── python.md          # Python coding standards
│   │   ├── rust.md            # Rust coding standards
│   │   └── typescript.md      # TypeScript coding standards
│   ├── decisions/             # Decision & governance records (the *DR family)
│   ├── releases/              # Detailed release notes per version
│   ├── security/              # Public release keys and the verifier guide
│   ├── operations/
│   │   ├── ci-baseline.md     # CI/CD patterns and gotchas
│   │   └── upstream-sync-guide.md  # How to vendor crucible content
│   ├── repository/
│   │   ├── makefile-minimum.md  # Essential make targets
│   │   ├── commit-style.md      # Commit message conventions
│   │   ├── frontmatter.md       # Document metadata standards
│   │   ├── agents.md            # AI agent collaboration pattern
│   │   └── agent-identity.md    # AI contribution attribution
│   ├── observability/
│   │   └── logging-baseline.md  # Logging levels, streams, format
│   ├── sop/                   # Standard operating procedures (mandatory)
│   │   └── stream-output.md   # stdout/stderr discipline for CLI tools
│   └── standards/             # Classification + portable contracts
├── schemas/                   # JSON schemas for validation
│   ├── application-control/v0/  # Portable application control and observation (proposed)
│   ├── agentic/v0/            # Role prompt schema
│   ├── ailink/v0/             # AILink prompt/response schemas
│   ├── auth/v0/               # Session artifact schema
│   ├── classifiers/v0/        # Classifier meta-schemas, agent interface schemas
│   ├── coverage-attestation/v0/  # Coverage attestation (proposed)
│   ├── agent-wait/v0/         # Portable agent wait/poll contract
│   ├── data-artifact/v0/      # Portable data artifact contract
│   ├── data-acquisition/v0/   # Source policy, acquisition scope and registration (proposed)
│   ├── durable-index/v0/      # Object-inventory snapshots, observation plans (proposed)
│   ├── durable-queue/v0/      # At-least-once queue envelope, ledger, profile (proposed)
│   ├── durable-record/v0/     # Revisioned record, journal, receipt, stratum profile (proposed)
│   ├── durable-record/v1/     # Retained records with use restrictions (proposed)
│   ├── forge-infra/v0/        # Forge capabilities, provider profiles, authority bindings
│   ├── foundation/v0/         # Lifecycle phases, release phases, types
│   ├── inference-path-taxonomy/v0/ # Parties, model pins, and declared paths (proposed)
│   ├── process-run/v0/        # Local process telemetry/control (proposed)
│   ├── recurrence/v0/         # RFC 5545 recurrence rule subset and corpus (proposed)
│   ├── project-work/v0/       # Ready packets, project state, work ledger (draft)
│   ├── segmented-snapshot/v0/ # Immutable snapshot publication and verification (proposed)
│   └── service-job/v0/        # Portable service job contract
├── keys/                      # Fingerprints of the release public keys
└── scripts/                   # Release and automation scripts
```

## For Developers

### Prerequisites

**bun is required** for 3leaps development:

```bash
# Install bun
curl -fsSL https://bun.sh/install | bash

# Or via Homebrew
brew install oven-sh/bun/bun
```

### Bootstrap

```bash
make bootstrap   # Install sfetch, goneat, bun deps, and foundation tools
make check       # Run all quality checks
make fmt         # Format all files
```

### Quality Gates

| Tool     | Purpose           | Files                      |
| -------- | ----------------- | -------------------------- |
| prettier | Formatting        | `*.md`, `*.json`           |
| yamlfmt  | Formatting        | `*.yaml`, `*.yml`          |
| yamllint | Linting           | `*.yaml`, `*.yml`          |
| goneat   | Schema validation | `schemas/**/*.json`        |
| goneat   | Config validation | `config/agentic/**/*.yaml` |

All checks run via `make check` and in GitHub Actions on PR/push.

Key targets:

- `make lint-schemas` — Validate JSON schemas against meta-schemas
- `make lint-config` — Validate role YAML files against role-prompt schema

## AI Agent Roles

Baseline role prompts for AI-assisted development sessions. Each role shapes how an agent approaches work through context engineering. Roles carry a **tier** — default guidance that adopting repos may re-tier: **core** (always-on spine), **supplemental** (adopt by need), **deprecated** (retired). See [PDR-0003](docs/decisions/PDR-0003-role-portfolio-tiering.md).

| Role           | Tier         | Category   | Purpose                                            |
| -------------- | ------------ | ---------- | -------------------------------------------------- |
| `devlead`      | core         | agentic    | Implementation, architecture                       |
| `devrev`       | core         | review     | Code review, four-eyes audit                       |
| `secrev`       | core         | review     | Security analysis                                  |
| `cxotech`      | core         | governance | Strategic fulcrum, brief/ADR approval              |
| `entarch`      | supplemental | governance | Technology-side architecture coherence             |
| `uxdev`        | supplemental | agentic    | Interactive experience implementation              |
| `analyst`      | supplemental | analytics  | Evidence and decision-ready findings               |
| `strategist`   | supplemental | consulting | Strategic choices and advice                       |
| `watcher`      | supplemental | automation | Bounded monitoring and escalation                  |
| `delegate`     | supplemental | governance | Privileged, compartmented assistance               |
| `secops`       | supplemental | automation | Privileged infrastructure operations               |
| `projectmgr`   | supplemental | governance | Land a stated unit of work with exact state and GO |
| `infoarch`     | supplemental | agentic    | Documentation, schemas                             |
| `dataeng`      | supplemental | analytics  | Data architecture, pipelines, lineage              |
| `prodmktg`     | supplemental | marketing  | Product positioning and messaging                  |
| `releng`       | supplemental | automation | Complex release systems                            |
| `dispatch`     | supplemental | governance | Estate routing and coordination                    |
| `qa`           | deprecated   | review     | Retired — use `devrev` + task acceptance           |
| `deliverylead` | deprecated   | governance | Retired — use `projectmgr`                         |
| `cicd`         | deprecated   | automation | Retired — use `releng` + `devlead`                 |

See [config/agentic/roles/README.md](config/agentic/roles/README.md) for full catalog and usage.

**Schema**: Roles validate against [`role-prompt.schema.json`](schemas/agentic/v0/role-prompt.schema.json)

## The 3 Leaps Repository Ecosystem

[3 Leaps](https://3leaps.net) maintains `3leaps/crucible` as a lightweight standards baseline for 3leaps projects and adopting repositories.

```
                    ┌─────────────────────────────────────────┐
                    │            3leaps/crucible              │
                    │      (lightweight baseline standards)   │
                    └─────────────────────────────────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           │                            │                            │
           ▼                            ▼                            ▼
   ┌───────────────┐           ┌───────────────┐            ┌───────────────┐
   │    3leaps     │           │   adopting    │            │  downstream   │
   │    tools      │           │ repositories  │            │implementations│
   │               │           │               │            │               │
   │  CLI tools    │           │  linked docs  │            │  local rules  │
   │  libraries    │           │  vendored     │            │  adapters     │
   │  policies     │           │  schemas      │            │  extensions   │
   └───────────────┘           └───────────────┘            └───────────────┘
```

### Relationship to Other Repositories

This repository **directly informs** 3leaps projects and can be **referenced by** adopting repositories.

#### 3leaps Org Foundation Layer

| Repository             | Purpose                      | Scope                                      |
| ---------------------- | ---------------------------- | ------------------------------------------ |
| `3leaps/crucible`      | Technical standards baseline | Coding, tooling, observability, AI roles   |
| `3leaps/oss-policies`  | Governance & legal           | Licenses, contributor agreements, security |
| `3leaps/sfetch`        | Secure downloader            | Zero-trust binary fetcher with signatures  |
| `3leaps/seekable-zstd` | Compression library          | Random access + parallel decompression     |

#### Adopting Repositories

| Relationship       | Purpose                                  | Typical Use                           |
| ------------------ | ---------------------------------------- | ------------------------------------- |
| Direct reference   | Link to the public standard              | Standards apply as written            |
| Vendored artifacts | Copy schemas or docs with provenance     | CI reliability or offline use         |
| Local extension    | Add stricter rules for a specific domain | Repo-specific requirements stay local |

## Design Principles

1. **Minimal** - Only what's needed, nothing more
2. **Practical** - Real patterns from real projects
3. **Reference-friendly** - Easy to link, easy to clone
4. **Extensible** - Baseline patterns can be adopted or extended locally

## Schemas

### Experimental snapshot contract

The [segmented-snapshot contract](docs/standards/segmented-snapshot-contract.md)
and [conformance cases](docs/standards/segmented-snapshot-conformance.md) define
a proposed immutable-snapshot companion to data-artifact, with an experimental
[schema bundle and semantic controls](schemas/segmented-snapshot/v0/README.md). See
[ADR-0011](docs/decisions/ADR-0011-segmented-snapshot-contract.md).

### Experimental durable queue contract

The [durable-queue contract](docs/standards/durable-queue-contract.md) defines
a proposed at-least-once queue: envelope, fenced leases, an append-only ledger
with fold rules, capability profiles and a wire binding, independent of
storage engine, with an experimental
[schema bundle, reject pairs and vectors](schemas/durable-queue/v0/README.md).
See [ADR-0012](docs/decisions/ADR-0012-durable-queue-contract.md).

### Experimental durable record contract

The [durable-record contract](docs/standards/durable-record-contract.md) defines
proposed engine-neutral record storage: stable record identity, exact
digest-pinned revisions, digest-bound bodies, provenance and retention intent,
keyed idempotent writes with typed receipts and reconciliation, an append-only
journal, and a stratum profile that declares durability and supported deletion
scope. An experimental
[schema bundle and reject fixtures](schemas/durable-record/v0/README.md) accompany it.
See [ADR-0013](docs/decisions/ADR-0013-durable-record-contract.md).

The [durable-record v1 contract](docs/standards/durable-record-v1-contract.md)
adds holds that block serving, export and reuse of a record while keeping it
readable for authorized audit. It is a new major contract version; v0 is
unchanged and there is no automatic migration. Its
[schemas and logical vectors](schemas/durable-record/v1/README.md) qualify no
store. See [ADR-0019](docs/decisions/ADR-0019-durable-record-tombstoning.md).

### Experimental data acquisition contract

The [Data Acquisition Contract](docs/standards/data-acquisition-contract.md)
defines proposed source-policy, selected-scope and shared-capacity registration
boundaries. The [schema family and synthetic controls](schemas/data-acquisition/v0/README.md)
separate shape and semantic acceptance from runtime authority qualification.
See [ADR-0014](docs/decisions/ADR-0014-data-acquisition-contract.md).

### Proposed recurrence rule contract

The [Recurrence Rule Contract](docs/standards/recurrence-rule-contract.md)
defines a canonical JSON form for a frozen RFC 5545 RRULE subset, normative
expansion semantics including DST gaps and overlaps, and a
[conformance corpus](schemas/recurrence/v0/README.md) pinned by digest to
IANA tzdb 2026e.

### Draft durable index contract

The [durable-index design](docs/standards/durable-index-contract.md) specializes
segmented snapshots with object inventory rows, observation plans, scoped coverage
and successor rules. The [initial schemas and logical vectors](schemas/durable-index/v0/README.md)
are design controls; the [conformance requirements](docs/standards/durable-index-conformance.md)
identifies the remaining physical corpus and adoption gates. See
[ADR-0017](docs/decisions/ADR-0017-durable-index-contract.md).

### Draft agent interface classifiers and profiles

Draft [agent interface classifiers](docs/standards/agent-interface-classification.md)
describe one agent interaction along separate dimensions: session lifecycle
relationship, selected entrypoint, carrier per connection hop, and
evidence-derived adapter confidence. A companion
[profile standard](docs/standards/agent-interface-profiles.md) declares per-hop
protocol stacks, execution and context continuity, and distinct delivery,
execution and cursor-commit signals. Values and profiles describe interfaces;
they confer no authority.

### Published schema assets

JSON schemas normally carry a canonical `$id` under the
`schemas.3leaps.dev` namespace:

```
https://schemas.3leaps.dev/<topic>/v0/<schema>.schema.json
```

Portable companion contracts may instead use a hostless `contract:` logical
identifier. The schema registry remains the retrieval origin; retrieval address
does not replace logical identity. See
[ADR-0007](docs/decisions/ADR-0007-separate-documentation-and-schema-registry-origins.md).

> A hosted endpoint at that domain is **planned**. Until then,
> fetch schemas from GitHub (raw) and vendor a pinned copy with documented provenance —
> see the per-family schema READMEs.

**Version convention** (asset-level maturity, independent of the repository's lifecycle):

- `v0/` — Unstable. May change without notice.
- `v1.0.0/`, `v2.0.0/`, etc. — Stable. Follows semantic versioning with deprecation notices.

A `v0/` schema can change regardless of the repo's lifecycle phase. Pin to a specific git commit (and SHA256) if you need stability.

## Contributing

Standards evolve. To propose changes:

1. Open an issue describing the need
2. Reference existing Crucible patterns where applicable
3. Keep it simple - repo-specific complexity belongs in the adopting repository

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Policies

- Security policy and reporting: [SECURITY.md](SECURITY.md)
- Verifying a release (signed tag only; no checksum files): [docs/security/README.md](docs/security/README.md);
  maintainers release with [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)
- Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Governance policies: [3leaps/oss-policies](https://github.com/3leaps/oss-policies)

## License

Dual-licensed: CC0 for documentation, MIT for code. See [LICENSE](LICENSE).

---

**Version**: See [VERSION](VERSION) | **Status**: Building in public
