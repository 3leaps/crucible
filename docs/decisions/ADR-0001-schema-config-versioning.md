---
id: "ADR-0001"
title: "Schema and Config Versioning with v0 and SemVer"
status: "accepted"
date: "2026-01-22"
last_updated: "2026-01-22"
deciders:
  - "@3leapsdave"
  - "devlead"
scope: "Crucible Foundation"
tags:
  - "versioning"
  - "schemas"
  - "config"
  - "standards"
---

# ADR-0001: Schema and Config Versioning with v0 and SemVer

## Status

**Current Status**: Accepted

## Context

3leaps/crucible serves as a shared foundation for schemas, standards, and configuration that flows downstream to adopting repositories. A consistent versioning strategy is essential for:

- Clear communication of stability and maturity
- Safe consumption by downstream systems
- Natural sorting in file systems and tooling
- Predictable upgrade paths

### The Problem

Without a defined versioning standard:

1. Consumers cannot distinguish experimental schemas from stable ones
2. File paths may not sort naturally when versions evolve
3. Breaking changes may be introduced without warning
4. Multiple conventions may emerge across ecosystems

### Requirements

- Pre-release/experimental work must be clearly marked
- Stable releases must use semantic versioning (SemVer)
- Version paths must sort naturally in file systems
- The transition from experimental to stable must be explicit

## Decision

Adopt a two-tier versioning system for schemas and config:

### Tier 1: Pre-Release (`v0`)

Use `v0/` in paths for specifications that are:

- Under active development
- Not yet committed to backward compatibility
- Subject to breaking changes without notice

**Path pattern**: `schemas/{domain}/v0/{name}.schema.json`

**Example**:

```
schemas/classifiers/v0/sensitivity-level.schema.json
schemas/agentic/v0/role-prompt.schema.json
config/classifiers/v0/dimensions/sensitivity.dimension.json
```

**Semantics**:

- No backward compatibility guarantees
- May change at any time
- Consumers should pin to specific commits if stability needed
- `v0` is the ONLY acceptable non-SemVer version identifier

### Tier 2: Stable Releases (SemVer)

Use semantic version paths for stable specifications:

**Path pattern**: `schemas/{domain}/v{MAJOR}.{MINOR}.{PATCH}/{name}.schema.json`

**Examples**:

```
schemas/classifiers/v1.0.0/sensitivity-level.schema.json
schemas/classifiers/v1.1.0/sensitivity-level.schema.json
schemas/classifiers/v2.0.0/sensitivity-level.schema.json
```

**Semantics**:

- MAJOR: Breaking changes (incompatible schema modifications)
- MINOR: Backward-compatible additions (new optional fields)
- PATCH: Backward-compatible fixes (documentation, examples)

### Natural Sorting

The chosen format ensures natural sorting:

```
v0/           (always first - experimental)
v1.0.0/
v1.0.1/
v1.1.0/
v1.10.0/      (sorts after v1.9.0, not after v1.1.0)
v2.0.0/
v10.0.0/      (sorts after v9.x.x)
```

**Note**: Numeric sorting requires tooling awareness. File systems sort lexicographically, so `v10.0.0` sorts before `v2.0.0`. For correct ordering:

- Use zero-padded versions if >9 major versions expected: `v01.0.0`
- Or rely on tooling (make targets, scripts) for version enumeration

### Promotion Process: v0 to v1.0.0

When promoting from experimental to stable:

1. **Review**: Ensure schema has been tested in at least one downstream consumer
2. **Document**: Update changelog with initial stable release notes
3. **Copy**: Create `v1.0.0/` directory with finalized schema
4. **Retain**: Keep `v0/` for continued experimental work (optional)
5. **Announce**: Notify downstream consumers of stable availability

### Schema $id URLs

Schema `$id` fields must reflect the version path:

```json
{
  "$id": "https://schemas.3leaps.dev/classifiers/v0/sensitivity-level.schema.json"
}
```

After promotion:

```json
{
  "$id": "https://schemas.3leaps.dev/classifiers/v1.0.0/sensitivity-level.schema.json"
}
```

## Rationale

### Why v0 Instead of "draft" or "experimental"

- **Consistency**: `v0` aligns with SemVer conventions (0.x.y = pre-release)
- **Sorting**: `v0` sorts before `v1.0.0`
- **Simplicity**: Single-character marker is unambiguous
- **Convention**: Widely understood in software versioning

### Why Full SemVer in Paths

- **Precision**: Consumers can pin exact versions
- **Coexistence**: Multiple versions can exist simultaneously
- **Rollback**: Easy to reference previous versions
- **Auditing**: Clear history of schema evolution

### Trade-offs

| Approach             | Pros                                        | Cons                                                |
| -------------------- | ------------------------------------------- | --------------------------------------------------- |
| v0 + SemVer (chosen) | Clear stability signal, standard convention | Path proliferation over time                        |
| Latest-only          | Simple paths                                | No version coexistence, breaking changes affect all |
| Date-based           | Natural sorting                             | No semantic meaning, hard to compare                |

## Consequences

### Positive

- Downstream consumers can trust `v1.0.0+` for stability
- Clear signal when schemas are experimental
- Safe to iterate on `v0/` without breaking consumers
- Version history preserved in file system

### Negative

- Directory proliferation as versions accumulate
- Consumers must update paths when adopting new major versions
- Tooling needed for proper numeric version sorting

### Neutral

- Existing `v0/` schemas in 3leaps/crucible already follow this pattern
- No migration needed for current content

## Implementation

### Directory Structure

```
3leaps/crucible/
├── schemas/
│   ├── agentic/v0/          # existing
│   ├── ailink/v0/           # existing
│   ├── foundation/v0/       # existing
│   └── classifiers/v0/      # new
├── config/
│   ├── agentic/             # no version in config paths (uses schema version)
│   └── classifiers/
│       └── dimensions/      # dimension configs reference schema version
└── docs/
    └── standards/           # standard docs (not versioned in path)
```

### Config File Version References

Config files reference schema versions via `$schema`:

```json
{
  "$schema": "https://schemas.3leaps.dev/classifiers/v0/dimension-definition.schema.json",
  "key": "sensitivity",
  "version": "1.0.0"
}
```

The config's own `version` field tracks its content version independently.

### Validation

```bash
# Validate schema $id matches file path
make validate-schema-ids

# List all schemas by version
make list-schema-versions
```

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [JSON Schema $id](https://json-schema.org/understanding-json-schema/structuring.html#id)
- Existing patterns in `schemas/agentic/v0/`, `schemas/ailink/v0/`

## Revision History

| Date       | Status Change | Summary                              | Updated By |
| ---------- | ------------- | ------------------------------------ | ---------- |
| 2026-01-22 | → accepted    | Initial decision for 3leaps/crucible | devlead    |
