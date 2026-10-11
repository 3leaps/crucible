---
title: "Portable Durable Queue Contract"
description: "Proposed at-least-once message queue semantics: envelope, leases with fencing, closed transition vocabulary, append-only ledger, capability profiles and a wire binding, independent of storage engine"
category: "standards"
status: "draft"
version: "0.0.0"
lastUpdated: "2026-10-11"
maintainer: "core-standards"
reviewers: ["architecture", "security", "data-engineering"]
approvers: ["lead-maintainer"]
tags: ["queue", "messaging", "contract", "ledger", "idempotency", "interoperability"]
content_license: "CC0"
relatedDocs:
  - "docs/standards/service-job-contract.md"
  - "docs/standards/process-run-contract.md"
  - "docs/standards/data-artifact-contract.md"
  - "docs/decisions/ADR-0012-durable-queue-contract.md"
audience: "implementers"
---

# Portable Durable Queue Contract

## Maturity and scope

This is the **proposed experimental contract** `contract: durable-queue/v0`.
It defines what a durable queue promises to producers and consumers, how a
queue records what it did, and how any implementation is driven for
conformance. This first publication is deliberately **narrowed to an audit and
lifecycle fold**: the ledger is an authoritative, consistently cuttable history
of transitions. Portable restore of a queue from its ledger, a `replay`
operation, cross-queue fan-out and a tolerant wall-clock conformance mode are
**deferred** and are not advertised in the v0 vocabulary. It does **not** define a storage engine, a table layout, a file
format, a worker runtime, or a job framework. Those are implementation
surfaces owned by adopting repositories.

The contract is deliberately narrow so that an embedded log, a SQL database,
a broker, or a cloud queue can each sit behind it and declare, through a
capability profile, which guarantees it actually provides.

## Design stance

- **At-least-once, never exactly-once.** A message may be delivered more
  than once. Consumers MUST be idempotent. The contract never claims
  exactly-once and no capability may add it.
- **No ordering unless declared.** Without the `ordering_key` capability,
  delivery order is unspecified. Deterministic conformance fixes order for
  test reproducibility only; it is not a product promise.
- **A lease is a value with a fence.** Every delivery carries a lease: queue,
  message id, opaque fencing token, attempt number and expiry. `ack`, `nack`,
  `extend`, `fail` and `fan_out` present the lease and the broker checks queue,
  message id and token together against the live lease. A wrong queue, wrong
  token, expired or superseded lease yields the outcome `stale_lease`, which is
  expected and is not an error. Fencing is core; it is not a capability.
- **The broker owns the clock.** Timestamps are assigned by the broker,
  RFC 3339 in UTC, millisecond precision. An implementation started in test
  mode exposes `advance_clock`; a conforming implementation MUST NOT accept
  it otherwise.
- **State is a fold over the ledger.** Each transition appends exactly its
  ledger events in the same atomic step as the state change, as one atomic
  group. Lifecycle state (ready, delayed, leased, done, dead, gone) at any
  consistent cut is derivable from the ledger alone. Message metadata and
  payloads are not in the ledger; portable restore is deferred. A profile
  declaring `ledger: inferred` is reconstructing, not recording, and is not
  admissible for deterministic conformance.
- **Everything is a batch.** Enqueue, claim, extend, ack, nack and fail take
  arrays. A single item is a batch of one. Outcomes are positional.
- **Roles are separate surfaces.** Producer, consumer and admin operations
  are separable so a service that only enqueues need not hold claim or purge
  rights.
- **Pull is the primitive.** Handler registries, concurrency control and
  backoff policy live in a worker library above this contract.
- **Closed vocabulary.** Unknown ops, event types, outcomes and error codes
  fail closed. There is no `x-` extension prefix in v0. Request parameters and
  successful results are typed per operation in the schema; an open or
  under-specified request is schema-invalid, not merely unusual.
- **Keyed deduplication is core.** Every conforming backend recognizes a
  repeated `idempotency_key` for a declared window and never silently accepts
  a different message under a live key.
