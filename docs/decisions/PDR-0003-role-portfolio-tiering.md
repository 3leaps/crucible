---
id: "PDR-0003"
title: "Role portfolio tiering: core spine, supplemental, deprecated"
status: "accepted"
date: "2026-06-29"
last_updated: "2026-06-29"
deciders:
  - "@3leapsdave"
  - "cxotech"
scope: "Crucible foundation / shared governance — agentic role catalog"
tags:
  - "process"
  - "roles"
  - "governance"
  - "agentic"
relates-to:
  - "crucible decision-records.md (the *DR taxonomy; PDR type)"
  - "crucible config/agentic/roles/ (the role catalog this tiers)"
  - "crucible ADR-0001 (v0 schema may evolve; the additive tier field)"
---

# PDR-0003: Role portfolio tiering

## Status

**Accepted.**

## Context

The agentic role catalog grew to twelve roles, but real-world use shows they are not
equal-weight. A few are run on essentially every project; most are situational; and at
least one did not earn its place in practice. Two consequences followed: the practical
overlap between an always-needed strategic role and a large-scale-only delivery role
read as "ambiguity," and a role that tested poorly stayed nominally `approved`. The
catalog needs to express **which roles are the default starting point** versus which are
opt-in — as default _guidance_ that downstream repos (which copy or subsume this catalog)
inherit by default but may freely override.

## Decision

### 1. Introduce a role **tier**: `core`, `supplemental`, `deprecated`

Add an optional `tier` field to the v0 role-prompt schema and set it on every role. Tier
is a **default that propagates** with the role definition (a repo that subsumes the
catalog inherits it) and is **guidance, not a mandate** — an adopting repo may re-tier
(e.g. make another role core). It is orthogonal to `status`: a `supplemental` role is
still fully `approved` and usable.

### 2. Core — the always-on default spine

**`devlead`, `devrev`, `secrev`, `cxotech`.** Implementation + four-eyes review +
security review + the strategic fulcrum (brief/ADR approval, tie-breaks) are the baseline
discipline a project runs by default — the role analogue of "always have devlead." At
current project scale, `cxotech` also absorbs the day-to-day delivery coordination that a
dedicated delivery role would own at larger scale (see §4).

### 3. Supplemental — adopt by need

**`qa`, `infoarch`, `dataeng`, `releng`, `prodmktg`, `dispatch`, `deliverylead`.** Added
when scale or complexity warrants — e.g. `releng` for gnarly release/versioning,
`deliverylead` for large multi-sprint coordination via projectbook, `dataeng` for data
pipelines.

### 4. Deprecated — `cicd`

Real-world testing showed `cicd` did not earn its place; complex CI/CD is better handled
by **`releng` supplementing `devlead`** (e.g. very complex pipelines or live
"must-run-locally" test coordination). Mark `cicd` `status: deprecated`, `tier:
deprecated`, and retain it (not delete) so the lesson is recorded rather than re-learned.

### 5. Promote the two completed governance roles

`cxotech` → `approved` (core) and `deliverylead` → `approved` (supplemental), after
cxotech review of the prodmktg-authored definitions. This also makes the `cxotech`
decider slug resolvable on the advertised catalog.

### 6. Amendment: add `entarch` as supplemental

As a follow-up to the initial tiering decision, add `entarch` as an approved
supplemental governance role. The catalog now carries thirteen baseline roles. `entarch`
is supplemental because it is cross-repo and cross-layer in scope rather than something
every repository needs by default.

`entarch` is distinct from `cxotech`: `cxotech` owns product-architecture trade-offs and
feature/ADR decision authority; `entarch` owns ecosystem architecture coherence, parity,
propagation, compatibility, and release-order constraints across repositories.

## Consequences

**Positive**

- A clear, propagating default starting point: adopters get a sensible spine out of the
  box and tune from there.
- The `cicd` lesson is preserved in-place rather than lost.
- `cxotech`/`deliverylead` are resolvable on the public catalog; the
  cxotech↔deliverylead "ambiguity" is resolved (cxotech is core and covers delivery
  coordination at current scale; deliverylead is the opt-in role for larger scale).

**Negative / costs**

- An additive `tier` field on the v0 schema (backward-compatible; v0 may evolve per
  ADR-0001).
- The in-yaml tier is a default that can drift from a downstream repo's actual usage if
  they do not re-tier — acceptable, since it is explicitly guidance.

## References

- [Decision & Governance Records — the `*DR` family](../repository/decision-records.md) — defines PDR
- [Role catalog](../catalog/roles/README.md) — advertised, tier-grouped
- [ADR-0001: Schema and Config Versioning](ADR-0001-schema-config-versioning.md) — v0 evolution

## Revision History

| Date       | Status Change | Summary                                                            | Updated By |
| ---------- | ------------- | ------------------------------------------------------------------ | ---------- |
| 2026-06-29 | → accepted    | Tier the role portfolio; promote cxotech/deliverylead; retire cicd | cxotech    |
| 2026-07-02 | accepted      | Add entarch as supplemental ecosystem architecture role            | cxotech    |
