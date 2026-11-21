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
tags:
  [
    "runner",
    "execution",
    "journal",
    "idempotency",
    "recovery",
    "contract",
    "interoperability",
  ]
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

| Mode        | Adds                                        | Without it                                |
| ----------- | ------------------------------------------- | ----------------------------------------- |
| `basic`     | One attempt per task                        |                                           |
| `retrying`  | Policy-controlled attempts                  |                                           |
| `journaled` | durable-record/v1 journal, recovery, replay | No crash-recovery or durable-replay claim |
| `scheduled` | Supplied-slot semantics                     | No scheduled-task claim                   |

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
- Scheduled invocation keys are a reserved prefix plus the digest of a
  domain-tagged canonical object. A slot key is `slot:` followed by
  `sha256(JCS({"domain": "slot", "instant": I, "rule": R, "scope": S, "v":
0}))`, where `R` is the rule pin digest, `S` the task scope and `I` the
  occurrence instant, and the authority namespace is `S`. A catch-up key is
  `catchup:` followed by `sha256(JCS({"catch_up_of": M, "domain": "catch_up",
"v": 0}))`, where `M` is the missed task's `task_id`, in the missed task's
  authority namespace. The `slot:` and `catchup:` prefixes are reserved: an
  ordinary caller registration in that space is refused (`reserved_key`), so a
  caller cannot squat a derived identity, while inspecting or reconciling an
  already derived task by its identifier stays possible. The `task_id` preimage
  is unchanged. Identity conflicts apply to these keys exactly as to a
  caller-supplied key: the same key with a different specification digest is a
  conflict and is never silently observed. A changed schedule or policy needs a
  new explicitly submitted definition, never silent mutation. A duration's
  spelling is part of the definition digest, so equal durations spelled
  differently are different definitions.

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

| From     | Permitted next state and condition                                                                                                                                                                                                                                                                                                     |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| New      | `pending` on validated acceptance; an invalid submission creates no executable task                                                                                                                                                                                                                                                    |
| pending  | `waiting` for admission or a slot; `running` on authorized start; `cancelled`; `failed` on terminal pre-execution refusal or deadline; `missed` for an expired eligible slot with no attempt                                                                                                                                           |
| waiting  | `running` on an eligible next start; `cancelled`; `failed` when retry or deadline is exhausted; `missed` only if no attempt ever started                                                                                                                                                                                               |
| running  | `succeeded` on mapped success with verified required outputs; `failed` on terminal mapped failure; `waiting` after a finished failed attempt when retry is allowed and safe; `cancelled` after cancellation and confirmed quiescence; `abandoned` when lost authority leaves effects unresolved and safe continuation cannot be proved |
| Terminal | No further task-state transition; late evidence stays audit evidence and never changes the terminal result                                                                                                                                                                                                                             |

An operator retry of a terminal task creates a new task that refers to the old
one. Each attempt is running after start intent, then exactly one of
succeeded, failed, cancelled or abandoned. An abandoned attempt may leave the
task `waiting` only if every one of these holds: effects are safely reconciled
(conflicting outstanding effects are excluded and completed effects are
accounted for by the checkpoint or reconciliation rule, not merely known),
attempts remain, the retry horizon and task deadline have not expired, and the
pinned task-kind profile grants `retry_after_abandonment` (default false).
No failure code is required for an abandonment, and the absence of one never
bypasses retry policy. The retry uses the same bounded backoff as any other
retry: the consumed attempt number feeds the formula below, anchored at the
validated recovery decision instant, and the selected next-eligible instant is
persisted in the recovery transition, so a replayed or repeated recovery reads
it and cannot move the anchor or draw again. The same feasible-band
intersection and every deadline, horizon, slot, lag and admission bound apply,
and an immediate retry is legal only when the pinned backoff permits a zero
delay. If no retry is feasible, the task is `abandoned`. A direct finish that
carries an abandoned result may target only terminal `abandoned`, and only with effects
`unknown` (otherwise it is refused `abandonment_needs_unresolved_effects`: resolved or
absent effects follow the retry rules or finish `cancelled`), retaining the
unresolved-effect evidence, and asserting neither quiescence nor permission for a
replacement effect); the move from abandonment to `waiting` exists only through
recovery. A terminal `failed` finish requires effects `none` or `resolved`.
A `pending` task
fails only on a terminal pre-execution refusal or an elapsed task deadline,
and a waiting task fails only when retries or the deadline are exhausted.
Normal slot expiry before any attempt is `missed`, never a generic failure. A
timeout is a failed-attempt reason. An **unknown external effect is not a
routine retryable error**. Admission refusal consumes no attempt, and once a
launch intent commits that attempt counts even if dispatch is later found not
to have occurred.

