---
id: "PDR-0005"
title: "Adopt the fierce-collaboration multi-agent review process"
status: "proposed"
date: "2026-07-23"
last_updated: "2026-07-27"
deciders:
  - "@3leapsdave"
  - "cxotech"
  - "entarch"
scope: "Crucible foundation / shared governance — ways-of-working"
tags:
  - "process"
  - "review"
  - "agents"
  - "governance"
sensitivity: "0-public"
access_tier: "public"
relates-to:
  - "crucible ADR-0003 (the *DR taxonomy; review flow is PDR territory)"
  - "crucible EPR-0002 (the verification principle this operationalizes for the review act)"
  - "crucible docs/standards/fierce-collaboration-review.md (the standard this ratifies)"
  - "crucible schemas/review-journal/v0 (the review-journal data contract)"
  - "crucible docs/standards/data-sensitivity-classification.md, access-tier-classification.md (the ROE yardstick)"
---

# PDR-0005: Adopt the Fierce-Collaboration Multi-Agent Review Process

## Status

**Proposed.** Ways-of-working record ratifying the fierce-collaboration review
standard.

## Context

Relied-upon reviews — those whose green authorizes a merge, release, or security
sign-off — increasingly run as panels of AI-agent seats plus human maintainers.
Their quality varies by **prompt, role framing, and approach at least as much as by
model**: the same model produces different results live versus as a sub-agent, and
different seats surface different findings. Without a hardened, shared process, a
relied-upon review's rigor is a function of who happened to run it.

The organization already practices a mature version of this — a fixed role-seat
panel, an evidence-or-it-didn't-happen bar, gate tables, adversarial verification,
numbered rounds with P1-blocker-until-green, and an append-only alignment log — but
it lives in practice, not in a referenceable standard. A standard lets any session
say _"follow the review process guidelines in the fierce-collaboration standard"_
and get the same rigor.

## Decision

Adopt three artifacts as the canonical review process for relied-upon
**collaborative, open, direct-access** reviews:

1. **The standard** — [`docs/standards/fierce-collaboration-review.md`](../standards/fierce-collaboration-review.md):
   the methodology (principles, panel, evidence bar, gates, adversarial techniques,
   rounds, implementing-side obligations, the review record, classification ROE,
   and the role-prompt requirement).
2. **This PDR** — the ratifying instrument (review flow is a ways-of-working choice,
   PDR territory per ADR-0003).
3. **The review-journal data contract** — [`schemas/review-journal/v0`](../../schemas/review-journal/v0):
   an optional-but-recommended append-only ndjson emission parallel to the required
   markdown alignment log.

Two framings are load-bearing:

- **Markdown alignment log is the required foundation; the ndjson journal is
  strongly-recommended best practice** (diffable across rounds and panels; makes
  panel variance measurable; intended, not yet evidenced, to cut review wall-time).
  Not mandated; when emitted it MUST conform to the contract.
- **Both the record and the journal use the ecosystem's own sensitivity and
  access-tier classification.** The cxotech agent for an org, or the maintainer,
  sets the content-level ceiling; contributors get a partially-objective scan of
  whether a piece of evidence is permitted in a given record.

Role prompts are reframed **adversarial-in-verification, collaborative-in-goal**,
and the review role catalog is reconciled incrementally — `devrev` and `secrev`
in this release, other seats as they are adopted — to that
stance in the same release.

**Mode boundary.** This process does not govern adversarial-by-design exercises,
arms-length attestations, blind or compartmented panels, or proof-mediated reviews.
Those modes have different independence, disclosure, evidence-access, and success
criteria. A larger assurance workflow may compose modes, but each stage retains
its own scoped disposition; one stage's green is evidence for, not a substitute
for, another stage's gate.

