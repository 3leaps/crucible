---
title: "npm OIDC Trusted Publishing"
description: "Setting up npm OIDC trusted publishing from GitHub Actions"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-11-28"
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

- **npm CLI >= 11.5.1** (required for OIDC trusted publishing; **npm >= 11.15.0** is required for `npm trust` CLI management commands)
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
4. Configure the four fields:
   - **Organization or user**: `your-org` (case-sensitive, match GitHub URL)
   - **Repository**: `your-repo`
   - **Workflow filename**: `publish.yml` (filename only, case-sensitive, include `.yml`)
   - **Environment name**: `publish-npm` (optional, e.g., when using GitHub environments for protection)
5. Tick **Allow npm publish** (required when workflows run `npm publish` directly rather than promoting staged publishes)
6. Click **Set up connection**

**CLI alternative (npm >= 11.15.0):**

```bash
npm trust github <pkg> --file <workflow>.yml --repo <org>/<repo> --env <env> --allow-publish -y
```

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
2. Select the recommended 2FA-only option that disallows token publishing (**"Require two-factor authentication and disallow tokens"** or **"Require two-factor authentication and disallow bypass 2fa tokens (recommended)"**, depending on the npmjs.com UI revision)
3. Save changes

Do **not** leave the bypass-2FA option (_"Require two-factor authentication or a granular access token with bypass 2fa enabled"_) selected. Although npm is progressively restricting bypass-2FA tokens (starting with account/governance actions and printing deprecation warnings during publish), a leftover bypass token can still direct-publish until removed and takes precedence over OIDC.

OIDC trusted publishing is unaffected by this restriction. Break-glass and initial first-publish operations require an interactive `npm login` with 2FA.

### 5. Renaming or Moving the Publish Workflow

Each package's trusted publisher binds a single workflow filename. If you rename, move, or unify the publish workflow:

1. Update the trusted-publisher entry on **every** package that uses the workflow, including every napi-rs platform package.
2. Make these updates before the first release from the new workflow, ideally in the same PR window as the workflow change.
3. Update via the website (delete and re-add the entry) or via the CLI (`npm >= 11.15.0`). Because `npm trust github` creates a publisher without replacing an existing one (and fails when one already exists), list and revoke the existing entry before creating the new one:
   ```bash
   npm trust list <pkg>
   npm trust revoke --id=<id> <pkg>
   npm trust github <pkg> --file <workflow>.yml --repo <org>/<repo> --env <env> --allow-publish -y
   ```
4. Expect HTTP 429 rate-limiting on `npmjs.com` when deleting and re-adding entries across many packages in the web UI; pace changes or use the CLI.
5. **Pre-flight check before tagging:** confirm each package's npm trusted-publisher settings name the exact workflow filename present on the tagged commit.

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

### `npm error code ENEEDAUTH` / "This command requires you to be logged in" under OIDC

With npm >= 11.5.1, if the OIDC token exchange is refused, npm falls back to anonymous (no-auth) mode and reports that you need to log in (`ENEEDAUTH` / `npm adduser`) rather than stating that the trusted publisher did not match.

**How to distinguish from other errors:**

- Unlike _"Access token expired or revoked" + E404_, no stale token is present in the environment.
- Unlike _404 without expired token_, npm fails before sending an authenticated PUT because the OIDC exchange itself did not succeed.

**Checks:**

1. Confirm the **workflow filename** (case-sensitive, with `.yml`) and **environment name** in each package's npm trusted-publisher entry match the workflow file on the tagged commit. This is the most common cause after renaming or unifying publish workflows.
2. Confirm `permissions: id-token: write` is set on the publish job. Note that the `GITHUB_TOKEN Permissions` block printed in GitHub Actions job logs does **not** list `IdToken`, so do not treat its absence there as evidence that OIDC is misconfigured.

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

All packages must use the same workflow file. When the publish workflow filename changes, update all platform packages and the root package together, then re-run only the failed npm job; resumable publish scripts skip versions that are already published.

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
