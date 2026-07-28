---
id: "EPR-0003"
title: "Durable claims assert on what exists and move when it moves"
status: "proposed"
date: "2026-07-27"
last_updated: "2026-07-27"
deciders:
  - "@3leapsdave"
  - "cxotech"
  - "entarch"
scope: "Crucible foundation / shared governance — durable engineering principle"
tags:
  - "principles"
  - "documentation"
  - "governance"
  - "review"
relates-to:
  - "crucible ADR-0002 (proposed; canonical upstream home with adopters linking or vendoring, for an interchange contract — the same reasoning this record applies to claims)"
  - "crucible ADR-0003 (the *DR taxonomy; third EPR under it)"
  - "crucible EPR-0001 (what you ship — published artifacts carry an integral dependency graph)"
  - "crucible EPR-0002 (what you check — its obligation 4 is the gate-coverage instance of this principle)"
---

# EPR-0003: Durable Claims Assert on What Exists and Move When It Moves

## Status

**Proposed.** Third Engineering Principle Record under ADR-0003. Altitude ruled by
entarch (sibling to EPR-0002, not a parent; EPR altitude rather than a process
section). It graduates to accepted when a conforming reference implementation
exists — see _Graduation condition_ — and not before. The record deliberately does
not claim a conformance it has not yet earned; doing so would be the defect it
describes.

## Context

A **durable claim** is any assertion about a system that outlives the change that
produced it: a decision record's conformance statement, a README describing what a
schema enforces, a doc comment about what a function guarantees, a token whose name
asserts an algorithm, a release note describing a capability.

Unlike a gate, a durable claim has no natural moment of failure. A gate that stops
matching reality goes red. A claim that stops matching reality simply keeps being
read — and it is read most trustingly by the people furthest from the code, who
have no way to check it.

Three failure modes recur. They are stated as hazards of the shape, not as history:

1. **The claim outruns the implementation.** It is written while the mechanism is
   planned, correct at the time as aspiration, and never revised when the mechanism
   lands narrower than intended. Nothing marks the moment it became false.
2. **The claim propagates and only one copy is fixed.** The same assertion is
   restated on several surfaces — a standard, a decision record, a contract README,
   packaging copy. A defect is found and closed on the surface under review, and
   the identical claim survives on the others. The fix is real and the class is
   untouched.
3. **The label asserts something the thing does not do.** A name, prefix, or
   summary carries a claim of its own — an algorithm, a coverage, an enforcement —
   and no one checks the label against the mechanism, because a label does not look
   like a claim.

What these share: **the claim describes something other than the resolved state of
the system**, and the gap is invisible precisely where a reader most relies on it.
The failure is silent by construction. A stale claim does not misbehave; it reads
well.

This principle belongs in the shared foundation because the organization has
already converged on it independently, without naming it. Two of three published
data contracts bound their conformance claims unprompted — `data-artifact/v0` and
`process-run/v0` each state that the schemas provide a structural validation
surface and that behavioral rules are enforced elsewhere, "not by schema
validation." The `auth/v0` session-artifact standard claims its invariants are
enforced structurally **and** discloses where structural enforcement cannot reach.
Those are this principle, practiced. What is missing is the record that makes the
practice binding rather than habitual, and reaches the surfaces where it was not
applied.

The standing tension this record arbitrates: **the pull toward the stronger claim**
— a record reads better, a contract sounds more complete, a release note lands
harder — **against the ongoing cost of keeping every claim level with what was
actually built.** The stronger claim is free at the moment of writing and expensive
at the moment someone relies on it.

## Principle

> **A durable claim MUST assert on the resolved state of what exists, MUST be
> labelled as aspiration while the thing it describes is still a plan, and MUST
> move on every surface that carries it when the implementation moves.**

Two obligations.

### 1. A claim is bounded by the evidence that exists for it

A claim states what is true of the implementation as built — its actual coverage,
its actual enforcement, its actual algorithm. Where the implementation discharges
part of what the claim would naturally imply, the claim **names the part it
discharges** and the boundary is stated with it, not left to the reader to infer
from silence.

