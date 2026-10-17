---
title: "Data Acquisition Contract"
description: "Proposed source policy, selected acquisition scope, and shared-capacity registration outcomes"
category: "standards"
status: "draft"
version: "0.0.0"
lastUpdated: "2026-10-17"
maintainer: "core-standards"
reviewers: ["architecture", "security", "data-engineering"]
approvers: ["lead-maintainer"]
tags: ["acquisition", "data", "budgets", "provenance", "contract"]
content_license: "CC0"
relatedDocs:
  - "docs/standards/data-artifact-contract.md"
  - "schemas/coverage-attestation/v0/README.md"
  - "docs/standards/durable-record-contract.md"
  - "docs/standards/segmented-snapshot-contract.md"
  - "docs/decisions/ADR-0014-data-acquisition-contract.md"
audience: "implementers"
---

# Data Acquisition Contract

## Maturity and boundary

`contract: data-acquisition/v0` is a **proposed experimental** contract for
upstream acquisition policy, a selected work scope, and a shared-capacity
registration outcome. It is independent of programming language, scheduler,
transport implementation and storage engine. A structural match is not a
qualified runner, authenticated review, lawful-access determination or export
authorization. No implementation is certified by publishing these schemas.

The governed objects are:

- **Source policy:** the entity/source parent budget, supplied terms review,
  transport declarations, target vocabulary and redistribution boundary.
- **Acquisition plan:** exact policy and work-manifest pins, original and selected
  scope, cadence, and any attributed compromise.
- **Registration result:** an unavailable, rejected, indeterminate or persisted
  allocation outcome. It never substitutes for per-attempt runtime admission.

This family does not define a downloader, price model, scheduler, authentication
protocol, data parser, storage layout or distributed lease algorithm. The first
meter profile is rolling-window only. Multi-host authority, fixed-window and
token-bucket semantics require separately reviewed profiles. Do not infer those
profiles from a backend's product name.

## Identity and trusted resolution

Resolve the hostless capability through a trusted, pinned `contract.json`.
Instances MUST NOT choose their own schema registry. All objects are closed;
unknown fields, enum values, duplicate JSON keys and invalid pins fail closed.
Many JSON parsers silently keep the last duplicate member, and JSON Schema
validators see only the parsed value, so a consumer MUST detect duplicate keys
while reading the bytes, before shape validation.

A pin is `{id, digest}`. Its `sha256:` digest binds the **exact UTF-8 document
bytes**, including whitespace. Resolve both fields and verify the bytes before
using the object. Reformatting produces a new pin. This family makes no RFC 8785
canonicalization claim. Source identity, plan identity, capture observation and
content identity remain distinct. A repeated content hash does not collapse
separate observations or terms versions.

`entity` identifies the consumer whose activity shares a source's budget;
`source` identifies the upstream policy domain. All jobs and machines using that
authority MUST share its parent budget. Creating another plan, credential or
worker does not create more capacity. A source domain must cover the provider's
actual policy scope, including aliases or endpoints that share a limit.

### Instants

Every timestamp, including timestamp-valued variants, is an RFC 3339 date-time
with an uppercase `Z` UTC designator. Consumers compare exact parsed instants,
never strings. A consumer that cannot represent a value's precision exactly
MUST refuse it rather than truncate or round, so a sub-resolution ordering can
never pass. The wire format sets no precision limit. The fixture checker in this
repository resolves microseconds, refuses non-zero digits beyond six, and accepts
trailing zero digits. Its parser is the strict RFC 3339 profile, not a permissive
ISO 8601 reader.

## Source policy

Schema: `source-policy.schema.json`.

### Access terms and review

`access_terms` carries a supplied current terms digest, reviewed digest,
reviewer role/seat and UTC review time. Equality is a necessary gate, not proof
that the observed digest is current or that a review was authorized. A runner
MUST verify current terms through its trusted observation/review mechanism before
new work. A changed digest, missing review or unavailable required observation
blocks new admission. Historical captures retain their original policy pin.

