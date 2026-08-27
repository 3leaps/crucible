---
title: "Portable Project Work Contract"
description: "Source-neutral contract for ready-work packets, project state, control records, and an append-only NDJSON progress ledger"
category: "standards"
status: "draft"
version: "0.0.0"
lastUpdated: "2026-08-21"
maintainer: "core-standards"
reviewers: ["architecture", "project-management"]
approvers: ["lead-maintainer"]
tags: ["project", "task", "contract", "ledger", "interoperability"]
content_license: "CC0"
relatedDocs:
  - "docs/standards/process-run-contract.md"
  - "docs/standards/data-artifact-contract.md"
  - "docs/standards/classifiers-framework.md"
audience: "implementers"
---

# Portable Project Work Contract

This draft defines the portable contract identified by
`contract: project-work/v0`.

The contract describes **ready work** and **project state** so a downstream
consumer can dispatch a bounded packet, inspect a project projection, append
progress as NDJSON, and honor classification without knowing which product
board or store produced the records.

This is not a kanban product, a session checkpoint, a mission runner, an
attribution ledger, or a data-pipeline grain. Producers keep native boards
and caches. The portable contract governs the envelopes that travel between
orgs: the packet, the project projection, the control record, and the
progress-event line.

## Design Stance

- **Flat work items.** Packets have no parent/child tree. Dependencies are
  edges. A project is a sibling object, not a parent task.
- **Semantic classes, not columns.** `lifecycle_class` is a closed set.
  Board column strings are producer-local mappings.
- **One accountable owner.** `unassigned` cannot be `ready`.
- **Payload-open events.** Progress-event `data` is producer-owned; the
  envelope and core kinds are closed.
- **Store-neutral ledger.** The contract line is NDJSON. Consumers may
  project to Parquet, DuckDB, WASM, or a local cache. A local SQL file is
  not the contract.
- **Sterile identity.** Opaque `id`, optional `scope` and `slug`. Instance
  prefixes are local convention, not a schema enum.

## Capability And Versioning

Ready packets and project-state documents MUST carry the capability token:

```json
{
  "capabilities": ["contract: project-work/v0"]
}
```

The L2 entry point is `schemas/project-work/v0/contract.json`. Consumers
resolve `contract: project-work/v0` to that manifest and load
`entry_schema` (`ready-packet.schema.json`).

Path versioning follows ADR-0001 (`v0/` is unstable).

## Objects

| Object         | Schema                       | Role                         |
| -------------- | ---------------------------- | ---------------------------- |
| Ready packet   | `ready-packet.schema.json`   | Dispatchable unit            |
| Project state  | `project-state.schema.json`  | Inspectable projection       |
| Control record | `control-record.schema.json` | Status, blocker, or decision |
| Progress event | `progress-event.schema.json` | One NDJSON ledger line       |

### Lifecycle class

Closed set on packets, projects, and `class-changed` events:

`draft` | `ready` | `active` | `blocked` | `review` | `done` | `cancelled`

| Value       | Dispatch?                                   |
| ----------- | ------------------------------------------- |
| `draft`     | No                                          |
| `ready`     | Yes                                         |
| `active`    | Already dispatched                          |
| `blocked`   | No                                          |
| `review`    | No (executor claims complete; not accepted) |
| `done`      | Terminal                                    |
| `cancelled` | Terminal                                    |

**Dispatchable-packet rule.** On a **ready packet**, classes `ready`,
`active`, `review`, and `done` require `owner.kind` ≠ `unassigned` and at
least one acceptance criterion. `draft`, `blocked`, and `cancelled` may
have an empty `acceptance` array. This rule applies to packets only.

**Project-state rule.** A project uses the same `lifecycle_class` vocabulary.
It does **not** carry `acceptance`. `owner` is optional. A project is an
inspectable projection, not a dispatchable packet.

**Milestone dates.** `project-state.milestones[].target` is an ISO-8601
full date (`YYYY-MM-DD`). The schema asserts both the pattern and
`format: date`, so impossible dates (for example `2026-99-99`) are
rejected.

### Owner

```json
{ "kind": "person" | "role" | "unassigned", "id": "…", "display": "…" }
```

`person` and `role` require `id`. When `kind` is `role`, `id` MUST match
the role-prompt slug shape: `^[a-z][a-z0-9]*$`, length 2–16 (no hyphens).
Do not catalog humans in the schema. `unassigned` MUST omit `id` and
`display`.

`escalation.default` (packets only) is the same role-slug shape — not a
closed list of one org's seats. Instance files may use those slugs; the
schema must not require them.

### Progress event kinds

