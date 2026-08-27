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
- **Local-only implicit default.** Omitting JobSpec `placement` and
  `backend_ref` resolves only when the referenced offer has exactly one
  declared available local default (`default_local=true`,
  `placement=local`, `availability=available`). Zero or multiple eligible
  defaults is a resolution failure. Hosted submit requires explicit
  JobSpec `backend_ref`, envelope `egress_authorization_ref`, offer
  membership, and egress authorization. There is no silent local→hosted
  fallback.
- **Admission is not a job state.** Receipt `admission` is
  `accepted` | `unknown` | `conflict` | `rejected`. The first job state is
  `admitted`. `accepted` is not started, completed, delivered, or activated.
  Every receipt requires `idempotency_key` and `decided_at`. An accepted
  receipt also requires `catalog_id`, `catalog_revision`, `service_id`,
  `offer_revision`, `job_id`, `resolved_backend_ref`,
  `resolved_placement`, and `observe_hint`. `unknown`, `conflict`, and
  `rejected` require `reason_code`. `unknown` MUST NOT invent `job_id`,
  `resolved_backend_ref`, `resolved_placement`, or `observe_hint`.
- **Digest-bound scoped idempotency.** `idempotency_key` is required. Scope
  is authenticated `actor_ref` + `service_id` + key. Receipts correlate by
  `submit_ref` = submit `message_id`. The JobSpec is canonicalized with RFC
  8785 (JCS) and bound by SHA-256. `jq -S` is not JCS. An exact retry of the
  same scoped digest MUST reuse the same `job_id`. A different digest is a
  hard conflict regardless of `job_id`. An `unknown` admission MUST be
  resolved before a later scoped resubmit.
- **Legal transitions; terminals never leave.** Job states include
  `partial`, `expired`, and observational `unknown`.
  `cancel_admission=accepted` is not "worker stopped".
  `cancel_requested → running` / `succeeded` / `partial` / `failed` /
  `expired` are honest races.

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
| `service_offer`            | Immutable method, artifact requirements, and backends. |
| `job_submit_request`       | Structured JobSpec + RFC 8785 digest; required key.    |
| `job_admission_receipt`    | `accepted` / `unknown` / `conflict` / `rejected`.      |
| `job_status_request`       | Ask for state at or after `minimum_state_version`.     |
| `job_status`               | Versioned state, backend, progress, and observe hint.  |
| `job_result_request`       | Ask for the result.                                    |
| `job_result`               | Terminal outcome only.                                 |
| `job_cancel_request`       | Ask to cancel; required `idempotency_key`.             |
| `job_cancel_receipt`       | Cancel admission plus `job_state` and `state_version`. |
| `service_job_error`        | Closed-envelope error, including `result_not_ready`.   |

## Frozen Rules

- **Catalog and offer.** Catalog list/describe and the offer carry
  `catalog_id`. A list request MAY carry `filters`. Each catalog service
  carries `offer_summary` (`method_id`, `availability`, `cancel_posture`).
  A `service_offer` also requires `cancel_posture`, overall
  `availability`, `default_backend_ref`, `required_actions`,
  `retention_ref`, `policy_ref`, `method_id`, `display_name`,
  `description`, `parameters_schema_ref`, `input_requirements`,
  `output_requirements`, and one or more `BackendOffer`s. Each backend
  declares `availability`, `default_local`, `cost_class`, `egress`,
  `limits`, `worker_version`, and optional `policy_claims` /
  `provenance_claims`. Artifact requirements MAY add `max_bytes` and
  `provenance_required`. `default_local=true` implies `placement=local`
  and `availability=available`.
- **JobSpec.** Closed object: `catalog_id`, `catalog_revision`,
  `offer_revision`, `service_id`, `requester_ref`, `inputs` (artifact
  refs), `parameters`, `outputs` (role slots), `deadline`, and optional
  `backend_ref` / `placement`. Hosted placement on the JobSpec requires
  `backend_ref`. Submit `placement` and `backend_ref` live only on the
  JobSpec; the envelope MUST NOT carry undigested copies. Envelope
  `catalog_id`, `service_id`, `catalog_revision`, and `offer_revision`
  are citations and MUST match the JobSpec. Provider- or CLI-specific fields
  (`cli_args` and kin) are rejected at the contract boundary. Parameters
  MUST validate against the referenced portable schema. The carried
  `job_spec_digest` MUST be the RFC 8785 SHA-256 of that JobSpec;
  a tampered body or a tampered digest is rejected before semantic use.
- **Artifact refs.** An `ArtifactRef` may carry `descriptor_ref`,
  `representation_id`, `profile`, `media_type`, and `digest` in addition to
  `artifact_ref` and `role`. Offers constrain cardinality, profile, media
  type, and whether a digest is required. No credentials and no
  machine-local paths. Audio travels as a `data-artifact` descriptor using
  profile-qualified tokens and `media_type`. This family does not bump the
  data-artifact base enums.
