---
id: "ADR-0008"
title: "Portable Project Work as a Companion Contract"
status: "proposed"
date: "2026-08-21"
last_updated: "2026-08-21"
deciders:
  - "@3leapsdave"
scope: "Crucible foundation / project-work contracts"
tags:
  - "schemas"
  - "project-work"
  - "tasking"
  - "interchange-contract"
relates-to:
  - "crucible ADR-0001 (schema/config versioning — the promotion gate)"
  - "crucible ADR-0006 (process-run — companion-contract and event-envelope precedent)"
  - "docs/standards/data-artifact-contract.md (published ledger representations)"
---

# ADR-0008: Portable Project Work as a Companion Contract

## Status

**Current Status**: Proposed — the contract enters its own review and adoption
lane at `v0`. Promotion to a stable version follows ADR-0001 and requires a
proven downstream producer and consumer.

## Context

Repositories and tools need to exchange bounded work without importing a
particular board, scheduler, database, or project-management product. The
shared minimum is broader than a task title and status string:

- an executable packet needs an outcome, accountable owner, acceptance
  criteria, dependencies, and escalation;
- project leadership needs an inspectable project projection without embedding
  a recursive task tree;
- status, blockers, and decisions need portable records;
- consumers need an ordered progress ledger whose lifecycle transitions can be
  projected deterministically.

Keeping these shapes product-local would create incompatible task dialects.
Making a product runtime canonical would also force adopters to install an
unrelated tool merely to validate a work packet. A prose convention alone
would not give producers and consumers an executable compatibility surface.

## Decision

Establish `contract: project-work/v0` as a companion portable contract family
in Crucible:

- `docs/standards/project-work-contract.md` is the normative standard.
- `schemas/project-work/v0/contract.json` is the capability manifest.
- `ready-packet.schema.json` is the entry schema and dispatchable root.
- `project-state.schema.json` is an inspectable project projection.
- `control-record.schema.json` represents status, blocker, and decision
  records.
- `progress-event.schema.json` represents one ordered NDJSON ledger line.

The family uses the same hostless capability-resolution posture as the other
portable contracts. Schema publication URLs are retrieval locations, not
instance identity.

### One family, four governed objects

The packet, project projection, control record, and progress event version
together under one capability. They describe different views of the same work
domain and share identity, lifecycle, ownership, and classification semantics.
Splitting them into independently versioned families would allow those shared
semantics to drift.

### Flat work, sibling projects

Work packets are flat. Dependencies are explicit edges; recursive
`children[]` and parent-task containment are outside the portable floor. A
project is a sibling object referenced by identity, not a task that contains
other tasks. Products may render hierarchy, columns, milestones, or grouping,
but those views do not change the interchange taxonomy.

### Semantic lifecycle, not board columns

Packets and projects use the closed lifecycle classes:

`draft | ready | active | blocked | review | done | cancelled`

These are portable meanings, not UI column names. Product-specific states map
onto them. Dispatch readiness and acceptance requirements are defined by the
standard rather than inferred from a column label.

### Portable ownership and escalation

A packet has one accountable owner expressed as a person, role, or explicitly
unassigned actor. Ready work cannot be unassigned. Role identities follow the
portable role-slug shape; the contract does not enumerate one organization’s
seats or human directory.

### Deterministic, store-neutral progress

The progress ledger is append-only NDJSON. Every event identifies exactly one
packet or project, carries an actor and per-subject sequence, and gives
unambiguous lifecycle-transition data. Timestamps describe occurrence time;
they are not ordering or deduplication keys.

The contract does not select a database. Implementations may project the
ledger into local SQL, analytical tables, columnar artifacts, or other query
stores. When a ledger is published as a data product, the data-artifact
contract governs the published bag while `progress-event` remains the line
contract.

### Reuse classifier dimensions

Packets and projects may carry the existing sensitivity, access-tier, and
retention-lifecycle classifier keys. Sensitivity and access tier travel as a
compatible pair. This family does not mint work-specific copies of those
dimensions.

### Product overlays remain downstream

Boards, timers, sprint identifiers, wait-state machinery, query engines,
product frontmatter, and persistence layouts remain implementation concerns.
They may extend or map to this floor but do not become alternate sources of
truth for the portable contract.

## Relationship to Other Contracts

- `process-run/v0` describes execution telemetry and live process control; it
  does not replace a work packet or project projection.
- `data-artifact/v0` describes a published ledger representation; it does not
  replace the event-line schema.
- `review-journal/v0` describes relied-upon review evidence; it does not become
  the general work ledger.
- `agent-wait/v0` describes waiting and wake outcomes; live wait state remains
  outside a work packet.

## Consequences

- Repositories can emit and validate ready work before adopting a project
  runtime.
- Tools gain one mapping target instead of defining competing task vocabularies.
- Flat identity and typed references make packets portable across storage and
  presentation models.
- Deterministic events support loss detection, replay, and downstream
  projections.
- Consumers still enforce cross-record rules, such as blocked work requiring
  an open blocker and completed work requiring a terminal lifecycle
  transition. Structural schema validation alone does not prove those set
  invariants.
- The `v0` family may change while adoption reveals gaps; consumers must pin a
  reviewed revision until a stable version is promoted.

## Alternatives Considered

### Make a project-management product the canonical home

Rejected. A runtime may implement the contract, but portable validation must
not require installing that runtime or importing its product-specific fields.

### Use one recursive task/project object

Rejected. Combining packet and project semantics invites recursive containment,
ambiguous ownership, and product-specific hierarchy into every consumer.

### Standardize a database or board model

Rejected. Storage engines and UI columns have different portability and
evolution constraints from the interchange contract.

### Keep the agreement as prose only

Rejected. Producers and consumers need machine-readable validation for the
closed envelope, lifecycle, ownership, and reference rules.

## Review-loop Items

1. Whether Crucible should provide a reference validator for cross-record
   journal-set invariants in addition to structural schema controls.
2. Whether a later stable version requires a first-class published-ledger
   profile beyond the existing data-artifact bridge.
