---
id: "PDR-0006"
title: "Crucible ships no consumer-linked code"
status: "accepted"
date: "2026-07-28"
last_updated: "2026-07-28"
deciders:
  - "entarch"
  - "@3leapsdave"
scope: "Crucible foundation / repository charter"
tags:
  - "process"
  - "governance"
  - "scope"
  - "supply-chain"
relates-to:
  - "crucible ADR-0003 (the *DR taxonomy; PDR = a revisable ways-of-working choice)"
  - "crucible EPR-0002 (a gate proven able to fail; the basis for admission-by-fixture)"
  - "crucible EPR-0003 (proposed; a claim states no more than its mechanism supports)"
---

# PDR-0006: Crucible Ships No Consumer-Linked Code

## Status

**Accepted.** Records a charter that has governed this repository implicitly
since its creation and was never written down.

## Context

Crucible is a standards repository: documentation, schemas, and configuration
are the product. What it may and may not **ship** has never been stated in any
committed file — no document in `docs/`, and no section of `README.md`, contains
a scope rule of this kind.

An implicit charter is not a harmless omission. It was discovered the way
implicit rules are usually discovered — by three concurrent work items relying
on incompatible readings of it:

- One task states that crucible hosts a contract and a conformance corpus,
  **"data only — charter excludes runtime."**
- A second states crucible owns "the public standard, adoption guide, schemas,
  **canonical scripts**, and conformance fixtures."
- A third specifies a canonical projector as "a small **Go command**, standard
  library only," landing in crucible as canonical and template-distributable.

All three had been reviewed and aligned. As written they make opposite claims
about whether this repository ships runtime. No reviewer caught the conflict,
because there was no charter statement to check any of them against.

The practical cost was not hypothetical. One of those work items selected an
implementation in another repository as its "reference emitter" **because it
assumed crucible could not host one** — a design decision inherited from an
unstated premise rather than made on its merits.

This is the defect class [EPR-0003](EPR-0003-claim-integrity.md) governs, applied
to the repository itself: a claim ("charter excludes runtime") carrying more load
than any stated mechanism supports.

## Decision

Two rules govern what crucible ships. They are independent. Both must hold.

### Rule 1 — Linkage

> Crucible ships nothing that consuming code imports, links, or depends on at
> build or run time. It MAY ship standalone canonical tools and fixtures whose
> sole purpose is to make its contracts **falsifiable** or **materializable** —
> and any such tool is itself admitted by the corresponding conformance
> fixtures, never by fiat.

The discriminator is **linkage**, not "is it code." A dependency edge from
consumer code makes an artifact a library, which is out of charter. A standalone
tool invoked at authoring or verification time is falsifiability tooling, which
is in charter.

Linkage is chosen deliberately over a purpose test. "Whose purpose is to support
the contract" is arguable by anyone motivated to argue it; whether consumer code
carries a dependency edge is answerable by inspection. A charter that can be
talked past is not a charter.

**Falsifiable or materializable** are both load-bearing, and the second is not
padding. A tool that only _checks_ an artifact is obviously falsifiability
tooling. A tool that _emits_ the artifact — a canonical projector producing
exact bytes — would argue out of charter on a technicality if the rule spoke
only of falsification, despite being the same kind of thing serving the same
purpose. Materialization is named so that the canonical producer and the
canonical checker sit on the same side of the line.

**Admitted by fixtures, never by fiat** is the clause that keeps Rule 1 honest.
A canonical tool that is canonical _because it is ours_ is precisely a gate that
has never been demonstrated able to fail — the defect
[EPR-0002](EPR-0002-verification-gate-integrity.md) obligation 3 exists to
prevent. Crucible's own tooling earns its status by passing the same conformance
fixtures any third-party implementation must pass, or it does not have that
status.

### Rule 2 — Dependencies

> Any canonical tool crucible ships is standard-library-only. This does not
> follow from Rule 1 and is not hygiene. Verification tooling that itself
> requires trusting a dependency tree re-introduces the exact trust question it
> exists to settle, and a standards repository's consumers cannot audit a
> supply-chain surface they never chose. A tool that satisfies Rule 1 is still
> refused under Rule 2; relaxing Rule 2 is an amendment to this record, not a
> siting judgment.

Rule 2 is stated separately because it is a genuinely independent constraint.
A tool can satisfy Rule 1 completely — standalone, never linked, invoked only at
verification time — and still be refused under Rule 2. A future reader
encountering such a refusal gets the reason from the text: the exclusion is on
principle, with a rationale that can be argued against if warranted, rather than
an unexplained habit.

#### Rule 2a — Which tools Rule 2 governs

> Rule 2 governs **canonical contract tooling**, and it governs **anything this
> repository holds out for copying or adoption** — being held out as a template
> _is_ shipping, in the sense the charter cares about. It does **not** govern
> purely repository-internal infrastructure, which is ordinary repo hygiene and
> not a charter matter.

