---
title: "Portable Service Job Contract"
description: "Authorization-filtered catalog, digest-bound submit, and legal job lifecycle without silent hosted fallback"
category: "standards"
status: "draft"
version: "0.0.0"
lastUpdated: "2026-08-15"
maintainer: "core-standards"
reviewers: ["architecture", "security"]
approvers: ["lead-maintainer"]
tags: ["service-job", "contract", "idempotency", "catalog", "interoperability"]
content_license: "CC0"
relatedDocs:
  - "docs/standards/agent-wait-contract.md"
  - "docs/standards/data-artifact-contract.md"
audience: "implementers"
---

# Portable Service Job Contract

This draft defines the portable contract identified by
`contract: service-job/v0`.

The contract describes how a consumer lists authorized services, receives an
immutable offer, submits a digest-bound job, and observes admission, status,
result, and cancel — without knowing which worker implements the service. It
is a message contract and a conformance corpus, not a production scheduler.

Companion schemas live in `schemas/service-job/v0/`. Behavioral rules that
JSON Schema cannot prove are enforced by
`scripts/validate-service-job-normative.sh` and the control battery in
`make check`.

## Design Stance

- **Authorization-filtered catalog.** A list response is what the caller may
  see, not a global dump. `catalog_revision` and `offer_revision` are
  immutable. Pagination MUST NOT silently cross revisions.
- **Local-only implicit default.** Omitting `placement` means local. Hosted
  submit requires explicit `backend_ref` and `egress_authorization_ref`.
  There is no silent local→hosted fallback.
- **Admission is not completion.** `accepted` is not started, completed,
  delivered, or activated. An accepted receipt requires `job_id`,
  `resolved_backend_ref`, and `observe_hint`.
- **Digest-bound idempotency.** The JobSpec is canonicalized with RFC 8785
  (JCS) and bound by SHA-256. `jq -S` is not JCS. An exact retry of the same
  digest MUST reuse the same `job_id`. A different digest is a hard conflict.
  An `unknown` admission MUST be resolved before retry.
- **Legal transitions; terminals never leave.** `cancel_admission=accepted`
  is not "worker stopped". `cancel_requested → succeeded` is an honest race.

## Capability And Versioning

Instances MUST carry the host-less capability token:

```json
{
  "capabilities": ["contract: service-job/v0"]
}
```

Consumers resolve the token to a trusted `contract.json`, verify
`capability`, and load the relative `entry_schema`. Resolution MUST fail
closed when the manifest is missing, the capability does not match, or the
entry schema is missing. The schema `$id` is
`contract:service-job/v0/service-job-message.schema.json`.

v0 admits exactly thirteen `message_type` values.

## Envelope

Every message is a closed object. Required: `capabilities`, `message_type`,
`message_id`, `correlation_id`, `created_at` (RFC3339), `actor_ref` (never a
credential). Optional: `causation_id`, `grant_ref`,
`verification_receipt_ref`, `policy_decision_ref`.

## Message Kinds

| Kind                       | Role                                                   |
| -------------------------- | ------------------------------------------------------ |
| `catalog_list_request`     | Authorization-scoped page, optionally revision-pinned. |
| `catalog_list_response`    | Filtered page bound to `catalog_revision`.             |
| `service_describe_request` | Ask for one service at a catalog revision.             |
| `service_offer`            | Immutable offer plus backends.                         |
| `job_submit_request`       | JobSpec + RFC 8785 digest; local default.              |
| `job_admission_receipt`    | `accepted` / `unknown` / `conflict` / `rejected`.      |
| `job_status_request`       | Ask for current state.                                 |
| `job_status`               | State plus the same start-position-free hint.          |
| `job_result_request`       | Ask for the result.                                    |
| `job_result`               | Terminal outputs, or `result_not_ready`.               |
| `job_cancel_request`       | Ask to cancel.                                         |
| `job_cancel_receipt`       | Cancel admission plus current `job_state`.             |
| `service_job_error`        | Closed-envelope error.                                 |

## Frozen Rules

- **`observe_hint`.** `method_id` is `job_complete`, `subject_kind` is
  `service_job`, `subject_id` is the `job_id`. The hint MUST NOT carry a
  start position. The consumer's agent-wait registration supplies
  `baseline_policy` XOR `start_anchor`.
- **Succeeded result.** Requires at least one output. A non-terminal result
  MUST use `reason_code` `result_not_ready`.
- **Artifact refs.** No credentials and no machine-local paths. Audio travels
  as a `data-artifact` descriptor using profile-qualified tokens and
  `media_type`. This family does not bump the data-artifact base enums.
- **One `job_complete` event.** A single stable event identity references the
  terminal `job_result`. It is not a second waiter.
- **Legal transitions.**

  | From                                 | To                                                |
  | ------------------------------------ | ------------------------------------------------- |
  | `accepted`                           | `queued`, `running`, `cancel_requested`, `failed` |
  | `queued`                             | `running`, `cancel_requested`, `failed`           |
  | `running`                            | `succeeded`, `failed`, `cancel_requested`         |
  | `cancel_requested`                   | `cancelled`, `succeeded`, `failed`                |
  | `succeeded` / `failed` / `cancelled` | (none)                                            |

  `accepted → succeeded` is illegal: admission is not completion.

## Canonicalization

JobSpec idempotency uses RFC 8785. Checked-in vectors live at
`schemas/service-job/v0/canonicalization/`: the input document, the expected
canonical bytes, and the SHA-256 of those bytes. The control battery
recomputes the bytes with the stdlib-only materializer and refuses `jq -S`
as the oracle.

## Relationship To Other Contracts

- **`contract: agent-wait/v0`** — observe via one waiter; the hint does not
  choose the start position.
- **`contract: data-artifact/v0`** — inputs and outputs are artifact refs
  plus optional profile tokens / `media_type`.

## Validation Requirements

- Producers and consumers MUST validate messages against the entry schema
  before acting on them.
- Conformance fixtures live under `schemas/service-job/v0/examples/` and
  `rejects/`. A gate that has never been seen to fail is not a gate.
