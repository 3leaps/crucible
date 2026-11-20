---
title: "Portable Durable Runner Contract"
description: "Proposed task execution semantics: immutable specification, derived identities, closed task and attempt transitions, single-authority journaled recovery, independent durability properties, exact time and supplied schedules, independent of storage engine and runtime"
category: "standards"
status: "draft"
version: "0.0.0"
lastUpdated: "2026-11-20"
maintainer: "core-standards"
reviewers: ["architecture", "security", "data-engineering"]
approvers: ["lead-maintainer"]
tags: ["runner", "execution", "journal", "idempotency", "recovery", "contract", "interoperability"]
content_license: "CC0"
relatedDocs:
  - "docs/standards/durable-record-v1-contract.md"
  - "docs/standards/data-acquisition-contract.md"
  - "docs/standards/recurrence-rule-contract.md"
  - "docs/standards/process-run-contract.md"
  - "docs/decisions/ADR-0021-durable-runner-contract.md"
audience: "implementers"
---

# Portable Durable Runner Contract

## Maturity and scope

This is the **proposed experimental contract** `contract: durable-runner/v0`.
It defines what a runner promises about executing a pinned task: how the task
is identified, which state changes are legal, what is journaled, who may
execute, what each durability claim means and how time and schedules are
handled. It is a logical contract. Storage layouts, process supervision,
schedulers and worker fleets belong to adopting repositories.

