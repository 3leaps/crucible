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
conformance. It does **not** define a storage engine, a table layout, a file
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
- **A lease is a value with a fence.** Every delivery carries a lease: message
  id, opaque fencing token, attempt number and expiry. `ack`, `nack`, `extend`
  and `fail` present the lease and the broker checks the token. A stale token
  yields the outcome `stale_lease`, which is expected and is not an error.
- **The broker owns the clock.** Timestamps are assigned by the broker,
  RFC 3339 in UTC, millisecond precision. An implementation started in test
  mode exposes `advance_clock`; a conforming implementation MUST NOT accept
  it otherwise.
- **State is a fold over the ledger.** Each transition appends exactly its
  ledger events in the same atomic step as the state change, or the profile
  declares `ledger: inferred`. Queue state at any `seq` is derivable from the
  ledger alone plus a store snapshot for payloads.
- **Everything is a batch.** Enqueue, claim, extend, ack, nack and fail take
  arrays. A single item is a batch of one. Outcomes are positional.
- **Roles are separate surfaces.** Producer, consumer and admin operations
  are separable so a service that only enqueues need not hold claim or purge
  rights.
- **Pull is the primitive.** Handler registries, concurrency control and
  backoff policy live in a worker library above this contract.
- **Closed vocabulary.** Unknown ops, event types, outcomes and error codes
  fail closed. There is no `x-` extension prefix in v0.
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
| `idempotency_key` | Producer-chosen. Scope is the queue. A repeat within the backend's idempotency window returns the original receipt with `deduplicated: true`. |
| `payload_contract` | Host-less token naming the payload's own contract. Carried, never validated by the broker. |
| `payload_ref` | A `contract: data-artifact/v0` reference. Requires capability `payload_ref`. |
| `not_before` | Requires `delay`. The message is not ready before this time. |
| `expires_at` | After this time the message is purged with reason `expired` and never delivered. |
| `max_attempts` | Default 5. The attempt at which a `nack` dead-letters instead of returning the message to ready. |
| `parent_id` | Set by `fan_out` on children. |
| `ordering_key`, `priority` | Each requires its capability. |
| `trace` | W3C traceparent, carried verbatim. |
| `attributes` | String map, producer-owned, never interpreted. |

### Lease

Not a stored object. A value returned by `claim`: `{message_id, token,
attempt, until}`. The token is opaque, unique per lease, and MUST NOT appear
in the ledger. The attempt number identifies the lease in the ledger.

### Ledger event

Schema: `ledger-event.schema.json`. One NDJSON line per event. `seq` is
monotonic per queue and gap-free; it is the replay cursor. A gap or
regression is corruption.

| Type | Appended when | Required fields beyond the envelope |
| --- | --- | --- |
| `enqueued` | A new message is accepted | `payload_digest`; `idempotency_key` if present; `parent_id` for children; `not_before` if delayed |
| `deduplicated` | An enqueue repeats a live key | `idempotency_key` |
| `leased` | A claim delivers the message | `attempt`, `worker`, `lease_until` |
| `extended` | A live lease is extended | `attempt`, `lease_until` |
| `acked` | A live lease is acked | `attempt` |
| `nacked` | A live lease is nacked | `attempt`; `reason`; `not_before` when the message returns to ready |
| `lease_expired` | A sweep finds an expired lease | `attempt` |
| `dead_lettered` | Attempts exhausted, or `fail` | `reason` |
| `redriven` | An admin returns a dead letter to ready | none |
| `purged` | An admin purge, or expiry | `reason` |

`payload_digest` is SHA-256 of the RFC 8785 canonical `payload`, or of the
referenced artifact bytes under `payload_ref`. The ledger never carries the
payload. Replay into a new backend therefore needs the ledger plus a store
snapshot; audit needs the ledger alone.

Stale-lease operations append nothing. A `deduplicated` event is appended so
that producer retries are visible in audit.

### Capability profile

Schema: `capability-profile.schema.json`. The discovery root. Two blocks are
mandatory and MUST be kept distinct:

- `build`: immutable facts about the artifact: version, target, native
  dependencies, compiled backends, compiled capabilities. A build with no
  native dependencies says nothing about durability.
- `runtime`: effective facts for the configuration exercised: selected
  backend, durability boundary, enabled capabilities. `enabled_capabilities`
  MUST be a subset of `build.compiled_capabilities`.

`origin: harness` means the conformance harness produced the profile from
observed runs. `origin: declared` is an unverified claim and MUST NOT be
presented as conformance evidence.

Capabilities in v0: `transactional_enqueue`, `atomic_fanout`, `delay`,
`fenced_ack`, `ordering_key`, `priority`, `payload_ref`, `long_poll`,
`virtual_clock`.

### Control exchange

Schema: `control-exchange.schema.json`. Line-delimited JSON request and
response over stdio or a local socket, in the shape of the process-run
control channel. Daemon deployments require `token` on every request and
reject failures with `unauthorized`, indistinguishable for wrong versus
unknown token. Harness stdio mode MAY omit the token.