- **Payload-open, envelope-governed.** The broker never reads, validates or
  rewrites `payload` or `attributes`. The envelope is contract-governed.

## Capability and versioning

A capability profile MUST carry the portable capability string:

```json
{ "capabilities": ["contract: durable-queue/v0"] }
```

The string is host-less. Consumers resolve it to a trusted `contract.json`,
verify `capability`, and load the relative `entry_schema`
(`capability-profile.schema.json`, the discovery root). Resolution fails
closed on a missing manifest, a capability mismatch, or a missing entry
schema. Messages, ledger lines and control exchanges do not repeat the token.

Additive changes within `v0` are permitted when older consumers ignore the
field or fail closed safely. Breaking changes include: changing the meaning
of an existing field; weakening fencing, at-least-once or closed-vocabulary
posture; changing the fold rules; adding or removing an event type; and
renaming fields without an alias.

## Governed objects

### Queue message

Schema: `queue-message.schema.json`. Required: `v`, `id`, `queue`,
`payload_contract`, and exactly one of `payload` or `payload_ref`.

| Field | Rule |
| --- | --- |
| `id` | Broker-assigned, unique per queue for the life of the ledger, opaque. |
| `idempotency_key` | Producer-chosen. Scope is the queue. Lifetime is the backend's declared `idempotency_window_ms` measured from the original `enqueued` event, **independent of message state** (a key stays live after ack, purge or redrive until the window ends). A repeat with the same identity digest returns the original id with outcome `deduplicated`; a repeat with a different identity digest returns the original id with outcome `conflict` and accepts nothing. |
| identity digest | SHA-256 over the RFC 8785 canonical bytes of `{payload_contract, payload}` or `{payload_contract, payload_ref: {artifact_id, digest}}`. Scheduling fields (`not_before`, `expires_at`, `max_attempts`, `priority`, `ordering_key`, `attributes`, `trace`) are not bound; on a repeated key the original's values win. |
| `payload_contract` | Host-less token naming the payload's own contract. Carried, never validated by the broker. |
| `payload_ref` | A `contract: data-artifact/v0` reference: `artifact_id` and `digest` required, optional `descriptor_ref` and `representation_id`, all opaque tokens, never filesystem paths. Requires capability `payload_ref`. Retention and custody of the referenced bytes are the artifact's contract, not the queue's. |
| `not_before` | Requires `delay`. The message is not ready before this time. |
| `expires_at` | After this time the message is purged with reason `expired` and never delivered. |
| `max_attempts` | Default 5. The attempt at which a `nack` dead-letters instead of returning the message to ready. |
| `parent_id` | Set by `fan_out` on children. Children are always enqueued to the parent's queue in v0. |
| `ordering_key`, `priority` | Each requires its capability. |
| `trace` | W3C traceparent, carried verbatim. |
| `attributes` | String map, producer-owned, never interpreted. |

### Lease

Not a stored object. A value returned by `claim`: `{queue, message_id, token,
attempt, until}`. The token is opaque, unique per lease, and MUST NOT appear
in the ledger. The attempt number identifies the lease in the ledger. Message
ids are unique per queue, not globally, so the queue is part of lease identity.

Producer input is `queue-message.schema.json#/$defs/newMessage`: the same
fields without `v`, `id`, `queue` or `parent_id`, which are broker-assigned.

### Ledger event

Schema: `ledger-event.schema.json`. One NDJSON line per event. `seq` is
monotonic per queue and gap-free; it is the audit cursor. A gap or regression
is corruption. Every event carries `group` (the `seq` of the first event in its
atomic group) and `group_size`. A prefix ending at `seq` N is a **consistent
cut** iff, for the event at N, `N - group + 1 == group_size`. A truncated final
group is therefore detectable from the lines alone; `export_ledger` reports
`consistent_cut` for the range it returned.

Two event types are **audit events, not transitions**: `deduplicated` and
`conflicted`. They record a producer retry against a live key, change no
state, and MAY follow a terminal state. Every other type is a transition.

