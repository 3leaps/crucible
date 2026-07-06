---
title: "npm OIDC Trusted Publishing"
description: "Setting up npm OIDC trusted publishing from GitHub Actions"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-31"
status: "approved"
tags: ["npm", "oidc", "trusted-publishing", "github-actions"]
---

# npm OIDC Trusted Publishing

OIDC trusted publishing creates a trust relationship between npm and GitHub Actions using OpenID Connect. When configured, npm accepts publishes from authorized workflows using short-lived, cryptographically-signed tokens.

## Benefits

- No long-lived secrets to manage or rotate
- Tokens cannot be accidentally exposed in logs
- Automatic provenance attestation for supply chain security
- Scoped to specific workflow files

## Prerequisites

- **npm CLI >= 11.5.1** (required for trusted publishing support)
- GitHub Actions workflow with OIDC enabled (`permissions: id-token: write`)
- Package must already exist on npm (first publish requires manual/token approach)
- `package.json` must include `repository.url` field
- **No `NPM_TOKEN` or `NODE_AUTH_TOKEN` secrets** in repo or environment

### npm CLI Version

Ubuntu runners with Node 20 ship with npm ~10.x, which does **not** support OIDC trusted publishing. You must upgrade npm in your workflow:

```yaml
- name: Ensure npm CLI supports OIDC
  run: |
    echo "npm (before): $(npm --version)"
    npm install -g npm@11.5.1
    echo "npm (after): $(npm --version)"
```

## One-Time Setup

### 1. First Publish (Manual)

The first version must be published manually before OIDC can be configured:

```bash
npm login  # Authenticate with OTP if 2FA enabled
npm publish --access public  # For scoped packages
```

### 2. Configure Trusted Publisher on npmjs.com

After the package exists:

1. Navigate to `https://www.npmjs.com/package/@org/package/access`
2. Find the **Trusted Publisher** section
3. Click **GitHub Actions**
4. Configure:
   - **Organization or user**: `your-org` (case-sensitive, match GitHub URL)
   - **Repository**: `your-repo`
   - **Workflow filename**: `publish.yml` (filename only, include `.yml`, case-sensitive)
   - **Environment name**: `publish-npm` (if using GitHub environments for protection)
5. Click **Set up connection**

Repeat for each package in a multi-package publish (e.g., napi-rs platform packages).

### 3. Remove Any NPM_TOKEN Secrets

**Critical**: If you previously used token-based publishing, you MUST remove any `NPM_TOKEN` or `NODE_AUTH_TOKEN` secrets from:

- Repository secrets (`Settings → Secrets and variables → Actions`)
- Environment secrets (if using GitHub environments)
- Organization secrets (if inherited)

npm will use token auth if any token is present, even with OIDC configured. The token takes precedence.

### 4. Restrict Token Access (Recommended)

After verifying OIDC works:

1. Navigate to package Settings → Publishing access
2. Select **"Require two-factor authentication and disallow tokens"**
3. Save changes

## Workflow Configuration

### Basic Configuration (May Have Issues)

```yaml
permissions:
  id-token: write # Required for OIDC
  contents: read

jobs:
  publish:
    runs-on: ubuntu-latest # Must be GitHub-hosted
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          registry-url: "https://registry.npmjs.org"

      # Do NOT set NODE_AUTH_TOKEN - must be unset for OIDC fallback
      - run: npm publish --access public
```

**Warning**: `actions/setup-node` with `registry-url` creates an `.npmrc` that references `$NODE_AUTH_TOKEN`. If any token is present in the environment (even from unrelated sources), npm will attempt token auth instead of OIDC.

### Recommended Configuration (Forces OIDC)

For reliable OIDC publishing, explicitly force OIDC mode:

```yaml
permissions:
  id-token: write
  contents: read

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: publish-npm # Optional: adds deployment protection
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          registry-url: "https://registry.npmjs.org"

      - name: Ensure npm CLI supports OIDC
        run: |
          npm install -g npm@11.5.1
          echo "npm version: $(npm --version)"

      - name: Publish to npm
        run: |
          # Force OIDC mode: prevent any token auth from interfering
          unset NODE_AUTH_TOKEN NPM_TOKEN
          export NPM_CONFIG_USERCONFIG="$RUNNER_TEMP/npmrc-oidc"
          printf '%s\n' 'registry=https://registry.npmjs.org/' 'always-auth=false' > "$NPM_CONFIG_USERCONFIG"

          npm publish --access public
```

