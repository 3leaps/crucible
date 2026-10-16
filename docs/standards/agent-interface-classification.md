---
title: "Agent Interface Classification"
description: "Separate lifecycle relationships, control surfaces, carriers and evidence-derived adapter confidence"
category: "standards"
status: "draft"
version: "0.1.0"
lastUpdated: "2026-10-15"
maintainer: "3leaps-core"
reviewers: ["architecture", "security"]
approvers: ["lead-maintainer"]
tags: ["agents", "classifiers", "interfaces", "reference-data"]
content_license: "CC0"
relatedDocs:
  - "docs/standards/classifiers-framework.md"
  - "schemas/classifiers/v0/agent-interface.schema.json"
  - "schemas/inference-path-taxonomy/v0/README.md"
audience: "implementers"
---

# Agent Interface Classification

These draft dimensions describe separate aspects of one declared agent
interaction. They do not grant control, create an addressable target, or prove
that an adapter works. A **seat** is an agent session with tool use and session
continuity. Bare inference calls, people and non-agent applications are not
seats; they can still be recipients under another contract.

| Dimension | Subject | Values |
| --- | --- | --- |
| `agent-seat-class` | Lifecycle relationship for the addressed session | `unknown`, `live`, `headless`, `hosted` |
| `agent-control-surface` | Selected entrypoint | `unknown`, `interactive-ui`, `invocation`, `session-api`, `embedded-api` |
| `agent-transport` | Carrier at one connection boundary | `unknown`, `stdio`, `unix-socket`, `named-pipe`, `tcp`, `in-process` |
| `agent-adapter-confidence` | Assessment for an exact adapter/surface/operation scope | `unknown`, `never-qualified`, `known-broken`, `drift-or-stale`, `untested-no-drift`, `qualified` |

Canonical definitions are in `config/classifiers/dimensions/agent-*.dimension.json`.
The [value schema](../../schemas/classifiers/v0/agent-interface.schema.json)
validates a nonempty selection of those dimensions. Consumers MAY adopt a subset;
they MUST declare which dimensions they require and reject missing required
values. An adopted but unclassified dimension MUST explicitly use `unknown`.
Omission is not a default, an exemption or `never-qualified`. All values are
opaque strings. The schema's `$defs` also permit consumers to reuse one value
vocabulary without embedding the entire projection.

## Classification scope and hybrids

Classify a **relationship**, not a product name. Establish who manages the
addressed session's native lifecycle in the declared operating context:

1. An external agent provider manages it: `hosted`.
2. The connecting host manages it under an explicit lifecycle delegation:
   `headless`.
3. Its interactive operator retains lifecycle control and participates through
   a cooperative connection: `live`.
4. The relationship is unestablished or cannot be represented: `unknown`.

“Headless” names the delegated relationship here, not the absence of pixels.
An attached UI does not itself change lifecycle ownership. A user-managed
session left running without an attendant is not automatically delegated.
Classification records describe an established relationship; class labels
are never evidence of that delegation.

| Case | Class | Selected surface and carrier |
| --- | --- | --- |
| Host-supervised agent on a rented VM | `headless` | Native API: `session-api`; actual carrier recorded separately |
| UI attaches to an already host-supervised session | `headless` remains | UI: `interactive-ui`; separate controller connection: `session-api` |
| Provider-managed agent opened in a browser | `hosted` | Browser entrypoint: `interactive-ui`; trigger entrypoint, if offered: `session-api` |
| Interactive session left unattended | `live` | No new connection or control permission follows |
| Shared backend serving independently owned sessions | Per addressed session | `session-api`; sharing describes topology, not ownership |
| One executable invocation streams results and exits | Depends on lifecycle relationship | `invocation`; streaming output alone does not make a session API |

Where different entrypoints or hops are used, keep separate scoped
classifications. For example, a proxy can accept `unix-socket` and speak `stdio`
to its child. An in-process SDK wrapping a remote service does not make the
remote hop `in-process`. A control surface can exist without being authorized
for this caller. Neither a census result nor a public endpoint supplies consent.

## Protocols and reference records

ACP, JSON-RPC, HTTP, WebSocket and SSE describe protocols or framing; none is a
carrier value. Cooperative wait, native inbox and webhook describe participation
or delivery patterns; they are not transport values either. Reference records
can describe a composition, with separate request and observation connections.
Do not flatten that composition into a supposedly universal mechanism enum.

