---
title: "Portable Agent Wait Contract"
description: "Transport-neutral wait/poll contract for one aggregate waiter per consuming seat"
category: "standards"
status: "draft"
version: "0.0.0"
lastUpdated: "2026-08-15"
maintainer: "core-standards"
reviewers: ["architecture", "security"]
approvers: ["lead-maintainer"]
tags: ["agent-wait", "contract", "cursor", "poll", "interoperability"]
content_license: "CC0"
relatedDocs:
  - "docs/standards/service-job-contract.md"
  - "docs/standards/data-artifact-contract.md"
audience: "implementers"
---

# Portable Agent Wait Contract

This draft defines the portable contract identified by
`contract: agent-wait/v0`.

The contract describes how a consumer registers interest in subject events and
receives them through live wait or poll cycles, without knowing which transport
or provider implements the waiter. It is a message contract, not a daemon, not
a delivery bus, and not an activation protocol.

Companion schemas live in `schemas/agent-wait/v0/`. Behavioral rules that JSON
Schema cannot prove are enforced by the repository's normative checker
(`scripts/validate-agent-wait-normative.sh`) and the control battery in
`make check`.

## Design Stance

- **One aggregate waiter per consuming seat.** A `registration_set` is the
  snapshot for that waiter. Replacing the snapshot emits a new set; it does
  not mutate the previous one.
- **Start position is explicit.** Every registration carries exactly one of
  `start_anchor` (exclusive continuation) or `baseline_policy`
  (`latest` | `earliest` | `provider_defined`). Omitted position is invalid.
  There is no implicit provider default.
- **Anchors are provider-opaque.** An exclusive continuation cursor has
  `kind` `provider_opaque`. Its `value` is not a source `event_id` and MUST
  NOT be treated as one. Stable event identity lives on `events[].event_id`
  and on ack/retention event-id lists.
- **Live match does not commit the cursor.** `proposed_next_anchor` is a
  proposal. The next live wait advances only after a new `registration_set`
  whose `start_anchor` is the consumer-chosen continuation.
- **Transport-neutral.** No socket, webhook, or chat binding is part of this
  family. `delivery_ref` and `activation_ref` are optional and never imply
  agent action; those contracts stay outside this family.
- **Payload by reference.** Event bodies carry a structured `payload`
  (`payload_ref`, `content_digest`, optional `media_type`). No embedded
  bodies and no secrets. `payload_ref` is never a bare token at the event
  surface.

## Capability And Versioning

Instances MUST carry the host-less capability token:

```json
{
  "capabilities": ["contract: agent-wait/v0"]
}
```

Consumers resolve the token to a trusted `contract.json`, verify
`capability`, and load the relative `entry_schema`. Resolution MUST fail
closed when the manifest is missing, the capability does not match, or the
entry schema is missing. The schema `$id` is
`contract:agent-wait/v0/agent-wait-message.schema.json`. Direct `$id` lookup
is valid for schema-aware tooling; it is not the contract-entry mechanism.

v0 admits exactly six `message_type` values. There is no `live_wait_ack` and
no undeclared `x-` kind.

## Envelope

Every message is a closed object. Required: `capabilities`, `message_type`,
`message_id`, `correlation_id`, `created_at` (RFC3339), `actor_ref` (an
identity reference, never a credential). Optional: `causation_id`,
`grant_ref`, `verification_receipt_ref`, `policy_decision_ref`.

## Message Kinds

| Kind                 | Role                                                                                                               |
| -------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `registration_set`   | Snapshot of registrations for one waiter/seat, with principal, authn, aggregate limits, and a registration digest. |
| `live_wait_request`  | Wait for a live match against that snapshot.                                                                       |
| `live_wait_outcome`  | Discriminated wait result. `events` is not required for every kind.                                                |
| `poll_cycle_request` | Poll against the snapshot: required arms, fairness, per-registration acknowledged anchors, activation, and cycle.  |
| `poll_cycle_outcome` | Discriminated poll result plus per-registration retention, fairness, and coverage arms.                            |
| `poll_cycle_ack`     | Consumer commit of per-registration opaque cursors. Cannot advance past unretained events.                         |

## Frozen Rules

- **Deadlines.** `run_deadline` is absolute and MUST be `<= logical_deadline`.
  Comparisons use portable RFC3339 instants and MUST fail closed on an
  unparseable timestamp.
