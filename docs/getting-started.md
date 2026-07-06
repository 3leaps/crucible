---
title: "Getting Started with Crucible"
description: "Practical guide to adopting 3leaps standards in your repository"
author: "Claude Opus 4.5"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2025-12-26"
status: "draft"
tags: ["getting-started", "onboarding", "adoption"]
---

# Getting Started with Crucible

**Canonical URL** (hosted site planned — v0.1.x): `https://crucible.3leaps.dev/getting-started`

This guide helps you adopt 3leaps Crucible standards in your repository—whether you're starting fresh, joining an existing project, or referencing standards from another ecosystem.

## What Crucible Provides

Crucible is a lightweight standards baseline covering:

| Category      | What You Get                                     |
| ------------- | ------------------------------------------------ |
| Coding        | Output hygiene, exit codes, timestamps, errors   |
| Repository    | Commit style, AGENTS.md, MAINTAINERS.md patterns |
| Observability | Structured logging baseline                      |
| AI Agents     | Attribution guidance and reusable role prompts   |
| Security      | Secure commit policy for sensitive repos         |
| Classifiers   | 7 orthogonal data classification dimensions      |
| Operations    | CI/CD patterns, stream output policy (SOP)       |
| Decisions     | ADR framework for architecture decision records  |

**Design philosophy**: Minimal, practical, reference-friendly. Only what's needed, nothing more.

## Accessing Standards (Lightweight SSOT Model)

3leaps Crucible uses a **reference-based model**—we don't sync or embed standards into your repository. You access them when needed.

### Access Priority

| Priority  | Source                               | When to Use                        |
| --------- | ------------------------------------ | ---------------------------------- |
| 1         | `https://github.com/3leaps/crucible` | Canonical source (web + raw files) |
| 2         | `../crucible/docs/`                  | Local sibling clone (offline)      |
| (planned) | `https://crucible.3leaps.dev/`       | Hosted docs site (targeted v0.1.x) |

**For development**, clone crucible as a sibling for fast offline access:

```bash
cd ~/dev  # or your org's dev folder
git clone https://github.com/3leaps/crucible.git
# Now accessible at ../crucible/ from any sibling repo
```

### When Local Copies Are Required

Most Crucible content is **guidance for humans and processes**—commit style, coding conventions, agent protocols. These are referenced, not embedded.

However, if your code or CI **depends on a Crucible artifact at runtime**, you must copy it locally:

| Artifact Type    | Example                      | Needs Local Copy? |
| ---------------- | ---------------------------- | ----------------- |
| Standards docs   | commit-style.md, baseline.md | No (reference)    |
| Role prompts     | catalog/roles/devlead.md     | No (reference)    |
| JSON schemas     | lifecycle-phase.schema.json  | **Yes** (CI/code) |
| Config templates | .yamllint, .prettierrc       | **Yes** (tooling) |
| Data files       | exit-codes.json              | **Yes** (runtime) |

### Creating Local Copies

When you need a local copy of a Crucible artifact:

1. **Create a designated folder** with clear provenance:

```
your-repo/
└── .3leaps-crucible/    # Use your source or org slug for provenance.
    ├── README.md        # Provenance documentation
    └── schemas/
        └── lifecycle-phase.schema.json
```

**Naming convention**: Use `.<org>-crucible/` to avoid collisions when multiple organizations' crucible artifacts coexist (for example, `.3leaps-crucible/`).

2. **Document provenance** in the README:

```markdown
# Crucible Artifacts

Local copies of 3leaps Crucible artifacts for offline/CI use.

## Source

- Repository: https://github.com/3leaps/crucible
- Version: v0.1.0
- Copied: 2024-12-25

## Contents

| File                         | Source Path                       |
| ---------------------------- | --------------------------------- |
| schemas/lifecycle-phase.json | docs/schemas/lifecycle-phase.json |

## Update Process

1. Check crucible releases for updates
2. Copy updated files
3. Update this README with new version/date
4. Test CI/code that depends on these files
```

3. **Reference in your docs** that these are copies:

