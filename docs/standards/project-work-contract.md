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
{ "kind": "person" | "role" | "unassigned" | "agent" | "run", "id": "…", "display": "…" }
```

`agent` and `run` are covered under
[Agent and run parties](#agent-and-run-parties). On a ready packet the owner
may be any of the five kinds. A project-state `owner` may be person, role,
unassigned, or `agent`; it is never a `run`, since a project outlives any one
run.

`person` and `role` require `id`. When `kind` is `role`, `id` MUST match
the role-prompt slug shape: `^[a-z][a-z0-9]*$`, length 2–16 (no hyphens).
Do not catalog humans in the schema. `unassigned` MUST omit `id` and
`display`.

**Person id.** When `kind` is `person`, `id` MUST match
`^[a-z][a-z0-9._-]{0,63}$` and MUST NOT start with `agent-` or `run-`
(those prefixes are reserved for agent seats and runs). This one definition
applies to every person id in `project-work/v0`: packet `owner` and
`requested_by`, project-state `owner`, ledger `actor`, `decider`, and a run's
`parent`. The schema still carries no catalog of people.

Handles are stored without `@`: use `maintainer-1`, not `@maintainer-1` (the `@`
is display punctuation and fails the pattern). Emails are not person ids; an
adopter maps an email to a handle in its own identity source before writing a
record.

**Compatibility and migration (`person-id` tightening within `v0`).** Earlier
`project-work/v0` revisions accepted any non-empty `person` `id` up to 128
characters; tightening `person-id` to `^[a-z][a-z0-9._-]{0,63}$` and reserving
`agent-` and `run-` rejects previously valid strings such as `@maintainer-1`,
`human@example.test`, `Human1`, `agent-human`, or 65-character ids. Adopters with
existing data outside this pattern SHOULD keep the prior schema commit pinned
until they establish an explicit, collision-checked identity-source mapping to
lowercase handles (do not blindly strip `@`/email domains or lowercase strings
in place without checking for collisions), and SHOULD validate historical
append-only ledger segments against the schema revision pinned when those
segments were written.

`escalation.default` (packets only) is the same role-slug shape — not a
closed list of one org's seats. Instance files may use those slugs; the
schema must not require them.

### Requested by and check-by

Both are optional on a ready packet and let a producer express a promise made
to someone, without a second schema.

`requested_by` names who asked for the work or is owed it:

```json
{ "kind": "person" | "role" | "agent", "id": "…", "display": "…" }
```

It has the owner shape without `unassigned` and without `run`: `id` is
required, and a `role` id MUST match the role-prompt slug shape. An `agent`
requester also carries `role`. A `run` is never a requester: a request is owed
to a durable party, and a run ends. The owner stays the one accountable party;
`requested_by` is the counterparty and carries no accountability.

`check_by` is a strict RFC 3339 instant by which the owner is next expected to
report status or acknowledge the packet. It requires a `T` time part and `Z` or
a numeric UTC offset, enforced by a pattern alongside `format: date-time`: a
date-only value is ambiguous across time zones and is rejected. (`updated`
keeps plain `format: date-time`.) It is a check-in time, not a completion
deadline, and it does not change `lifecycle_class`. The schema
validates the shape only. Scheduling a wake or reminder for `check_by` is the
consumer's job, and a consumer MAY ignore it on `done` and `cancelled`
packets.

### Agent and run parties

Hosted agents are named parties. Two further kinds extend the party record used
by `owner` and (for `agent` only) `requested_by`. Adding `agent`, `run`,
`requested_by`, and `check_by` is additive within `v0`, while the shared
`person-id` handle pattern above tightens `person` `id` validation within
unstable `v0` (no version bump).

```json
{ "kind": "agent", "id": "agent-seat-router", "role": "dispatch", "display": "…" }
{ "kind": "run", "id": "run-01JC8Z3K5M7Q4W9XBTN2VYE6RD", "parent": "agent-seat-builder",
  "expires": "2026-11-01T23:00:00Z", "role": "devlead" }
