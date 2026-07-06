---
title: "Agentic Interface Adoption Guide"
description: "How to adopt 3leaps Crucible's role catalog and attribution baseline in your repository"
author: "Claude Opus 4.5"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-01"
last_updated: "2026-01-01"
status: "approved"
category: "guide"
tags: ["agentic", "adoption", "roles", "attribution", "migration"]
---

# Agentic Interface Adoption Guide

This guide helps maintainers adopt 3leaps Crucible's agentic interface: schema-validated role prompts and standardized commit attribution.

## Overview

### What's Available

Crucible v0.1.2 provides a formal agentic interface:

| Component               | Location                                 | Purpose                       |
| ----------------------- | ---------------------------------------- | ----------------------------- |
| **Role Catalog**        | `config/agentic/roles/*.yaml`            | Schema-validated role prompts |
| **Role Schema**         | `schemas/agentic/v0/`                    | JSON Schema for validation    |
| **Standards**           | `docs/repository/agent-identity.md`      | AI contribution attribution   |
| **Upstream Sync Guide** | `docs/operations/upstream-sync-guide.md` | Vendoring patterns            |

### Who This Is For

Repositories that:

- Use AI agents for development (Claude Code, Cursor, Copilot, etc.)
- Want consistent role definitions across teams
- Need schema-validated agent prompts
- Want standardized commit attribution

## Adoption Paths

### Path 1: Reference Only (Simplest)

Reference Crucible documentation without copying files:

```markdown
<!-- In your AGENTS.md -->

## Roles

See [3leaps Crucible Role Catalog](https://crucible.3leaps.dev/catalog/roles) for role definitions.

This repository uses:

- `devlead` for implementation work
- `devrev` for code review
```

**Pros**: No files to maintain, always up-to-date
**Cons**: Requires network access, no local validation

### Path 2: Vendor Schema + Config (Recommended)

Copy schema and role definitions into your repository for offline use and validation.

See [Upstream Sync Guide](../operations/upstream-sync-guide.md) for detailed instructions.

**Directory structure:**

```
your-repo/
├── schemas/
│   └── upstream/
│       └── 3leaps/
│           ├── PROVENANCE.md
│           └── agentic/v0/
│               └── role-prompt.schema.json
├── config/
│   └── agentic/
│       └── roles/
│           ├── devlead.yaml
│           ├── devrev.yaml
│           └── ...
└── AGENTS.md
```

**Pros**: Offline access, local validation, version control
**Cons**: Must update manually when upstream changes

### Path 3: Selective Role Adoption

Copy only the roles you need:

```bash
# Create directories
mkdir -p config/agentic/roles schemas/upstream/3leaps/agentic/v0

# Copy schema
cp ~/dev/crucible/schemas/agentic/v0/role-prompt.schema.json \
   schemas/upstream/3leaps/agentic/v0/

# Copy selected roles
cp ~/dev/crucible/config/agentic/roles/devlead.yaml \
   config/agentic/roles/
cp ~/dev/crucible/config/agentic/roles/devrev.yaml \
   config/agentic/roles/
```

## Role Selection

### Available Roles

| Role       | Slug       | Use When                                      |
| ---------- | ---------- | --------------------------------------------- |
| Dev Lead   | `devlead`  | Writing features, fixing bugs, implementation |
| Dev Review | `devrev`   | Code review, four-eyes audit                  |
| Info Arch  | `infoarch` | Documentation, schemas, standards             |
| Sec Review | `secrev`   | Security analysis, vulnerability review       |
| QA         | `qa`       | Testing, validation                           |
| CI/CD      | `cicd`     | Pipelines, GitHub Actions, automation         |
| Rel Eng    | `releng`   | Versioning, releases, changelogs              |
| Dispatch   | `dispatch` | Session coordination, role assignment         |

### Recommended by Repository Type

| Repository Type | Recommended Roles                   |
| --------------- | ----------------------------------- |
| Library/Package | `devlead`, `devrev`, `infoarch`     |
| CLI Tool        | `devlead`, `devrev`, `secrev`       |
| Web Application | `devlead`, `devrev`, `secrev`, `qa` |
| Standards/Docs  | `infoarch`, `devlead`               |
| Infrastructure  | `cicd`, `secrev`, `devlead`         |

## AGENTS.md Integration

### Update Your AGENTS.md

Reference the role catalog:

