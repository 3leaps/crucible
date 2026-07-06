# AI Agent Collaboration

**Canonical URL** (hosted site planned — v0.1.x): `https://crucible.3leaps.dev/repository/agents`

Pattern for AI agent collaboration in 3leaps repositories.

## Related Standards

| Standard                               | Purpose                     |
| -------------------------------------- | --------------------------- |
| [agent-identity.md](agent-identity.md) | AI contribution attribution |
| [commit-style.md](commit-style.md)     | Commit attribution patterns |

## Required Files

| File              | Purpose                                |
| ----------------- | -------------------------------------- |
| `AGENTS.md`       | Startup guide for AI assistants        |
| `MAINTAINERS.md`  | Human and AI maintainer registry       |
| `AGENTS.local.md` | Tactical session guidance (gitignored) |

## AGENTS.md Structure

```markdown
# Project Name - AI Agent Guide

## Read First

1. Check `AGENTS.local.md` if it exists (gitignored)
2. Read `MAINTAINERS.md` for contacts and governance
3. Understand project scope before making changes

## Operating Model

| Aspect   | Setting                                  |
| -------- | ---------------------------------------- |
| Mode     | Supervised (human reviews before commit) |
| Role     | Development assistant                    |
| Identity | Per session (no persistent memory)       |

See [AI attribution guidance](https://crucible.3leaps.dev/repository/agent-identity) for public attribution.

## Quick Reference

| Task           | Command          |
| -------------- | ---------------- |
| Quality checks | `make check-all` |
| Tests          | `make test`      |
| Build          | `make build`     |

## Session Protocol

### Before Changes

- Read relevant code first
- Understand the scope
- Keep changes minimal and focused

### Before Committing

- Run `make check-all`
- Verify tests pass
- Use proper attribution (see [commit-style](commit-style.md))
- Include Committer-of-Record trailer for AI-assisted commits

## DO / DO NOT

### DO

- Run quality gates before commits
- Read files before editing
- Keep changes focused
- Document decisions

### DO NOT

- Push without maintainer approval
- Skip quality gates
- Commit secrets
- Touch code outside task scope
```

## AGENTS.local.md Pattern

Gitignored file for tactical session guidance:

```markdown
# AGENTS.local.md

## Current Focus

Implementing feature X for v0.2.0

## Active Streams

| Stream | Focus         |
| ------ | ------------- |
| A      | API endpoints |
| B      | Tests         |

## Avoid

- internal/legacy/\* - do not modify
- Refactoring outside current scope
```

## MAINTAINERS.md Structure

```markdown
# Maintainers

## Human Maintainers

| Name          | GitHub      | Email                    | Role            |
| ------------- | ----------- | ------------------------ | --------------- |
| Dave Thompson | @3leapsdave | dave.thompson@3leaps.net | Lead maintainer |

## Automation Accounts

_None configured._

## AI-Assisted Development

This repository may use AI assistants under human review. See [AGENTS.md](AGENTS.md) for configuration.

## Governance

See [3leaps/oss-policies](https://github.com/3leaps/oss-policies) for governance.
```

When a repository uses dedicated automation accounts, the automation section can describe public accountability:

```markdown
## Automation Accounts

| Account      | Purpose     | Maintainer  |
| ------------ | ----------- | ----------- |
| @example-bot | CI workflow | @maintainer |
```

## Fallback Convention

When spec-host is unavailable:

1. Check for sibling `../crucible/` directory
2. Reference local copy of standards
3. Document in AGENTS.md:

```markdown
## Standards Reference

- Canonical: https://github.com/3leaps/crucible
- Fallback: Clone https://github.com/3leaps/crucible as sibling
```

## References

For comprehensive AI collaboration standards:

- [FulmenHQ Crucible - AI Agent Collaboration Standard](https://github.com/fulmenhq/crucible/blob/main/docs/standards/ai-agents.md)
- [FulmenHQ Crucible - Agentic Attribution Standard](https://github.com/fulmenhq/crucible/blob/main/docs/standards/agentic-attribution.md)