```markdown
## Schemas

This repo uses [3leaps Crucible](https://crucible.3leaps.dev/) schemas.
Local copies in `.<org>-crucible/` for CI reliability.
```

### Contrast: Heavier Sync Models

Some repositories use a **heavier sync model** with actual embedding:

| Aspect       | 3leaps (Lightweight)    | Heavier local model         |
| ------------ | ----------------------- | --------------------------- |
| Standards    | Reference only          | Reference or sync           |
| Schemas      | Manual copy when needed | Auto-sync via local tooling |
| Go packages  | N/A                     | `go:embed` for schemas      |
| Other langs  | Manual copy             | Sync scripts copy to repos  |
| Update model | Manual pull             | Automated sync + PR         |

For 3leaps tools, the lightweight model is sufficient. Most standards are DX guidance, not runtime dependencies.

## Which Path Are You On?

### Path A: Joining a 3leaps Repository

Your repo already uses Crucible. Here's your checklist:

1. **Read AGENTS.md** - Understand your operating context
2. **Read MAINTAINERS.md** - Know who's accountable
3. **Run `make bootstrap`** - Install required tools
4. **Run `make check`** - Verify your setup works

Key standards to know:

- [commit-style.md](repository/commit-style.md) - How to write commits
- [baseline.md](coding/baseline.md) - Coding conventions
- [Role catalog](catalog/roles/) - If you're working with AI agents

### Path B: Setting Up a New 3leaps Repository

Minimum viable Crucible adoption:

#### Step 1: Create AGENTS.md

```markdown
# [Project Name] – AI Agent Guide

## Read First

1. Check `AGENTS.local.md` if it exists (gitignored)
2. Read `MAINTAINERS.md` for contacts and governance
3. Review this document for operational protocols

## Operating Model

| Aspect   | Setting                                  |
| -------- | ---------------------------------------- |
| Mode     | Supervised (human reviews before commit) |
| Role     | devlead                                  |
| Identity | Per session (no persistent memory)       |

See [AI attribution guidance](https://crucible.3leaps.dev/repository/agent-identity).

## Quick Reference

| Task           | Command      |
| -------------- | ------------ |
| Quality checks | `make check` |
| Format         | `make fmt`   |
| Build          | `make build` |
| Test           | `make test`  |

## Commit Attribution

Follow [commit-style](https://crucible.3leaps.dev/repository/commit-style):

\`\`\`
<type>(<scope>): <subject>

<body>

Generated by <Model> via <Interface> under supervision of @<maintainer>

Co-Authored-By: <Model> <noreply@3leaps.net>
Committer-of-Record: @<maintainer>
\`\`\`

## Standards Reference

- **Canonical**: [github.com/3leaps/crucible](https://github.com/3leaps/crucible)
- **Local fallback**: Clone `https://github.com/3leaps/crucible` as sibling
- **Hosted site**: planned (targeted v0.1.x) at `https://crucible.3leaps.dev/`
```

#### Step 2: Create MAINTAINERS.md

```markdown
# Maintainers

## Human Maintainers

| Name      | GitHub  | Email          | Role            |
| --------- | ------- | -------------- | --------------- |
| Your Name | @handle | you@domain.com | Lead maintainer |

## Autonomous Agents

_None configured. This repository uses supervised mode only._

## AI-Assisted Development

This repository uses AI assistants in **supervised mode**. See `AGENTS.md`.

## Governance