Aspiration is legitimate. A record may describe an intended end state **while the
thing it describes is a plan**, provided it is labelled as intent and carries an
owner and a closure trigger. What is not legitimate is leaving that language in
place once the implementation lands: at that moment the aspiration becomes a claim
broader than its evidence, committed to a durable surface where it outlives the
review that would have caught it.

_Corollary — a label is a claim._ A name that asserts an algorithm, a coverage, or
an enforcement is checked against the mechanism like any other assertion. A label
is the claim least likely to be reviewed and most likely to be trusted without
re-derivation.

### 2. A claim moves on every surface that carries it

Where one assertion appears on more than one durable surface, it is **stated once
and referenced**, or the surfaces carrying it are **enumerated in the record that
owns the claim**. A claim restated in N places has N opportunities to go stale and
one review that will notice.

This is the same reasoning
[ADR-0002](ADR-0002-keymaterial-fingerprint-portable-contract.md) (proposed)
applies to an interchange contract — one canonical upstream home, adopters linking
or vendoring rather than maintaining divergent copies, so producer and consumer
cannot drift — carried over from documents to claims: the reason not to fork a
standard is the reason not to restate an assertion.

_Corollary — closing an instance is not closing the class._ When a stale claim is
found, the remediation covers every surface carrying it. Fixing the reviewed copy
and leaving the others is a partial fix presented as a closure.

## Relationship to EPR-0002 (layering, stated to avoid dual authority)

[EPR-0002](EPR-0002-verification-gate-integrity.md) obligation 4 — "an exactness
claim admits no undeclared exemption" — is **the gate-coverage instance** of this
record's general principle: a check's coverage claim, bounded to what the check
actually reconciles.

The citation is **one-directional**. This record cites EPR-0002; EPR-0002 is not
edited to cite this one. It is accepted and publicly cited, and mutating what a
cited record says in order to tidy a genealogy would itself violate obligation 1.

**More-specific-wins.** EPR-0002 obligation 4 remains the authority for gate
exactness claims. This record governs durable claims generally, including those
with no gate anywhere near them. Where both could apply to a check's coverage
statement, EPR-0002 governs.

## Consequences

**Makes easier**

- A reader can rely on a record without re-deriving it. That is the whole value of
  a durable record, and it is exactly what a stale claim destroys.
- Deferral becomes honest and cheap: "intended, not yet evidenced, owner X, trigger
  Y" is a conforming way to say something true, so there is no pressure to either
  overclaim or stay silent.

**Makes harder / costs (accepted)**

- Every claim acquires maintenance. Landing an implementation now includes
  revisiting the language that anticipated it.
- Records read less confidently. A bounded claim is less quotable than an
  unbounded one; that is the trade, and the bounded one is the one that stays true.
- Enumerating a claim's surfaces is work that has no payoff until the claim
  changes — the same shape as writing a negative control, and accepted for the same
  reason.

**Where this bites — an open question, not a finding.** The instances observed so
far cluster in **recently authored material**, where a claim was written alongside
a mechanism that was not finished. It is tempting to conclude the hazard
concentrates there and to direct adopters accordingly. That conclusion is not
supported: the sampling was itself concentrated on recent material, so
_"concentrated in recent work"_ and _"we have only examined recent work"_ are not
yet distinguished. The competing hypothesis is at least as plausible — the oldest
records have had the most time to drift out of step with their implementations, and
the least recent scrutiny.

A full sweep of this repository's own corpus — every decision record, published
contract, core standard, and role prompt — narrows the question without settling
it. The established corpus is not clean: it holds a record whose worked example
asserts an ordering its own next paragraph denies, and a decision record whose
graduation claims whole-record conformance while its evidence bounds one
obligation. But it holds **fewer** instances, and none at the severity of the worst
found in recent material. The skew is real and the sample is small.

So: treat recency as a weak prior, not an ordering. An adopter auditing its own
claims should start where a mechanism landed after the language describing it was
written — which correlates with recency but is not the same thing, and is the
property that actually predicts the defect.

## Graduation condition

This record graduates from proposed to accepted when a conforming reference
implementation exists in a repository **other than crucible**, comprising:

