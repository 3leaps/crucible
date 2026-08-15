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
- **Live match does not commit the cursor.** `proposed_next_anchor` is a
  proposal. The next live wait advances only after a new `registration_set`
  whose `start_anchor` is the consumer-chosen continuation.
- **Transport-neutral.** No socket, webhook, or chat binding is part of this
  family. `delivery_ref` and `activation_ref` are optional and never imply
  agent action; those contracts stay outside this family.
- **Payload by reference.** Event bodies are `payload_ref` only. No embedded
  bodies and no secrets.

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

| Kind                 | Role                                                                                  |
| -------------------- | ------------------------------------------------------------------------------------- |
| `registration_set`   | Snapshot of registrations for one waiter/seat, with a frozen `registration_revision`. |
| `live_wait_request`  | Wait for a live match against that snapshot.                                          |
| `live_wait_outcome`  | Matched events plus `proposed_next_anchor`. Does not commit a cursor.                 |
| `poll_cycle_request` | Poll against the snapshot, naming `required_arms` and absolute deadlines.             |
| `poll_cycle_outcome` | Events, coverage, retained ids, and an outcome kind.                                  |
| `poll_cycle_ack`     | Consumer commit of a cursor. Cannot advance past unretained events.                   |

## Frozen Rules

- **Deadlines.** `run_deadline` is absolute and MUST be `<= logical_deadline`.
- **`no_change`.** Empty `events`, `coverage_complete`, every required arm
  `no_change`, and `completed_at < logical_deadline`.
- **`logical_deadman`.** Empty `events`, complete non-degraded required
  coverage, and `completed_at >= logical_deadline`.
- **Outage is not clean.** A required-arm `outage` or `cursor_uncertain`
  (or a degraded required arm) MUST NOT validate as `no_change` or
  `logical_deadman`.
- **Ack vs retention.** `poll_cycle_ack` MUST NOT commit an anchor or ack an
  event id that the paired outcome did not retain.
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