The boundary is named because the original rule did not name one, and three
different things were sitting behind the same word. The honest consequence is
recorded rather than avoided: this repository's release-signing scripts are
held out as a template others clone, so they are **class (b) and governed** —
there is no grandfathering by silence.

#### Rule 2b — The external-invocation set

Rule 2's original phrasing, "standard-library-only," has a precise and
inspectable meaning for a compiled program and **no defined referent for a tool
that orchestrates other programs.** A shell tool has no standard library in the
sense the rule intends. Left unaddressed, the rule would refuse every such tool —
including tooling this repository already ships — and a rule the repository's own
tooling fails is one that gets quietly ignored rather than applied. An ignored
rule is worse than an absent one: it launders later exceptions as precedent.

> A canonical or held-out tool that is not a compiled standard-library-only
> program **MUST declare the closed set of external commands it invokes**, and
> every entry in that set MUST be justified on **exactly one** of two grounds:
>
> 1. **Subject-matter** — the command is, or implements, a mechanism **the
>    contract itself names**.
> 2. **Baseline** — the command appears on the baseline list fixed by this
>    record: **POSIX `sh`, POSIX coreutils, and `git`**.
>
> **Undeclared invocation is nonconformance.** Extending the baseline list is an
> amendment to this record, not a siting judgment.

**The subject-matter ground is "named by," not "related to."** That distinction
is the whole of its discipline. A verifier of OpenPGP signatures invokes the
OpenPGP implementation the contract names; a fingerprint checker invokes the
oracle the specification names. Invoking the system under verification adds no
trust surface beyond what the contract already requires — refusing it would
remove the _check_, not the trust, and would leave the contract's central gate
unproven able to fail, which is exactly what
[EPR-0002](EPR-0002-verification-gate-integrity.md) obligation 3 forbids. Were
the ground "related to the contract," it would become a purpose test through the
back door, reopening precisely what Rule 1 chose linkage to close. The contract
text is the inspectable referent.

**The baseline ground is a written list, not a category.** "Operating-system
baseline" is arguable by anyone motivated to argue it, in the same way a purpose
test is. An enumerated list is not. The list is deliberately short, and growing
it is a visible act.

**What Rule 2 was always aiming at.** The target was never "this tool invokes
other programs." It is the **unauditable dependency tree** — code this repository
vendors, pins, or causes to be fetched, chosen by us and invisible to the people
who must trust the result. An operator-supplied external command is the opposite
posture: the consumer chose it, installed it, and audits it through their own
platform. So Rule 2 reads, in full: no vendored third-party code, no
manifest-resolved dependency trees, no fetches — and, for tools that orchestrate,
a declared invocation set justified on the two grounds above.

The declared set is verified by **reading the tool** — inspection, not argument.
That is the same property that made linkage win over purpose in Rule 1, and it is
why the declaration is mandatory rather than advisory: a rule you can only
satisfy by explaining yourself is a rule that erodes.

## Worked examples

Applying both rules to the work items that surfaced the conflict:

| Artifact                                                                                             | Rule 1                                     | Rule 2                                                                                                                                                   | Result                                                                                                    |
| ---------------------------------------------------------------------------------------------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Canonical trust-anchor projector (standalone command; materializes and verifies the anchor contract) | **In** — never linked by consumers         | **Compliant** — standard-library-only                                                                                                                    | **Ships in crucible**                                                                                     |
| Portable-claims conformance corpus (fixtures)                                                        | **In** — data                              | n/a                                                                                                                                                      | **Ships in crucible**                                                                                     |
| Portable-claims encoders (canonical encoding in each foundation library)                             | **Out** — consumer-linked                  | never reached                                                                                                                                            | **Ships in the foundation libraries**, which vendor the crucible contract                                 |
| A crucible-hosted reference encoder                                                                  | **Permitted**                              | **Permitted**                                                                                                                                            | **Declined on the merits** — see below                                                                    |
| Canonical chain verifier (shell; invokes an OpenPGP implementation and a fingerprint oracle)         | **In** — standalone falsifiability tooling | **Compliant** — declared set: `sh`/coreutils (baseline), the OpenPGP implementation and the fingerprint oracle (subject-matter; the contract names both) | **Ships in crucible**                                                                                     |
| This repository's release-signing scripts (shell; invoke `git` and an OpenPGP implementation)        | **In** — class (b), held out as a template | **Compliant** substantively — `git` baseline, OpenPGP subject-matter — but the declaration is **required when next touched**                             | **Ships**, conformance by declaration rather than by coincidence                                          |
| A shell tool invoking a general-purpose JSON processor for its own convenience                       | **In**                                     | **Refused** — clears neither ground                                                                                                                      | **Does not ship** as written: declare the need and argue the baseline addition in daylight, or do without |

