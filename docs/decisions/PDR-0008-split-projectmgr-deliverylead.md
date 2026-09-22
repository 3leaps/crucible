---
id: "PDR-0008"
title: "Split projectmgr and deliverylead on the governance timeline"
status: "proposed"
date: "2026-09-22"
last_updated: "2026-09-22"
deciders:
  - "@3leapsdave"
  - "cxotech"
scope: "Crucible foundation / reusable agentic role catalog"
tags:
  - "process"
  - "roles"
  - "governance"
  - "agentic"
relates-to:
  - "PDR-0003 role portfolio tiering"
  - "PDR-0007 curate role catalog"
  - "crucible config/agentic/roles/ (the role catalog this splits)"
---

# PDR-0008: Split projectmgr and deliverylead on the governance timeline

## Status

**Proposed.** Revises PDR-0007 §4's deprecation of `deliverylead`.

## Context

PDR-0007 folded project control into a new `projectmgr` seat and deprecated
`deliverylead` because the earlier role coupled tasking to projectbook, sprint,
WIP, and velocity assumptions that are not universal.

Subsequent operating use showed four distinct horizons on the sitting
governance stack:

- `dispatch`: minutes–days session routing and handoff
- `projectmgr`: days–program standing program and panel chair
- `deliverylead`: sprint–quarter projectbook, WIP, capacity, and ship forecast
- `cxotech`: path, ADR, and directional conflict

Sibling organization catalogs still publish `deliverylead` and do not publish
`projectmgr`. The 3leaps catalog is the canonical source for the split.

## Decision

1. Keep `projectmgr` as a supplemental draft role: the default chair for
   standing program and panel threads. It is outcome-aware and does not become
   `cxotech`.
2. Restore `deliverylead` as an approved supplemental role for projectbook
   delivery governance. It is not a migration alias for `projectmgr`.
3. Keep `dispatch` thin: session routing and handoff only.
4. Escalate to `cxotech` only for path, ADR, or conflict.
5. Document the four-row governance timeline in the role catalog.

Tier remains default adoption guidance per PDR-0003. Both `projectmgr` and
`deliverylead` stay `supplemental`.

## Consequences

### Positive

- Adopters can chair standing threads without adopting projectbook process.
- Adopters who need WIP, capacity, or ship forecast keep `deliverylead`.
- PDR-0007's other curations (`qa`, `cicd`, authority/outputs, core spine) stand.

### Costs

- Downstream catalogs that already migrated `deliverylead` → `projectmgr` need
  a second, smaller remap: panel chairing stays on `projectmgr`; projectbook
  work returns to `deliverylead`.

## Acceptance

- `projectmgr.yaml` and `deliverylead.yaml` validate against the role-prompt
  schema.
- Catalog indexes list both as supplemental with distinct purposes.
- Distinct-from blurbs separate `projectmgr`, `dispatch`, `deliverylead`, and
  `cxotech`.

## Revision History

| Date       | Status Change | Summary                                                   | Updated By |
| ---------- | ------------- | --------------------------------------------------------- | ---------- |
| 2026-09-22 | → proposed    | Split panel chairing from projectbook delivery governance | infoarch   |
