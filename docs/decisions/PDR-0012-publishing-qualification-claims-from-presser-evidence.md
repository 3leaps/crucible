---
id: "PDR-0012"
title: "Publishing qualification claims from presser evidence"
status: "proposed"
date: "2026-11-22"
last_updated: "2026-11-22"
deciders:
  - "@3leapsdave"
  - "cxotech"
scope: "Crucible foundation / adopting repositories' published qualification results"
tags:
  - "process"
  - "qualification"
  - "reporting"
  - "evidence"
relates-to:
  - "repository classes standard, section 8 (pressers: qualification harnesses)"
  - "EPR-0002 (verification of resolved state and discriminating negative controls)"
  - "EPR-0003 (durable claims assert on what exists and move when it moves)"
  - "EPR-0005 (test evidence independence)"
---

# PDR-0012: Publishing Qualification Claims from Presser Evidence

## Status

**Proposed.** Acceptance establishes a reporting practice for published
presser results. It adds no schema, registry, runner or implementation, and it
does not change the harness checks of the repository classes standard.

## Decision

When a project publishes a presser result, it states what a caller can
conclude from the run and gives the reader enough evidence to check that
conclusion. The decision applies per operation. A conformance result can be
published independently of a migration study, fuzz campaign or benchmark.

1. **Identify what ran.** Name the caller operation, implementation and shared
   backend, artifact and contract pins, settings, host and relevant compiler or
   engine version. Identify the path actually exercised when a package can
   choose an optional accelerator or fallback. A newly independent
   implementation earns coverage operation by operation.
2. **Establish the expectation and scope.** Identify who fixed the
   expectations and their source before subject execution. Publish the
   selected pack, the verifier and the full case accounting for each subject,
   including required capabilities, exclusions, failures and unresolved
   outcomes. A claim of portability across independent implementations
   requires full required coverage on each for the profile being claimed.
3. **Report each conclusion with its evidence.** Compare incumbents through
   the public API an adopter uses. The maintainer decides how third-party
   reference results may be presented. Publication of third-party failure,
   hang, limit or crash results requires a maintainer decision and a security
   disposition. For approved comparisons, give the typed outcomes, intentional
   differences and practical migration consequences. Attribute enforced limits
   and measured resource use separately. Give comparable workloads, samples
   and timing boundaries for a speed comparison.
4. **Make the claim verifiable.** Link pinned inputs, raw observations, the
   selection ledger, replay and offline verification instructions. Include a
   negative control that changes the specific evidence on which the claim
   rests. Mark staging results and pending work visibly. Reassess a published
   claim when an implementation, contract, pack or material runtime setting
   changes.

### Provisional fuzz reporting guidance

After review of the first bounded campaign record, consider requiring the seed
corpus identity, execution budget, operations exercised and disposition of
findings. Public reports include findings only as released by security. An
unexecuted campaign stays pending. This guidance is provisional until that
record has been reviewed.

## Lessons from the first trials

A build can match every applicable case while a capability remains unexercised
or a required qualification revision is missing. Name the excluded cases,
reasons, and exact revisions each subject declared. An external reference
contributes interoperability evidence. A native portability claim requires
evidence from each implementation in scope.

A migration report can pass verification while recording a real difference
between two loaders. Publish the observed values and the count of relevant
findings that answer the adopter's question. Exercise a control that makes that
count change and confirm the report shows the change.

## Ownership and scope

The repository classes standard, section 8, defines harness checks R1 to R5.
Domain teams own expected semantics, corpus curation, drivers and
domain-specific verdict rules. A companion guide can carry report examples and
language-specific considerations. The lessons above support a common reporting
practice. A shared schema, capability registry or runner would need a separate
case for adoption.
