---
id: "EPR-0005"
title: "Test evidence is independent of the implementation it judges"
status: "proposed"
date: "2026-10-09"
last_updated: "2026-10-09"
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
relates-to:
  - "crucible ADR-0003 (the *DR taxonomy; fifth EPR under it)"
  - "crucible EPR-0002 (gates are proven able to fail; this record governs where a gate's expectations and inputs come from)"
  - "crucible EPR-0003 (claims bounded by existing evidence; an expected value is a claim about the system)"
  - "crucible PDR-0005 (proposed; fierce-collaboration review, where test-strategy review belongs to devrev)"
---

# EPR-0005: Test Evidence Is Independent of the Implementation It Judges

## Status

**Proposed.** Fifth Engineering Principle Record under ADR-0003. Drafted by
devlead from conforming implementation work in progress; review requested from
entarch on altitude and from cxotech on scope. It graduates under the condition
in _Graduation condition_ and not before.

## Context

A test makes two inputs and one assertion: the **input** it feeds the system, the
**expected result** it compares against, and the comparison. EPR-0002 governs the
comparison: it must assert on resolved state, treat absence as failure, be shown
able to fail, and declare its exemptions. This record governs the other two.

A test can satisfy every obligation of EPR-0002 and still certify a wrong
system, because both of its inputs came from the same understanding as the code.
Four failure modes recur. They are stated as hazards of the shape, not as
history:

1. **The expectation is derived from the implementation.** The expected value is
   whatever the code produced when the test was written, or is computed by a
   helper that shares the code's model of the format. The test then asserts that
   the system agrees with itself. A misreading of the specification is encoded
   twice and passes.
2. **The implementer authors the specimens.** Inputs are constructed by helpers
   in the same repository, by the same hand, from the same assumptions. The input
   space the tests explore is the input space the implementer imagined, which is
   the space the implementation already handles. The shapes that matter are the
   ones nobody imagined.
3. **Coverage is enumerated by example, not stated by class.** Each fixture has a
   per-file expected result, and nothing states what must hold for every member
   of a class. A new fixture with a wrong expectation is accepted, because no
   rule it could violate exists.
4. **A finding is closed without becoming evidence.** A reviewer demonstrates a
   defect, the code is fixed, and the demonstration is discarded or kept only in
   the review record. The defect class is then guarded by nothing durable, and
   the next change can reopen it silently.

What these share: **the evidence and the thing it judges have a common origin**,
so their agreement is weak evidence on exactly the question that matters: whether
the shared understanding is correct. It still catches regressions against that
understanding; it cannot catch the understanding being wrong. The failure is
silent by construction. A self-consistent test does not misbehave; it passes.

This is the point where review most often finds slippage against a specification
or standard. Tests are written alongside the code, by the same author, at the
same moment, and reviewers read the green suite as independent confirmation. It
is not independent, and nothing in it says so.

The standing tension this record arbitrates: **convenience of co-located test
authoring** (fast, self-contained, no cross-repository coordination) **versus
independence of evidence** (expectations and specimens that could disagree with
the implementation, and would, if it were wrong).

## Principle

> **A relied-upon test MUST take its expected results from a source the
> implementation does not determine, MUST draw its specimens from an
> independently derived and reviewed authority where one exists, MUST state class
> invariants that every specimen inherits, and MUST turn every confirmed finding
> into durable executable evidence before the finding is closed.**

Four obligations, each independent of language, framework, and domain:

### 1. Expectations cite a source the implementation does not determine

An expected result is traceable to a specification, a published contract, a
reference implementation, or an independently maintained manifest, never to the
output of the code under test. Where an expectation is a judgement call that no
source settles, the test says so, so a reader does not mistake a chosen behaviour
for a specified one.

_Self-check:_ **if the implementation changed to violate the cited source, would
this expectation stay fixed and make the test fail?** If not, the test is not
independent evidence of that requirement.

### 2. Specimens come from an independently derived and reviewed authority

Independence is a property of **derivation and review**, not of location or
authorship alone. A specimen authority is independent when what each specimen
**is** (its class and expected verdict) is derived from a source the
implementation does not determine, and is reviewed against that source by
someone other than the implementation's author. Moving specimens written from
the implementation's own assumptions into another repository, or under another
name, does not make them independent.

