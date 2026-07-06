---
title: "Workflow Version Resolution"
description: "How GitHub Actions resolves workflow file versions for different trigger types"
author: "Claude Opus 4.5"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-31"
last_updated: "2026-01-31"
status: "approved"
tags: ["github-actions", "workflow", "tags", "releases", "troubleshooting"]
---

# Workflow Version Resolution

When a GitHub Actions workflow runs, GitHub must decide which version of the workflow YAML file to use. This decision happens **before** any workflow steps execute, including checkout.

## The Key Insight

**The workflow file is read from the commit/ref that triggers the workflow, not from the default branch.**

This means:

- Pushing fixes to `main` does NOT affect workflows triggered from tags
- Re-running a failed workflow uses the same workflow file version
- To update a workflow for a tagged release, you must move the tag

## Resolution by Trigger Type

| Trigger                      | Workflow File Source                           |
| ---------------------------- | ---------------------------------------------- |
| `push` to branch             | The pushed commit                              |
| `push` tag                   | The tagged commit                              |
| `pull_request`               | The PR's head commit (merge commit for checks) |
| `workflow_dispatch` (branch) | HEAD of selected branch                        |
| `workflow_dispatch` (tag)    | The tagged commit                              |
| `schedule`                   | Default branch HEAD                            |
| `workflow_call`              | Caller's ref                                   |

## Common Misconception

```
Scenario: Release workflow fails on v1.0.0 tag
Attempted fix: Push workflow fix to main
Result: Re-running workflow from v1.0.0 still uses old workflow

Why: The tag points to commit A, which has the old workflow.
     Main now has commit B with the fix.
     Running from tag v1.0.0 uses commit A's workflow.
```

## Implications for Release Workflows

### Problem: Hotfixing a Release Workflow

When a release workflow fails after tagging:

1. You identify a bug in the workflow YAML
2. You fix it and push to main
3. You re-run the workflow from the tag
4. **It fails the same way** - using the old workflow from the tag

### Solution: Move the Tag

To use a fixed workflow for an existing tag:

```bash
# 1. Delete the remote tag
git push origin :refs/tags/v1.0.0

# 2. Delete local tag
git tag -d v1.0.0

# 3. Push the fix to main
git push origin main

# 4. Recreate tag pointing to new HEAD
git tag -a v1.0.0 -m "v1.0.0"
git push origin v1.0.0
```

**Warning**: Moving tags that have been published can cause issues:

- Go modules cache the tag's commit SHA
- Container registries may have cached images
- Users may have pinned the old SHA

### Alternative: New Patch Release

For published releases, prefer creating a new version:

```bash
# Instead of moving v1.0.0, create v1.0.1
git push origin main
git tag -a v1.0.1 -m "v1.0.1: workflow fix"
git push origin v1.0.1
```

## Workflow File Location

The workflow file must exist at `.github/workflows/<name>.yml` in the source ref. GitHub validates:

1. File exists at expected path
2. YAML is valid
3. Workflow syntax is correct

If the workflow file doesn't exist in the tagged commit, the workflow cannot run from that tag.

## Multi-Stage Release Patterns

For releases with multiple workflows (build → sign → publish):

```
main: A ─── B ─── C ─── D (Go bindings merge) ─── E (workflow fix)
                        │
                        └── v1.0.0 (tag)

Problem: v1.0.0 doesn't include commit E's workflow fix
```

**Best practice**: Complete ALL workflow testing before tagging:

1. Push all code changes to main
2. Run test workflows on main
3. Fix any issues, push to main
4. Tag only after workflows pass on main
5. Run release workflows from tag

## Debugging Version Issues

### Check which commit a tag points to:

```bash
git rev-parse v1.0.0
# or for annotated tags:
git rev-parse v1.0.0^{}
```

### Check workflow file at a specific ref:

```bash
git show v1.0.0:.github/workflows/release.yml
```

### Compare workflow versions:

```bash
git diff v1.0.0:.github/workflows/release.yml main:.github/workflows/release.yml
```

### Check workflow run's commit:

In GitHub Actions logs, look for:

- `head_sha` in environment variables
- The checkout step shows the commit being checked out

## Related

- [Release Rollback Procedure](release-rollback.md) - Full procedure for release do-overs
- [npm OIDC Publishing](../registry/npm-oidc.md) - npm-specific considerations