Outcome codes and their success or failure mapping are closed by the pinned
task-kind schema. An unknown code fails closed, and a known code that
contradicts the claimed success or failure class is refused; neither mutates
state, and mapping success cannot bypass required output evidence. A measured provider failure
may map to task success, while an integrity failure does not. `max_attempts`
includes the first attempt. A retry additionally requires a permitted reason,
remaining attempts, the retry horizon and the task deadline. The horizon is
anchored at the first committed attempt-start intent, even if dispatch never
occurred, and persists across restarts. Admission or acceptance waiting does
not consume it, though the independent task deadline still applies. Both
bounds are exclusive: no new attempt starts at or after either expiry. The selected
next-eligible instant is persisted so replay never draws jitter again.
Core timeouts are attempt, task deadline and termination grace. Named phases
are closed by the kind profile. In this release an omitted whole-attempt timeout
requires a finite task deadline; a kind profile may later name other controlling
bounds. Retry disposition is policy, not caller preference. With no prior
cancellation, a safely finished failure for which retry is enabled, permitted
and still feasible leads to `waiting` (possibly with an admission or hold
reason); terminal `failed` is for a non-retryable outcome, disabled or exhausted
retry, or no feasible next attempt before the deadline, horizon or slot end. A
caller that selects `failed` while retry is admitted is refused `retry_required`,
the opposite direction being `retry_not_permitted`. Unresolved effects follow
abandonment and reconciliation, never ordinary retry.

Backoff is bounded by the contract and measured in integer microseconds. Let
`I` be the initial delay, `C` the maximum (`0 <= I <= C`), `m >= 1` the
multiplier and `0 <= j <= 1` the jitter fraction, with `m` and `j` read as exact
decimal rationals and never as binary floats. For a retry after attempt
`n >= 1` the nominal delay is `B = min(C, ceil(I * m^(n-1)))`, computed from the
original `I` (fixed backoff omits `m` or sets 1, so `B = I`). The admissible
selected delay `d` satisfies `L <= d <= U` with `L = ceil(B * (1 - j))` and
`U = min(C, floor(B * (1 + j)))`; a pinned kind may narrow the band. The same
transition records the decision instant `t` (the validated evaluation clock) and
`next_eligible_at = t + d`, never anchored to a caller-supplied finish time. The
draw is persisted and replay never redraws it. Before drawing, the band is
intersected with `[0, E - t - 1]` microseconds, where `E` is the earliest
applicable exclusive bound (task deadline, retry horizon or slot end): if the
intersection is empty, retry is infeasible and terminal failure is permitted,
and a draw above it is refused so a caller cannot overshoot a bound to evade a
required retry. A delay that lands at or after an exclusive bound cannot
authorize a start. The runtime supplies the draw, and the model verifies the
band and the exact arithmetic; no distribution is claimed. Elapsed timers use
monotonic time, and recovery rechecks persisted deadlines without resetting
elapsed budgets.

