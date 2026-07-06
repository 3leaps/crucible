---
id: "PDR-0002"
title: "One git worktree per concurrent task"
status: "accepted"
date: "2026-06-29"
last_updated: "2026-06-30"
deciders:
  - "@3leapsdave"
  - "devlead"
scope: "Crucible repository working practice"
tags:
  - "process"
  - "git"
  - "worktrees"
  - "concurrency"
relates-to:
  - "crucible decision-records.md (the *DR taxonomy that defines the PDR type; filed after the genesis ADR-0003)"
  - "crucible docs/repository/secure-commits.md (public-surface discipline this practice protects)"
---

# PDR-0002: One git worktree per concurrent task

## Status

**Accepted.** A Process Decision Record filed under the
[`*DR` taxonomy](../repository/decision-records.md) (ratified by ADR-0003).

## Context

More than one agent or person can work this repository at the same time. When
two streams share a **single working clone**, they share one `HEAD` and one
index. A branch switched by one stream silently moves the ground under the
other: edits made against one branch get committed onto another, and a broad
`git add` can sweep an unrelated stream's working-tree files into the wrong
commit. Both failure modes are easy to miss because each command, viewed alone,
succeeds.

This is not hypothetical. A concurrent stream switching the shared clone's
branch mid-task produced exactly this: a commit landed on the wrong branch, and
a `git add -A` pulled another stream's in-progress file into an unrelated
change that then reached a public branch. Recovery was possible but cost a
history rewrite and a force-push — friction on a world-readable surface that the
work never needed to touch.

## Decision

**Each concurrent task gets its own `git worktree`.** A shared working clone
carries at most one active task at a time.

- Create a task's worktree with `git worktree add <path> <branch>`; remove it
  with `git worktree remove <path>` when the task is done.
- A long-lived or background stream (review, release prep, an agent left
  running) **must** operate in its own worktree, never by switching the branch
  of a clone another stream is using.
- Prefer **scoped staging** (`git add <paths>` / `git add -p`) over `git add -A`
  so a commit can only contain files the task deliberately touched. `git add -A`
  in a shared tree is how unrelated files travel.
- Worktree directory names are local and OOB — they may carry task codes; the
  rule in [secure-commits](../repository/secure-commits.md) still governs what
  reaches commits, branches, and PRs.

## Consequences

**Positive**

- Concurrent streams cannot collide on a shared `HEAD` or index; a branch switch
  in one worktree is invisible to the others.
- Commits contain only their task's files — the cross-contamination path is
  closed at the source, not patched after it reaches a public branch.
- Fewer history rewrites and force-pushes on public branches, keeping
  world-readable history clean by default.

**Negative / costs**

- A little more disk and one extra setup/teardown step per task.
- Worktrees must be cleaned up (`git worktree prune` / `remove`) so stale ones
  do not accumulate.

## References

- [Decision & Governance Records — the `*DR` family](../repository/decision-records.md) — defines PDR, the type of this record
- [Secure Commit Policy](../repository/secure-commits.md) — the public-surface discipline this practice protects
- `git worktree` — Git documentation