A terms or meter review after the plan's start is not prior approval. Actor
identifiers are opaque, scope-qualified role/seat records, not signatures.
Credentials MUST be referenced by name. Inline values are forbidden. v0 target
URLs exclude userinfo, query strings and fragments; query parameters belong in a
digest-pinned parameter profile, whose values must be inspected before use.
This is not a general detector of secrets hidden in paths or arbitrary text.

### Budgets and defaults

`meters.requests` is required. Body-byte and error meters may be absent only
when `meter_review.unconfigured` lists exactly those absent meters. Absence means
**unconfigured and reviewed**, not unlimited provider permission. An explicit
zero refuses new work. A zero concurrency limit also refuses new work.

Each meter declares `rolling_window`, a positive window in seconds and a limit.
A declared burst MUST be positive and cannot exceed its rolling-window limit.
This condition alone does not prove that a transport respects every rolling
interval. The runtime governor must enforce the selected window semantics.

When omitted, `headroom_bps` is **2000**: reserve 20% and plan against 80% of the
stated ceiling. Effective quantities MUST be recorded and rounded conservatively;
round capacity downward, required time upward. A caller may choose more headroom.
An explicit value is part of the reviewed policy, never silently overwritten.
JSON Schema default annotations do not apply values; an adapter must do so.

An omitted byte-meter `basis` means `response_body`. `transfer` is a distinct
basis. A runner MUST refuse a basis it has not qualified. Body bytes do not imply
headers, transport framing, prefetch or unread response bodies. The per-response
body cap bounds permitted exposure; declared or observed size is not a reason to
omit an overrun-detection allowance when the implementation consumes one.

Before sending each request, the runtime must reserve its request charge,
worst-case qualified byte exposure and potential error exposure atomically
against the parent authority. Outstanding exposure MUST NOT expire merely
because its admission window elapsed. A sent request remains charged, including
429 responses. Unknown outcomes retain conservative exposure until reconciled.
Retry-After and source cooldown apply across all children. Local storage failures
and upstream failures may have separate classifications, but consumed bytes and
request charges remain accounted for.

This family does not select one settlement-time convention. An adopter profile
MUST name which timestamps charge requests, bytes and errors and demonstrate that
all retries, partials and crash recovery follow that convention.

### Targets and availability

A versioned target set declares stable target IDs, endpoints and a closed set of
variant dimensions. Each target assigns every declared dimension exactly once;
`variants` is empty only when no dimensions are declared. v0 has no omitted-
dimension wildcard or default expansion, and optional or not-applicable
dimensions need a future explicit model rather than inference. Enum values must
be members of their declared vocabulary; revision values are opaque; timestamp
values are UTC instants under the rules below. Unknown dimensions and duplicate
target/dimension identifiers are refused.

A policy catalog holds at most 4096 targets; one plan scope selects at most 256.
These are separate bounds. A plan claims only its own selected scope, never the
whole catalog, and a consumer MUST NOT silently split an oversized selection
into several plans. Separate plans for one entity/source still share its parent
budget.

Every paged endpoint declares a completion rule and page-size ceiling. Cursor and
total-count rules name their required fields. Successful HTTP status is not proof
that a response is complete, valid or within the intended target grid. Required
probe evidence and response validators belong to a digest-pinned adopter profile;
absence of a qualified validator cannot become a completeness claim.

A declared source deletion window is a planning bound. Recurring effective
cadence MUST be strictly shorter than that window. This does not prove that an
already old object survives until the next capture. Runtime source-age checks,
late publication, gaps and deletion-lag alarms remain separately qualified.

### Redistribution

Access review and redistribution review are separate. `redistribution` always
retains `block_export` as the default; a reviewed terms reference does not grant
an export capability. Export authorization comes from a separate trusted policy.
Removal/correction signals may require a tombstone and export hold; a missing
index entry alone is not proof of the reason for disappearance.

## Acquisition plan

Schema: `acquisition-plan.schema.json`.

The plan pins the source policy and a work manifest, names the exact target-set
version, and records its creation/start times. A work manifest is resolved under
a trusted adopter profile that declares its schema, target expansion, request
count, size bounds and completion rules. This family does not fetch or execute
instance-supplied references. A plan with unresolved required inputs is not ready
for registration or execution.