1. a **claim register** — the durable claims an artifact makes, the surfaces
   carrying each, and the mechanism each asserts;
2. **executable checks** for what is mechanizable — that enumerated surfaces move
   together, that a claim naming a mechanism can be asserted against it, and that a
   public artifact references nothing an external reader cannot resolve;
3. **negative controls** for those checks, per EPR-0002 obligation 3: a baseline
   green as case zero, one mutation per direction expected to turn each check red,
   each pinned to its own failure identity rather than a non-zero exit;
4. a **replay result** against a corpus of real, previously shipped stale claims —
   what the mechanism catches is its coverage, and what it misses is a declared
   boundary rather than an omission.

**Why external, and why unprimed.** Validation outside crucible keeps the evidence
independent of the record's author and leaves room to change crucible if the
mechanism does not work first time. Beyond that, the reference corpus should be one
**not already shaped by this estate's EPR or panel work**: a primed corpus yields
correlated evidence for the same reason a single-reasoner panel does. A repository
already conformed to EPR-0001, or already reviewed under a fierce-collaboration
panel, is a weaker cold test than one meeting the claim register for the first
time.

**Not evidence.** A review panel that catches stale claims does **not** discharge
this condition. It evidences that reviewers work, not that the mechanism works —
EPR-0002 obligation 3 applied to this record, and the failure mode here most likely
to be mistaken for success.

## Adoption & propagation

Per ADR-0002/0003 this record is canonical upstream; adopting repositories **link
or vendor** it rather than maintaining divergent copies, and prefer a pinned
reference over a vendored copy. Conformance is recorded locally.

There is no qualifying shape to check. A repository that publishes durable claims —
which is every repository with a README — is in scope.

When the fierce-collaboration review standard is ratified (PDR-0005, proposed), its
implementing-side obligation to keep a claim level with what exists becomes the
**review-act instance** of this record, in the same relation EPR-0002 holds to that
standard's trust-nothing principle. That standard is not yet merged, so this record
states the relationship as **intended rather than as existing** — an aspiration
under obligation 1, and therefore owned and triggered like any other: **owner**
cxotech; **trigger** — on PDR-0005's ratification the sentence states the relation
as existing, and if PDR-0005 is not ratified the sentence is removed rather than
left standing.

## Not this record (one principle per record)

- **Whether a remediation addresses a defect class or only the instance shown** →
  a review-process concern; the fierce-collaboration standard's convergence rule.
  Related in shape, distinct in subject: that rule governs _fixes_, this record
  governs _claims_.
- **Separation of duties and human authority over AI-authored merges**
  (`author-≠-approver`, `human-merge-authority`) → their own deferred record,
  owned by entarch. This record governs how a principle-without-a-mechanism is
  **stated**; that record supplies the anchor for those two.
- **Whether a given claim is worth making at all** — product positioning,
  messaging, emphasis → not a principle question.
- **Prose quality, tone, and readability** → style, not integrity.

## References

- [ADR-0002: Key-Material Fingerprint Contract as a Portable Schema](ADR-0002-keymaterial-fingerprint-portable-contract.md) (proposed) — canonical upstream home, link-or-vendor, producer and consumer cannot drift
- [ADR-0003: Decision & Governance Record Taxonomy](ADR-0003-decision-record-taxonomy.md) — defines EPR
- [EPR-0001: Published Artifacts Carry an Integral Dependency Graph](EPR-0001-published-artifact-dependency-integrity.md) — what you ship; its reference-implementation section is the model for per-obligation evidence accounting
- [EPR-0002: Gates Assert on Resolved State and Are Proven Able to Fail](EPR-0002-verification-gate-integrity.md) — what you check; obligation 4 is this principle's gate-coverage instance
- [Decision & Governance Records — the `*DR` family](../repository/decision-records.md) — the normative catalog

## Revision History

| Date       | Status Change | Summary                                                                                                                                          | Updated By       |
| ---------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------- |
| 2026-07-27 | → proposed    | Third EPR under ADR-0003; sibling to EPR-0002 per entarch altitude ruling; graduation deferred to an external, unprimed reference implementation | cxotech, entarch |
