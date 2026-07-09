# 3leaps Crucible

![Version: 0.1.19](https://img.shields.io/badge/version-0.1.19-blue)
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

> A hosted docs site at `crucible.3leaps.dev` is **planned** (targeted for v0.1.x).
> Until it's live, use GitHub as the canonical source.

### Local Fallback

When network access is unavailable:

```bash
# Clone as sibling to your project
cd ~/dev
git clone https://github.com/3leaps/crucible.git

# Reference via relative path
../crucible/docs/coding/baseline.md
```

**Convention**: 3leaps tools check for `../crucible/` as a fallback when GitHub is unreachable.

### Access Priority

| Priority  | Source                       | Use Case                           |
| --------- | ---------------------------- | ---------------------------------- |
| 1         | `github.com/3leaps/crucible` | Canonical source (web + raw files) |
| 2         | `../crucible/`               | Local sibling (offline)            |
| (planned) | `crucible.3leaps.dev`        | Hosted docs site (targeted v0.1.x) |

This is a **reference-based model**—we don't sync standards into repositories. For artifacts your code or CI depends on at runtime (schemas, config templates), create local copies with documented provenance. See [Getting Started](docs/getting-started.md) for details.

## Repository Structure

```
3leaps/crucible/
├── config/                    # Configuration data (YAML/JSON, schema-validated)
│   ├── agentic/
│   │   └── roles/             # AI agent role prompts (13 baseline roles)
│   └── classifiers/
│       └── dimensions/        # Classifier dimension definitions (7 dimensions)
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
│   ├── decisions/             # ADR framework (architecture decision records)
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
│   ├── agentic/v0/            # Role prompt schema
│   ├── ailink/v0/             # AILink prompt/response schemas
│   ├── auth/v0/               # Session artifact schema
│   ├── classifiers/v0/        # Classifier dimension meta-schemas
│   ├── coverage-attestation/v0/  # Coverage attestation (proposed)
│   ├── data-artifact/v0/      # Portable data artifact contract
│   ├── foundation/v0/         # Lifecycle phases, release phases, types
│   └── process-run/v0/        # Local process telemetry/control (proposed)
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

| Role           | Tier         | Category   | Purpose                               |
| -------------- | ------------ | ---------- | ------------------------------------- |
| `devlead`      | core         | agentic    | Implementation, architecture          |
| `devrev`       | core         | review     | Code review, four-eyes audit          |
| `secrev`       | core         | review     | Security analysis                     |
| `cxotech`      | core         | governance | Strategic fulcrum, brief/ADR approval |
| `entarch`      | supplemental | governance | Cross-repo architecture coherence     |
| `infoarch`     | supplemental | agentic    | Documentation, schemas                |
| `dataeng`      | supplemental | agentic    | Data engineering, pipelines           |
| `prodmktg`     | supplemental | agentic    | Product messaging, personas           |
| `qa`           | supplemental | review     | Testing, validation                   |
| `releng`       | supplemental | automation | Versioning, releases                  |
| `dispatch`     | supplemental | governance | Session coordination                  |
| `deliverylead` | supplemental | governance | Delivery coordination (large efforts) |
| `cicd`         | deprecated   | automation | Retired — use `releng` + `devlead`    |

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

JSON schemas carry a canonical `$id` under the `schemas.3leaps.dev` namespace:

```
https://schemas.3leaps.dev/<topic>/v0/<schema>.schema.json
```

> A hosted endpoint at that domain is **planned** (targeted for v0.1.x). Until then,
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
- Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Governance policies: [3leaps/oss-policies](https://github.com/3leaps/oss-policies)

## License

Dual-licensed: CC0 for documentation, MIT for code. See [LICENSE](LICENSE).

---

**Version**: See [VERSION](VERSION) | **Status**: Building in public
