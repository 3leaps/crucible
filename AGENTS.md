# 3leaps Crucible - Contributor Agent Guide

This repository is a public standards repository. Documentation and schemas are
the product, so changes should be small, reviewable, and easy for downstream
readers to understand.

## Start Here

1. Read `README.md` for repository scope.
2. Read `CONTRIBUTING.md` for contribution flow.
3. Read `MAINTAINERS.md` for accountability and review expectations.
4. Use the standards under `docs/` as the source of truth for style and
   structure.

## Working Rules

- Keep private planning, credentials, customer details, and local-only operating
  notes out of the repository.
- Do not name private repositories, private services, internal channels, local
  filesystem paths, or private task identifiers in committed content.
- Treat commit messages, PR text, issues, and review comments as public and
  durable.
- Prefer generic descriptions over proper names unless the named project or
  service is intentionally public and relevant to the standard.
- Keep examples realistic but non-sensitive.

## Quality Gates

Run the repository checks before proposing changes:

```bash
make check
```

Useful targets:

| Task           | Command          |
| -------------- | ---------------- |
| Install tools  | `make bootstrap` |
| Quality checks | `make check`     |
| Format all     | `make fmt`       |
| Lint all       | `make lint`      |
| Pre-commit     | `make precommit` |
| Show version   | `make version`   |

## Attribution

AI-assisted contributions are welcome under human supervision. Use the public
attribution format documented in
[`docs/repository/commit-style.md`](docs/repository/commit-style.md), and keep
role labels generic, such as `devlead`, `devrev`, `secrev`, or `docs`.

## Roles

Role prompt templates live in [`config/agentic/roles/`](config/agentic/roles/)
and are summarized in [`docs/catalog/roles/`](docs/catalog/roles/). They are
reusable public templates, not private operating instructions.

Roles carry a **tier** as default guidance:

| Tier           | Meaning                              |
| -------------- | ------------------------------------ |
| `core`         | Baseline role for most repositories  |
| `supplemental` | Adopt when the repository needs it   |
| `deprecated`   | Retired; use the documented fallback |

See [PDR-0003](docs/decisions/PDR-0003-role-portfolio-tiering.md) for the tiering
decision.

## Public References

- [README.md](README.md) - Repository overview
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution flow
- [MAINTAINERS.md](MAINTAINERS.md) - Maintainer accountability
- [docs/repository/commit-style.md](docs/repository/commit-style.md) - Commit
  conventions and attribution
- [docs/repository/agents.md](docs/repository/agents.md) - Agent collaboration
  file pattern
- [config/agentic/roles/README.md](config/agentic/roles/README.md) - Role prompt
  catalog
