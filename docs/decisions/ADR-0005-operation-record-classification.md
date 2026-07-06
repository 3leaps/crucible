---
id: "ADR-0005"
title: "Operation-Record Classification Standard (run status/error taxonomy above tool implementations)"
status: "proposed"
date: "2026-07-02"
last_updated: "2026-07-02"
deciders:
  - "@3leapsdave"
scope: "Crucible foundation / classifiers"
tags:
  - "classifiers"
  - "operations"
  - "run-records"
  - "error-taxonomy"
relates-to:
  - "docs/standards/data-artifact-contract.md (producer.run_id — the dereference target)"
  - "docs/standards/classifiers-framework.md (the capture idiom)"
  - "crucible ADR-0004 (coverage attestation — claims reference runs via method/emitter)"
---

# ADR-0005: Operation-Record Classification Standard

## Status

**Current Status**: Proposed — deliberately **schema-less**. Graduation to a
`schemas/` family is gated on a second independent implementation consuming
the taxonomy. This ADR reserves the shape and records the rationale; it asks
nothing of the data-artifact/v0 freeze.

## Context

Multiple tools in adopting repositories emit run/operation records — an object-store
indexer/mover, an extraction engine, a publisher, a pipeline runner — each
with its own status values and error vocabulary. Two observations motivate a
standard **above** the implementations:

1. **Misclassification at tool seams is an observed failure mode.** One
   tool's structured error wrapper, re-ingested by an orchestrator that did
   not share its vocabulary, was classified `unknown` and not retried —
   turning a transient network blip into a mass-failed run. The status/error
   taxonomy is already a de-facto cross-tool contract; leaving it implicit is
   what bites.
2. **The data-artifact contract points at runs but nothing standard answers.**
   `producer.run_id` is carried "where safe to expose", and coverage
   attestations reference runs through emitter/method — a portable notion of
   what a run _record_ says (status, error class, scope) is the missing
   dereference target.

What does **not** need standardizing is the envelope: an operation record is
itself a data artifact (`grain.kind: record_stream`, NDJSON representation,
`building → complete` lifecycle) and maps onto data-artifact/v0 like any
producer — including default-deny protection for freeform note/error/metrics
fields, which can carry captured content. No new top-level contract family.

## Decision (proposed shape)

An **operation-record classification standard** in the crucible classifiers
idiom (a peer of the existing classification standards), defining:

1. **Status taxonomy** — portable states
   (`pending | running | complete | failed | blocked | skipped`) with
   transition rules (e.g. `failed` requires an error summary); tool-specific
   statuses map into it.
2. **Error-class taxonomy** — portable failure classes (transient/network,
   throttled, auth/credential, integrity, cancelled, unknown) with the rule
   that a wrapped/re-ingested structured error retains its class.
3. **Subject scoping** — subject id + window + operation id, aligned with the
   coverage-attestation scope vocabulary.
4. **State-projection semantics** — latest-record-per-operation is current
   derived state; the append-only record stream remains authoritative. An
   ordered required-operation registry yields "next required operation". This
   is what makes a log _drivable_ by an operator or an automation rather than
   telemetry exhaust.

## Consequences

- Orchestrators classify foreign tools' outcomes without bespoke adapters;
  retry policy attaches to the error class, not to per-tool string matching.
- Run records become mappable data-artifact producers for free.
- Cost is deferred by design: no schema, no validation surface, no producer
  changes until the graduation trigger (a second independent consumer) fires.

## Graduation trigger

Promote to `schemas/operation-record/v0/` (or fold into the classifiers
config surface) when a second implementation consumes the taxonomy across a
tool boundary. Until then this ADR is the standard's reservation, not its
delivery.