| Role | Op | Semantics |
| --- | --- | --- |
| Producer | `enqueue` | `{queue, messages[]}` → one receipt per message, positional. |
| Consumer | `claim` | `{queue, worker, max, lease_ms, wait_ms}` → deliveries, each with a lease. `wait_ms > 0` requires `long_poll`. |
| Consumer | `extend` | `{leases[], lease_ms}` → one outcome per lease. |
| Consumer | `ack` | `{leases[]}` → outcomes. |
| Consumer | `nack` | `{leases[], retry_after_ms, reason}` → outcomes. Counts the attempt. |
| Consumer | `fail` | `{leases[], reason}` → outcomes. Dead-letters immediately. |
| Consumer | `fan_out` | `{parent: lease, children[]}` → receipts. Requires `atomic_fanout`. |
| Admin | `stats`, `peek`, `redrive`, `purge`, `sweep` | Inspection and repair. `sweep` expires overdue leases and purges expired messages. |
| Admin | `export_ledger` | `{queue, from_seq}` → NDJSON lines. |
| Admin | `replay` | Apply ledger lines plus a snapshot into an empty backend. |
| Any | `capabilities` | Returns the profile. |
| Test | `advance_clock` | `{by_ms}`. Present only under `virtual_clock` in test mode. |

Lease outcomes: `ok`, `stale_lease`, `unknown_message`. Error codes:
`unknown_op`, `invalid_params`, `unauthorized`, `unknown_queue`,
`capability_unsupported`, `payload_too_large`, `backend_unavailable`,
`internal`.

## Portable invariants

1. **Fencing.** An `ack`, `nack`, `extend` or `fail` whose token does not
   match the live lease for that message returns `stale_lease` and changes
   nothing.
2. **Single live lease.** At most one live lease exists per message. A
   `claim` never delivers a message with a live lease.
3. **Attempt monotonicity.** Each `leased` event for a message carries an
   attempt strictly greater than the previous.
4. **Expiry before redelivery.** A message is redelivered only after a
   `lease_expired` or `nacked` event for its previous attempt.
5. **Dead-letter boundary.** A `nack` at `attempt >= max_attempts` appends
   `nacked` then `dead_lettered` with reason `max_attempts`, in that order,
   in the same atomic step.
6. **Idempotent enqueue.** Within the declared idempotency window, a repeated
   key returns the original `message_id` with `deduplicated: true` and
   appends `deduplicated`, not `enqueued`.
7. **Atomic fan-out.** Under `atomic_fanout`, the children's `enqueued`
   events and the parent's `acked` event are appended in one atomic step, in
   that order. Without the capability, `fan_out` returns
   `capability_unsupported` and the consumer enqueues children with
   deterministic idempotency keys derived from the parent and recipient, then
   acks the parent.
8. **Durability claim.** An acknowledged `enqueue` or `fan_out` survives
   process loss at `group_commit` or stronger. `os_buffered` survives process
   loss only. `none` makes no claim. Profiles MUST state which.
9. **Closed vocabulary.** Unknown ops, event types, outcomes and error codes
   are rejected, not ignored.
10. **Ledger completeness.** Under `ledger: recorded`, folding the ledger from
    `seq` 1 reproduces the queue's state at every `seq`.

## Fold rules

A consumer or auditor reconstructs state by folding events in `seq` order.

| Event | Message state after |
| --- | --- |
| `enqueued` | `ready` (or `delayed` until `not_before`) |
| `deduplicated` | unchanged |
| `leased` | `leased` |
| `extended` | `leased` with new expiry |
| `acked` | `done` (terminal) |
| `nacked` | `ready` or `delayed`, unless followed in the same step by `dead_lettered` |
| `lease_expired` | `ready` |
| `dead_lettered` | `dead` |
| `redriven` | `ready` |
| `purged` | `gone` (terminal) |

`done` and `gone` are terminal. Any event after a terminal state for the same
message is a fold error.

## Conformance

Behavioral vectors live under `schemas/durable-queue/v0/vectors/`, grouped by
the capability they require. A vector is an op script with expected results
and the exact expected ledger. Ids bound with `$name` are substituted from
results; timestamps derive from `clock_start` plus each op's `at_ms`.

Two conformance modes exist and a profile declares which it achieved:

- **deterministic**: `virtual_clock` is enabled, and the normalized ledger
  (ids substituted, timestamps compared exactly) matches byte for byte.
- **tolerant**: wall clock; event order and type match; timestamps and
  `lease_until` are compared with declared tolerances.

Adapters over third-party backends normally achieve only `tolerant`. The
harness, not the implementation, produces the profile it records.

## Relationship to other contracts

- **`contract: service-job/v0`** — a queue transports job messages. The
  JobSpec `idempotency_key` and the queue `idempotency_key` are different
  scopes and MUST NOT be conflated. The service-job standard carries the
  composition note.
- **`contract: data-artifact/v0`** — `payload_ref` bodies are artifacts.
- **`contract: process-run/v0`** — a queue daemon publishes a process card;
  the `worker` field MAY reuse a `run_id`; the control exchange follows the
  same lock-and-key stance.
- **`contract: segmented-snapshot/v0`** — a ledger-native store MAY publish
  sealed segments and checkpoints as snapshots. This is a storage choice,
  not a requirement.

## Validation requirements

- Profiles, messages, ledger lines and control exchanges MUST validate
  against their schemas before being acted on.
- Reject fixtures under `rejects/schema/` prove each schema gate can fail
  (EPR-0002 obligation 3). Each pair differs in exactly one field.
- Vectors are hand-authored from this document and are the language-neutral
  authority. An implementation's own receipts are never the oracle.

## Open items before freeze

- Idempotency window default, and whether it is bounded by ledger retention.
- Ledger retention and compaction: a checkpoint event followed by truncation
  is the expected shape but is not yet specified.
- Whether `priority` and `ordering_key` need their own vector groups in v0.
- Payload size ceiling and the `payload_ref` threshold recommendation.
- Alignment of envelope field names with CloudEvents where it costs nothing.
