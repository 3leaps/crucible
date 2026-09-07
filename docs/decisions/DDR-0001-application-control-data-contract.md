---
id: "DDR-0001"
title: "Application control data contract"
status: "proposed"
date: "2026-09-06"
last_updated: "2026-09-06"
deciders:
  - "@3leapsdave"
  - "entarch"
scope: "Crucible foundation / application-control data model"
tags:
  - "application-control"
  - "data-contract"
  - "schemas"
  - "telemetry"
relates-to:
  - "crucible ADR-0010 (portable application-control boundary)"
  - "crucible SecDR-0001 (application-controller authority)"
---

# DDR-0001: Application Control Data Contract

## Status

**Proposed.** Defines the data-model choices for the experimental
`contract: application-control/v0` family.

## Context

A useful application-control layer provides more than callable operation names.
Human and programmatic clients need the same vocabulary, user-visible controls
must not escape instrumentation, and observers must know whether a value is an
event, snapshot, scrape, sample, or client-side derivation.

Some invariants span multiple artifacts and cannot be expressed by JSON Schema
alone. Adopting products also need closed payload shapes without putting their
object model into the portable envelope.

## Decision

The v0 family uses an application descriptor that pins an operation catalog, an
information-source catalog, and an active policy by logical identity and
SHA-256 digest.

The operation catalog is exhaustive for user-visible controls. Every button,
menu item, shortcut, command-palette entry, gesture, or equivalent affordance
maps to exactly one operation or is recorded as non-controllable with a reason.
Multiple surfaces may map to one operation. A programmatic-only operation may
omit surface references.

Each operation declares its target kind, effect class, capability,
confirmation posture, idempotency and precondition requirements, exact request
and result payload contracts, possible outcomes, and emitted information
sources.

The information-source catalog is exhaustive for application state emitters,
readable values, notifications, measurements, and parallel telemetry. Each
source declares one delivery mode:

- `event` for a meaningful state transition;
- `snapshot` for synchronization or recovery;
- `scrape` for an on-demand read;
- `sample` for an intentionally bounded measurement stream; or
- `client_derived` for a value computed from cataloged inputs.

Only events, snapshots, and samples produce observation messages. A clock or
similarly cheap continuously changing value normally uses scrape or
client-derived delivery rather than emitting on every tick.

Product payloads remain closed under their own schemas. The portable envelope
carries the payload schema identifier, SHA-256 artifact digest, and value.
Consumers resolve and validate the exact payload artifact before use.

Cross-artifact requirements live in the versioned
`application-control/v0-semantics` layer and are exercised by conforming and
negative fixtures.

## Consequences

- Native UI and remote automation can dispatch through the same operation
  registry.
- Catalog tests can detect missing control or information instrumentation.
- Information can be streamed selectively without losing discoverability.
- Content-addressed payload contracts prevent a stable identifier from hiding
  a changed shape.
- Consumers must implement both structural JSON Schema validation and semantic
  validation.
- Application profiles must update catalogs and fixtures whenever their
  control or information surfaces change.

## References

- [Portable Application Control and Observation Contract](../standards/application-control-contract.md)
- [ADR-0010: Application Control and Observation as a Portable Contract](ADR-0010-application-control-contract.md)
- [SecDR-0001: Application Controller Authority](SecDR-0001-application-controller-authority.md)
