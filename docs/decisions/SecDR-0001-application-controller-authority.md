---
id: "SecDR-0001"
title: "Application controller authority"
status: "proposed"
date: "2026-09-06"
last_updated: "2026-09-06"
deciders:
  - "@3leapsdave"
  - "entarch"
  - "secrev"
scope: "Crucible foundation / application-control security"
tags:
  - "application-control"
  - "authorization"
  - "security"
  - "audit"
relates-to:
  - "crucible ADR-0010 (portable application-control boundary)"
  - "crucible DDR-0001 (application-control data model)"
---

# SecDR-0001: Application Controller Authority

## Status

**Proposed.** Security review is required before the application-control family
can leave `v0`.

## Context

An application-control listener creates a privileged path around ordinary user
interaction. A request may originate from a local human tool, an agent, or a
remote enterprise controller. Treating endpoint possession, capability
advertisement, or caller-supplied identity as authority would create a confused
deputy.

Control also has four separately observable stages: user interaction, protocol
request, authorization decision, and application effect. Collapsing those
stages into one success flag loses essential audit meaning.

## Decision

Application control is disabled by default unless an adopting product explicitly
defines another fail-closed posture. When disabled, the application does not
listen and advertises a null control endpoint. A non-null endpoint requires an
active policy artifact; enabling a listener grants no operation by itself.

The receiving trust boundary derives principal identity from authenticated
transport state or local peer credentials. A control request has no principal
field.

Authorization is evaluated against the exact active policy, application,
operation or information source, target, confirmation posture, and bounds.
Denials take precedence. Absence of an allow is a denial. Observation
authorization covers subscriptions, snapshots, scrapes, and samples.

Mutating and destructive operations require an idempotency key and canonical
request fingerprint. Operations that require compare-and-set also require an
expected application generation. A reused key with a different fingerprint is
rejected; a valid replay returns the original result identity.

Evidence records interaction, request, decision, and effect as distinct stages.
Each source attests only a stage it can observe. Decision and effect are never
inferred from a button press or request receipt.

The shared policy schema remains deliberately thin. Product or deployment
profiles own policy issuance, signatures, enrollment, expiry, revocation,
offline behavior, and gateway trust.

Application-control authority does not extend into hosted content sessions.
Terminal input, browser automation, document editing, conversation turns, and
arbitrary framework or process invocation require separate contracts and
authorization.

## Consequences

- A maintainer can enable a narrow experimental control surface without
  silently granting remote authority.
- Enterprise provisioning can later supply policy artifacts without changing
  product operation schemas.
- Implementations preserve authenticated connection context outside the
  caller-controlled request body.
- Auditors can distinguish intent, admission, and actual effect.
- Managed lifecycle interoperability remains downstream until independent
  deployments establish a portable contract.

## References

- [Portable Application Control and Observation Contract](../standards/application-control-contract.md)
- [ADR-0010: Application Control and Observation as a Portable Contract](ADR-0010-application-control-contract.md)
- [DDR-0001: Application Control Data Contract](DDR-0001-application-control-data-contract.md)
