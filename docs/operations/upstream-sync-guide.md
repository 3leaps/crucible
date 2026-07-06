# Upstream Sync Guide

How to vendor content from 3leaps/crucible into your repository.

## Overview

When your repository needs to use schemas, configs, or other assets from 3leaps/crucible at runtime (for validation, code generation, etc.), you should **vendor** them rather than reference them dynamically. This ensures:

- Reproducible builds (no network dependency)
- Explicit version control (you choose when to update)
- Clear provenance (documented source and commit)

## Directory Structure

```
your-repo/
├── schemas/
│   └── upstream/
│       └── 3leaps/              # Vendored from 3leaps/crucible
│           ├── PROVENANCE.md    # Source tracking
│           └── agentic/v0/
│               └── role-prompt.schema.json
├── config/
│   └── upstream/                # (if vendoring config data)
│       └── 3leaps/
│           └── ...
└── .goneatignore                # Exclude upstream from lint/format
```

## Step-by-Step Setup

### 1. Create the upstream directory

```bash
mkdir -p schemas/upstream/3leaps
```

### 2. Create PROVENANCE.md

Track where vendored content comes from:

```markdown
# Upstream Provenance

Content vendored from external repositories.

## 3leaps/crucible

- **Repository**: https://github.com/3leaps/crucible
- **Commit**: abc123def456...
- **Date**: 2026-01-01
- **Vendored paths**:
  - `schemas/agentic/v0/role-prompt.schema.json`

## Update Instructions

To update vendored content:

1. Check latest commit: `cd ~/dev/crucible && git log -1`
2. Copy updated files to `schemas/upstream/3leaps/`
3. Update this PROVENANCE.md with new commit hash
4. Run `make upstream-validate` to verify
5. Commit with message referencing upstream commit
```

### 3. Copy the schema files

```bash
# From 3leaps/crucible, copy the schema
cp ~/dev/crucible/schemas/agentic/v0/role-prompt.schema.json \
   schemas/upstream/3leaps/agentic/v0/

# Verify it copied correctly
cat schemas/upstream/3leaps/agentic/v0/role-prompt.schema.json | head -5
```

### 4. Exclude from lint/format

Add to `.goneatignore`:

```gitignore
# Vendored upstream content - validated separately
schemas/upstream/
config/upstream/
```

This prevents your local formatters from modifying vendored files (which would create false diffs with upstream).

### 5. Add Makefile targets

Add validation targets to your Makefile:

```makefile
.PHONY: upstream-validate lint-config

# Validate vendored upstream schemas against meta-schemas
upstream-validate: ## Validate vendored upstream files
	@echo "Validating vendored upstream files..."
	@if command -v goneat >/dev/null 2>&1; then \
		goneat validate --no-ignore --include "schemas/upstream/**/*.schema.json"; \
	else \
		echo "goneat not found, skipping"; \
	fi

# Validate your config files against vendored schemas
lint-config: ## Validate config data against schemas
	@echo "Validating config files..."
	@for f in config/agentic/roles/*.yaml; do \
		goneat validate data \
			--schema-file schemas/upstream/3leaps/agentic/v0/role-prompt.schema.json \
			--data "$$f" || exit 1; \
	done
```

### 6. Reference in your configs

Point your local configs to the vendored schema:

```yaml
# config/agentic/roles/devlead.yaml
# yaml-language-server: $schema=../../../schemas/upstream/3leaps/agentic/v0/role-prompt.schema.json
slug: devlead
name: Development Lead
# ... rest of role definition
```

## Updating Vendored Content

When 3leaps/crucible updates and you want the new version:

```bash
# 1. Check what changed upstream
cd ~/dev/crucible
git pull
git log --oneline -5

# 2. Copy updated files
cp schemas/agentic/v0/role-prompt.schema.json \
   ~/dev/your-repo/schemas/upstream/3leaps/agentic/v0/

# 3. Update PROVENANCE.md with new commit hash
cd ~/dev/your-repo
# Edit schemas/upstream/3leaps/PROVENANCE.md

# 4. Validate
make upstream-validate
make lint-config

# 5. Commit
git add schemas/upstream/
git commit -m "chore(upstream): update 3leaps schemas to abc123

Upstream commit: abc123def456
Changes: Updated role-prompt.schema.json with new fields"
```

## What to Vendor

**Recommendation**: If you vendor schemas, also vendor the corresponding config data (and vice versa). This keeps validation and data in sync.

### Vendor (copy locally)

- **Schemas** used for validation at build/runtime
- **Config data** (role definitions, etc.) used at runtime
- **Fixtures** needed for testing

### Reference (don't vendor)

- **Documentation** - link to canonical URLs
- **Standards** - reference via URL in comments/docs
- **Guides** - link to upstream

## AGENTS.md Integration

Document the upstream relationship in your AGENTS.md:

```markdown
## Upstream Dependencies

This repository vendors content from:

| Source                                                | Path                       | Purpose            |
| ----------------------------------------------------- | -------------------------- | ------------------ |
| [3leaps/crucible](https://github.com/3leaps/crucible) | `schemas/upstream/3leaps/` | Role prompt schema |

**DO NOT** edit files in `schemas/upstream/` or `config/upstream/` directly.
These are vendored from external repositories. To update, see
[Upstream Sync Guide](docs/operations/upstream-sync-guide.md).
```

## Automation (Future)

For repositories with frequent upstream syncs, consider:

1. **Dependabot-style PR automation** - Check upstream for changes, open PR
2. **GitHub Action workflow** - Scheduled sync with validation
3. **goneat sync command** - (roadmap) Declarative upstream sync

For now, manual sync with PROVENANCE.md tracking is the recommended approach.

## Troubleshooting

### Schema validation fails after update

The upstream schema may have new required fields. Check:

```bash
# See what changed
diff schemas/upstream/3leaps/agentic/v0/role-prompt.schema.json \
     ~/dev/crucible/schemas/agentic/v0/role-prompt.schema.json

# Update your config files to match new schema requirements
```

### Formatter modified vendored files

Your `.goneatignore` may not be set up correctly:

```bash
# Verify the pattern
cat .goneatignore | grep upstream

# Should contain:
# schemas/upstream/
# config/upstream/
```

### Merge conflicts in PROVENANCE.md

Always take the newer commit hash. PROVENANCE.md is documentation, not code.

## References

- [3leaps/crucible](https://github.com/3leaps/crucible) - Upstream source
- [fulmenhq/crucible](https://github.com/fulmenhq/crucible) - Example implementation
- [Role Prompt Schema](../../schemas/agentic/v0/role-prompt.schema.json) - Schema being vendored
