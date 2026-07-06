# CI/CD Baseline

Patterns and gotchas for CI/CD pipelines across 3leaps projects. This document captures hard-won lessons that apply regardless of specific repository or organization.

> **Living Document**: We actively solicit input from maintainers and teams. If you've burned hours on a CI issue that others shouldn't have to rediscover, please contribute.

## Git in Containers

### Safe Directory (Git 2.35+)

**Problem**: Git 2.35+ enforces "safe directory" checks. When a container runs as `root` but the workspace is owned by a non-root UID (common in GitHub Actions), Git refuses to operate on the repository.

**Symptoms**:

- `git diff --exit-code` exits 129 with usage message
- `fatal: detected dubious ownership in repository`
- Formatting tools run successfully but Git commands fail

**Solutions** (in order of preference):

1. **Match container user to workspace owner** (recommended):

   ```yaml
   container:
     image: ghcr.io/fulmenhq/goneat-tools:latest
     options: --user 1001 # Match GHA runner mount ownership
   ```

2. **Declare workspace safe** (when root is required):

   ```sh
   git config --global --add safe.directory "$GITHUB_WORKSPACE"
   ```

3. **Use formatter check mode** (avoid Git dependency entirely):
   ```sh
   goneat format --check  # or prettier --check, yamlfmt -lint
   ```

**Complete pattern** (when git diff is needed):

```sh
set -euo pipefail
make fmt
unset GIT_DIFF_OPTS GIT_EXTERNAL_DIFF || true
git config --global --add safe.directory "$GITHUB_WORKSPACE"
git diff --exit-code --
```

## Formatting Verification

### Check Mode vs Git Diff

Two approaches for verifying formatting in CI:

| Approach            | Pros                        | Cons                                  |
| ------------------- | --------------------------- | ------------------------------------- |
| Formatter `--check` | No Git dependency, explicit | Must support check mode               |
| `git diff`          | Works with any formatter    | Requires safe.directory, more fragile |

**Recommendation**: Prefer check mode when available. Most modern formatters support it:

- `prettier --check`
- `yamlfmt -lint` or `yamlfmt -dry`
- `goneat format --check`
- `biome check`
- `taplo fmt --check`

## Workflow Validation

### actionlint

Validate GitHub Actions workflow files before push. Catches syntax errors, invalid action references, and common mistakes.

**Local usage**:

```sh
actionlint .github/workflows/*.yml
```

**Via goneat** (for repos using goneat):

```sh
goneat assess --categories lint
# or specifically:
goneat assess --lint-gha
```

**Configuration** (`.goneat/assess.yaml`):

```yaml
lint:
  github_actions:
    actionlint:
      enabled: true
      paths: [".github/workflows/**/*.yml", ".github/workflows/**/*.yaml"]
```

## YAML Formatting

### yamlfmt and GitHub Runners

GitHub-hosted runners can be particular about YAML formatting. Inconsistent indentation or trailing whitespace may cause unexpected behavior.

**Pre-commit**:

```sh
yamlfmt .
```

**CI validation**:

```sh
yamlfmt -lint .
# or
yamlfmt -dry -lint .  # Check without writing
```

## Quality Gates with goneat

For repositories using [goneat](https://github.com/fulmenhq/goneat) as a DX tool, leverage `goneat assess` for comprehensive quality checks.

### Pre-commit / Pre-push

```sh
# Pre-commit: fast, fail on critical only
goneat assess --categories format,lint,security --fail-on critical

# Pre-push: thorough, fail on high severity
goneat assess --categories format,lint,security --fail-on high
```

### CI Integration

```yaml
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install goneat
        run: |
          curl -fsSL https://github.com/3leaps/sfetch/releases/latest/download/install-sfetch.sh | bash
          sfetch --repo fulmenhq/goneat --tag latest
      - name: Run quality checks
        run: goneat assess --ci-summary --fail-on high
```

### Scaffold Configuration

```sh
goneat doctor assess init  # Creates .goneat/assess.yaml starter
```

## Container-Based CI

### fulmen-toolbox

For repositories that use `make` commands in CI, [fulmen-toolbox](https://github.com/fulmenhq/fulmen-toolbox) provides specialized containers with pre-installed tools.

**Available images**:

| Image                       | Purpose                          | Use When                          |
| --------------------------- | -------------------------------- | --------------------------------- |
| `goneat-tools-runner`       | Code quality + CI baseline       | Make-based workflows, musl/Alpine |
| `goneat-tools-runner-glibc` | Code quality + glibc baseline    | CGO builds, glibc-only deps       |
| `goneat-tools-slim`         | Tools only, smaller footprint    | Local tool replacement            |
| `sbom-tools-runner`         | SBOM/vuln scanning + CI baseline | Security scanning workflows       |

**GitHub Actions example**:

```yaml
jobs:
  quality:
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/fulmenhq/goneat-tools:latest
      options: --user 1001 # Critical: match GHA runner mount ownership
    steps:
      - uses: actions/checkout@v4
      - run: make check
```

**Why `--user 1001`?** GitHub Actions mounts the workspace as UID 1001. Without this option, non-root containers fail with `EACCES` errors on `/__w/_temp/_runner_file_commands/`.

**Bundled tools** (goneat-tools): prettier, biome, yamlfmt, shfmt, checkmake, actionlint, goneat, sfetch, jq, yq, ripgrep, taplo, and more.

## Common Gotchas

### Environment Variables

CI runners may have different environment than local:

- `HOME` may be `/github/home` or similar, not `/root`
- `PATH` may not include expected locations
- Temp directories vary by runner OS

**Pattern**: Use explicit paths or rely on tool defaults rather than environment assumptions.

### Matrix Testing

Avoid:

- Testing combinations that can't exist in production
- Duplicating tests across matrix dimensions unnecessarily
- Large matrices that slow CI without proportional value

### Debug Probes

When adding debug output to diagnose CI issues:

- Keep probes short-lived
- Remove after green runs
- Don't commit temporary echo/printenv statements

## Related Resources

- [goneat assess documentation](https://github.com/fulmenhq/goneat/blob/main/docs/assess/)
- [fulmen-toolbox container patterns](https://github.com/fulmenhq/fulmen-toolbox/blob/main/docs/user-guide/container-usage-patterns.md)
- [GitHub Actions security hardening](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
