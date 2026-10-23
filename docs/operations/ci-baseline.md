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
     image: ghcr.io/fulmenhq/goneat-tools-runner:vX.Y.Z@sha256:<digest>
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

**Via goneat** (for repos using goneat): actionlint runs as part of the lint
category and is on by default (`--lint-gha=false` turns it off):

```sh
goneat assess --categories lint
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

Run goneat from a digest-pinned toolbox image (see [Container-Based CI](#container-based-ci)),
or install it with verification at a pinned version. Never pipe a downloaded
installer into a shell, and never install `latest`: both make the build depend on
whatever the network serves that day.

When installing on the host, pin the sfetch bootstrap by version and digest, then
have sfetch verify goneat against a committed key (see
[Pins and Keys](#pins-and-keys)):

```sh
sfetch --repo fulmenhq/goneat --tag vX.Y.Z --dest-dir ./bin \
  --require-minisign --minisign-key docs/security/fulmenhq-goneat-minisign.pub
./bin/goneat assess --ci-summary --fail-on high
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
permissions:
  contents: read

jobs:
  quality:
    runs-on: ubuntu-latest
    container:
      # Pin the tag for readability and the digest for integrity.
      image: ghcr.io/fulmenhq/goneat-tools-runner:vX.Y.Z@sha256:<digest>
      options: --user 1001 # Critical: match GHA runner mount ownership
    steps:
      - uses: actions/checkout@<full-commit-sha> # vN.N.N
        with:
          persist-credentials: false
      - run: make check
```

The image carries a fixed tool set. If a step needs a tool the image lacks (for
example `gpg` for signature checks), run that step as a separate host job rather
than installing tools inside the container at run time.

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

### Pipes Under `pipefail`

`producer | grep -q pattern` can fail under `set -o pipefail`, sometimes or every time.
`grep -q` exits at the first match and closes the pipe; a producer still writing
then dies of `SIGPIPE`, and `pipefail` reports the match as a failure. The larger
the input and the earlier the match, the more often it happens.

Match from a variable or a here-string instead:

```sh
listing="$(gpg --list-secret-keys --with-colons)"
grep -q '^sec' <<<"$listing"
```

A control for this needs a large input with an early match; a small input passes
either way.

### Windows Runners

- Set `git config --global core.autocrlf false` **before** checkout when the
  repository's bytes matter (digests, golden files, fixtures). Otherwise text
  files arrive with CRLF line endings and every byte-level comparison fails.
- `python3` is often absent; `actions/setup-python` provides `python`. A small
  shim on `PATH` keeps shared scripts portable.
- Shard long Windows jobs and add one aggregate job that requires every shard,
  so branch protection can name a single stable check.

### Debug Probes

When adding debug output to diagnose CI issues:

- Keep probes short-lived
- Remove after green runs
- Don't commit temporary echo/printenv statements

## Supply Chain

### Pin Everything by Content

- **Actions**: reference by full commit SHA with the version in a comment
  (`uses: actions/checkout@<sha> # v5.0.1`). A tag can be moved; a commit cannot.
- **Container images**: `name:tag@sha256:<digest>`. The digest is the pin; the
  tag is for humans.
- **Downloaded tools**: commit the expected SHA-256 of each archive, one line per
  platform, and refuse a mismatch before extracting. Select exactly one line per
  platform, so a missing pin fails rather than passing vacuously (as
  `sha256sum --check --ignore-missing` would).
- **Never** `curl … | bash` or `--tag latest` in CI.

### Least Privilege

- Set `permissions: contents: read` at the workflow level and grant write scope
  only to the one job that needs it (for example, the job that creates a
  release).
- Use `persist-credentials: false` on checkout unless a later step must push.
- A verification job that passes is a consistency signal, not authorization:
  keep verification read-only, and keep publication in a separate job.

### Pins and Keys

Public keys used to verify downloaded tools are committed files named for the
producing organization and tool (for example
`docs/security/fulmenhq-goneat-minisign.pub`), passed to the verifier
explicitly. A key fetched from the same release it verifies is not independent
authentication. See
[PDR-0008](../decisions/PDR-0008-release-public-identity-in-tree.md).

### Negative Controls

Every gate CI relies on needs a committed test that proves it can fail: feed it
the bad input (wrong digest, tampered key, missing variable) and assert both
that it fails and **why**. A check that has never failed is not yet evidence. See
[EPR-0002](../decisions/EPR-0002-verification-gate-integrity.md).

## Related Resources

- [goneat assess documentation](https://github.com/fulmenhq/goneat/blob/main/docs/assess/)
- [fulmen-toolbox container patterns](https://github.com/fulmenhq/fulmen-toolbox/blob/main/docs/user-guide/container-usage-patterns.md)
- [GitHub Actions security hardening](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