| Type | Appended when | Required fields beyond the envelope |
| --- | --- | --- |
| `enqueued` | A new message is accepted | `payload_digest`; `idempotency_key` if present; `parent_id` for children; `not_before` if delayed |
| `deduplicated` | An enqueue repeats a live key with the same identity digest (audit) | `idempotency_key` |
| `conflicted` | An enqueue repeats a live key with a different identity digest (audit) | `idempotency_key`, `payload_digest` of the rejected identity |
| `leased` | A claim delivers the message | `attempt`, `worker`, `lease_until` |
| `extended` | A live lease is extended | `attempt`, `lease_until` |
| `acked` | A live lease is acked | `attempt` |
| `nacked` | A live lease is nacked | `attempt`, `reason`; `not_before` when the message returns to ready |
| `lease_expired` | A sweep finds an expired lease | `attempt` |
| `dead_lettered` | Attempts exhausted, or `fail` | `reason` |
| `redriven` | An admin returns a dead letter to ready | none |
| `purged` | An admin purge, or expiry | `reason` |

`payload_digest` on `enqueued` is the identity digest defined above. The ledger
never carries the payload or the message's scheduling metadata. Audit needs
the ledger alone; portable restore would additionally need a defined snapshot
cut and immutable payload bindings, which this publication defers.

Stale-lease operations append nothing. `deduplicated` and `conflicted` are
appended so producer retries are visible in audit.

### Capability profile

Schema: `capability-profile.schema.json`. The discovery root. Two blocks are
mandatory and MUST be kept distinct:

- `build`: immutable facts about the artifact: version, target, native
  dependencies, compiled backends, compiled capabilities. A build with no
  native dependencies says nothing about durability.
- `runtime`: effective facts for the configuration exercised: selected
  backend, failure model, enabled capabilities. `enabled_capabilities` MUST be
  a subset of `build.compiled_capabilities`; the controls enforce this.

`runtime.failure_model` is a **guarantee**, not a technique: the strongest
failure an acknowledged `enqueue` or `fan_out` survives, one of
`survives_power_loss`, `survives_process_loss`, `none`. `commit_strategy` is
free text for information only and never upgrades the model. This keeps
remote brokers and cloud queues comparable with embedded stores.

`idempotency_window_ms` is required: keyed deduplication is core.

`origin: harness` means the conformance harness produced the profile from
observed runs. `origin: declared` is an unverified claim and MUST NOT be
presented as conformance evidence.

`conformance` is `deterministic` or `benchmark_only`. A deterministic profile
MUST have `ledger: recorded`, `origin: harness` and `virtual_clock` enabled;
the schema enforces all three. `benchmark_only` means the backend was
exercised for measurement and claims no conformance. A tolerant wall-clock
mode is deferred.

Capabilities in v0: `transactional_enqueue`, `atomic_fanout`, `delay`,
`ordering_key`, `priority`, `payload_ref`, `long_poll`, `virtual_clock`.
Fencing and keyed deduplication are core and have no capability.

### Control exchange

Schema: `control-exchange.schema.json`. Line-delimited JSON request and
response over stdio or a local socket, in the shape of the process-run
control channel. Requests are discriminated by `op` with closed, typed
`params`; responses echo `op` and carry a typed `result` or a typed `error`.
Daemon deployments require `token` on every request and reject failures with
`unauthorized`, indistinguishable for wrong versus unknown token. Harness
stdio mode MAY omit the token. All batches are positional and bounded (1 to
1024 members); durations are integer milliseconds, 0 to 86,400,000.