`original_scope` and `effective_scope` contain between 1 and 256 unique target
IDs and a time-scope token. Both use the policy's target vocabulary. A recurring plan declares original and
effective cadence. One-off plans declare neither.

A changed scope or cadence requires `compromise`: chooser, prior choice time,
reason, kind, effective limit and explicit exclusions. The declared limit MUST
match the actual effective scope/cadence. The initial kinds are:

- `lower_frequency`: only cadence increases; target/time scope is unchanged.
- `fewer_targets`: effective targets are a strict subset; time/cadence unchanged.
- `time_scope`: a different time-scope token, unchanged targets/cadence. The
  adopter profile must validate that the new time scope actually narrows work.

A choice never bypasses budget feasibility. Plans remain advisory with
`execution_authorization: none`. Before execution they require entity/source
registration **and** per-attempt admission under a qualified authority.

Scope exclusions, chooser, time and reason MUST propagate into downstream
coverage evidence. A declaration of planned scope uses unknown acquisition
coverage, with no acquired-volume or completeness claim. Actual captures and
extraction later establish their own observed evidence. In particular, choosing
weekly snapshots cannot be reported as complete daily-vintage coverage.

## Registration result

Schema: `registration-result.schema.json`.

The result binds request/idempotency identities, entity/source, policy and plan
pins, and UTC recorded time. Consumers verify those pins against the submitted
request and trusted authority; a matching shape alone is insufficient.

| Outcome | Meaning |
| --- | --- |
| `unavailable` | No qualified registration service was available; no allocation receipt is returned. |
| `rejected` | The authority explicitly refused the proposal; no allocation receipt is returned. |
| `indeterminate` | The caller cannot establish whether a write occurred; a reconciliation key is required. No new capacity may be inferred. |
| `registered` | The named authority durably recorded the named allocation under its declared failure model. |

Only `registered` carries an authority and allocation. The first authority shape
is `single_owner`, with epoch, digest-pinned authority profile and declared
failure model. The profile must explain how ownership is enforced and how stale
owners are fenced. Naming an epoch or using an object bucket is not fencing.

An allocation binds a positive-duration time interval and request quantity, plus
a quantity for each configured byte/error meter and none for an unconfigured
meter. Each quantity MUST NOT exceed that meter's ceiling for the interval: the
headroom-adjusted limit, rounded down, times the number of windows that the
interval spans, rounded up. This is a necessary bound on one allocation in
isolation. It is not evidence that a request schedule is feasible or that every
rolling window inside the interval is respected. The authority MUST check all overlapping
plans against the same parent policy and persist the decision before returning
`registered`. It must bind idempotency keys to the full proposal, return the same
original result for a replay, and refuse conflicting reuse. An uncertain write
requires reconciliation; silence does not mean rejection. No default expiry may
release unknown sent-attempt exposure. Scheduling allocation and runtime attempt
exposure are distinct lifecycles.

### Reconciliation (deferred)

v0 defines no portable reconciliation request or result. An `indeterminate`
result names a `reconcile_key` only. A qualified authority profile MUST define
the lookup identity, return the exact original result for a write it accepted,
state its retention of reconcilable results, and say how late or in-flight
writes are handled. An unknown or absent lookup is neither a rejection nor fresh
capacity. A caller MUST NOT expire, or retry under a fresh idempotency key, an
indeterminate registration. A stub `unavailable` result stays valid because it
allocates nothing. The fixtures in this repository make no reconciliation
conformance claim.

Even a registered result carries `execution_authorization: none`: it records
capacity, not a transferable permission to send requests. A runner still checks
trusted current policy, terms, ownership and each attempt's remaining budget.
Unavailable or stub adapters MUST NOT fabricate registered/admitted outcomes.

## Composition and qualification

- `data-artifact/v0` describes sealed captured representations and protection.
- `coverage-attestation/v0` describes observed or declared coverage and gaps.
- `durable-record/v0` may carry revisioned policy/plan/result records; adopting
  it requires its own exact revision and receipt semantics.