Product parties, exact protocol versions, species profiles and adapter builds
are revisioned reference **instances**, not classifier values. Keep their opaque
IDs and exact revisions in the consuming catalog. Inference party records may
use the `harness` role in [inference-path-taxonomy/v0](../../schemas/inference-path-taxonomy/v0/README.md).
That taxonomy describes identity, not machine health or authorization.

A catalog profile describes a possible interface. Actual attachment identity,
node/session incarnation, credentials, policy and registration belong to the
consumer's authority contract. A profile MUST NOT become a control grant merely
because it validates or is retrieved from a trusted catalog.

## Confidence: evidence first, policy separately

Confidence is categorical. The color labels and display order are presentation
hints, not numerical assurance levels. Policies MUST select explicit accepted
states rather than use ordinal thresholds. No state supplies consent, strengthens
a delivery fact or resolves an ambiguous external effect.

An assessment MUST identify its producer, assessment time and evidence,
adapter revision, observed recipient build or surface revision, operation(s),
machine/platform and relevant configuration scope, baseline, and the assessment
policy revision. It MUST state its applicability/freshness conditions. These
bindings live in the adopting observation contract, not the value-only schema.
If the current build or scope cannot be established, exact qualification cannot
be claimed. Provider-reported surface versions are labelled as such; they are
not invented executable hashes.

The consumer evaluates an assessment for one required operation and scope:

- **Unknown:** evidence is unavailable, insufficient or contradictory for a
  current assessment. A missing observation does not prove a failure or prove
  that no baseline ever existed.
- **Grey / never qualified:** the evidence scope establishes that no baseline
  exists for this adapter/surface, or no adapter exists. State which evidence
  scope was searched; do not make an estate-wide claim from one machine.
- **Red / known broken:** applicable evidence demonstrates a required behavior
  or compatibility check fails. A read timeout alone is not proof the remote
  operation did not execute.
- **Orange / drift or stale:** a baseline exists but a relevant change or expired
  validity condition prevents its use. Changed bytes do not themselves prove
  incompatibility; stale qualification does not mean the target is broken.
- **Yellow / untested, no detected drift:** the current build is not qualified,
  but its declared comparable contract matches a baseline and required current
  canaries pass. State the comparison and its coverage gaps. No digest or a
  small version step alone cannot establish no detected drift.
- **Green / qualified:** the exact adapter, recipient revision, required
  operation and platform/configuration scope are qualified; required current
  canaries and freshness conditions also hold.

Use red for a demonstrated applicable failure even if qualification is otherwise
current. Absent such a failure, missing evidence yields unknown; a known absent
baseline yields grey. With a baseline, relevant drift or stale evidence yields
orange; only then consider yellow's comparable-contract conditions or green's
exact qualification. Contradictory observations require explicit reconciliation,
not choosing the most favorable color. A policy accepting a degraded state does
not rewrite it to green.

A read-only canary can establish reachability or detect contract drift within
its scope; it does not qualify turn-start, idle handling, deduplication or restart
recovery. An identical protocol schema is not proof of identical behavior.
Qualification and observation are per operation and machine; aggregate displays
MUST preserve coverage and cannot promote one passing cell to fleet-wide green.

Retain assessments immutably for history. Re-evaluation produces a new assessment;
it does not rewrite earlier evidence. Before dispatch, check applicability to
the current attachment and the current policy independently of registration,
expiry, revocation and other authorization requirements.

## Shape, instance, observation, authority

| Kind | Changes when | Home |
| --- | --- | --- |
| Shape and normative meaning | Consumers must interpret a different contract | Versioned schema and standard |
| Reference instance | New vendor, model, species or protocol fact | Revisioned catalog records |
| Observation | A producer measures a particular machine/build/operation | Attributed evidence with validity conditions |
| Authority | A principal grants, expires or revokes permission | Consumer-specific authorization/registration system |

Pin schema and dimension revisions together. Reference-data publication may use
immutable snapshots and independent query projections; it does not turn a
historical observation into current authorization. Dataset descriptors and
representations can reuse `data-artifact/v0`; this standard introduces no dataset
publication format, protocol catalog, observation envelope or registration schema.

These dimensions and the value schema are draft additions. They do not change
existing classifier schemas, inference identity records or agent-wait semantics.
The [agent-wait contract](agent-wait-contract.md) registers interest and cursor
state; it does not establish a seat's opt-in authority or activate that seat.