**Structural placement (ruled by entarch).** The standard is homed at
`docs/standards/` (the process signal is carried at the decision layer by this
PDR's type, not re-encoded in the tree); scope is **crucible-canonical,
link-or-vendor, prefer pinned-reference**, the same model EPR-0001/0002 run under.
Seat **identity** (the seat enum) is the galaxy-stable contract surface; role-prompt
**content** is per-org, which is what lets a sibling org link rather than fork.

**Altitude of the two non-negotiables.** The standard's `author-≠-approver` and
`human-merge-authority` are **principle-level** commitments: weakening or removing
either requires **principle-altitude review**, not a routine revision of a
PDR-ratified standard. They are EPR candidates should the durable core warrant its
own record; extraction is deferred with an owner (entarch) rather than minting the
EPR now — this closes the wrong-altitude-revisability without premature ceremony.

## Consequences

**Positive**

- A relied-upon review's rigor stops depending on who ran it; the framing is
  hardened and vendorable across the estate.
- Panel variance (sub-agent vs live, model vs model, framing vs framing) is
  **intended** to become measurable via the journal, so the org can learn which
  framings harden the process. Stated as design intent: v0 records the raw fields
  for partial or manual analysis, but does not yet join a participant to its
  role-prompt and reasoner, so conformance is not evidence that this measurability
  has been achieved (see _Deferred with owner and trigger_).
- Sensitivity/access-tier classification on records turns "is this evidence OK to
  put here?" into a check against a declared bound.

**Negative / costs**

- A relied-upon review carries more ceremony (named role prompts, gate tables,
  classified records). Accepted: the cost is bounded and the alternative is
  unreproducible rigor.
- The ndjson journal adds an emission to maintain where a team opts into it.

## Deferred with owner and trigger

This decision ratifies the methodology. It does **not** claim the `review-journal/v0`
contract enforces everything the standard requires. The gaps below are accepted
knowingly, each with an owner and a closure trigger, and are disclosed on the
contract surface itself so a downstream adopter reading a pinned reference can see
them without access to any panel's working record.

| Gap                                                                                                                                              | Owner   | Closure trigger                                                                                 |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | ------- | ----------------------------------------------------------------------------------------------- |
| Cross-enum: `access_tier ≥ sensitivity` is a documented rule, not a schema check                                                                 | secrev  | Before v0 is described as enforcing it, or before promotion to a stable contract                |
| Cross-stream: an event's classification is not checked against the manifest ceiling                                                              | secrev  | As above                                                                                        |
| Anchor content is unconstrained — presence is required, well-formedness is not                                                                   | secrev  | As above                                                                                        |
| Participant identity cannot be joined to role-prompt and reasoner, so variance is not machine-measurable                                         | cxotech | Before any claim that panel variance is machine-measurable is made without a caveat             |
| Prompt identity is not integrity-bearing: `role_prompt.digest` is optional, so `{slug, version}` alone can name two materially different prompts | cxotech | With the participant-join work, or before any framing-comparison claim is made without a caveat |
| `author-≠-approver` is stated at principle altitude and enforced by no mechanism on any surface                                                  | cxotech | Before v0 is described as carrying the non-negotiable, or at draft→accepted                     |
| `human-merge-authority` is likewise stated at principle altitude and enforced by no mechanism                                                    | cxotech | As above                                                                                        |
| Anchor token form: a composite anchor must name the object format that produced it                                                               | secrev  | With the anchor-content constraint above                                                        |

Until a trigger fires, the corresponding claim is stated as design intent and the
gap travels with the contract. A conforming journal is evidence of shape, not of
these properties.

**Scope of this table.** It lists every accepted contract gap that bears on a
public claim. The remaining items in the contract's implementation queue —
machine-readable finding lifecycle and gate scope, the defect-`class` field, the
`reasoner` field, and a validator for the classification ceiling across a journal
set — are **implementation work under claims this table has already bounded**, not
additional accepted gaps. They are named here once so a public reader does not have
to reconstruct the boundary, and they do not carry separate triggers.

## References

- [Fierce-Collaboration Review standard](../standards/fierce-collaboration-review.md)
- [EPR-0002: Gates Assert on Resolved State and Are Proven Able to Fail](EPR-0002-verification-gate-integrity.md)
- [ADR-0003: Decision & Governance Record Taxonomy](ADR-0003-decision-record-taxonomy.md)
- [Decision & Governance Records — the `*DR` family](../repository/decision-records.md)

## Revision History

| Date       | Status Change | Summary                                                                                       | Updated By |
| ---------- | ------------- | --------------------------------------------------------------------------------------------- | ---------- |
| 2026-07-23 | → proposed    | Ratify the fierce-collaboration review standard + journal contract                            | cxotech    |
| 2026-07-27 | (refine)      | Record deferred contract gaps with owners and closure triggers; bound the measurability claim | cxotech    |
