---
id: "EPR-0002"
title: "Gates assert on resolved state and are proven able to fail"
status: "accepted"
date: "2026-07-20"
last_updated: "2026-07-20"
deciders:
  - "@3leapsdave"
  - "cxotech"
  - "entarch"
scope: "Crucible foundation / shared governance — durable engineering principle"
tags:
  - "principles"
  - "verification"
  - "testing"
  - "review"
  - "governance"
relates-to:
  - "crucible ADR-0003 (the *DR taxonomy; second EPR under it)"
  - "crucible EPR-0001 (negative-control obligation, scoped to pinned dependency graphs)"
  - "crucible PDR-0004 (release publication gate; asserts signature state rather than a reported verdict)"
  - "crucible docs/standards/data-engineering/data-pipeline-principles.md (GP-2.2, GP-2.4 — the domain-scoped instances)"
---

# EPR-0002: Gates Assert on Resolved State and Are Proven Able to Fail

## Status

**Accepted.** Second Engineering Principle Record under ADR-0003. Drafted by
devlead from conforming implementation work; scoped and brought forward by
cxotech; ratified on entarch ecosystem-parity assent. A conforming reference
implementation has landed (see _Adoption & propagation_), which is the condition
under which the record graduates from proposed to accepted.

## Context

A gate is any automated check whose passing is treated as evidence: a test, a
validator, a CI assertion, a release check, a schema conformance run. We rely on
them transitively — a green gate is taken as a statement about the system, and
review effort is allocated on the assumption that what the gate covers has been
established.

Four failure modes make that assumption false. They are stated here as hazards of
the shape, not as history:

1. **The gate asserts on the input, not the outcome.** It confirms that a system
   was _given_ some configuration rather than that the system _reached_ the state
   claimed. Where inputs compete — a precedence chain, a minimum-selection, a
   fallback — a supplied value can lose and the gate still passes, certifying
   intent as though it were behavior.

2. **Absent evidence is converted into passing evidence.** Something upstream
   substitutes a placeholder for a value that was never produced, and the gate
   accepts the placeholder. The absence is real; the record of it is not.

3. **The gate has never been observed failing.** It is present, configured, and
   green — and would be green against a broken system too. Nothing distinguishes
   "verified" from "not actually wired up".

4. **An exactness claim carries an undeclared exemption.** A check that claims to
   cover exactly some declared set skips a category on a shape-wide condition. The
   coverage claim reads as total; the hole is invisible at the call site.

What these share: **the gate reports on something other than the resolved state of
the system**, and the gap is invisible precisely where a reader most trusts it.
The failure is silent by construction — a gate in this condition does not
misbehave, it passes.

This principle belongs in the shared foundation because the organization has
already derived pieces of it independently — four derivations across three
domains, each confined to its own boundary:

- `data-pipeline-principles` **GP-2.2** ("no silent skip — emit a verdict or
  fail") and **GP-2.4** (later stages re-prove earlier claims from independent
  evidence rather than trusting the earlier verdict) — domain-scoped to data
  engineering and explicitly opt-in.
- **EPR-0001** — "a pin the release build can silently ignore does not satisfy
  this record", and its conformance-by-negative-control requirement, because "an
  enforcement mechanism that has never been seen to fail is configured, not
  proven". Scoped to pinned dependency graphs.
- **PDR-0004** — CI must assert full-fingerprint signature validity against a
  pinned keyring rather than trust a reported `verified` boolean, so the checklist
  "stops being able to reach false-complete". Scoped to release publication.

Each is correct and each stops at its own boundary. Nothing in the foundation
states the rule for an ordinary test or validator, which is where most gates are
written and where the cost of getting it wrong is paid repeatedly.

The standing tension this record arbitrates: **cheap green** (a gate that is
quick to write, quick to satisfy, and rarely blocks) **versus evidentiary force**
(a gate whose passing licenses a real claim). For anything whose green we
_rely on_ — to gate a merge, authorize a release, or discharge a reviewer's
attention — evidentiary force wins, and the extra construction cost is accepted
as its price.

## Principle

> **A gate MUST assert on the resolved state the system actually reached, MUST
> treat absent evidence as a failure rather than substituting a value for it, MUST
> be demonstrated capable of failing, and MUST NOT carry an exemption its stated
> coverage does not declare.**

