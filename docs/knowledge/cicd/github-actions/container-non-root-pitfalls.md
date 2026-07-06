---
title: "Container Non-Root Pitfalls"
description: "Running GitHub Actions containerized jobs as non-root (UID 1001) with custom images"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-03-23"
last_updated: "2026-03-23"
status: "draft"
tags: ["github-actions", "containers", "security", "non-root", "gopath"]
---

# Container Non-Root Pitfalls

Running containerized GitHub Actions jobs as non-root is a security best practice, but it introduces filesystem permission issues that are easy to miss — especially with custom runner images that pre-configure tool paths.

## The UID 1001 Convention

GitHub-hosted runners use UID 1001 for the runner agent. When running containerized jobs with `options: --user 1001`, the process inherits that UID but **not** the container image's default user environment.

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/myorg/my-runner:v1.0
      options: --user 1001
```

### What UID 1001 Can Write

| Path                                               | Writable | Why                                                                      |
| -------------------------------------------------- | -------- | ------------------------------------------------------------------------ |
| `${{ github.workspace }}` (e.g., `/__w/repo/repo`) | Yes      | Mounted from host, owned by runner                                       |
| `${{ github.workspace }}/..` (e.g., `/__w/repo/`)  | Yes      | Parent workspace dir                                                     |
| `/github/home`                                     | Yes      | GitHub-injected HOME                                                     |
| `/__t` (hosted tool cache)                         | Varies   | Mounted read-only for cached tools, but `setup-*` actions may write here |
| `/opt/*` (image-installed paths)                   | No       | Root-owned from image build                                              |
| `/home/runner`                                     | No       | May not exist in container                                               |
| Container's native `$HOME`                         | No       | Likely root-owned                                                        |

### What GitHub Actions Overrides

When running in a container, GitHub Actions injects its own environment regardless of what the Dockerfile sets:

```
HOME=/github/home          # NOT the container's native $HOME
GITHUB_WORKSPACE=/__w/repo/repo  # Mounted from host
```

This means any Dockerfile `ENV` that references `$HOME` or hardcodes paths under `/root`, `/home/user`, or `/opt` will point to directories the UID 1001 process cannot write to.

## Common Failure: GOPATH

Custom Go runner images often set `GOPATH` in the Dockerfile:

```dockerfile
ENV GOPATH=/opt/gopath
```

This directory is created and owned by root during image build. When `actions/setup-go` runs as UID 1001, it tries to `mkdir` inside `GOPATH/bin` and fails:

```
EACCES: permission denied, mkdir '/opt/gopath/bin'
```

### Fix: Override GOPATH to a Writable Location

Use a workspace-relative path that UID 1001 can write to:

```yaml
env:
  GOPATH: ${{ github.workspace }}/../_go
steps:
  - uses: actions/checkout@v4
  - name: Prepare Go directories
    run: mkdir -p "$GOPATH/bin" "$GOPATH/pkg"
  - uses: actions/setup-go@v5
    with:
      go-version: "1.25.x"
```

The workspace parent (`/__w/repo/`) is writable by UID 1001, so `/__w/repo/_go` works reliably.

### Why Not `/github/home/go`?

`/github/home` is writable, but it is a temporary directory that GitHub Actions creates per-job. Using it for GOPATH works, but `${{ github.workspace }}/..` is more predictable and easier to reason about in logs.

### Why Not `$HOME/go`?

In container mode, `$HOME` is `/github/home` (injected by Actions), not the container's native home. While this would technically work, it is confusing because the path does not match what the Dockerfile documents, and future image updates could change the container's home directory assumption.

## Same Pattern: Other Toolchains

The GOPATH case is the most common, but the same pattern applies to any tool that expects a writable path set during image build:

| Tool       | Image-set path              | Override env var   | Workspace-relative fix              |
| ---------- | --------------------------- | ------------------ | ----------------------------------- |
| Go         | `GOPATH=/opt/gopath`        | `GOPATH`           | `${{ github.workspace }}/../_go`    |
| Cargo/Rust | `CARGO_HOME=/opt/cargo`     | `CARGO_HOME`       | `${{ github.workspace }}/../_cargo` |
| npm        | `npm_config_cache=/opt/npm` | `npm_config_cache` | `${{ github.workspace }}/../_npm`   |
| pip        | `PIP_CACHE_DIR=/opt/pip`    | `PIP_CACHE_DIR`    | `${{ github.workspace }}/../_pip`   |

## Debugging Container Permission Issues

When a containerized job fails with `EACCES` or `Permission denied`:

1. Check which step failed and what path it tried to write:

   ```bash
   gh run view <run-id> --log-failed 2>&1 | grep -i "EACCES\|permission\|mkdir"
   ```

2. Check the container's environment to see what paths are injected:

   ```bash
   gh run view <run-id> --log 2>&1 | grep -i "HOME=\|GOPATH=\|CARGO_HOME="
   ```

3. Look at the `docker create` command in the "Initialize containers" log step — it shows the exact volume mounts, user override, and HOME injection.

4. The fix is almost always: override the failing env var to a workspace-relative path and pre-create the directory before the setup action runs.

## Key Takeaway

`${{ github.workspace }}` (and its parent) is the **one path guaranteed writable** by UID 1001 in containerized jobs. When a custom runner image sets tool paths to `/opt/*` or other root-owned locations, override them to workspace-relative paths in the workflow `env` block.

## Related

- [yaml-shell-gotchas.md](yaml-shell-gotchas.md) — Shell scripting pitfalls in Actions YAML
- [artifact-handling.md](artifact-handling.md) — Single-job vs artifact store patterns
