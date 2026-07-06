---
title: "CI/CD Knowledge"
description: "CI/CD platform knowledge, automation patterns, and registry publishing"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["cicd", "automation", "knowledge"]
---

# CI/CD Knowledge

CI/CD platform knowledge and automation patterns across 3leaps projects.

## Structure

```
cicd/
├── github-actions/          # GitHub Actions platform knowledge
│   └── README.md
└── registry/                # Package registry publishing
    ├── README.md
    └── npm-oidc.md
```

## Topics

### GitHub Actions

Platform-specific knowledge for GitHub Actions workflows.

| Document                           | Description                                                 |
| ---------------------------------- | ----------------------------------------------------------- |
| [github-actions/](github-actions/) | GitHub Actions patterns and gotchas (incl. Windows runners) |

### Registry Publishing

Package registry publishing patterns and authentication.

| Document               | Description                     |
| ---------------------- | ------------------------------- |
| [registry/](registry/) | npm, crates.io, PyPI publishing |

## What Belongs Here

- **Platform quirks** - GitHub Actions gotchas, runner limitations
- **Authentication patterns** - OIDC, tokens, trusted publishing
- **Workflow patterns** - Matrix builds, artifact handling
- **Registry publishing** - Per-registry publishing knowledge

## Related

- [Toolchain Knowledge](../toolchains/) - Language-specific build knowledge
- [Operations](../../operations/) - CI baseline and operational guides
- [Guide: Multi-Org GitHub CLI Auth](../../guides/multi-org-github-cli-auth.md) - Operator auth context outside GitHub Actions