Four obligations, each durable and independent of language, framework, and domain:

### 1. Assert on resolved state, not requested input

The assertion is made against what the system resolved, produced, or published —
not against the configuration it was handed. Where an input competes with others
to determine an outcome, the gate names the **outcome and its provenance**, so a
supplied value that did not prevail cannot satisfy a claim that it did.

_Corollary:_ a gate that consumes another component's verdict re-derives the claim
from primary evidence where it is feasible to do so. Trusting a reported verdict
inherits every blind spot of the reporter.

### 2. Absence is a verdict, never a placeholder

When evidence is missing, it must present as missing and the gate must fail. No
layer between the system and the gate may substitute a synthetic value —
`unknown`, `not_reported`, an empty default, a zero — for a fact that was never
established. **Manufacturing a value to stand in for missing evidence is the
mechanism by which an unverified system reports as verified.**

Producers are as bound as gates here: the substitution usually happens on the
producing side, where it looks like defensive coding. Where the hazard is
producer-side substitution, the negative control that proves the gate MUST flow
through the real producing path — driving the actual component to withhold the
value — not feed the gate a pre-made absent value. A hand-fed absence proves the
gate rejects absence, not that the producer surfaces it honestly.

### 3. A gate is proven by a negative control

Every gate ships with at least one executable test that feeds it a deliberate
mutation of the state the gate exists to catch. The test **MUST assert that the
gate rejects the mutation and fail if the gate accepts it**. A gate never observed
failing is configured, not proven; the two are indistinguishable from a green run.

_The self-check this reduces to, and the cheapest one available:_ **would this
success fixture still pass against a deliberately broken build?** If yes, the
fixture is documentation of intent, not coverage. And its dual: does the broken
build fail **at this gate's assertion**, not before it? A mutation that trips a
compile error, an earlier gate, or a panic upstream yields a green→red transition
that never exercised the gate under test.

### 4. An exactness claim admits no undeclared exemption

A gate that claims to cover exactly some declared set must reconcile in both
directions: every element it encounters resolves to a declared member, and every
declared element whose multiplicity requires presence is encountered and judged.
The gate verifies the declared shape and multiplicity; an unexpected element or a
missing required element is a failure. Categories that are legitimately out of
scope are **declared in the contract** — named, with their shape and multiplicity
— never expressed as a shape-wide skip inside the check. Where a declared scope
cannot be judged by the rule at hand, the gate refuses rather than silently
applying a rule that does not describe it.

Because the reconciliation runs in two directions, an exactness gate's
Obligation 3 evidence is **one negative control per direction**: an undeclared
element shown rejected, and a removed required element shown rejected. Obligation
3's "at least one" is a floor — a single control here proves only one direction
and leaves the other unexercised.

## Consequences

**Makes easier**

- A green gate licenses a claim, so reviewer attention can be spent on what gates
  cannot see instead of re-deriving what they assert.
- Review rounds collapse: a defect class that would otherwise be found once per
  abstraction layer, by a panel, is caught once by construction.
- Gate failures become informative — a gate proven able to fail tells you
  something when it does.
- A new component inherits a pre-stated bar rather than re-litigating it per
  author and per reviewer.

**Makes harder / costs (accepted)**

- Every gate costs at least one extra case (the negative control), and the case
  must be maintained alongside it.
- Removing placeholder substitution surfaces latent gaps as failures, sometimes in
  quantity, at the moment the obligation is adopted. This is the obligation
  working, not a regression, but it is real adoption cost.
- Fail-closed gates block on genuinely benign absences. Accepted for the same
  reason EPR-0001 accepts parity as a hard failure: a gate that yields under time
  pressure is not a gate.
- Asserting on resolved state usually requires the system to _report_ its resolved
  state, which is an observability obligation the producing component may not have
  had.

**How it is checked (per adopting repository)**

Mechanics are a per-repo concern. This EPR fixes the obligations, not the tooling:
test framework, mutation approach, and how provenance is surfaced are local
choices expected to change without disturbing this record.

Two checking requirements are themselves obligations:

- **Obligation 3 is self-demonstrating** — the negative control _is_ the evidence
  of conformance. A repository claiming conformance can point at the executable
  test that asserts the gate rejects its deliberately invalid state.
