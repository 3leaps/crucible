---
title: "Agent Interface Profiles"
description: "Revisioned protocol composition, continuity and delivery declarations for agent operations"
category: "standards"
status: "draft"
version: "0.1.0"
lastUpdated: "2026-10-16"
maintainer: "3leaps-core"
reviewers: ["architecture", "security"]
approvers: ["lead-maintainer"]
tags: ["agents", "interfaces", "profiles", "protocols"]
content_license: "CC0"
relatedDocs:
  - "docs/standards/agent-interface-classification.md"
  - "docs/standards/agent-wait-contract.md"
  - "schemas/classifiers/v0/agent-interface-profile.schema.json"
audience: "implementers"
---

# Agent Interface Profiles

An interface profile is an immutable, revisioned **declaration** of one
operation's possible interface composition. It complements the
[classifier values](agent-interface-classification.md); it is not a live seat
registry, capability negotiation, observation envelope, grant or delivery receipt.
It does not launch a process or prove that a declared behavior works.

The [profile schema](../../schemas/classifiers/v0/agent-interface-profile.schema.json)
is a separate closed object. Existing value-only projections remain unchanged.
The profile has an ID, revision, schema version, operation pin, endpoint roles,
connection bindings, continuity declaration and delivery declaration. Different
operations or incompatible configurations SHOULD have separate profile revisions.
Products, builds and platforms reference profiles from revisioned catalog records;
actual applicability is established by separate operation-scoped evidence.

## Pins and validation

A pin is `{id, revision}`. The pair MUST resolve to immutable content through
the consumer's trusted catalog. Revision is opaque, not a sortable version or
permission. Floating aliases such as `latest` MUST NOT be used as revisions.
Syntactic validity alone cannot prove immutability. Consumers MUST pin the schema,
classifier definitions and profile together (including artifact digests in their
adoption manifest), reject missing/conflicting pins, and fail closed when a
required referenced contract cannot be resolved. Do not fetch arbitrary URLs
from profile fields. IDs are references, never credentials or live addresses.

Run JSON Schema validation, then
`python3 scripts/validate-agent-interface-profile.py <profile.json>` for the
combined schema and local-reference checks. The checker verifies unique IDs,
endpoint/binding/signal references and the minimum graph rules below. A trusted
catalog resolver must additionally check the meaning and exact contents of pins;
the repository checker neither retrieves them nor qualifies a native adapter.

All fields are explicit; `unknown` means unestablished, `unsupported` means
declared absent, and `supported` means declared present, **not qualified**.
Consumers MUST NOT upgrade unknown or omitted information into eligibility.
No ordering among these values supplies authorization or confidence.

## Per-hop bindings

Endpoint IDs are local role labels, not runtime identities. Exactly one endpoint
has role `agent`: this is the subject of the continuity declaration. At least one
is a `controller`; optional `intermediary` endpoints represent proxies. All
endpoints MUST participate in a connected graph reaching the agent. Each binding
connects two distinct declared endpoints and has its own ID, selected control
surface, carrier, and protocol stack. Request and observation connections MAY be
separate bindings. The graph expresses possible connections, not a routing table,
execution order, delegation chain or authorization path.

`initiator` and `acceptor` identify connection roles; they do not restrict message
direction. Responses and server-initiated callbacks can travel the reverse way.
Classify the surface exposed by the acceptor at that boundary. An embedded wrapper
does not turn its subsequent network connection into `in-process`.

`protocol_stack` lists layers from application outward toward the carrier, in
encapsulation order. Each layer has a role and an exact protocol/dialect pin.
For example, an application dialect may use a JSON-RPC envelope, newline framing
and standard streams; another binding may use HTTP, SSE and TLS over TCP. These
are compositions, not alternatives in a single protocol-family enumeration.
Layer roles may recur when nesting actually requires them. The referenced
protocol specifications define how the layers compose. The schema does not
establish wire compatibility from their names or validate encryption behavior.

A null stack explicitly means that composition is unknown. A non-null stack
MUST describe the complete relevant composition, not a known fragment presented
as a full stack. Unknown transport/surface/stack cannot satisfy a consumer that
requires an exact wire binding. Partial research belongs in catalog notes or
observations, not an eligible profile disguised as complete.

## Continuity: three identities, independent capabilities

The consumer binds the profile to **logical session**, **native execution
incarnation** and **controller attachment** identities separately. None of these
is the profile ID, an endpoint role label, a process ID alone or a control grant.

| Field | Meaning for the agent endpoint |
| --- | --- |
| `execution_lifetime` | `bounded`: native execution terminates after its assigned unit of work; `resident`: execution can remain between units; `unknown`: unestablished |
| `context_persistence` | `volatile`: context exists only within that execution; `durable`: recoverable context can outlive it; `unknown`: unestablished |
| `resume` | Ability to restore durable context into a new execution incarnation |
| `reconnect` | Ability to establish a new controller attachment to the same surviving execution incarnation |