- `segmented-snapshot/v0` may publish a sealed graph of immutable artifacts;
  it is not a mutable queue or live governor journal.
- Application-control's information-source catalog describes an application's
  emitted state/telemetry, not this upstream acquisition policy.

Bucket-compatible adopters can create immutable blobs, sealed event segments and
manifests. A listing yields candidate heads; claims about latest or complete
history require a declared listing/consistency profile and verified committed
chains. Replay uses an explicit committed cut. Retention must preserve all bytes,
bases and deltas needed for every promised historical cut. Physical deletion is
a scoped operation with evidence; a tombstone changes the logical view only.

The fixture controls check structure, pins and selected semantic rules. They do
not exercise a source, prove every rolling interval, allocate capacity, observe
live terms, authenticate actors or qualify durability. Adopters must publish
profile-specific refusal and failure-boundary evidence before claiming those
behaviors. Proposed v0 schemas and publication are not stable promotion.

## Refusal reasons

The reasons below are a portable vocabulary for fixtures and adopter evidence,
not a precedence algorithm. A runtime may use richer diagnostics provided it can
map them to these reasons. An input that breaks exactly one rule MUST be refused
with that rule's reason; an input that breaks several may be refused with any
applicable one. Duplicate member names are always refused while reading bytes,
before shape validation. Every reason has at least one single-fault vector under
`rejects/semantic/`; `rejects/multiple/` holds multiple-fault vectors with their
applicable reasons.

| Reason | Refused when |
| --- | --- |
| `duplicate_key` | Any object repeats a member name |
| `utc_required` | A timestamp is not written as a UTC `Z` instant |
| `unrepresentable_precision` | A timestamp is finer than the consumer can represent exactly |
| `invalid_time` | A timestamp does not parse as a strict RFC 3339 instant |
| `plan_time_order` | The plan is created after its start |
| `terms_changed` | Current and reviewed terms digests differ |
| `review_after_start` | A terms or meter review is later than the plan start |
| `unreviewed_meter_absence` | `unconfigured` does not list exactly the absent meters |
| `zero_meter` | A configured meter has a zero limit |
| `burst_exceeds_window` | A burst is zero or exceeds its window limit |
| `unsupported_meter_basis` | The byte basis is not qualified by the consumer |
| `zero_concurrency` | The transport concurrency limit is zero |
| `duplicate_dimension` | A target set declares a dimension name twice |
| `duplicate_target` | A target set declares a target id twice |
| `unsafe_target_url` | A target URL is not https or carries userinfo, query or fragment |
| `unknown_variant` | A target uses an undeclared dimension |
| `missing_variant` | A target does not assign every declared dimension |
| `variant_outside_vocabulary` | An enum variant value is not declared |
| `policy_pin_mismatch` | The plan's policy pin does not bind the policy bytes |
| `target_set_version` | The plan names a different target-set version |
| `undeclared_target` | A plan scope names a target outside the target set |
| `compromise_required_or_spurious` | Scope or cadence changed without a compromise, or a compromise has no change |
| `choice_after_plan` | The compromise was chosen after the plan was created |
| `scope_limit_mismatch` | The declared limit does not match the effective scope or cadence |
| `invalid_frequency_choice` | `lower_frequency` does not only lengthen a recurring cadence |
| `invalid_target_choice` | `fewer_targets` is not a strict target subset with unchanged time and cadence |
| `invalid_time_scope_choice` | `time_scope` changes targets or cadence, or not the time scope |
| `cadence_reaches_deletion` | Effective cadence is not shorter than the deletion window |
| `registration_policy_binding` | The result's policy pin, entity or source differs from the policy |
| `registration_plan_binding` | The result's plan pin does not bind the plan bytes |
| `registration_time_order` | The result is recorded before the plan was created |
| `invalid_allocation_window` | The allocation interval is empty or opens before the plan start |
| `zero_allocation` | A registered allocation grants zero requests |
| `allocation_missing_meter` | A configured meter has no allocation quantity |
| `allocation_unconfigured_meter` | An allocation carries a quantity for an unconfigured meter |
| `allocation_exceeds_policy` | One allocation exceeds its meter's ceiling for the interval |
