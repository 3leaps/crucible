---
id: "ADR-0013"
title: "Durable record as a portable contract with declared stratum guarantees"
status: "proposed"
date: "2026-10-12"
last_updated: "2026-10-12"
deciders:
  - "@3leapsdave"
  - "cxotech"
  - "entarch"
scope: "Crucible foundation / portable storage contracts"
tags: ["records", "journal", "storage", "retention", "provenance", "interchange-contract"]
---

# ADR-0013: Durable Record as a Portable Contract with Declared Stratum Guarantees

## Status

**Proposed.** Establishes the boundary for a candidate
`contract: durable-record/v0` family. The prose standard and an experimental
schema bundle with golden examples and one-field reject pairs accompany this
record. Behavioral vectors and adopter qualification are separately gated.

## Context

Several tools keep append-only journals of records: run and operation records,
review journals, process telemetry, queue ledgers, index lineage, and agent
session state. Each defines its own envelope, sequencing, provenance and
consistency rules. Adopters that want to keep notes, reusable procedures,
pipeline stage results or session state somewhere durable, readable by another
tool or model, and movable between machines have no shared contract to
target. Without one, the choice of store becomes the contract, and moving
between an embedded database, a journal of files, a Git repository and an
object-storage bucket becomes a migration rather than a copy.

These stores differ in what they can promise. Some survive power loss on
acknowledgement and some do not. Some can remove bytes from history and some
retain all history by design. Some replicate to copies they cannot later
reach. A contract that hides these differences would let consumers rely on
guarantees no store provides.

## Decision

Define `contract: durable-record/v0` as a **logical contract only**:
- a thin record envelope with stable identity, exact digest-pinned revisions, provenance, a required retention and sensitivity classification, and either an inline payload or a digest-bound body reference;
- an append-only journal with gap-free sequence and the atomic-group consistent-cut rule shared with the durable queue;
- a closed write-outcome vocabulary;
- a stratum profile.

Make the unit a **revisioned record**. An event is a record with one revision.
Streams declare `single_revision` or `revisioned` mode, so high-volume event
paths stay plain appends while notes and procedures detect conflicting
revisions.

Keep the envelope thin and push meaning into payload contracts named by
host-less tokens. Domain specialisation is by **profile**, which may narrow but
never widen the core.

Treat the journal as the portable form of the store. Unlike the queue ledger,
accepted entries carry the record, so a copy of the journal is a copy of the
store. Choice of physical engine remains open.

State deletion as **scope**, not as a boolean. The profile declares, per
surface (live head, retained history, managed replicas, external bodies,
decryption capability), what the store's own operations achieve. Key
retirement is a distinct claim from byte removal and must list its key-custody
assumptions. Copies outside management are outside every claim. History policy
(`append_only` or `managed_redaction`) is chosen at store creation and is
independent of writer topology.

### Exclusions

This is not a storage engine, a file layout, a query language, a sync or
replication protocol, a retrieval API, a merge algorithm, or a benchmark
standard. v0 defers shared stream-level metadata, multi-host ownership of one
stream, automatic merge, a wire binding, and behavioral conformance vectors.
It does not change the audit-history policy of any existing adopter.

### Publication and adoption

The review surface is the prose standard, three schemas with manifest, golden
examples and one-field reject pairs. Crucible ships standards, schemas and
validation material under PDR-0006. Engines, adapters and workload harnesses
belong elsewhere.

Qualify with an independent synthetic workload harness that compares strata at
a matched declared failure model and reports capability refusals as outcomes.
Shape the core against two concrete payloads first: session handoff state and
a pipeline stage result. Apply the stable-promotion gate of ADR-0001
independently of the repository's release maturity.

## Alternatives

- **Domain-specific record contract only (for example agent records):** fits
  the first consumer, but every other journal keeps its own envelope and the
  estate pattern stays duplicated.
- **Model everything as an event stream:** simple append semantics, but
  revised documents masquerade as event sequences and conflict detection
  becomes each consumer's problem.
- **Extend the durable-queue ledger:** reuses an existing cut rule, but the
  ledger deliberately excludes payloads and portable restore, and delivery
  semantics are not storage semantics.
- **Standardise one engine:** fastest to a first implementation; freezes
  durability, history and deletion behaviour into the contract before they
  are measured.
- **Thin logical contract plus declared stratum profiles:** selected proposal.

## Consequences

Consumers can read a record by `{record_id, revision, digest}` from any
conforming store and detect changed bytes. A pin to a redacted revision says
so rather than resolving to other bytes. A consumer that requires byte removal
from history can refuse a stratum whose profile does not declare it. Moving
between strata is a journal copy, checked against the target profile.
Publishing this proposal does not require any existing producer or consumer to
change.

## References

- [Durable record contract](../standards/durable-record-contract.md)
- [Durable queue contract](../standards/durable-queue-contract.md)
- [Data artifact contract](../standards/data-artifact-contract.md)
- [Segmented snapshot contract](../standards/segmented-snapshot-contract.md)
- [Retention lifecycle classification](../standards/retention-lifecycle-classification.md)
- [Crucible shipping charter](PDR-0006-shipping-charter.md)
