---
id: "PDR-0007"
title: "Curate the role catalog around proven decision boundaries"
status: "accepted"
date: "2026-08-19"
last_updated: "2026-08-19"
deciders:
  - "@3leapsdave"
  - "cxotech"
  - "entarch"
scope: "Crucible foundation / reusable agentic role catalog"
tags:
  - "process"
  - "roles"
  - "governance"
  - "agentic"
relates-to:
  - "PDR-0003 role portfolio tiering"
  - "role-prompt schema v0"
---

# PDR-0007: Curate the role catalog around proven decision boundaries

## Status

**Accepted.**

## Context

The initial role catalog established a reusable vocabulary, but downstream use
revealed three different outcomes:

1. Roles with a clear decision boundary and output became durable operating
   seats.
2. Broad roles without distinct authority overlapped more effective roles.
3. Organization-specific copies drifted from the baseline despite sharing role
   slugs.

The catalog also needs roles for bounded monitoring, analytical evidence,
strategy consulting, project control, user experience, and data systems.

## Decision

### Relationship to PDR-0003

This decision updates PDR-0003's portfolio assignments. It retains PDR-0003's
tier semantics: tiers remain default adoption guidance, not a measure of
authority or a mandate for downstream repositories.

### 1. Preserve the core spine

Keep `devlead`, `devrev`, `secrev`, and `cxotech` as core.

### 2. Establish the product/technology pair

For long-running systems:

- `cxotech` is the product-side actor: problem choice, user value, bets, and priority.
- `entarch` is the technology-side actor: boundaries, contracts, compatibility,
  and architectural integrity.

They are peers with distinct domains. Consequential commitments remain subject
to human approval.

### 3. Add proven and newly required supplemental roles

- Promote `uxdev` as the reusable user-experience implementation role.
- Strengthen `dataeng` as a generic data architecture and operations role.
- Add draft `watcher`, `analyst`, `strategist`, `delegate`, `secops`, and
  `projectmgr`.
- Define `delegate` as principal-facing privileged assistance whose information,
  action, and disclosure authority comes only from explicit compartmented grants.
- Define `secops` as asset-facing privileged operation and curation under
  explicit custodianship grants, separate from independent `secrev` review.
- Clarify `dispatch` as an estate exchange operator and coordination-tool steward,
  not a project manager.

### 4. Retire overlapping roles

- Deprecate `qa`; use `devrev` for independent review, `devlead` for test
  implementation, and task briefs for acceptance criteria.
- Retain deprecated `cicd`; routine automation belongs to `devlead`, with
  `releng` reserved for complex release systems.
- Deprecate `deliverylead`; use `projectmgr` for reusable project control.

### 5. Make authority and outputs explicit

Require portfolio `tier` and permit structured `outputs`, `authority`, and
`replaced_by` metadata in the experimental role schema.

### 6. Keep one canonical full catalog

Reusable full prompts live here. Adopters reference or vendor pinned prompts.
In `v0`, `extends` records provenance only and does not imply merge semantics.

## Consequences

### Positive

- Role selection follows demonstrated decision boundaries rather than an
  equal-weight list.
- Monitoring, evidence, strategy, project control, product direction, and
  technical coherence no longer collapse into general coordination.
- Downstream catalogs have a clear migration path toward a single baseline.

### Costs

- Downstream vendored schemas and prompts must move together.
- Draft roles need practical review before approval.
- A future overlay resolver, if justified, requires a separate contract.

## Acceptance

- All canonical prompts validate.
- Each active role names outputs, authority, escalation, and exclusions.
- Deprecated roles name their replacements.
- Catalog documentation no longer recommends `qa` as an additional review stage.
- Downstream migrations remain explicit and independently reviewable.

## Revision History

| Date       | Status Change | Summary                                                                                 | Updated By  |
| ---------- | ------------- | --------------------------------------------------------------------------------------- | ----------- |
| 2026-08-19 | → accepted    | Curate the role catalog and update PDR-0003 portfolio assignments while retaining tiers | @3leapsdave |