| Role | Op | Semantics |
| --- | --- | --- |
| Producer | `enqueue` | `{queue, messages[]}` of `newMessage` → one receipt per message, positional, each `{message_id, outcome: accepted \| deduplicated \| conflict}`. |
| Consumer | `claim` | `{queue, worker, max, lease_ms, wait_ms}` → deliveries, each with a lease. `wait_ms > 0` requires `long_poll`. |
| Consumer | `extend` | `{leases[], lease_ms}` → one outcome per lease. |
| Consumer | `ack` | `{leases[]}` → outcomes. |
| Consumer | `nack` | `{leases[], retry_after_ms, reason}` → outcomes. Counts the attempt. |
| Consumer | `fail` | `{leases[], reason}` → outcomes. Dead-letters immediately. |
| Consumer | `fan_out` | `{parent: lease, children[]}` → `{outcome, receipts[]}`. Children go to the parent's queue. Requires `atomic_fanout`. A stale parent yields `outcome: stale_lease` and empty receipts. |
| Admin | `stats`, `peek`, `redrive`, `purge`, `sweep` | Inspection and repair. `sweep` expires overdue leases and purges expired messages. |
| Admin | `export_ledger` | `{queue, from_seq, max}` → `{events[], consistent_cut}`. |
| Any | `capabilities` | Returns the profile. |
| Test | `advance_clock` | `{by_ms}`. Present only under `virtual_clock` in test mode. |

Deferred, not in the vocabulary: `replay`. Lease outcomes: `ok`,
`stale_lease`, `unknown_message`. Error codes:
`unknown_op`, `invalid_params`, `unauthorized`, `unknown_queue`,
`capability_unsupported`, `payload_too_large`, `backend_unavailable`,
`internal`.

## Portable invariants

1. **Fencing.** An `ack`, `nack`, `extend`, `fail` or `fan_out` whose
   `{queue, message_id, token}` does not match the live lease returns
   `stale_lease` and changes nothing. For `fan_out` the parent check, child
   publication and parent ack are one atomic step.
2. **Single live lease.** At most one live lease exists per message. A
   `claim` never delivers a message with a live lease.
3. **Attempt monotonicity.** Each `leased` event for a message carries an
   attempt strictly greater than the previous.
4. **Expiry before redelivery.** A message is redelivered only after a
   `lease_expired` or `nacked` event for its previous attempt. A `claim` that
   finds an expired lease appends `lease_expired` and the new `leased` in one
   atomic group; a prior `sweep` is not required.
5. **Dead-letter boundary.** Both `nack` and lease expiry consume an attempt.
   When the consumed attempt equals `max_attempts`, the `nacked` or
   `lease_expired` event and `dead_lettered` with reason `max_attempts` form
   one atomic group. `redrive` returns a dead message to ready with a fresh
   attempt budget; the attempt counter itself never resets, so lease identity
   stays monotonic.
6. **Idempotent enqueue.** Within the declared window, measured from the
   original `enqueued` event and independent of message state, a repeated key
   with the same identity digest returns the original `message_id` with
   outcome `deduplicated` and appends a `deduplicated` audit event; a repeated
   key with a different identity digest returns the original `message_id`
   with outcome `conflict`, accepts nothing, and appends `conflicted`.
7. **Atomic fan-out.** Under `atomic_fanout`, the children's `enqueued`
   events and the parent's `acked` event are appended in one atomic step, in
   that order. Without the capability, `fan_out` returns
   `capability_unsupported` and the consumer enqueues children with
   deterministic idempotency keys derived from the parent and recipient, then
   acks the parent.
8. **Durability claim.** An acknowledged `enqueue` or `fan_out` survives the
   failure named by `runtime.failure_model`. Profiles MUST state it as a
   guarantee; a commit strategy name never substitutes for it.
9. **Closed vocabulary.** Unknown ops, event types, outcomes and error codes
   are rejected, not ignored.
10. **Ledger completeness.** Under `ledger: recorded`, folding the ledger from
    `seq` 1 to any consistent cut reproduces every message's lifecycle state
    at that cut. Lifecycle state only; metadata and payload restore are
    deferred.
11. **Atomic groups.** Every multi-event transition is one contiguous group
    with matching `group` and `group_size` on each member. An exporter MUST
    NOT present a prefix ending inside a group as a consistent cut.

## Fold rules

A consumer or auditor reconstructs state by folding events in `seq` order.