- **JobSpec digest.** Changing any digest-covered component
  (`catalog_id`, `catalog_revision`, `offer_revision`, `service_id`,
  `requester_ref`, `backend_ref`, `placement`, `inputs`, `parameters`,
  `outputs`, `deadline`) MUST change the RFC 8785 SHA-256. Catalog pages
  pair by `request_ref`. Offers and accepted admissions pair to submits
  by catalog identity, service, catalog revision, and offer revision.
  Unrelated interleaved exchanges MUST NOT be globally paired. Instant
  comparisons use the portable RFC3339 helper
  (`YYYY-MM-DDThh:mm:ss[.fraction]Z` or a colon-separated numeric
  offset). Equivalent offsets are the same instant. Basic date/time,
  week dates, ordinal dates, missing seconds, a space separator, and
  offsets without a colon fail closed. Leap seconds (`hh:mm:60`) are
  not admitted.
- **`observe_hint`.** `method_id` is `job_complete`, `subject_kind` is
  `service_job`, `subject_id` is the `job_id`. The hint MUST NOT carry a
  start position. The consumer's agent-wait registration supplies
  `baseline_policy` XOR `start_anchor`.
- **Status.** `job_status_request` requires `minimum_state_version`.
  `job_status` requires monotonic `state_version` (including same-state
  progress), `updated_at`, `resolved_backend_ref`, `progress`, and
  `observe_hint`. `failed` requires `error`. Order transitions by
  `state_version`, not envelope `created_at`.
- **Result.** `job_result` is terminal only:
  `succeeded` | `failed` | `cancelled` | `partial` | `expired`.
  Required: `job_spec_digest`, `resolved_backend_ref`, `finished_at`,
  always-present `outputs` array, `result_digest`, and `worker_version`.
  Optional `model_ref`. `succeeded` and `partial` require at least one
  output. `failed`, `cancelled`, and `expired` require `reason_code`.
  Not-ready is `service_job_error` with `error_code` `result_not_ready`,
  never a `job_result`.
- **Cancel.** `job_cancel_request` requires `idempotency_key`. The receipt
  requires `cancel_request_ref`, `state_version`, `idempotency_key`,
  `decided_at`, and `cancel_admission` of
  `accepted` | `refused` | `unsupported` | `unknown`. Non-accept decisions
  require `reason_code`. Exact replay of the same scoped key MUST repeat
  the admission. A conflict on that key is rejected.
- **Errors.** `service_job_error` requires `operation`
  (`catalog_list` | `service_describe` | `job_submit` | `job_status` |
  `job_result` | `job_cancel`), a stable `error_code`
  (`result_not_ready` | `offer_revision_mismatch` | `idempotency_conflict`
  | `unknown_admission` | `unauthorized` | `invalid_job_spec` |
  `backend_unavailable` | `cancel_unsupported` | `timeout` | `internal`),
  `redacted_message`, and `retryable`. Optional: `retry_after_s`,
  `detail_ref`, `related_ref`.
- **One `job_complete` event.** A single stable event identity references the
  terminal `job_result`. It is not a second waiter.
- **Legal transitions.**

  | From               | To                                                                           |
  | ------------------ | ---------------------------------------------------------------------------- |
  | `admitted`         | `queued`, `running`, `cancel_requested`, `cancelled`, `failed`, `expired`    |
  | `queued`           | `running`, `cancel_requested`, `cancelled`, `failed`, `expired`              |
  | `running`          | `succeeded`, `failed`, `cancel_requested`, `cancelled`, `partial`, `expired` |
  | `cancel_requested` | `cancelled`, `succeeded`, `failed`, `running`, `partial`, `expired`          |
  | `unknown`          | any non-observational job state                                              |
  | `succeeded`        | (none)                                                                       |
  | `failed`           | (none)                                                                       |
  | `cancelled`        | (none)                                                                       |
  | `partial`          | (none)                                                                       |
  | `expired`          | (none)                                                                       |

  `admitted → succeeded` is illegal: admission is not completion. Terminals
  never leave.

## Canonicalization

JobSpec idempotency uses RFC 8785. Official-style conformance vectors live
at `schemas/service-job/v0/canonicalization/rfc8785/` and cover ECMAScript
number serialization (exponent zero-padding, `1e-6` / `1e21` thresholds,
negative zero, subnormal and min/max finite doubles), I-JSON rejection of
non-finite values, unsafe integers, duplicate object members, and lone
surrogates, UTF-16 key order, and string escaping. Quote, backslash, and
C0 controls are escaped; other Unicode, including U+2028 and U+2029, is
emitted as UTF-8. The friendly JobSpec digest at
`schemas/service-job/v0/canonicalization/jobspec.*` is an integration case,
not the conformance oracle. The control battery recomputes both with the
stdlib-only materializer and refuses `jq -S` as the oracle.

## Relationship To Other Contracts

- **`contract: agent-wait/v0`** — observe via one waiter; the hint does not
  choose the start position.
- **`contract: data-artifact/v0`** — inputs and outputs are artifact refs
  that may carry descriptor identity, representation, profile, media type,
  and digest.
- **`contract: forge-infra/v0`** — side-effecting authority acquisition,
  binding, verification, rotation, revocation, and teardown may execute as
  digest- and idempotency-bound service jobs. The forge plan and receipts
  remain forge-infra artifacts.

## Validation Requirements

- Producers and consumers MUST validate messages against the entry schema
  before acting on them.
- Conformance fixtures live under `schemas/service-job/v0/examples/` and
  `rejects/`. A gate that has never been seen to fail is not a gate.