Where such an authority exists for a domain, relied-upon tests consume it by
pinned reference rather than constructing their own specimens. The authority
owns what each specimen is. The consumer proves it treats each specimen
correctly.

Two consequences follow:

- **A component that judges a class of artifact should not be the source of
  the specimens it is judged against.** Specimens it generates inherit its
  assumptions, so they are weak evidence that it recognizes the class
  correctly. Whether a given repository forbids such generation outright is a
  repository decision, recorded in its own PDR.
- **An unavailable authority is a failure, never a skip.** This is EPR-0002
  obligation 2 applied to specimens: a missing corpus is absent evidence.

Where no independent authority exists yet, locally constructed specimens are
permitted as an explicitly **transitional** state, named as such with an owner
and a trigger, in the form EPR-0003 (proposed) sets out for aspirational
claims. They are not a conforming end state.

### 3. Class invariants are stated, and every specimen inherits them

Alongside per-specimen expectations, the tests state what must hold for every
member of each class, as "must never" rules. Examples: *no specimen of class X
ever produces outcome Y*; *no specimen of class X passes gate Z*. The invariants
are driven by class membership, so a new specimen is covered on arrival without
an author writing its expectation correctly.

### 4. A confirmed finding becomes durable executable evidence before it is closed

When review or field use demonstrates a defect, the finding is closed by
durable executable evidence. Usually that is the demonstrating input, added to
the specimen authority (or, transitionally, to the local tests) together with
its class. Where the defect is closed by a class invariant rather than a
specimen, the evidence is the control-of-the-control described below. Before the finding is closed, the new specimen is shown to **fail
against the pre-fix implementation** and pass against the fix. The baseline is
built from its own checkout of the pre-fix revision, not by stashing or reverting
working-tree changes, which can remove the new test along with the fix.

That last step is EPR-0002 obligation 3 applied to the regression itself. A
regression test that was never observed failing on the defect it names is
configured, not proven.

Where a finding is closed by a new **class invariant** rather than a new
specimen, no single specimen may be able to discriminate it: a conforming
specimen passes with or without the rule. The evidence is then a
**control-of-the-control**. Construct a specimen that violates only the new
rule, show it fails at that rule's assertion, and show the same specimen no
longer fails there when the rule is removed.

## Relationship to EPR-0002 and EPR-0003 (layering, stated to avoid dual authority)

[EPR-0002](EPR-0002-verification-gate-integrity.md) governs whether a gate's
**assertion** carries evidentiary force. This record governs whether the
**inputs to that assertion** (expectations and specimens) are independent of the
system being judged. A test needs both: a gate proven able to fail, fed evidence
that could disagree with the implementation.

The citation is one-directional, following the precedent set by EPR-0003
(proposed). EPR-0002 is
accepted and is not edited to cite this record. **More-specific-wins:** where a
question concerns the assertion itself (resolved state, absence, negative
control, exemptions), EPR-0002 governs.

[EPR-0003](EPR-0003-claim-integrity.md) treats any durable assertion as a claim.
An expected value is a claim about the system's behaviour, and obligation 1 here
is that record's evidence bound applied to tests. The transitional allowance in
obligation 2 is stated in EPR-0003's form (owner and trigger), so it cannot
quietly become permanent.

## Consequences

**Makes easier**

- A green suite becomes evidence a reviewer can rely on without re-deriving its
  expectations, because each expectation names its source.
- Review effort moves from "are these tests right?" to "do the cited sources say
  this?", which is checkable.
- Confirmed findings accumulate as durable specimens, so a defect class stays
  closed across later changes and across consumers of the same corpus.

**Makes harder / costs (accepted)**

- Cross-repository coordination. A behaviour change needs the corpus and the
  consumer to move in lockstep, with a pin bump between them.
- Slower test authoring. Writing a specimen into a separate authority, with its
  class and expected verdict, costs more than an inline string.
- Corpus availability becomes a test dependency, in CI and locally. A missing
  corpus fails the build by design.

## Graduation condition