```

**`agent`** is a durable seat: the same party across many packets and days.

- `id` is a seat id matching `^agent-[a-z0-9]+(-[a-z0-9]+)*$`, length 3–64
  (for example `agent-seat-alpha`).
- `role` is required and uses the same role-prompt slug shape as a `role`
  party id (`^[a-z][a-z0-9]*$`, length 2–16, no hyphens). It is the hat the
  seat wears **for this work**, not a property of the seat: one seat may wear
  different roles on different packets.
- `display` is optional, as for person and role.
- Whether the seat is an agent, how it is hosted, and what it may do
  (`seat_kind`) live in the adopter's **seat registry** (the seat manifest),
  not in this contract. The party
  record names the seat and the hat; it does not describe the seat.

**`run`** is one bounded execution acting for a parent: a delegated session,
job, or sub-agent invocation. It is not a seat and has no standing of its own.

- `id` is `run-` plus a 26-character ULID in canonical **uppercase**
  Crockford base32 (`^run-[0-7][0-9A-HJKMNP-TV-Z]{25}$`). The first ULID
  character is `0`–`7` because the 48-bit timestamp tops out at `7ZZZZZZZZZ`;
  lowercase is not accepted.
- `parent` is required: an agent seat id (`agent-…`) or a person id, the party
  the run acts for. The schema models it as `anyOf` agent id or person id, so
  another run cannot be a `parent` (the `run-` prefix matches neither), runs
  cannot chain, and values with a leading space, an uppercase prefix, or an
  embedded space or newline fail.
- `expires` is required: a strict RFC 3339 instant, the same definition as
  `check_by` (`T` time part with `Z` or a numeric offset; a date alone is
  rejected).
- `role` is optional, with the same slug shape. When omitted, a run inherits its
  parent's work role only if the consumer holds an unambiguous work-role binding
  for that parent on the packet; otherwise expiry reassignment falls through to
  `escalation.default` or operator handling (see `SEM-P02`).
- `display` is optional.
- **Immutable run binding (`SEM-P07`):** A `run` `id` identifies one bounded
  execution; its `(parent, expires, role)` binding is fixed at creation/first
  observation and MUST NOT be mutated across packets or ledger lines. Renewing
  or extending work beyond `expires` requires issuing a new `run` `id`.
  Structural validity or a resolving seat/parent records provenance shape only
  and does not grant execution or delegation authorization.

**Agent versus run.** Use `agent` when the work belongs to a seat that
persists and answers for it. Use `run` when a particular execution holds the
work for a short time and the seat or person behind it stays accountable.
When the run ends or `expires` passes, ownership is not silently the run's any
longer; see the semantic rules below. A packet owned by a run requires
`check_by` (the schema enforces presence; SEM-P05 enforces that it falls before
`expires`), except in `done` and `cancelled`.

**Where each kind may appear.**

| Kind         | packet `owner` | `requested_by` | project `owner` | ledger `actor` | `decider` |
| ------------ | -------------- | -------------- | --------------- | -------------- | --------- |
| `person`     | yes            | yes            | yes             | yes            | yes       |
| `role`       | yes            | yes            | yes             | yes            | yes       |
| `unassigned` | yes            | no             | yes             | no             | no        |
| `agent`      | yes            | yes            | yes             | yes            | yes       |
| `run`        | yes            | no             | no              | yes            | no        |

Ledger `actor` is the `actor` of a progress event or control record. A `run`
actor carries `parent` and `expires` like a run owner, so a ledger line stays
attributable after the run ends. A `decider` is never a run: a decision outlives
the run that records it.

`agent` and `run` are closed shapes: `agent` rejects `parent` and `expires`;
`person`, `role`, and `unassigned` reject `role` (as a property), `parent`, and
`expires`. `check_by` addresses the owner and is an instant on the packet; the
schema models no separate check-by owner, so no further `run` exclusion exists
there.

The schema checks shape only. Cross-document checks are consumer
responsibilities and are listed in
[`schemas/project-work/v0/semantic-validation.md`](../../schemas/project-work/v0/semantic-validation.md).
Consumers MUST run them.

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
carry `decider` or `affects`. Decisions require `decider` (person, role, or
agent — never `unassigned` and never a `run`) and `affects` (a non-empty, unique list of the
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

## Semantic validation (consumer-enforced)

Agent and run parties carry cross-document rules that JSON Schema cannot
express. They are specified in
[`schemas/project-work/v0/semantic-validation.md`](../../schemas/project-work/v0/semantic-validation.md)
and consumers MUST run them in addition to structural validation.

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