**Cancellation** is a committed, state-preserving request fact: an explicit
transition record that keeps the current nonterminal state and attempt identity
(it is not a general self-transition). Once it commits, every new attempt start
and every running-to-waiting retry is refused (`cancellation_precedes_start`),
`missed` is refused, and a normal succeeded or failed finish is audit evidence
only, because cancellation won (`cancellation_precedes_success`,
`cancellation_precedes_failure`). Quiescence then becomes terminal `cancelled`;
if effects or cleanup cannot be resolved the task is explicitly `abandoned`.
Once a request commits on a pending or waiting task, normal admission progress
is frozen as well: starts, ordinary admission waiting and pre-execution failed
transitions are refused, while state-preserving cancellation facts and explicit
confirmed cancellation remain allowed. A valid, authorized recovery that proves
quiescence and effects none or resolved records the confirming fact itself and
finishes `cancelled`, with no second confirmation call and never returning to
`waiting`; a recovery with unresolved effects commits an abandonment only when
the operation explicitly selects it with the required authority (naming `abandon`
with resolved effects changes nothing: the retry and cancellation rules decide), and a refused,
malformed, stale or unauthorized recovery commits nothing. Confirmation for a
pending or waiting task with no live work may be immediate but remains explicit
evidence. A request against a succeeded task is a no-op
`too_late`, and against any other terminal task is refused `task_terminal`; a
confirmation never resurrects a terminal task, and an exact repeat of a recorded
request returns the original result. If final success commits first,
cancellation is too late. A lost or indeterminate cancellation-write reply
requires reconciliation before either order is assumed. A journal failure does
not forbid emergency process termination, and the runner reports the unresolved
evidence instead of falsely claiming durable cancellation.

## Shared gates

Every path that creates a task or changes its state passes the same gates, so a
rule cannot be satisfied on one path and bypassed on another.

- **Registration.** A caller submission, a supplied slot, a coverage-recorded
  miss and a catch-up all register through one path. It validates the
  definition (including an unsupported durability requirement, outcome mapping
  with no duplicate codes and at least one success code, positive deadlines and
  horizon, closed phases and backoff with `I <= C`), the mode, the identity
  expiry and history, and the specification conflict. A scheduled task can
  therefore never carry a definition a submission would be refused.
- **Task deadline anchor.** `timeouts.task_deadline` is a duration budget. An
  ordinary submission anchors it at first acceptance. A task derived from a
  supplied slot anchors it at that slot's pinned `not_before`, not at delivery.
  A catch-up task anchors its own budget at its first acceptance and
  independently satisfies the lag limit. The anchor and absolute deadline are
  persisted, so a duplicate submission, restart, recovery or late receipt cannot
  reset them, a task supplied after its fixed deadline gains no new budget, and
  an overflowing sum is refused.
- **Finish.** A finish names the live attempt (a different attempt number is
  refused), carries an effects statement, and has a result that matches the
  target state. A `succeeded` or `failed` domain result requires a known outcome
  code and the pinned mapping, and the retry reason is taken from that mapping,
  never from the caller. A runtime failure before a domain result exists uses
  one of a closed set of framework reasons (`timeout`, `process_failure`). The
  lifecycle dispositions `cancelled` and `abandoned` rest on control evidence
  and fabricate no outcome code.
- **Start.** An attempt-start intent never claims dispatch is confirmed. A catch-up
  task is also bound to its lag at every new attempt start, not only at
  registration, and does not inherit the missed slot's expired window.
- **Crash.** After a runner crash and before recovery, every runner operation
  (including profile admission) except replay and the recovery itself is refused.
- **Authority handle.** Every operation that can create history or dispatch
  effects (submit, supplied slot or occurrence set, coverage, catch-up, transition,
  cancellation request and confirmation, checkpoint, admission reservation and
  settlement) presents the generation bound
  to the authority context its adapter acquired. It must equal the active claim:
  lower is `generation_stale`, higher is `generation_unclaimed`, and a missing one
  is `generation_required`. A trusted adapter attaches its already acquired handle
  and never looks up the current generation at commit time. Equality is evidence
  only, not authentication or proof of predecessor quiescence. Only recovery
  advances the claim, and exact keyed replay or read-only inspection that returns
  an existing result creates no commit.