- **Outcome kinds.** Live and poll share the same `outcome_kind` vocabulary:
  `events` | `no_change` | `logical_deadman` | `partial` | `cancelled` |
  `coverage_degraded` | `refused` | `reauthentication_required` | `failed`.
  `cancelled`, `refused`, `reauthentication_required`, and `failed` require
  `reason_code`.
- **`no_change`.** Empty `events`, `coverage_complete`, every required arm
  `no_change` and not degraded, and `completed_at < logical_deadline`.
- **`logical_deadman`.** Empty `events`, complete non-degraded required
  coverage, and `completed_at >= logical_deadline`.
- **Outage is not clean.** A required-arm `outage`, `cursor_uncertain`, or
  `degraded` MUST NOT validate as `no_change` or `logical_deadman`. Report
  `coverage_degraded` (or another non-clean kind) instead.
- **Fairness.** Poll request and outcome carry `fairness_cursor`. The
  outcome also carries `next_fairness_cursor`. A required arm MAY be
  `deferred` in one cycle; a noisy arm MUST NOT keep another required arm
  deferred across successive outcomes that never rotate the fairness
  cursor.
- **Bounds.** Poll request and outcome MAY carry `bound`
  (`max_events`, `max_payload_refs`) when the provider degrades or
  truncates a cycle.
- **Registration set.** Required: `principal_ref`, `logical_deadline`,
  `authn_mode` (`required` | `optional` | `disabled`), `aggregate_limits`
  (`max_events`, `max_bytes`), and `registration_digest` (RFC 8785 SHA-256
  of the `registrations` array). Each registration requires `required`,
  `source_instance_ref`, `predicate_ref`, `capability_ref`,
  `lease_expires_at`, and per-registration `bounds`, plus the start-position
  XOR. `authn_mode=required` needs a `verification_receipt_ref` on the wait
  request, or the outcome MUST be `reauthentication_required`. A completed
  wait after `lease_expires_at` MUST be `reauthentication_required`.
  Exceeding per-registration or aggregate bounds is valid only as `partial`
  or `coverage_degraded`.
- **Events.** Each `waitEvent` carries `registration_id`,
  `source_instance_ref`, `start_anchor`, `proposed_next_anchor`,
  `observed_at`, provider timestamp `occurred_at`, `replay_status`
  (`fresh` | `replay`), `correlation_id`, optional `causation_id`, and
  structured `payload`.
- **Coverage arms.** Each arm carries `registration_id`, `start_anchor`,
  `proposed_next_anchor`, `event_count`, and `byte_count`. `reason_code` is
  required when `status` is `outage` or `cursor_uncertain`, or when
  `degraded` is true.
- **Ack vs retention.** Pair `poll_cycle_ack.outcome_ref` to the outcome
  `message_id`. Poll request `acknowledged_anchors`, outcome
  `retained_through` / `retained_events` / `proposed_next_anchors`, and ack
  `committed_anchors` / `retained_events` are maps keyed by
  `registration_id`. An empty acknowledged map is a first cycle. Each
  committed anchor MUST equal that registration's `retained_through`. Each
  acked event id MUST be a subset of that registration's retained events.
  A commit MUST NOT apply another registration's cursor or events. The
  opaque anchor value is not an event id.
- **Crash-before-ack.** A later outcome MAY replay stable event ids. The
  cursor MUST NOT silently advance across unacked events.
- **Revision freeze.** Live and poll requests MUST cite the
  `registration_revision` of the referenced `registration_set`.

## Relationship To Other Contracts

- **`contract: service-job/v0`** — a job admission may carry an
  `observe_hint` (`method_id=job_complete`, `subject_kind=service_job`,
  `subject_id=job_id`) with **no** start position. The consumer's
  `registration_set` supplies `baseline_policy` XOR `start_anchor`. One
  stable `job_complete` event identity references the terminal job result.
  That is not a second waiter.
- **`contract: data-artifact/v0`** — event payloads are artifact or message
  refs, not embedded bytes.

## Validation Requirements

- Producers and consumers MUST validate messages against the entry schema
  before acting on them.
- Conformance fixtures live under `schemas/agent-wait/v0/examples/` and
  `rejects/`. A gate that has never been seen to fail is not a gate.