- **Pre-merge self-review and review inspection each carry one question**, stated
  at the point of use rather than left to a general policy read. Suggested wording
  for role checklists, kept mutation-flavored because generic
  "are error paths tested?" prompts demonstrably do not catch this class:
  - _author:_ "Does each new gate assert on resolved output state rather than
    requested input, and does a negative-control case prove it fails?"
  - _reviewer:_ "Could this gate pass against a mutated build? Are exemptions
    declared in the contract rather than coded as skips?"

## Adoption & propagation

Per ADR-0002/0003, this principle is canonical upstream in crucible. Adopting
repositories link or vendor it and record local conformance; they do not fork
divergent copies.

It binds any repository whose gates are relied upon to discharge review or
authorize a release — in practice, all of them. Unlike EPR-0001 there is no
qualifying shape to check: a repository with no gates has nothing to conform to,
and a repository with gates is in scope.

**Relationship to existing records.** This record generalizes; it does not
supersede. GP-2.2 and GP-2.4 remain the data-engineering instances and keep their
opt-in domain scoping. EPR-0001's negative-control requirement remains the
supply-chain instance. PDR-0004 remains the release-publication instance. Where a
domain record states a sharper obligation than this one, the domain record governs
within its domain.

**Reference implementation.** A conforming implementation has landed in the
public [`gonimbus`](https://github.com/3leaps/gonimbus/pull/167) measurement
harness: provenance-based assertions in place of input assertions, removal of a
placeholder substitution at its source, mutation-pinned negative controls per
gate, and a coverage check keyed on declared identity with an explicit refusal
where its rule does not apply.

## Not this record (one principle per record)

- **Which** gates a repository runs, at what thresholds, on what triggers → that
  repository's **PDR**, runbook, or CI baseline.
- **How** mutation coverage is produced (hand-written negative controls, a
  mutation-testing tool, fault injection) → repo choice.
- **What** a published measurement is permitted to claim, and the separation
  between a quantity measured and a conclusion drawn from it → adjacent and
  genuinely distinct; a candidate for its own record if the need recurs.
- **Whether** a specific finding is accepted as residual risk → **SecDR**.
- Coverage percentage targets → repo policy; this record is about whether a gate
  means anything, not how much surface it touches.

## Rationale for the record type

**EPR, not PDR.** By ADR-0003's two axes: the domain is engineering practice, and
the lifecycle is durable. The litmus is satisfied — strip every framework and tool
and the four obligations survive intact. "Stop requiring gates to be able to fail"
would not be a process revision but a reversal of principle.

**Not a domain record marked principle-lifecycle.** ADR-0003 §6 says a durable
principle inside one domain should stay in that domain's letter. That path was
considered and rejected on the evidence: this obligation has already been derived
independently in data engineering, supply chain, and release management, and was
then re-derived a fourth time in test tooling. A principle that four domains need
is not a domain principle.

**Consistent with EPR-0001.** EPR-0001 states obligation 3 for one artifact class
and names the reason ("configured, not proven"). This record lifts that reasoning
to its natural scope and adds the three obligations that accompany it. EPR-0001
remains correct and unchanged; it becomes an instance rather than an exception.

## References

- [ADR-0003: Decision & Governance Record Taxonomy](../decisions/ADR-0003-decision-record-taxonomy.md) — defines EPR
- [EPR-0001: Published Artifacts Carry an Integral Dependency Graph](../decisions/EPR-0001-published-artifact-dependency-integrity.md) — negative control, scoped to pinned graphs
- [PDR-0004: Release Publication Gate](../decisions/PDR-0004-release-publication-gate.md) — assert signature state, not a reported verdict
- `docs/standards/data-engineering/data-pipeline-principles.md` — GP-2.2, GP-2.4
- [Decision & Governance Records — the `*DR` family](../repository/decision-records.md) — the normative catalog

## Revision History

| Date       | Status Change | Summary                                                                                                                       | Updated By       |
| ---------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| 2026-07-20 | → proposed    | Second EPR under ADR-0003; generalizes GP-2.2/2.4, EPR-0001, PDR-0004                                                         | devlead, cxotech |
| 2026-07-20 | → accepted    | Ratified on entarch ecosystem-parity assent; reference implementation landed                                                  | cxotech, entarch |
| 2026-07-20 | (refine)      | Sharpen negative-control evidence: per-direction for exactness gates, producer-path for absence, fail-at-assertion self-check | devlead, cxotech |
