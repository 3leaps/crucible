---
title: "GitHub Actions Knowledge"
description: "GitHub Actions platform knowledge, patterns, and workarounds"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-02-10"
status: "approved"
tags: ["github-actions", "cicd", "automation"]
---

# GitHub Actions Knowledge

GitHub Actions platform knowledge and patterns.

## Topics

| Document                                                               | Description                             | Status   |
| ---------------------------------------------------------------------- | --------------------------------------- | -------- |
| [release-rollback.md](release-rollback.md)                             | Release rollback procedure              | Approved |
| [workflow-version-resolution.md](workflow-version-resolution.md)       | How workflow file versions are resolved | Approved |
| [yaml-shell-gotchas.md](yaml-shell-gotchas.md)                         | YAML + shell script pitfalls            | Approved |
| [windows-runners.md](windows-runners.md)                               | Windows runner platform differences     | Draft    |
| [cross-platform-asset-selection.md](cross-platform-asset-selection.md) | OS token matching pitfalls              | Draft    |
| [artifact-handling.md](artifact-handling.md)                           | Single-job vs artifact store patterns   | Draft    |
| [manual-signing-handoff.md](manual-signing-handoff.md)                 | Draft release local signing workflow    | Draft    |
| [release-verification-checklist.md](release-verification-checklist.md) | Pre-publish release verification gate   | Draft    |
| [container-non-root-pitfalls.md](container-non-root-pitfalls.md)       | UID 1001 container permission gotchas   | Draft    |
| (planned) esm-library-publishing.md                                    | ESM library publishing gotchas          | Planned  |
| (planned) matrix-builds.md                                             | Cross-platform matrix build patterns    | Planned  |

## Common Patterns

### OIDC Permissions

For OIDC-based authentication (npm, PyPI trusted publishing):

```yaml
permissions:
  id-token: write # Required for OIDC
  contents: read
```

### Cross-Platform Matrix

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    include:
      - os: ubuntu-latest
        target: x86_64-unknown-linux-gnu
      - os: macos-latest
        target: aarch64-apple-darwin
```

### Artifact Handling

Download artifacts from another workflow run:

```yaml
- name: Download artifact
  env:
    GH_TOKEN: ${{ github.token }}
  run: |
    gh run download "$RUN_ID" --name artifact-name --dir output/
```

## Key Concepts

### Workflow File Version Resolution

When a workflow triggers, GitHub reads the workflow YAML **from the triggering ref**, not from the default branch. This means:

- `workflow_dispatch` from a tag uses the workflow file at that tag's commit
- Pushing fixes to `main` doesn't affect workflows triggered from existing tags
- To fix a workflow for a tagged release, you must move the tag

See [workflow-version-resolution.md](workflow-version-resolution.md) for details.

### Shell Scripts in YAML

Writing shell scripts in YAML `run:` blocks requires care:

- Heredocs break YAML parsing (use `printf` instead)
- `set -euo pipefail` for proper error handling
- Explicitly set `shell: bash` when using bash features

See [yaml-shell-gotchas.md](yaml-shell-gotchas.md) for patterns.

### Windows Runners

Windows runners differ from Linux/macOS in shell defaults, filesystem behavior, and binary naming. Key issues include cross-device `os.Rename` failures, `.exe` extension propagation, and PowerShell as the default shell.

See [windows-runners.md](windows-runners.md) for details.

### Cross-Platform Asset Selection

When selecting release assets by OS/arch, short platform aliases (like `"win"`) can match as substrings inside other platform names (`"darwin"`). Boundary-aware token matching prevents false positives.

See [cross-platform-asset-selection.md](cross-platform-asset-selection.md) for the pattern.

### Artifact Handling Strategy

Prefer single-job release assembly when possible. Use `upload-artifact` / `download-artifact` only when cross-job boundaries are required by platform or trust constraints.

See [artifact-handling.md](artifact-handling.md) for selection criteria.

### Manual Signing Handoff

For key isolation, keep release generation in CI but perform checksum/signature work on a trusted local machine before undrafting.

See [manual-signing-handoff.md](manual-signing-handoff.md) for the operator flow.

### Release Verification Gate

Use a fixed pre-publish checklist before undrafting.

See [release-verification-checklist.md](release-verification-checklist.md).

### Container Non-Root Pitfalls

Running containerized jobs with `--user 1001` breaks any image-defined paths owned by root (`/opt/gopath`, `/opt/cargo`, etc.). GitHub Actions also overrides `HOME` to `/github/home`. The safe anchor is `${{ github.workspace }}` — override tool paths to workspace-relative locations.

See [container-non-root-pitfalls.md](container-non-root-pitfalls.md) for the full pattern.

## Known Issues

### actions/download-artifact v4 < 4.1.3

**Severity**: High (GHSA-cxww-7g56-2vh6)
**Fix**: Update to v4.1.3 or later

### Transient API Failures

GitHub-hosted runners occasionally hit transient network errors when calling api.github.com. Mitigate with retries:

```yaml
- name: Download with retry
  run: |
    for attempt in 1 2 3 4 5; do
      if gh run download "$RUN_ID" --name artifact --dir output; then
        break
      fi
      echo "::warning::Download failed (attempt $attempt/5). Retrying..."
      sleep $((attempt * attempt))
    done
```

### GitHub Infrastructure Outages (500/502/503)

GitHub occasionally experiences infrastructure outages that cause `actions/checkout` to fail with HTTP 500, 502, or 503 errors on `git clone`. These affect all runner types (Linux, Windows, macOS) simultaneously.

**Symptoms**:

- All jobs fail at `actions/checkout@v4` (or any version)
- Error: `fatal: unable to access 'https://github.com/...': The requested URL returned error: 500`
- Multiple retries within checkout fail (checkout retries 3 times internally)

**Diagnosis**:

```bash
# Check which step failed
gh run view <run-id> --json jobs --jq '.jobs[] | {name, steps: [.steps[] | select(.conclusion == "failure") | .name]}'

# Get error details
gh run view <run-id> --log-failed 2>&1 | grep -i "error\|500\|502\|503"

# Check GitHub status
# Visit https://www.githubstatus.com/ or use gh api
```

**Resolution**: Wait for GitHub to recover, then re-run failed jobs:

```bash
gh run rerun <run-id> --failed
```

**Key insight**: Don't waste time debugging your code when all jobs fail at checkout. Check `githubstatus.com` first — if Git Operations shows degraded, it's an infrastructure issue.

## Related

- [Registry Publishing](../registry/) - Package registry OIDC setup
- [Operations: CI Baseline](../../../operations/ci-baseline.md) - CI standards
- [Guide: Multi-Org GitHub CLI Auth](../../../guides/multi-org-github-cli-auth.md) - Local operator auth context for `gh` outside Actions