- **Batches.** An occurrence set or coverage evaluation validates the whole batch
  (including conflicts between its own items) before its first write, then commits
  per item in a deterministic order with stable identities. It stops at the first
  failed or indeterminate commit and reports to the caller the committed prefix, the
  unresolved item and the unattempted suffix; it makes no all-or-none claim and rolls nothing
  back, and a retry reconciles per item.
- **Profile admission** is atomic: a refused or malformed profile changes no setting,
  and a catch-up task keeps the lag bound pinned when it was registered, so a later
  profile cannot widen it for existing work. A task's idempotency window (inside the
  kind range) and retry horizon must fit the admitted store window.
- **Boundary.** Wire tokens, integers and civil times are validated as written,
  and an unrecognized predecessor-proof or effects value fails closed. A supplied
  slot repeated after its window closed observes the existing task and keeps the
  key.

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

**Resume** is not a separate operation. Authorized resumption passes the
existing gates: validate retained history and the exact task and
specification, reconcile outstanding commits, effects and predecessor
authority, verify the checkpoint, its body and any restrictions, preserve rate
debt and retry limits, and then explicitly start a next attempt. Replay alone
grants no such authorization. A retried execution after a lost process gets a
new attempt identity, and it may consume an eligible predecessor checkpoint
(verified, on the chain, written by an earlier attempt, body not held) without
rewriting the earlier attempt. A refused start, recovery or checkpoint commits
nothing, preserves `running` and its facts, and dispatches no effect.

The initial authority is **one host per execution stream**, held through a
process-shared exclusive lock spanning recovery, child containment, execution,
effects, orphan cleanup and publication. An append lock alone does not
establish that lifetime. The authority generation is evidence only and does not
claim to fence a running child or remote request. It is strictly increasing for
each new execution-authority owner or run; a repeated reconciliation of an
already recorded claim by the same owner may retain it, and a different owner
cannot be granted a generation already held. The claim is persisted and
exhaustion of the safe-integer range refuses. Before a successor
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

| Property                 | Rule in this release                                                                                                                                                    |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `attempt_journal_ack`    | `none`, `survives_process_loss`, `survives_power_loss`. `journaled` requires at least process-loss survival. A stronger value may substitute only within this property. |
| `remote_sealed_coverage` | `none`. A detached record seal or a bucket copy does not upgrade it.                                                                                                    |
| `replication`            | `none`. It means no contract claim, not that infrastructure has no replicas.                                                                                            |

The acknowledgement property is bound to the actual v1 stratum failure model:
`attempt_journal_ack` must not exceed the journal stratum's `failure_model`
(none < survives_process_loss < survives_power_loss, within this property only),
or the profile is refused `journal_ack_exceeds_failure_model`. Receipt and
configuration evidence must agree, and `commit_strategy` alone grants nothing. Bodies required for success or for
checkpoint reuse must meet the task's declared durability as well as digest
verification, and a record receipt cannot certify weaker external-body
storage. A valid task that requires remote sealed coverage or replication is refused as
an unsupported requirement.

## Time

Operational instants use the v1 canonical UTC spelling with exactly six
fractional digits. A value that is not representable is refused, never
rounded. Wire strings are validated as written: an absent or short fraction
and a non-UTC offset are refused, and a harness never normalizes incoming
strings or digested bytes. A typed instant that is exactly representable may be
formatted to the canonical spelling before a contract document is built, and
that formatting claims no finer observation. Source
precision is independent provenance, and its interval comparison yields
before, after or overlapping. Exact deadlines are operational instants.