| Event | Message state after |
| --- | --- |
| `enqueued` | `ready` (or `delayed` until `not_before`) |
| `deduplicated` | unchanged (audit; legal after terminal) |
| `conflicted` | unchanged (audit; legal after terminal) |
| `leased` | `leased` |
| `extended` | `leased` with new expiry |
| `acked` | `done` (terminal) |
| `nacked` | `ready` or `delayed`, unless followed in the same step by `dead_lettered` |
| `lease_expired` | `ready` |
| `dead_lettered` | `dead` |
| `redriven` | `ready` |
| `purged` | `gone` (terminal) |

`done` and `gone` are terminal. Any **transition** event after a terminal
state for the same message is a fold error; audit events are permitted.

## Conformance

Behavioral vectors live under `schemas/durable-queue/v0/vectors/`, grouped by
the capability they require. A vector is an op script with expected results
and the exact expected ledger. Ids bound with `$name` are substituted from
results; timestamps derive from `clock_start` plus each op's `at_ms`.

Vector grammar: `ops[]` are requests validated against the request schema
with `$name` tokens in place of ids and leases; `{"$rebind": "$l", field: v}`
presents a bound lease with one field altered; `expect` is matched
structurally against the typed result; `bind` captures result paths. The
expected `ledger[]` must validate line by line, be gap-free from 1, carry
contiguous atomic groups, bind every `$name` it uses, satisfy the fold rules
and invariants above, and carry identity digests that match the ops. The
crucible controls enforce all of that on the fixtures; the executing harness
lives in the adopting repository.

One conformance mode is defined in v0: **deterministic**, requiring
`virtual_clock`, `ledger: recorded` and an exact normalized ledger match on
every core vector. Backends that cannot meet it are `benchmark_only`. A
tolerant wall-clock mode with declared tolerances is deferred until an
execution and transformation rule exists for it.

## Relationship to other contracts

- **`contract: service-job/v0`** — a queue transports job messages as opaque
  payloads. The submit request's `idempotency_key` (scope: actor, service,
  key) and the queue `idempotency_key` (scope: queue) are different scopes;
  an adopter MAY carry the same string in both provided the mapping is
  explicit and collisions are isolated per scope. Queue transport events
  (`leased`, `nacked`, `lease_expired`) and queue completion (`acked`,
  `dead_lettered`, `purged`) never change job state and are never a
  service-job terminal result. `examples/queue-message.service-job.example.json`
  carries a submit request as payload and the controls validate that payload
  against the service-job entry schema.
- **`contract: data-artifact/v0`** — `payload_ref` bodies are artifacts.
- **`contract: process-run/v0`** — a queue daemon publishes a process card;
  the `worker` field MAY reuse a `run_id`; the control exchange follows the
  same lock-and-key stance.
- **`contract: segmented-snapshot/v0`** — a ledger-native store MAY publish
  sealed segments as snapshots. A future restore bundle would compose with it;
  this publication does not define one.

## Validation requirements

- Profiles, messages, ledger lines and control exchanges MUST validate
  against their schemas before being acted on.
- Reject fixtures under `rejects/schema/` prove each schema gate can fail
  (EPR-0002 obligation 3). Each pair differs in exactly one field.
- Semantic reject vectors under `rejects/semantic/` prove the vector controls
  detect an invalid or empty behavioral script: unknown op, attempt never
  leased, seq gap, transition after terminal, truncated group, unbound
  binding, digest mismatch, illegal transition, redelivery without expiry.
- Vectors are hand-authored from this document and are the language-neutral
  authority. An implementation's own receipts are never the oracle.
- Identity digests in fixtures are produced by the repository's RFC 8785
  materializer, never by a generic JSON serializer.

## Deferred from this publication

- Portable restore: snapshot cut identity, suffix range, message metadata and
  immutable payload bindings, custody and retention, and the `replay` op.
- Tolerant wall-clock conformance with declared tolerances.
- Cross-queue fan-out.
- Ledger retention, checkpoint and truncation.

## Open items before freeze

- Idempotency window default recommendation.
- Whether `priority` and `ordering_key` need their own vector groups in v0.
- Payload size ceiling and the `payload_ref` threshold recommendation.
- Alignment of envelope field names with CloudEvents where it costs nothing.