See [3leaps/oss-policies](https://github.com/3leaps/oss-policies).
```

#### Step 3: Add Makefile Targets

Per [makefile-minimum.md](repository/makefile-minimum.md):

```makefile
.PHONY: check fmt lint test build clean

check: fmt lint  ## Run all quality checks

fmt:             ## Format code
	# Your formatting commands

lint:            ## Lint code
	# Your linting commands

test:            ## Run tests
	go test ./... # or your test command

build:           ## Build project
	# Your build commands

clean:           ## Clean artifacts
	rm -rf dist/
```

#### Step 4: Reference Standards

In your README.md or docs:

```markdown
## Standards

This project follows [3leaps Crucible](https://crucible.3leaps.dev/) standards:

- [Coding Baseline](https://crucible.3leaps.dev/coding/baseline)
- [Commit Style](https://crucible.3leaps.dev/repository/commit-style)
- [Logging Baseline](https://crucible.3leaps.dev/observability/logging-baseline)
```

### Path C: Adopting in an Existing Repository

Incremental adoption works best. Priority order:

1. **AGENTS.md** - Enables AI-assisted development immediately
2. **Commit style** - Low friction, high value
3. **Makefile targets** - Standardizes developer workflow
4. **MAINTAINERS.md** - Clarifies accountability
5. **Coding baseline** - Apply to new code, retrofit gradually

Don't try to retrofit everything at once. Standards apply to new work; legacy code can be updated opportunistically.

### Path D: Adopting Organization

Your organization may have its own Crucible that extends 3leaps standards.

**Lookup order:**

1. **Your org's crucible first** - `github.com/<org>/crucible`
2. **3leaps crucible as fallback** - `github.com/3leaps/crucible`

**Relationship patterns:**

| Pattern              | When to Use                                   |
| -------------------- | --------------------------------------------- |
| **Direct reference** | Standard applies as-is                        |
| **Extend**           | Org adds requirements on top of baseline      |
| **Override**         | Org standard supersedes (document explicitly) |

Example in your org's docs:

```markdown
## Commit Style

Follows [3leaps commit-style](https://crucible.3leaps.dev/repository/commit-style) with these extensions:

- All commits require issue reference: `Refs: #123`
- Security fixes require `Security-Reviewed-By:` trailer
```

### Path E: General Reference

Outside the 3leaps ecosystem? You can still use these standards:

- **Fork and adapt** - Dual-licensed (CC0 for docs, MIT for code), modify as needed
- **Reference directly** - Link to standards you want to adopt
- **Cherry-pick** - Use specific patterns (exit codes, logging levels) without full adoption

No obligation to adopt everything. Take what's useful.

## Quick Reference Card

### Essential URLs (hosted site planned — v0.1.x)

| Resource        | URL                                             |
| --------------- | ----------------------------------------------- |
| Standards home  | `crucible.3leaps.dev`                           |
| Coding baseline | `crucible.3leaps.dev/coding/baseline`           |
| Commit style    | `crucible.3leaps.dev/repository/commit-style`   |
| AI attribution  | `crucible.3leaps.dev/repository/agent-identity` |
| Role catalog    | `crucible.3leaps.dev/catalog/roles`             |

### Essential Commands

```bash
# Clone for local reference
git clone https://github.com/3leaps/crucible.git ../crucible

# In your repo
make bootstrap  # First-time setup (if using 3leaps tooling)
make check      # Before committing
make fmt        # Format code
```

### Essential Files

| File             | Purpose                        |
| ---------------- | ------------------------------ |
| `AGENTS.md`      | AI agent operating guide       |
| `MAINTAINERS.md` | Human accountability           |
| `Makefile`       | Standard development targets   |
| `VERSION`        | Single source of truth version |

## What's NOT in 3leaps Crucible

Intentionally excluded from this lightweight baseline:

- Progressive logging profiles (beyond baseline)
- Sync infrastructure between repositories
- Language-specific implementation libraries

**Note**: 3leaps Crucible now includes JSON schemas, ADRs, SOPs, and classifiers as lightweight baselines. Adopting repositories can extend these with domain-specific depth and automation.

## Next Steps

After initial setup:

1. **Add frontmatter** to documentation files ([frontmatter.md](repository/frontmatter.md))
2. **Configure roles** if using AI agents ([role catalog](catalog/roles/))
3. **Enable secure commits** for security-sensitive repos ([secure-commits.md](repository/secure-commits.md))
4. **Set up CI** to run `make check` on PRs

## Getting Help

- **Issues**: [github.com/3leaps/crucible/issues](https://github.com/3leaps/crucible/issues)
- **Standards questions**: Reference the specific standard document
- **Extension patterns**: Start from the closest 3leaps Crucible standard and document local differences

## References

- [README.md](../README.md) - Repository overview
- [docs/README.md](README.md) - Standards index
- [CONTRIBUTING.md](../CONTRIBUTING.md) - How to contribute
