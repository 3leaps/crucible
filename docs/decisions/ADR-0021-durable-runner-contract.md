---
id: "ADR-0021"
title: "Durable runner as a portable contract with a core-first mode set"
status: "proposed"
date: "2026-11-20"
last_updated: "2026-11-20"
deciders:
  - "@3leapsdave"
  - "cxotech"
  - "entarch"
scope: "Crucible foundation / portable execution contracts"
tags: ["runner", "execution", "journal", "idempotency", "recovery", "interchange-contract"]
relates-to:
  - "crucible ADR-0006 (process-run contract)"
  - "crucible ADR-0013 (durable-record contract)"
  - "crucible ADR-0014 (data-acquisition contract)"
  - "crucible ADR-0019 (durable-record v1 tombstoning)"
  - "crucible PDR-0006 (shipping charter)"
  - "crucible EPR-0002 (verification gate integrity)"
  - "crucible EPR-0005 (test evidence independence)"
---

# ADR-0021: Durable Runner as a Portable Contract with a Core-First Mode Set

## Status

**Proposed.** Establishes the boundary for a candidate
`contract: durable-runner/v0` family. The experimental schema bundle, reject
pairs, behavioral vectors and reference consistency model accompany the prose.
Adopter conformance and runtime qualification remain separately gated.

## Context

Governed data acquisition and scheduled measurement both need to run a pinned
task, retry it under a policy, survive a crash and prove afterwards what
happened without running it again. Existing contracts cover neighbouring
ground. Process-run governs one process's telemetry and control, durable-record
governs retained records, data-acquisition governs source policy and plans, and
recurrence governs rules. None says what makes one execution the same task
across restarts, which state changes are legal, who may execute, or what a
durability claim means for an attempt journal.

## Decision

1. **A portable contract, not a runtime.** Publish `durable-runner/v0` as
   schemas, a standard, examples, rejects and behavioral vectors. Execution
   and triggering stay separate. There is no DAG engine, broker, recurrence
   host or multi-host failover.
2. **Core-first modes.** Admit `basic`, `retrying`, `journaled` and
   `scheduled` as cumulative prefixes. Reserve `sealed` and refuse any profile
   that advertises it. Passing the reservation reject is not sealed
   conformance. A companion durable-ledger contract carries sealed in a later
   release.
3. **Identity separates definition, logical task and invocation.** The
   specification digest, the authority-and-key task identity, the process run
   identifier and the per-task attempt identity are distinct. Reusing a key with
   another specification conflicts, and store expiry never grants a new
   execution.
4. **Closed transitions with no terminal resurrection.** Task and attempt
   states follow an explicit table, `blocked` is a reason, cancellation is a
   request that becomes terminal only after quiescence, and an unknown external
   effect is never a routine retry.
5. **One immutable record per transition.** Journaled mode pins
   durable-record/v1 and writes single-revision transition records that carry
   the state change and attempt fact together. Summaries are derived. No
   durable-record journal entry kind is added, and v0 is not a fallback.
6. **One execution authority per stream.** A process-shared exclusive
   authority spans recovery, containment, execution, effects, orphan cleanup
   and publication. A recorded generation is evidence, not fencing. A successor
   that cannot establish quiescence blocks or abandons.
7. **Durability is independent properties.** Attempt-journal acknowledgement
   reuses the record failure-model values, while remote sealed coverage and
   replication are `none` in this release. No ordinal classifier is added.
8. **Exact time.** Operational instants carry six fractional digits and
   durations are exact integer microseconds. Lossy conversions are refused.
9. **Supplied schedules.** The caller supplies slots and coverage with exact
   pins. The executor validates them, treats a DST-skipped candidate as a
   non-slot, keeps `missed` terminal and permits catch-up only as a linked new
   task within the configured lag.
10. **Behavioral conformance, independently authored.** Vectors are hand
    authored from the standard, a reference model executes them, and mutation
    controls remove one guard at a time. A schema-only pass is not evidence.

## Alternatives

- **A single ordinal durability class.** Rejected: one rank hides that
  acknowledgement, remote coverage and replication vary independently.
- **Revisioned task record plus separate attempt writes.** Rejected: it needs a
  cross-record transaction. One record per transition does not.
- **A lease epoch as the execution fence.** Rejected: a stored epoch neither
  stops an orphan process nor fences a remote request.
- **Admitting `sealed` now.** Rejected: it needs the ledger composition, which
  is a separate contract.
- **Deriving expected histories from the model.** Rejected: it would test the
  model against itself.

## Consequences

- Adopters pin one family manifest and one durable-record/v1 manifest.
- A runner built from the core can claim recovery and replay without claiming
  sealed output, remote coverage or replication.
- The next contract release must publish the shared ledger composition before
  any sealed or attested claim is made under this runner composition.
- Runtime, cloud and language qualification are later gates and are not implied
  by passing the schema harness.

## References

- [Portable Durable Runner Contract](../standards/durable-runner-contract.md)
- [durable-runner/v0 schemas](../../schemas/durable-runner/v0/README.md)
- [durable-record/v1 standard](../standards/durable-record-v1-contract.md)
- [data-acquisition standard](../standards/data-acquisition-contract.md)
- [recurrence rule standard](../standards/recurrence-rule-contract.md)