```markdown
## Roles

| Role      | Prompt                                            | Notes          |
| --------- | ------------------------------------------------- | -------------- |
| `devlead` | [devlead.yaml](config/agentic/roles/devlead.yaml) | Implementation |
| `devrev`  | [devrev.yaml](config/agentic/roles/devrev.yaml)   | Code review    |

See [config/agentic/roles/README.md](config/agentic/roles/README.md) for full catalog.
```

### Document Operating Mode

```markdown
## Operating Model

| Aspect         | Setting                                  |
| -------------- | ---------------------------------------- |
| Mode           | Supervised (human reviews before commit) |
| Default Role   | devlead                                  |
| Classification | Standard                                 |
```

## Commit Attribution

### Format

Adopt standardized attribution for AI-assisted commits:

```
<type>(<scope>): <subject>

<body>

Generated by <Model> via <Interface> under supervision of @<maintainer>

Co-Authored-By: <Model> <noreply@3leaps.net>
Role: <role>
Committer-of-Record: @<maintainer>
```

### Example

```
feat(api): add rate limiting middleware

Implements token bucket algorithm with configurable limits.

Changes:
- Add ratelimit package
- Wire middleware in server initialization
- Add integration tests

Generated by Claude Opus 4.5 via Claude Code under supervision of @yourusername

Co-Authored-By: Claude Opus 4.5 <noreply@3leaps.net>
Role: devlead
Committer-of-Record: @yourusername
```

### Key Requirements

- Use `noreply@3leaps.net` for Co-Authored-By email
- Include `Role:` trailer matching your operating role
- Include `Committer-of-Record:` for accountability

## Schema Validation

### Using goneat

```bash
# Validate all role files
for f in config/agentic/roles/*.yaml; do
  goneat validate data \
    --schema-file schemas/upstream/3leaps/agentic/v0/role-prompt.schema.json \
    --data "$f" || exit 1
done
```

### Using ajv-cli

```bash
npx ajv validate \
  -s schemas/upstream/3leaps/agentic/v0/role-prompt.schema.json \
  -d config/agentic/roles/devlead.yaml
```

### Makefile Target

```makefile
.PHONY: lint-roles
lint-roles: ## Validate role YAML files
	@echo "Validating role files..."
	@for f in config/agentic/roles/*.yaml; do \
		goneat validate data \
			--schema-file schemas/upstream/3leaps/agentic/v0/role-prompt.schema.json \
			--data "$$f" || exit 1; \
	done
```

## Customization

### Repository-Specific Extensions

If you need custom roles:

1. **DO NOT** edit vendored baseline roles
2. **DO** create custom roles in `config/agentic/roles.local/` (gitignored)
3. **DO** follow the schema for custom roles
4. **DO** document custom roles in your AGENTS.md

### Overriding Baseline Roles

Create a local override that extends the baseline:

```yaml
# config/agentic/roles.local/devlead-custom.yaml
slug: devlead-custom
extends: devlead
scope:
  - ...additional scope items specific to your repo...
```

## Adoption Checklist

- [ ] Chose adoption path (reference, vendor, or selective)
- [ ] Created directory structure (if vendoring)
- [ ] Copied schema file (if vendoring)
- [ ] Copied or referenced role definitions
- [ ] Updated AGENTS.md with role table
- [ ] Documented operating mode in AGENTS.md
- [ ] Updated commit message templates
- [ ] Added Makefile validation target (optional)
- [ ] Notified team of new attribution format

## Troubleshooting

### Role YAML Not Found

**Problem**: Agent can't find role definition file

**Solution**: Verify path in AGENTS.md matches actual file location

### Schema Validation Fails

**Problem**: `role_id must match pattern`

**Solution**: Ensure slug uses lowercase alphanumeric with hyphens only

### Attribution Format Rejected

**Problem**: CI rejects commit message format

**Solution**: Ensure all required trailers are present:

- `Co-Authored-By:`
- `Role:`
- `Committer-of-Record:`

## References

- [Role Catalog](../../config/agentic/roles/README.md)
- [Role Schema](../../schemas/agentic/v0/role-prompt.schema.json)
- [AI Attribution](../repository/agent-identity.md)
- [Commit Style Guide](../repository/commit-style.md)
- [Upstream Sync Guide](../operations/upstream-sync-guide.md)
- [3leaps Crucible README](../../README.md)
