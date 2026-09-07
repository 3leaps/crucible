---
title: "Portable Application Control and Observation Contract"
description: "Transport-neutral discovery, control, observation, and evidence for operating an application without driving the content sessions it hosts"
status: proposed
date: "2026-09-06"
last_updated: "2026-09-06"
tags:
  - application-control
  - automation
  - observability
  - security
  - schemas
---

# Portable Application Control and Observation Contract

This standard defines the experimental capability
`contract: application-control/v0`. It gives human tools, agents, SDKs, native
interfaces, and remote adapters one typed way to discover, observe, and operate
an application.

The contract controls the application itself. It does not authorize a
controller to drive a terminal, browser, document, conversation, or other
content session hosted by that application.

## Contract boundary

The portable family owns:

- discovery of one application instance and its immutable catalog references;
- exhaustive operation and information-source catalog shapes;
- transport-neutral request, result, observation, and evidence envelopes;
- replay-safe mutation and optimistic-concurrency inputs;
- explicit event, snapshot, scrape, sample, and client-derived delivery modes;
- separation of interaction, request, authorization decision, and effect;
- a thin, deny-by-default authorization-policy input; and
- cross-artifact semantic rules and conformance fixtures.

An adopting product owns:

- its application object and target model;
- operation, capability, surface, outcome, and information-source identifiers;
- request, result, observation, and evidence payload schemas;
- the startup circuit breaker and supported transport bindings;
- authentication, policy issuance, enrollment, expiry, revocation, and offline
  behavior;
- authorization enforcement and evidence storage; and
- any stricter boundary around content sessions or product internals.

The shared contract standardizes the seam. It does not publish a global list of
application operations or information sources.

## Discovery and pinned artifacts

An application descriptor identifies one application instance, its current
generation, its control endpoint when enabled, and content-addressed references
to the operation catalog, information-source catalog, and active policy.

The descriptor advertises capability; it does not grant authority. A null
control endpoint means no external listener is available. A non-null endpoint
requires an active policy, but policy presence is still not proof that any
particular request is authorized.

Consumers resolve hostless `contract:` identifiers through a trusted registry
or a vendored copy. Every referenced catalog, policy, or payload schema is
pinned by SHA-256. A consumer fails closed when an artifact is absent, has a
different digest, or does not validate.

Local process discovery may advertise the application-control capability and
descriptor. That composes with `contract: process-run/v0`; it does not turn
process lifecycle verbs into application operations.

## Complete operation inventory

Every user-visible control surface must appear exactly once in the adopting
product's operation catalog:

- as a `surface_ref` for the operation it dispatches; or
- as a non-controllable surface with a reason.

Buttons, menu items, shortcuts, command-palette entries, gestures, and
equivalent affordances are all control surfaces. Multiple surfaces may map to
one operation. Implementations should dispatch native UI actions and remote
requests through the same application service. When code generation is not
practical, contract tests compare the runtime UI inventory with the catalog.

An operation exposed only through a CLI, SDK, agent tool, or other programmatic
adapter may omit `surface_refs`. The completeness rule accounts for every
surface that exists; it does not require every operation to have a graphical
surface.

Each operation declares:

- a stable operation identifier and target kind;
- effect class: `read`, `navigate`, `mutate`, or `destructive`;
- required capability and confirmation posture;
- idempotency and generation-precondition requirements;
- exact request and result payload contracts;
- bounded outcomes; and
- information sources it may emit.

Adapters may expose fewer cataloged operations than the application supports.
They may not invent operations, widen payloads, or turn an open transport
argument bag into an unversioned application API.

## Control exchange

The request envelope carries application, instance, operation, target,
correlation, and payload identity. A request never supplies its own principal.
The receiving trust boundary binds authenticated identity from transport or
local peer state.

Mutating and destructive operations require an idempotency key and canonical
request fingerprint. Operations whose catalog entry requires compare-and-set
also carry the expected application generation. Reusing an idempotency key with
a different fingerprint is rejected; a valid replay returns the original
result identity.