The first publication admits four **modes**: `basic`, `retrying`, `journaled`
and `scheduled`. The name `sealed` is reserved and not admitted; see
[Reserved: sealed](#reserved-sealed). Nothing here describes a DAG engine, a
broker, a recurrence host or multi-host failover. The schema harness proves the
rules in this document against authored histories; it is not a runtime
qualification and implies no cloud, language or sealed parity.

Schemas live in
[`schemas/durable-runner/v0/`](../../schemas/durable-runner/v0/README.md).
Decision record:
[ADR-0021](../decisions/ADR-0021-durable-runner-contract.md).

## Modes

Modes are cumulative prefixes, and an implementation declares and passes every
mode it claims.

| Mode | Adds | Without it |
| --- | --- | --- |
| `basic` | One attempt per task | |
| `retrying` | Policy-controlled attempts | |
| `journaled` | durable-record/v1 journal, recovery, replay | No crash-recovery or durable-replay claim |
| `scheduled` | Supplied-slot semantics | No scheduled-task claim |

No mode implies a scheduler or a distributed worker service. A mode that
vectors do not exercise cannot be advertised. A profile that advertises a mode
outside the closed set, or a non-prefix set, is refused.

## Task definition and identity

A **task definition** is the immutable specification: the pinned task-kind
schema, parameters, input requirements, outcome mapping, policy pins, timeouts
and retry policy. It excludes runtime identifiers, evidence timestamps and
derived state. Secrets are references only. Instances never resolve a schema
over the network.

- `task_spec_digest` is `sha256:` over the RFC 8785 canonical bytes of the
  definition.
- `task_id` is `sha256(JCS({"authority": A, "invocation_key": K, "v": 0}))`
  where `A` is a caller-supplied authority namespace and `K` a stable
  invocation key. The first acceptance permanently binds the pair to one
  specification digest within retained task history. Reusing the pair with a
  different digest is a **conflict**. Reusing it with the same digest
  observes or reconciles existing work and never starts another task.
- `run_id` identifies one runner process invocation. It is not an idempotency
  key. A restart changes it without changing the task or an attempt.
- `attempt_n` is positive, contiguous per task and increments only on a
  committed attempt-start intent. `attempt_id` is
  `sha256(JCS({"attempt_n": N, "task_id": T, "v": 0}))`. Start intent may
  commit before dispatch, and evidence must not claim dispatch is proven.
- Scheduled invocation keys derive from a canonical object holding the exact
  rule pin, task scope and occurrence instant. Catch-up uses a distinct key and
  the original missed-task pin. A changed schedule or policy needs a new
  explicitly submitted definition, never silent mutation.

Counters use durable-record's safe-integer ceiling with checked arithmetic, and
exhaustion refuses before effects. A finite store idempotency window does not
expire task identity. After it, retained history is reconstructed or the
unresolved identity is refused; uncertainty is never treated as a new task.
Discarded history requires a new authority namespace or an explicit
unavailable result, never invented replay continuity.

## Task and attempt transitions

Task states are `pending`, `waiting`, `running`, `succeeded`, `failed`,
`cancelled`, `abandoned` and `missed`. `blocked` is a reason on `pending` or
`waiting`, never a state.

| From | Permitted next state and condition |
| --- | --- |
| New | `pending` on validated acceptance; an invalid submission creates no executable task |
| pending | `waiting` for admission or a slot; `running` on authorized start; `cancelled`; `failed` on terminal pre-execution refusal or deadline; `missed` for an expired eligible slot with no attempt |
| waiting | `running` on an eligible next start; `cancelled`; `failed` when retry or deadline is exhausted; `missed` only if no attempt ever started |
| running | `succeeded` on mapped success with verified required outputs; `failed` on terminal mapped failure; `waiting` after a finished failed attempt when retry is allowed and safe; `cancelled` after cancellation and confirmed quiescence; `abandoned` when lost authority leaves effects unresolved and safe continuation cannot be proved |
| Terminal | No further task-state transition; late evidence stays audit evidence and never changes the terminal result |

An operator retry of a terminal task creates a new task that refers to the old
one. Each attempt is running after start intent, then exactly one of
succeeded, failed, cancelled or abandoned. An abandoned attempt may leave the
task `waiting` only if recovery proves no outstanding conflicting effects and
the task-kind policy permits retry; otherwise the task is `abandoned`. A
timeout is a failed-attempt reason. An **unknown external effect is not a
routine retryable error**. Admission refusal consumes no attempt, and once a
launch intent commits that attempt counts even if dispatch is later found not
to have occurred.

Outcome codes and their success or failure mapping are closed by the pinned
task-kind schema, and an unknown code fails closed. A measured provider failure
may map to task success, while an integrity failure does not. `max_attempts`
includes the first attempt. A retry additionally requires a permitted reason,
remaining attempts, the retry horizon and the task deadline. The selected
next-eligible instant is persisted so replay never draws jitter again.
Core timeouts are attempt, task deadline and termination grace. Named phases
are closed by the kind profile, and an omitted whole-attempt timeout requires a
finite task deadline. Elapsed timers use monotonic time, and recovery rechecks
persisted deadlines without resetting elapsed budgets.

**Cancellation** is a durable request before an intentional stop, and it
becomes terminal `cancelled` only after quiescence is established. If final
success commits first, cancellation is too late. If cancellation commits first,
later success evidence cannot produce `succeeded`. A journal failure does not
forbid emergency process termination, and the runner reports the unresolved
evidence instead of falsely claiming durable cancellation.

## Journal, authority and recovery

In `journaled` mode the authoritative execution stream is a durable-record/v1
stream of **single-revision transition records**. Each payload binds the task
and specification, the exact preceding transition (absent only for the first),
the resulting state, attempt facts when present, the authority generation and
evidence pins. Start and finish are separate immutable transition facts that
share an attempt identity. Task and attempt indexes and summaries are derived
projections and never a second authority, so no cross-record or cross-stream
transaction is assumed. The single execution authority checks the predecessor
before append. The journal adds no durable-record journal entry kinds, and
there is no v0 fallback or implicit migration.

A checkpoint is one payload binding the journal cursor and the exact verified
state body pin. Bodies are staged and verified before the referencing record,
and an unreferenced body is not a checkpoint. A crash exposes the previous
complete record or an indeterminate or damaged state, never a fabricated
committed cursor. Existing v1 receipts, recovery, holds, retirement and
reconciliation apply unchanged.

The initial authority is **one host per execution stream**, held through a
process-shared exclusive lock spanning recovery, child containment, execution,
effects, orphan cleanup and publication. An append lock alone does not
establish that lifetime. The authority generation is evidence only and does not
claim to fence a running child or remote request. Before a successor
dispatches, it establishes predecessor quiescence or applies an explicit
verified task-kind reconciliation rule; otherwise it blocks or abandons rather
than execute concurrently. Automatic multi-host takeover and advisory-only
authority are unsupported.

Source-rate admission persists under the declared coordination scope before
acquisition requests, and unsettled reservations survive restart
conservatively. Sources that share a quota share an admission authority, and
separate stream-local limiters cannot advertise a global limit. Policy
language is `data-acquisition/v0`'s and is not replaced here.

**Replay** folds authoritative history to the same task and attempt heads,
outcomes and output pins and performs no external effect. **Resume** is a
separately authorized action after replay and is not an alias for it. A
missing write receipt stays indeterminate until v1 reconciliation establishes
the result. Broken predecessor chains, ambiguous identity, unverified
checkpoints and unresolved output restrictions are refused before reliance.

## Durability properties

Durability is independent properties. There is no global rank and no new
failure-model value.

| Property | Rule in this release |
| --- | --- |
| `attempt_journal_ack` | `none`, `survives_process_loss`, `survives_power_loss`. `journaled` requires at least process-loss survival. A stronger value may substitute only within this property. |
| `remote_sealed_coverage` | `none`. A detached record seal or a bucket copy does not upgrade it. |
| `replication` | `none`. It means no contract claim, not that infrastructure has no replicas. |

The acknowledgement property is bound to the actual v1 stratum failure model,
and `commit_strategy` alone grants nothing. Bodies required for success or for
checkpoint reuse must meet the task's declared durability as well as digest
verification, and a record receipt cannot certify weaker external-body
storage. Tasks requiring remote sealed coverage or replication are refused.

## Time

Operational instants use the v1 canonical UTC spelling with exactly six
fractional digits. A value that is not representable is refused, never
rounded, and padding for serialization claims no finer observation. Source
precision is independent provenance, and its interval comparison yields
before, after or overlapping. Exact deadlines are operational instants.

Durations are the fixed-unit ISO 8601 subset (`W`, `D`, `H`, `M`, `S`; no
years or months), evaluated as exact integer microseconds. Bounds are checked
before conversion, and fractional loss is refused when a millisecond-only
interface is called. Existing `*_ms` fields of other contracts keep their
meaning.

Idempotency windows belong to the task-kind profile, not to durability. The
acquisition kind's minimum, default and maximum are `P7D`, `P14D` and `P35D`. A
runner profile admits a store window that covers the configured window and the
retry horizon, and supplied policy outside the applicable range is refused.
Expiry falls back to retained replay or reconciliation, never to blind
re-execution.

## Supplied schedules

`recurrence/v0` owns rule normalization, expansion and tzdb identity. The
caller supplies one slot or a bounded occurrence set with exact rule, scope,
instant and window pins, and the executor validates identity and eligibility
without discovering unspecified slots. A reconciliation invocation may supply
past expected slots so missed work can be recorded, and no claim of detecting
all misses exists without that supplied coverage. A DST-skipped candidate is a
non-slot. `missed` is terminal, and a catch-up is a separate task linked to it,
allowed only within the kind's configured maximum lag. `requires` checks pins
and never schedules an edge.

## Reserved: sealed

`sealed` is reserved in this standard and excluded from the accepted
advertised-mode enumeration, so a profile claiming it is refused. A passing
reservation-reject test is not sealed conformance. Publication of acquisition
authority is a separate boundary from record commitment. A future shared ledger
composition will own complete-group closure, signed immutable cuts, parent
linkage, a conditional head and distinct `committed`, `not_committed` and
`indeterminate` publication receipts. Failed execution may have committed audit
records, and failed publication acquires no installed position by intent alone.
A lost reply or an unchanged head does not prove non-commit. No runner-local
sealed format may ship in the interim.

## Conformance

A **vector** is an ordered op script with hand-authored expectations: each op
states `ok` members or an exact closed refusal reason, and the vector states
the final task projection and the exact committed history. A reference
consistency model executes each script against the rules above, so a
fabricated receipt, an invented transition or a missing guard is detected as a
mismatch. The authored histories are independent of the model, and mutation
controls remove one guard at a time and must change the verdict of the vector
that targets it.

The minimum inventory covers identity reuse, conflict and expired keys; every
permitted transition and forbidden terminal resurrection; cancellation races;
a crash after start before dispatch and after an effect before finish; retry
limits and persisted jitter; orphan refusal; admission denial and unsettled
reservations; predecessor-chain conflict; checkpoint body and record ordering;
unknown receipt reconciliation; hold and retirement refusal; exact time and
integer bounds; supplied coverage, DST non-slots, missed and catch-up work;
replay with zero effects; and unsupported sealed and replication claims. Stored
state stays separate from caller knowledge.

**Assurance boundary.** The model checks fixtures; it is not a conformance
oracle for an implementation. Runtime proof, crash and power-loss behavior on
real storage, cloud qualification and language parity need adopter tests.