This record graduates from proposed to accepted when a conforming reference
implementation exists in a repository **other than crucible**, with landed,
pinned evidence against every obligation and a declared coverage boundary,
comprising:

1. tests whose expectations trace to a cited specification or an independently
   maintained manifest, and not to the code under test;
2. specimens consumed by pinned reference from a corpus maintained separately
   from the consuming implementation, with an unavailable corpus failing the run;
3. class invariants that a newly added specimen inherits without per-specimen
   expectations, declared by the specimen authority in a form the consumer
   enforces exactly, with a check that fails when the two disagree;
4. at least one confirmed finding carried into durable executable evidence,
   with its control against the pre-fix revision recorded;
5. negative controls for (2) and (3), per EPR-0002 obligation 3: a missing or
   wrong-pin corpus is shown to fail the run, and a specimen given a violating
   verdict is shown to fail its class invariant.

**Candidate reference (not yet evidence).** A key-material detector and its
synthetic fixture corpus are being brought into this shape: the detector's tests
move to the corpus by pinned reference, and adversarial review findings become
corpus specimens. Until that work lands and meets every item above, it is a plan,
and this record does not cite it as conformance.

A separate repository is necessary for that implementation but is not, by
itself, proof of independence; the evidence must show independent derivation
and review of the specimen authority.

**Not evidence.** A review panel that catches self-consistent tests does not
discharge this condition. It shows that reviewers work, not that the evidence is
independent.

## Adoption & propagation

Per ADR-0002/0003, this record is canonical upstream in crucible. Adopting
repositories link or vendor it, prefer a pinned reference, and record local
conformance.

It binds any repository whose tests are relied upon to discharge review or
authorize a release. Obligation 2 binds where a shared specimen corpus exists for
the domain; where none exists, a repository conforms by naming its local
specimens as transitional, as obligation 2 requires.

## Not this record (one principle per record)

- **Whether a gate can fail, asserts resolved state, or carries undeclared
  exemptions** → EPR-0002.
- **Which corpus a domain uses, how it is pinned, and how consumers fetch it** →
  the consuming repository's **PDR** and the corpus repository's records.
- **Whether a corpus specimen is safe to commit** (for example, provably unusable
  key material) → the corpus repository's records, and **SecDR** where security
  posture is at stake.
- **Test-strategy ownership within a review panel** → PDR-0005 and the
  fierce-collaboration standard.
- **Coverage targets** → repository policy.

## Rationale for the record type

**EPR, not PDR.** The domain is engineering practice and the lifecycle is
durable. Strip every tool, corpus, and language and the four obligations survive.
Which corpus to use and how to pin it is revisable and belongs in a PDR;
"evidence must be independent of what it judges" is not revisable without
reversing the principle.

**Not an amendment to EPR-0002.** EPR-0002 is accepted and publicly cited, and
its subject is the assertion. Folding specimen and expectation provenance into it
would widen a ratified record's scope after citation. A sibling record with a
stated layering keeps both citable.

## References

- [ADR-0003: Decision & Governance Record Taxonomy](ADR-0003-decision-record-taxonomy.md) — defines EPR
- [EPR-0002: Gates Assert on Resolved State and Are Proven Able to Fail](EPR-0002-verification-gate-integrity.md) — the assertion; obligations 2 and 3 are applied here to specimens and regressions
- [EPR-0003: Durable Claims Assert on What Exists and Move When It Moves](EPR-0003-claim-integrity.md) — expectations as claims; the transitional-state form
- [PDR-0005: Adopt the Fierce-Collaboration Multi-Agent Review Process](PDR-0005-adopt-fierce-collaboration-review.md) (proposed) — review roles for test strategy and implementation
- [Decision & Governance Records — the `*DR` family](../repository/decision-records.md) — the normative catalog

## Revision History

| Date       | Status Change | Summary                                                       | Updated By |
| ---------- | ------------- | ------------------------------------------------------------- | ---------- |
| 2026-10-09 | → proposed    | Draft: expectations, specimens, class invariants, findings    | devlead    |
| 2026-10-09 | (proposed)    | Independence is derivation and review, not location; EPR-0003 cited as precedent; Obl. 4 allows control-of-the-control | devlead (entarch review) |