Resume support requires durable context. Durable storage alone does not imply a
resume API, full transcript restoration, recovery of pending operations or any
retention guarantee. A bounded invocation can resume durable context; a resident
execution can also be resumable. Neither `session-api` nor `headless` implies
persistence. The operation's pinned specification MUST state what resume restores,
its retention/compatibility conditions, and how same-incarnation reconnect is
verified. Context transfer into a new incarnation is never proof that old work
completed or did not execute.

Before reconnect/resume or further work, the host MUST recheck exact attachment
identity, ownership/delegation, policy, and assessment applicability. An ownership
generation fences an already authorized relationship; it does not create one.
Unknown operation effects survive even if ownership recovery succeeds. No profile
authorizes teardown of discovered processes or replay of uncertain work.

## Participation and evidence meanings

`participation` describes this operation's path: `native` through a native control
interface, `cooperative` through an opted-in participant, or `provider-mediated`
through an external provider. It is independent of lifecycle seat class. A hosted
agent may expose several paths; use separate profiles for distinct compositions.

`activation` states whether this path requires a distinct activation step:
`none`, `explicit` (with an `activation_contract` pin), or `unknown`. `none` does
not promise automatic execution; admission, capacity, consent and liveness still
apply. Activation support and wait registration are separate contracts.

`signals` maps protocol message pins to declared evidence meanings, a binding,
an emitting endpoint and correlation scopes. It describes available observations,
not observations that have occurred. An empty list claims no signal mappings;
absence of a meaning is not proof that the protocol can never supply it.

| Meaning | Maximum claim from an authenticated, correlated observation |
| --- | --- |
| `delivery-received` | The named emitter received the specified operation input; not necessarily durable admission, forwarding or native execution |
| `execution-started` | The specified native operation began |
| `execution-completed` | The specified native operation terminated; inspect its result for success, rejection, cancellation or failure |
| `cursor-committed` | A consumer committed a retention/continuation position for the named registration and outcome; not execution of the event payload |

Each signal emitter MUST be an endpoint of its binding. Receipt/execution signals
require operation correlation; cursor commits require registration and outcome
correlation. These are minimum scopes, not correlation values. The pinned message
contract MUST define their wire representation, issuer, scope, uniqueness and
lifetime. Actual observations MUST be bound to the current attachment/session/
incarnation as applicable, with evidence and producer attribution. A proxy report
of remote execution MUST preserve the originating evidence and correlation; its
own transport ACK is not an execution signal. Unverified or unmatched reports
remain unknown. Never promote a lower-level ACK, model-written acknowledgement,
transport success or profile validation into execution evidence.

Native completion is separate from application acceptance of the result. This
profile neither defines a task-result acceptance contract nor collapses accepted,
started and completed into a single success flag. A timeout or lost ACK leaves
effects unknown unless independent evidence resolves them. Instance/configuration
operations can have unknown outcomes too.

Deduplication and reconciliation support each require an immutable contract pin
when declared supported; a pin is forbidden for unknown/unsupported states. The
contract MUST specify operation scope, identity/retention bounds and failure
semantics. A dedup claim is not an exactly-once guarantee or replay permission.
Consumers MUST verify current capability, evidence and authority before acting;
missing reconciliation can make a delivery policy ineligible without changing
adapter confidence. Explicit activation likewise requires a contract pin.

## Alignment with agent-wait

[Agent-wait](agent-wait-contract.md) observes events; it does not activate seats.
A live match's `proposed_next_anchor` is a proposal, not a committed cursor. Its
next live wait uses a new consumer-selected registration snapshot. Poll cursor
commit refers to `poll_cycle_ack` paired with its outcome and registration;
retained-event and retained-through constraints still apply. A cursor is opaque,
not an event ID, session ID or operation ID.

No `live_wait_ack` is introduced here. No receipt or execution signal advances a
cursor. Crash-before-ack replay remains possible, and host durable intake and
deduplication must tolerate it under their own contract. The profile schema does
not validate agent-wait messages or supersede its normative checker. Its signal
pin refers to the adopted message contract, not to a new wait message type.

## Adoption boundary

This draft adds a profile shape, not new classifier values or runtime authority.
The host owns attachment credentials, permissions, process lifecycle, callbacks,
deadlines and recovery. A permission callback is a protocol exchange requiring
its own authorized decision; observing it does not grant permission to answer.
Reference profiles remain separately versioned from deployments and their policy.
Consumers may adopt the classifier-only baseline without adopting this companion.
