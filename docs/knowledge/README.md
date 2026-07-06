---
title: "Knowledge Base"
description: "Informative knowledge, workarounds, and lessons learned across 3leaps projects"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["knowledge", "operations", "troubleshooting"]
---

# Knowledge Base

This directory contains **informative knowledge** - lessons learned, workarounds, troubleshooting guides, and platform-specific know-how that supports operational processes across 3leaps projects.

## Distinction from Standards

| Aspect        | Standards (normative docs under `docs/`) | Knowledge (`docs/knowledge/`)          |
| ------------- | ---------------------------------------- | -------------------------------------- |
| **Nature**    | Normative ("you SHOULD")                 | Informative ("here's what we learned") |
| **Content**   | Rules, conventions, requirements         | Workarounds, gotchas, tribal knowledge |
| **Stability** | Stable, versioned                        | Evolves with tooling and platforms     |
| **Example**   | "Use semantic versioning"                | "cargo-deny fails on CVSS 4.0 scores"  |

## Structure

```
knowledge/
├── testing/                 # Testing patterns and strategies
│   ├── http-server-patterns.md
│   └── http-client-patterns.md
├── cicd/                    # CI/CD platform knowledge
│   ├── github-actions/      # GitHub Actions specifics
│   └── registry/            # Package registry publishing
└── toolchains/              # Language toolchain knowledge
    ├── rust/                # Rust ecosystem (cargo-deny, MSRV)
    ├── typescript/          # TypeScript/Node (bun, biome)
    ├── python/              # Python (uv, ruff, pytest)
    └── go/                  # Go ecosystem (Cobra, slog)
```

## Usage

Knowledge documents should:

1. **State the problem clearly** - What symptom or error did you encounter?
2. **Explain root cause** - Why does this happen?
3. **Document the workaround** - What's the fix or mitigation?
4. **Track upstream status** - Is there a fix coming? Link to issues.
5. **Include tags** - Enable discovery via frontmatter tags

## Contributing

When adding knowledge:

- Use frontmatter per `docs/repository/frontmatter.md`
- Include `tags` for discoverability
- Date the document - knowledge can become stale
- Link to upstream issues when applicable
- Update when the situation changes (e.g., upstream fix released)

## Related

- [Frontmatter Standard](../repository/frontmatter.md) - Required document metadata
- [Operations](../operations/) - Operational guides and processes
- [SOP](../sop/) - Standard Operating Procedures
