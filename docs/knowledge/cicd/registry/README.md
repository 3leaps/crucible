---
title: "Registry Publishing Knowledge"
description: "Package registry publishing patterns and authentication"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["registry", "publishing", "npm", "crates-io", "pypi"]
---

# Registry Publishing Knowledge

Package registry publishing patterns, authentication, and troubleshooting.

## Registries

| Registry  | Document                   | Auth Method             |
| --------- | -------------------------- | ----------------------- |
| npm       | [npm-oidc.md](npm-oidc.md) | OIDC Trusted Publishing |
| crates.io | (planned)                  | Token-based             |
| PyPI      | (planned)                  | OIDC Trusted Publishing |

## Authentication Approaches

### OIDC Trusted Publishing (Preferred)

- No long-lived secrets to manage
- Tokens cannot be extracted from logs
- Automatic provenance attestation
- Scoped to specific workflow files

Supported by:

- **npm** - via npmjs.com trusted publisher configuration
- **PyPI** - via pypi.org trusted publisher configuration

### Token-Based (Legacy)

- Requires secret management and rotation
- Risk of token exposure in logs
- Still required for first publish (before OIDC can be configured)

## Common Issues

### First Publish Chicken-and-Egg

OIDC trusted publishing requires the package to already exist. First publish must use:

1. Manual `npm publish` / `twine upload` with local auth
2. Or token-based CI publish

After first publish, configure OIDC for subsequent releases.

### Scoped Packages Default to Private

npm scoped packages (`@org/package`) default to private. Use:

```bash
npm publish --access public
```

Or in package.json:

```json
{
  "publishConfig": {
    "access": "public"
  }
}
```

## Related

- [GitHub Actions](../github-actions/) - CI platform patterns
- [Toolchains](../../toolchains/) - Language-specific build knowledge
