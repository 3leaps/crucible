---
id: "ADR-0012"
title: "Durable queue as a portable contract with engine-neutral conformance"
status: "proposed"
date: "2026-10-11"
last_updated: "2026-10-11"
deciders:
  - "@3leapsdave"
  - "cxotech"
  - "entarch"
scope: "Crucible foundation / portable messaging contracts"
tags: ["messaging", "queue", "ledger", "idempotency", "interchange-contract"]
relates-to:
  - "crucible ADR-0001 (schema/config versioning)"
  - "crucible ADR-0006 (process-run contract)"
  - "crucible ADR-0011 (segmented snapshot contract)"
  - "crucible PDR-0006 (shipping charter)"
  - "crucible EPR-0002 (verification gate integrity)"
---

# ADR-0012: Durable Queue as a Portable Contract with Engine-Neutral Conformance

## Status

**Proposed.** Establishes the boundary for a candidate
`contract: durable-queue/v0` family. The experimental schema bundle,
reject pairs and first behavioral vectors accompany the prose; adopter
conformance remains separately gated.

## Context

Several applications in the estate need durable, at-least-once delivery of
work items with fan-out, retry, dead-lettering and an auditable record of
what the queue did. The existing contracts do not cover this. The service-job
contract governs job admission, status and results, and names `queued` as a
job state, but says nothing about how a message is transported, leased, or
redelivered. The process-run contract governs a single process's telemetry
and control, not a message's lifetime across many processes.

Candidate implementations differ widely: an embedded append-only log, a SQL
database shared with the application, a broker, or a cloud queue. Each gives
different guarantees around atomic commit with business data, ordering,
fencing and clock control. Choosing one engine before the contract exists
would bake that engine's behaviour into every consumer.

## Decision

Define `contract: durable-queue/v0` as a **logical contract only**: message
envelope, queue-scoped lease with fencing token, closed ledger event
vocabulary with atomic groups and fold rules, capability profile, and a
line-delimited control exchange with typed per-operation requests and
results. The contract carries no storage layout, file format, table schema,
worker runtime or job framework.

The first publication is narrowed to an **audit and lifecycle fold**. The
ledger is an authoritative, consistently cuttable history of transitions;
portable restore from it, a `replay` operation, cross-queue fan-out and a
tolerant wall-clock conformance mode are deferred rather than advertised.

Separate what an implementation **is** from what it **does**: the capability
profile holds immutable build facts and effective runtime facts as distinct
blocks, and records whether the profile was produced by the conformance
harness or merely declared.

Make the behavioural vectors, hand-authored from the prose, the
language-neutral authority. An implementation's own receipts are never the
oracle. Crucible's controls validate the vectors themselves: request and
result shapes, bindings, gap-free sequence, contiguous atomic groups, legal
transitions, attempt correspondence and RFC 8785 identity digests. One
conformance mode, deterministic under a virtual clock with a recorded ledger,
is defined; backends that cannot meet it are `benchmark_only`.

Fencing and keyed deduplication are core, not capabilities. The failure model
a backend guarantees is declared independently of its commit strategy.

Keep the queue's idempotency scope (per queue, by producer key) distinct from
the service-job submit request's idempotency scope (actor, service, key). The
same string may appear in both with an explicit mapping; the service-job
standard carries the composition note and neither contract absorbs the other.

### Exclusions

This is not a storage engine, a WAL protocol, a SQL schema, a broker
protocol, a job framework, a workflow engine, a pub/sub or stream contract,
or an exactly-once delivery guarantee. Storage bindings, drivers, daemons,
worker loops and workload corpora belong to adopting repositories.

### Publication and adoption

The review surface is the prose standard, the four schemas with manifest,
golden examples, one-field reject pairs, and the first core and fan-out
vectors. Crucible ships standards, schemas and validation material under
PDR-0006; engines and harness runners belong elsewhere.

Qualify with one owned engine passing the core vectors deterministically and
one independent workload corpus driving it through the control exchange.
Storage selection follows that corpus comparison; it is not decided here.
Apply the stable-promotion gate of ADR-0001 independently of the repository's
release maturity.

## Alternatives

- **Adopt one off-the-shelf library's semantics as the standard:** fastest to
  a first app; ties every consumer to one library's table layout, language
  bindings and native dependencies, and leaves cross-language interop to
  that library's maintainers.
- **Extend service-job into transport:** conflates job lifecycle with message
  delivery and forces every job consumer to carry queue semantics.
- **Standardize the storage binding now:** gives cross-language interop over
  shared tables but freezes a SQL dialect into a public contract before the
  access pattern has been measured.
- **Logical contract plus capability profiles:** selected proposal; shares the
  verifiable boundary while leaving the engine, store and packaging open to
  measured choice.

## Consequences

Adopters can put an embedded log, a database, a broker or a cloud queue
behind one interface and state, through a harness-produced profile, exactly
which guarantees hold. Moving between backends changes configuration rather
than application code **only when the new backend's enabled capabilities and
failure model cover what the application requires**; the profile makes that
check explicit. Adapters over third-party backends that cannot record a
complete ledger or enforce fencing atomically are `benchmark_only`; a precheck
plus an unfenced delete is not fencing. Publishing this proposal does not
require any existing producer or consumer to change.

## References

- [Durable queue contract](../standards/durable-queue-contract.md)
- [Service job contract](../standards/service-job-contract.md)
- [Process run contract](../standards/process-run-contract.md)
- [Crucible shipping charter](PDR-0006-shipping-charter.md)