`created` | `class-changed` | `reopened` | `blocked` | `unblocked`

There is no `completed` kind. Completion is `class-changed` with
`data.to` = `done`. Each event names exactly one of `packet_id` or
`project_id`. `seq` is required: monotonic per subject; it is the ledger
order key. Timestamp is not a ledger key.

| kind            | Authoritative transition                | Required `data`                                                                                          |
| --------------- | --------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `created`       | Birth of the subject                    | `lifecycle_class` (initial class); MUST NOT carry `from` or `to`                                         |
| `class-changed` | Any other class→class not covered below | `from`, `to` (`from` ≠ `to`; `from` not terminal; not a block/unblock); MUST NOT carry `lifecycle_class` |
| `reopened`      | Terminal → open                         | `from` ∈ {done, cancelled}, `to` ∈ {draft, ready}; MUST NOT carry `lifecycle_class`                      |
| `blocked`       | Open → blocked                          | `from` ∈ {draft, ready, active, review}, `to` = blocked; MUST NOT carry `lifecycle_class`                |
| `unblocked`     | blocked → open                          | `from` = blocked, `to` ∈ {draft, ready, active, review}; MUST NOT carry `lifecycle_class`                |

### Control records

`kind` is `status` | `blocker` | `decision`. Status notes do not change
class and MUST NOT carry `waiting_on`, `decider`, `open`, or `affects`.
Blockers require `waiting_on` (opaque), may carry `open`, and MUST NOT
carry `decider` or `affects`. Decisions require `decider` (person or role
— never `unassigned`) and `affects` (a non-empty, unique list of the
packet or project ids the decision governs) and MUST NOT carry
`waiting_on` or `open`. Every record requires `actor` and exactly one of
`packet_id` or `project_id`.

## Journal-set rules (consumer-enforced)

These rules span multiple records. Structural `make check` does **not**
prove them. Consumers MUST enforce:

1. A subject with `lifecycle_class` `blocked` has at least one control
   record with `kind=blocker` and `open` not false.
2. `done` is claimed by a `class-changed` event to `done`, not by activity
   prose.
3. A packet in `done` MUST NOT `depends_on` a packet that is not `done` or
   `cancelled`.
4. Additional properties on governed envelopes fail closed. Event `data`
   may carry extra producer keys beside the required transition fields.
   Extra keys MUST NOT be reserved core transition keys of another
   discriminant (`lifecycle_class` vs `from`/`to`).

## Classifiers

When a `classifiers` object is present on a packet, project, or published
ledger grain, `sensitivity` and `access-tier` are required (keys from the
existing classifier dimensions). `retention-lifecycle` is optional.

`unknown` is valid only as a pair (both dimensions unknown, or neither).
`access-tier` MUST meet the minimum for `sensitivity` in
`docs/standards/access-tier-classification.md`. Inlined schema enums MUST
match `config/classifiers/dimensions/*` (the control script checks this).

Do not attach `volume-tier`, `velocity-mode`, or `volatility` to a single
packet. Those classify a published ledger grain under the data-artifact
contract, not a task.

Optional `priority` on a packet is `p0` | `p1` | `p2` | `p3`. It is not a
classifier dimension.

## Relationship To Other Contracts

- **process-run** — local process telemetry. Do not encode a packet as a
  process card.
- **data-artifact** — when a progress ledger is **published** (not a private
  cache), wrap it with `contract: data-artifact/v0`. Representations:
  NDJSON (interchange) and optional Parquet (compact). Query
  (DuckDB/WASM) is a consumer, not this contract. Hang `volume-tier` /
  `velocity-mode` / `volatility` on **that artifact**, never on a single
  packet. `progress-event` remains the line; data-artifact is the
  published bag. Do not invent a second ledger wrapper.
- **review-journal** — relied-upon review events. Not the work ledger.
- **agent-wait** — live wait/poll. Not a packet field.
- **forge-infra** — forge issues may project or provide an interaction lane
  for project work, but a provider-native issue is not automatically a
  portable work packet or the authoritative progress ledger.

## Out Of Scope For v0

Board columns, timers, nested tasks, sprint identifiers as required fields,
and product-specific wait-state.

## Schema identity

The contract identity is the host-less capability token
`contract: project-work/v0`. Schema `$id` values are
`contract:project-work/v0/<file>`. Instances MUST NOT embed a schema host
as identity.

## Publication / registry URL

A hosted documentation or registry URL (for example
`https://schemas.3leaps.dev/project-work/v0/ready-packet.schema.json`) is
a retrieval convenience for humans and tooling. It is **not** the
capability token and **not** the schema `$id`. Same posture as
`process-run/v0`.
