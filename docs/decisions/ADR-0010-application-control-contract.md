---
id: "ADR-0010"
title: "Application control and observation as a portable contract"
status: "proposed"
date: "2026-09-06"
last_updated: "2026-09-06"
deciders:
  - "@3leapsdave"
  - "entarch"
scope: "Crucible foundation / application contracts"
tags:
  - "application-control"
  - "automation"
  - "observability"
  - "schemas"
relates-to:
  - "crucible ADR-0001 (schema and configuration versioning)"
  - "crucible ADR-0006 (local process telemetry and control)"
  - "crucible DDR-0001 (application-control data model)"
  - "crucible SecDR-0001 (application-controller authority)"
---

# ADR-0010: Application Control and Observation as a Portable Contract

## Status

**Proposed.** The family remains experimental at `v0` while independent
applications validate the shared boundary.

## Context

Interactive and headless applications increasingly expose their own controls
and observable state to native interfaces, local automation, remote operators,
and agents. Driving a terminal, browser, document, conversation, or other
content session hosted by an application is a different security and semantic
boundary from controlling the application itself.

Process-discovery contracts can locate a process and describe a small lifecycle.
Generic command and telemetry envelopes can carry bytes. Neither defines an
application object model, an exhaustive control and information inventory,
replay-safe mutation, or the distinction between streamed events and on-demand
reads.

## Options considered

### Extend process control

- Reuses local discovery and control-endpoint conventions.
- Conflates process lifecycle with application semantics and encourages open
  verb or argument surfaces.

### Extend generic command and telemetry envelopes

- Reuses existing transports.
- Turns a transport into an implicit unversioned API and encourages every
  observable value to become pushed telemetry.

### Define a portable application-control contract

- Keeps application semantics independent of transport.
- Requires each product to maintain a profile and conformance fixtures.

## Decision

Define `contract: application-control/v0` as a portable companion contract.

The foundation family owns:

- application discovery descriptors;
- operation and information-source catalog shapes;
- transport-neutral request, result, observation, and evidence envelopes;
- replay-safe mutation and generation preconditions;
- a thin authorization-policy input; and
- cross-artifact semantic rules and fixtures.

Each adopting application owns its objects, operation and source identifiers,
payload schemas, startup circuit breaker, transport binding, policy lifecycle,
authorization enforcement, and evidence storage.

The contract controls application objects only. It does not grant authority to
drive content sessions hosted by the application.

`contract: process-run/v0` may advertise the application-control descriptor for
a local process. Process control remains a separate lifecycle contract.

## Consequences

- Applications can expose the same typed operation vocabulary through native
  UI, CLI, SDK, agent, and remote adapters.
- Information sources remain discoverable even when they are scraped or
  client-derived rather than streamed.
- Products must maintain complete, reviewable catalogs and exact payload-schema
  pins.
- The contract can be adopted across organizations without importing a
  product-specific object model.
- Premature generalization remains a risk, so the family stays at `v0` until
  independent implementations provide compatibility evidence.

## References

- [Portable Application Control and Observation Contract](../standards/application-control-contract.md)
- [DDR-0001: Application Control Data Contract](DDR-0001-application-control-data-contract.md)
- [SecDR-0001: Application Controller Authority](SecDR-0001-application-controller-authority.md)
- [ADR-0006: Local Process Telemetry & Control](ADR-0006-process-run-contract.md)
