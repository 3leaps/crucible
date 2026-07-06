# Document Frontmatter

**Canonical URL** (hosted site planned — v0.1.x): `https://crucible.3leaps.dev/repository/frontmatter`

Required frontmatter format for documentation files in 3leaps repositories.

## Overview

Frontmatter provides structured metadata at the top of documentation files. It enables automated processing, search, organization, and clear accountability for AI-assisted content.

## Required Fields

Documentation files in consuming repositories SHOULD include YAML frontmatter. For AI-assisted content, frontmatter with accountability fields is REQUIRED.

**Scope**: This standard applies to documentation in repositories that adopt Crucible. Reference documentation (like role prompts in `catalog/`) and standards documents may omit frontmatter where metadata adds no value.

```yaml
---
title: "Document Title"
description: "Brief description of the document's purpose"
author: "@githubhandle"
date: "2024-12-24"
status: "draft"
---
```

| Field         | Type   | Description                                         |
| ------------- | ------ | --------------------------------------------------- |
| `title`       | string | Document title for navigation and indexing          |
| `description` | string | 1-2 sentence summary of purpose                     |
| `author`      | string | Primary author (`@handle` or role identifier)       |
| `date`        | string | Creation date (YYYY-MM-DD)                          |
| `status`      | enum   | One of: `draft`, `review`, `approved`, `deprecated` |

## Optional Fields

| Field          | Type   | Description                                           |
| -------------- | ------ | ----------------------------------------------------- |
| `last_updated` | string | Last modification date (YYYY-MM-DD)                   |
| `tags`         | array  | Categorization tags (lowercase, hyphenated)           |
| `version`      | string | Document version for versioned content                |
| `category`     | string | Document category (e.g., "standards", "architecture") |
| `reviewers`    | array  | List of reviewers for collaborative documents         |
| `related_docs` | array  | Links to related documentation                        |

## AI-Assisted Documentation

When AI assistants author or significantly contribute to documentation, add accountability fields.

### Supervised Mode

Human reviews before commit. Use `author_of_record` and `supervised_by`:

```yaml
---
title: "API Integration Guide"
description: "Guide to integrating with the 3leaps API"
author: "Claude Sonnet"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2024-12-24"
status: "draft"
tags: ["api", "integration", "guide"]
---
```

| Field              | Type   | Description                               |
| ------------------ | ------ | ----------------------------------------- |
| `author_of_record` | string | Human maintainer accountable for accuracy |
| `supervised_by`    | string | Human supervisor (`@handle`)              |

### Autonomous Mode

When AI tools materially assist with documentation:

```yaml
---
title: "Dependency Update Summary"
description: "Weekly automated dependency update report"
author: "@3leaps-agent-cicd"
escalation_contact: "@3leapsdave"
date: "2024-12-24"
status: "draft"
tags: ["automation", "dependencies"]
---
```

| Field                | Type   | Description                      |
| -------------------- | ------ | -------------------------------- |
| `escalation_contact` | string | Human to contact if issues arise |

### Attribution Parallel

This mirrors the commit attribution pattern:

| Mode       | Frontmatter          | Commit Trailer        |
| ---------- | -------------------- | --------------------- |
| Supervised | `author_of_record`   | `Committer-of-Record` |
| Autonomous | `escalation_contact` | `Escalation-Contact`  |

## Status Lifecycle

```
draft → review → approved → deprecated
```

| Status       | Meaning                                      |
| ------------ | -------------------------------------------- |
| `draft`      | Work in progress                             |
| `review`     | Ready for review                             |
| `approved`   | Reviewed and approved for use                |
| `deprecated` | No longer current, replaced by newer version |

## Examples

### Standard Document

```yaml
---
title: "Coding Baseline"
description: "Language-agnostic coding standards for 3leaps tools"
author: "@3leapsdave"
date: "2024-12-24"
status: "approved"
tags: ["standards", "coding", "baseline"]
---
```

### Versioned Schema Document

```yaml
---
title: "Config Schema v1.0.0"
description: "JSON Schema for configuration files"
author: "@3leapsdave"
date: "2024-12-24"
last_updated: "2024-12-24"
status: "approved"
version: "v1.0.0"
tags: ["schemas", "config", "validation"]
---
```

### Collaborative Document

```yaml
---
title: "Architecture Decision Record: API Gateway"
description: "ADR for API gateway selection and implementation"
author: "@3leapsdave"
date: "2024-12-24"
status: "review"
reviewers: ["@contributor1", "@contributor2"]
tags: ["adr", "architecture", "api"]
---
```

## Validation Rules

- Frontmatter must be valid YAML
- All required fields must be present
- Dates must follow ISO 8601 format (YYYY-MM-DD)
- Status must be one of the defined values
- Tags should be lowercase with hyphens

## File Naming

- Use kebab-case: `document-title.md`
- Include version if needed: `schema-reference-v1.0.0.md`
- Store in appropriate directory: `docs/standards/`, `docs/architecture/`

## Relationship to Commit Attribution

| Aspect            | Frontmatter              | Commit Attribution          |
| ----------------- | ------------------------ | --------------------------- |
| Scope             | Document metadata        | Commit messages             |
| Purpose           | Organization & discovery | Version control attribution |
| Location          | Top of document          | Git commit message          |
| AI accountability | `author_of_record`       | `Committer-of-Record`       |

Use both for complete attribution chain from document creation through version control.

## References

- [commit-style.md](commit-style.md) - Commit attribution patterns
- [agent-identity.md](agent-identity.md) - AI contribution attribution