The fourth row is the important one. A crucible-hosted reference encoder is
permitted by both rules and was still declined, because a designated reference
implementation _anywhere_ establishes an authority competing with the conformance
corpus — and the corpus, not any implementation, is the normative arbiter of
conformance. Recorded here to make the charter's shape explicit: **it bounds what
crucible _may_ ship, not what it _must_.** A siting question is answered by these
rules; a design question is still argued on its merits afterward.

## Consequences

- Every future siting question has a citable rule and a testable discriminator,
  rather than a reading reconstructed per task.
- Canonical tooling in crucible carries a standing obligation: it passes its
  contract's conformance fixtures like any other implementation. Canonical status
  is earned per release, not held by provenance.
- Crucible acquires no third-party dependency surface, so a consumer auditing
  what it vendors audits the standard library and nothing else.
- Work items whose siting was decided before this record are re-checkable against
  it. The three that surfaced the conflict are resolved in the table above.
- A tool that needs a dependency is refused, and the refusal is contestable by
  amending this record — a visible, deliberate act rather than a quiet exception.
- Orchestrating tools carry a standing authoring obligation: the declared
  invocation set ships with the tool. Tooling that predates this record gains its
  declaration when next touched, so conformance is stated rather than inferred.
- The baseline list is a deliberate chokepoint. Convenience dependencies are
  refused by default, and the cost of adding one is a visible amendment rather
  than a commit nobody reads.
- Charter conformance for shell tooling is now decidable by reading the tool.
  Both rules are answerable by inspection, which was the property Rule 1 was
  designed for and Rule 2 previously lacked.

## Alternatives considered

**Leave the charter implicit.** Rejected: it had already produced three mutually
inconsistent statements across reviewed work, and one design decision made from
an unstated premise. An implicit rule cannot be cited, tested, or argued against.

**A purpose test** ("tools whose purpose is to support the contract"). Rejected:
it leaves _who decides the purpose_ open, so it settles nothing that a motivated
reading cannot reopen. Linkage is inspectable.

**Land the charter sentence in the portable-claims contract PR.** Rejected: a
durable scope rule inside a contract PR reads as incidental to that contract and
is awkward to cite from unrelated siting questions. It also lands later than the
work it needs to govern — two queued tasks would otherwise be authored against an
unwritten charter, which is the condition this record exists to end.

**Fold the dependency constraint into Rule 1.** Rejected: it presents one rule
where there are two, leaving a later reader unable to tell whether a
dependency-bearing standalone tool was excluded on principle or on hygiene.

_The alternatives below were considered when Rule 2's referent was settled._

**Read Rule 2 literally and ship no canonical checker.** Rejected. It is
rule-compliant and the worst available outcome: it leaves a contract with a
canonical producer and no canonical checker, so the contract's central gate is
never demonstrated able to fail, and every consumer writes its own verifier —
the per-repo drift a canonical checker exists to end. The literal reading also
condemns tooling this repository already ships, and a rule its own tooling fails
does not get applied; it gets ignored, and the exceptions become precedent.

**Scope Rule 2 to compiled tools and govern shell tooling separately.**
Rejected: two regimes re-create inside Rule 2 the ambiguity that splitting it
from Rule 1 was meant to end. A reader would have to determine which regime
applies before learning what the rule is.

**Admit "operating-system baseline" as a category rather than a written list.**
Rejected for the same reason a purpose test was rejected for Rule 1: a category
is arguable by anyone motivated to argue it. The list is short and explicit, and
extending it is an amendment in daylight.

**Rewrite the affected tooling in a compiled language to satisfy the literal
rule.** Rejected as not constructible, and it is worth recording why rather than
leaving a future reader to rediscover it. No mainstream systems language ships an
OpenPGP implementation in its standard library. A stdlib-only canonical verifier
of OpenPGP signatures therefore cannot be written in any language — the
constraint is structural, not a consequence of the implementation language
chosen.

## References

- [ADR-0003: Decision record taxonomy](ADR-0003-decision-record-taxonomy.md)
- [EPR-0002: Gates assert on resolved state and are proven able to fail](EPR-0002-verification-gate-integrity.md)
- [EPR-0003: Durable claim integrity](EPR-0003-claim-integrity.md)

## Revision History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 2026-07-28 | Initial record. Charter ruled by entarch; two-rule form adopted after review found the dependency constraint was independent of the linkage discriminator.                                                                                                                                                                                                                                                                     |
| 2026-07-28 | Amendment: Rule 2a (which tools Rule 2 governs) and Rule 2b (the declared external-invocation set, with the subject-matter and baseline grounds). Added on the charter's first hard case — Rule 2's "standard-library-only" had no defined referent for a tool that orchestrates other programs, and the literal reading refused tooling this repository already ships. Rule 1 and the original Rule 2 sentence are unchanged. |