This pattern:

1. Unsets any token environment variables
2. Creates a fresh `.npmrc` that doesn't reference tokens
3. Forces npm to use OIDC for authentication

## Troubleshooting

### "Access token expired or revoked" + E404

This error combination indicates npm is **not using OIDC** - it's attempting token auth with an invalid or missing token.

**Symptoms:**

```
npm notice Access token expired or revoked. Please try logging in again.
npm error code E404
npm error 404 Not Found - PUT https://registry.npmjs.org/@org%2fpackage
```

**Root causes:**

1. **npm CLI too old** - Version < 11.5.1 doesn't support OIDC
2. **Token present in environment** - `NODE_AUTH_TOKEN` or `NPM_TOKEN` set somewhere
3. **`.npmrc` configured for token auth** - `actions/setup-node` + `registry-url` does this

**Solutions:**

1. Upgrade npm: `npm install -g npm@11.5.1`
2. Unset tokens: `unset NODE_AUTH_TOKEN NPM_TOKEN`
3. Use isolated npmrc (see recommended configuration above)
4. Check for secrets at repo/environment/org level and remove them

### "Unable to authenticate" error

- Verify workflow filename matches exactly (case-sensitive, include `.yml`)
- Ensure using GitHub-hosted runners, not self-hosted
- Check `id-token: write` permission is set
- Confirm `NODE_AUTH_TOKEN` is NOT set (not even empty string)

### 404 on publish (without "expired token" message)

npm could not match workflow to trusted publisher configuration:

- Check organization name matches GitHub URL exactly (case-sensitive)
- Verify `package.json` has correct `repository.url`
- Confirm workflow file exists at `.github/workflows/<filename>.yml`
- Check environment name matches if specified in npm config

### E402 Payment Required

Scoped packages default to private:

```bash
npm publish --access public
```

Or add to package.json:

```json
{
  "publishConfig": {
    "access": "public"
  }
}
```

### Provenance not generated

Automatic provenance requires:

- Publishing via OIDC (not token)
- Public repository
- Public package

Private repositories cannot generate provenance even for public packages.

## Multi-Package Publishing (napi-rs)

For napi-rs projects with platform packages:

1. Configure trusted publisher for **each** platform package
2. Configure trusted publisher for root package
3. Publish platform packages first, then root package

All packages must use the same workflow file.

**Important**: Each platform package (e.g., `@org/pkg-darwin-arm64`, `@org/pkg-linux-x64-gnu`) needs its own trusted publisher configuration on npmjs.com.

## GitHub Environments

When using GitHub environments (e.g., `publish-npm`) for deployment protection:

1. Configure the environment in repo Settings → Environments
2. Add deployment branch/tag rules (e.g., `v*` tags only)
3. Specify the environment name in npm trusted publisher config
4. Reference it in workflow: `environment: publish-npm`
5. **Do NOT add `NPM_TOKEN` as an environment secret** - this overrides OIDC

The environment provides:

- Approval requirements before publish
- Branch/tag restrictions
- Audit trail of deployments

## Security Considerations

- Each package can only have one trusted publisher at a time
- Workflow filename is part of the trust anchor - changing it requires reconfiguration
- Consider using GitHub environments with approval requirements for additional control
- Regularly audit trusted publisher configurations
- **Never store `NPM_TOKEN` alongside OIDC configuration** - token auth takes precedence

## References

- [npm Trusted Publishers Documentation](https://docs.npmjs.com/trusted-publishers/)
- [GitHub Actions OIDC Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [OpenSSF Trusted Publishers Specification](https://repos.openssf.org/trusted-publishers-for-all-package-repositories)

## Projects Using This

- sysprims (v0.1.8+) - TypeScript bindings via napi-rs
- docprims (v0.1.4+) - TypeScript bindings via napi-rs
- tsfulmen (v0.2.4+) - TypeScript library with automated release workflow