Result records distinguish authorization decision from application effect.
Receipt or validation does not imply authorization, and authorization does not
imply that the effect was applied.

## Complete information-source inventory

Every application information source must appear in the adopting product's
information-source catalog. This includes state transitions, point-in-time
state, status values, measurements, counters, notifications, and parallel
telemetry.

Each source declares:

- stable source identity and any application surface references;
- exact payload schema and digest;
- classification and provenance;
- delivery mode;
- freshness and suggested collection cadence;
- retention and replay behavior.

A source available only through a programmatic adapter may omit
`surface_refs`. The source record itself still provides the stable identity and
semantics.

Delivery mode is explicit:

| Mode             | Contract meaning |
| ---------------- | ---------------- |
| `event`          | Emitted for a meaningful state transition |
| `snapshot`       | Emitted state suitable for initial synchronization or recovery |
| `scrape`         | Read on demand; not emitted merely because time passed |
| `sample`         | Emitted on an intentionally bounded measurement cadence |
| `client_derived` | Computed by a consumer from cataloged inputs |

Only event, snapshot, and sample sources produce observation messages. A clock
or similarly cheap continuously changing display normally uses scrape or
client-derived delivery. Instrumenting every information source therefore does
not imply streaming every value.

Stream producers advertise sequence or cursor semantics when replay is
supported. Consumers treat gaps as explicit state and recover through a
cataloged snapshot or scrape path.

## Evidence stages

Control evidence records four distinct stages:

1. `interaction`: a user activated a named application surface;
2. `request`: a controller submitted a well-formed operation request;
3. `decision`: the policy boundary allowed, denied, or required confirmation;
4. `effect`: the application applied, rejected, conflicted, failed, or could
   not determine the operation outcome.

Each evidence producer attests only the stage it can observe. A user interface
cannot assert an authorization decision or application effect. An interaction
record uses the same request and operation identifiers as the downstream
exchange and names the exact `surface_ref`.

Aggregate metrics use bounded operation and surface dimensions. Request
parameters, object identifiers, names, paths, prompts, credentials, and
correlation identifiers do not become metric labels.

## Authorization

Authorization is deny by default and operation specific. Endpoint possession,
same-user colocation, visible UI focus, or a caller-provided role does not grant
a capability.

The receiver:

1. binds the authenticated principal outside the request body;
2. resolves and verifies the active policy artifact;
3. evaluates denials before allows;
4. enforces application, operation or source, target, confirmation, and rate
   bounds; and
5. records decision and effect independently.

Observation authorization applies to subscriptions, snapshots, scrapes, and
samples. The shared policy is deliberately thin. Enterprise provisioning and
policy lifecycle remain downstream until independent deployments establish a
portable agreement.

An adopting product decides whether control is disabled, local, or available
through an authenticated gateway. Disabled applications do not listen.
Enabling a listener without an active policy grants nothing.

## Content-session exclusion

No product profile may treat this contract as implicit authority to:

- inject keyboard, pointer, terminal, or browser input into hosted content;
- read raw terminal output, transcripts, prompts, or document contents;
- select or approve an agent or model turn;
- invoke arbitrary executables, shell commands, processes, or internal
  framework methods; or
- convert ordinary text, chat, or model output directly into an unvalidated
  operation.

If a product intentionally controls hosted content, that requires a separate
contract and authorization boundary.

## Conformance and versioning

Structural conformance requires the JSON Schemas under
`schemas/application-control/v0/`. Behavioral conformance also requires the
versioned semantic rules and positive and negative fixtures in that family.
Product profiles add fixtures proving their complete control-surface and
information-source inventories.

The `v0` family is experimental and may change. Consumers pin an exact
repository revision or content-addressed bundle, schema identifiers, artifact
digests, and semantic-layer version. Promotion to a stable family requires
independent producer and consumer evidence plus a security review of the
authority boundary.