Durations are the fixed-unit ISO 8601 subset (`W`, `D`, `H`, `M`, `S`; no
years or months), evaluated as exact integer microseconds. Bounds are checked
before conversion, and fractional loss is refused when a millisecond-only
interface is called. Existing `*_ms` fields of other contracts keep their
meaning.

Idempotency windows belong to the task-kind profile, not to durability. The
acquisition kind's minimum, default and maximum are `P7D`, `P14D` and `P35D`. A
runner profile selects an effective window within the kind's range (the range
default when omitted) and admits a store window that covers that effective
window and the retry horizon. The kind's maximum is a ceiling on configuration,
not the required store setting, and a window is never silently reduced to fit
the store. Supplied policy outside the applicable range is refused.
Expiry falls back to retained replay or reconciliation, never to blind
re-execution.

## Supplied schedules

`recurrence/v0` owns rule normalization, expansion and tzdb identity. The
caller supplies one slot or a bounded occurrence set with exact rule, scope,
instant and window pins, and the executor validates identity and eligibility
without discovering unspecified slots. A supplied slot carries, or
deterministically derives from pinned policy, a window with `not_before <
not_after`, and missing or ambiguous window information is refused rather than
guessed. A task created from a slot may start only when `not_before <= now <
not_after` in addition to its next-eligible, deadline and horizon checks; a
slot that has not opened waits. At or after `not_after` a never-started task
may become `missed`, but a task with a prior attempt does not: if no further
start is feasible it finishes `failed`, or follows cancellation or abandonment.
A running attempt is not made `missed` when the slot closes, because attempt and
task deadlines govern it; a kind that requires completion within a slot binds
its task deadline accordingly. For a never-started slot already expired, `missed`
takes precedence over a coincident generic deadline failure, while a deadline
reached with the slot still open produces a pre-execution failure. A
reconciliation invocation may supply past expected occurrences so missed work
can be recorded. Coverage describes which occurrences were supplied over the
half-open span `[from, to)` and does not replace slot windows. It requires `to <=
now`, its rule pin must be the profile's, and each expected occurrence must lie
inside the span and carry its window. An occurrence is marked `missed` only when
`now >= not_after`, no attempt has started and no cancellation or terminal result
already wins; a past instant whose window is still open stays eligible. No claim
of detecting all misses exists without that supplied coverage. A DST-skipped
candidate is a non-slot. The harness checks a fixture-limited zone table; a real
implementation validates occurrence membership, including DST, against the
pinned recurrence semantics within declared bounds, or reports unavailable, and
never accepts a rule pin alone as proof. `missed` is terminal, and a catch-up is
a separate task linked to it, allowed only within the kind's pinned maximum lag.
The lag end is the missed occurrence plus the pinned maximum lag and is
inclusive: a start is eligible at that instant and not after it, and in retry
feasibility the lag contributes `end - t` to the upper delay (the other bounds
contribute their exclusive end minus `t` minus one microsecond). A repeat
catch-up after the lag expires observes the existing derived task without new
work. The lag is computed from the clock and the stored missed instant and is never
supplied by the caller, and neither a caller nor a new policy pin silently
resets the missed task's identity or history. `requires` checks pins and never
schedules an edge.

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
controls remove one guard at a time and at least one vector must fail with a
checker verdict.

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
oracle for an implementation. Passing every vector does not cover the rules this
standard states for reconciliation after a lost cancellation-write reply, keyed
cancel-request idempotency across retries, and an audit-evidence operation: they
are normative here and carry no vector in this release. Runtime proof, crash and power-loss behavior on
real storage, cloud qualification and language parity need adopter tests. The
model does not enforce attempt-timeout or deadline expiry while an attempt is
running, does not bind admission to a task, does not bound supplied instants to the exact-integer microsecond range (the wire pattern admits years the arithmetic cannot represent; sums that cross it refuse `counter_exhausted`), and does not draw the backoff (the runtime
supplies and persists its choice; the model only verifies a supplied draw lies inside
the band); those are runtime behaviors.
