---
id: "ADR-0003"
title: "Decision & Governance Record Taxonomy (the *DR family)"
status: "accepted"
date: "2026-06-29"
last_updated: "2026-06-29"
deciders:
  - "@3leapsdave"
  - "cxotech"
scope: "Crucible foundation / shared governance"
tags:
  - "decision-records"
  - "governance"
  - "taxonomy"
  - "standards"
relates-to:
  - "crucible decision-records.md (the normative catalog this ADR ratifies)"
  - "crucible ADR-0002 (single canonical source: the agreement lives upstream, consumers link-or-vendor)"
  - "crucible docs/decisions/README.md (per-lane index, reconciled by this ADR)"
---

# ADR-0003: Decision & Governance Record Taxonomy (the `*DR` family)

## Status

**Accepted.** Shared-governance position recorded in crucible's decision lane;
ratifies the [decision-record catalog](../repository/decision-records.md) as the
normative standard.

## Context

3leaps/crucible is the shared standards foundation: its conventions serve the
immediate org and flow downstream to adopting repositories (the
single-canonical-source pattern of ADR-0002). Decision records need a single, durable
taxonomy here so that intent survives across repos and over time.

The prior convention was only an ad-hoc sketch — three types (ADR / DDR / SDR),
no process- or principle-level records, and a security label (`SDR`) ambiguous
enough to read as Security / Schema / System / Standards. This ADR ratifies a
fuller catalog ([`docs/repository/decision-records.md`](../repository/decision-records.md))
as the standard and settles the reconciliations it implies — including the
`SDR → SecDR` rename.

## Decision

### 1. Ratify the catalog; this ADR is the genesis instrument

Adopt [`docs/repository/decision-records.md`](../repository/decision-records.md)
as the **normative standard** for decision and governance records across the
adopting repositories. This ADR is the ratifying instrument.

**Why an ADR, and the genesis exception.** Establishing a taxonomy of
record types is a _governance_ act, not a software-architecture choice — by the
ratified taxonomy itself, that is **PDR/EPR** territory, not ADR territory. But at
genesis only ADR exists as a ratified type, so it is the **only non-circular
instrument** available: a PDR cannot be the record that brings PDRs into
existence. This mirrors the root convention's own self-establishing record
(Nygard's "ADR-0001: record architecture decisions"). This ADR is therefore a
deliberate **genesis exception**. Going forward, governance-of-governance changes
use **PDR** (a revisable process choice) or **EPR** (a durable principle) — the
taxonomy classifies everything except its own birth.

### 2. Mandate exactly two things

The standard is deliberately a **thin mandate** so downstream orgs can adopt it
without inheriting layout or workflow opinions. **Two things are normative:**

**(a) The supported type set** — the minimal shared vocabulary is the five-type
`*DR` family:

| Type      | Name                          | Captures                                    |
| --------- | ----------------------------- | ------------------------------------------- |
| **ADR**   | Architecture Decision Record  | A significant architecture/technical choice |
| **DDR**   | Design / Data Decision Record | A design or data-model/schema choice        |
| **SecDR** | Security Decision Record      | A security posture/control choice           |
| **PDR**   | Process Decision Record       | A ways-of-working choice                    |
| **EPR**   | Engineering Principle Record  | A durable principle (the "constitution")    |

Reserving the letters does not force their use — a repo uses the types it needs —
but it prevents downstream reinvention and keeps the vocabulary one grep wide
across adopting repositories.

**(b) The naming convention** — `<TYPE>-<NNNN>-<kebab-slug>.md`:

- `<NNNN>` is **4-digit, zero-padded** (`ADR-0001`, not `ADR-001`) — consistent
  with the records already in this repo.
- Numbering is **per-type and repo-global-per-type**: each type carries one
  monotonic sequence across the _whole repo_, independent of where records are
  filed. (This is what lets storage homes be unmandated — see §3 — without two
  folders both minting an `ADR-0001`.)
- Numbers are monotonic and **never reused**; a withdrawn record keeps its number.

### 3. What is NOT mandated

Everything else is **recommended default, not rule**:

- **Storage location.** The standard mandates _no_ home. `docs/decisions/`,
  `docs/governance/`, `docs/adr/`, or any layout a repo prefers are all valid.
  The catalog's homes are examples. (This repo happens to file its records under
  `docs/decisions/` — that is this repo's choice, not the shared rule.)
- **Lifecycle / status model.** The recommended lifecycle is
  `Proposed → Accepted → (Superseded | Rejected | Withdrawn)` with
  `Supersedes:` / `Superseded-by:` pointers — a strict improvement over a bare
  `deprecated`. It is a **strongly-recommended default**: adopting it keeps record
  status greppable across repos, but it is outside the hard mandate.
- **Optional fields, audience/graduation, per-project confidentiality** — all
  per-repo concerns.

### 4. Reconciliations

- `SDR` **→ `SecDR`** everywhere (the bare `S` is ambiguous). Zero migration
  cost: no DDR/SecDR/PDR/EPR records exist yet, so this is a prose change only.
- Lifecycle `deprecated` **→ `superseded`** (with explicit replacement pointers);
  `rejected` and `withdrawn` retained as distinct end states.
- `docs/decisions/README.md` is reframed from "the convention" to a **per-lane
  index** that defers to the catalog as the normative source and presents this
  repo's `docs/decisions/` as one valid home.

### 5. One canonical source

To avoid the multi-master drift ADR-0002 was written to prevent, the **published
catalog** (planned: `https://crucible.3leaps.dev/repository/decision-records`) is
the **single canonical source** for the taxonomy. Downstream OSS orgs **link or
vendor** it and choose their own homes; they do not co-author divergent copies.
The agreement lives upstream.

### 6. The EPR axis exception (and its extension path)

Four types (ADR/DDR/SecDR/PDR) are **domain**-typed; EPR is the lone
**lifecycle**-typed entry (a durable _principle_ rather than a revisable
_decision_). This asymmetry is a **deliberate exception**: process principles earn
a first-class type because a team's "constitution" is referenced often enough to
warrant its own letter. Other domains that need a durable principle apply the same
**decision-vs-principle axis within that domain** (a durable architectural
_principle_ recorded as an ADR marked principle-lifecycle) **without minting new
letters or re-ratifying**. The longer-term evolution — making lifecycle an
orthogonal attribute across all domains — is noted in the catalog as future work,
not adopted here.

## Rationale

- **Non-circularity is dispositive.** Only a pre-existing type can ratify the
  family; ADR is that type. The genesis-exception framing keeps the taxonomy
  self-consistent afterward.
- **A thin mandate travels.** Mandating only the type set and naming convention
  minimizes the conformance surface, which is exactly what makes the standard
  adoptable by downstream repositories. Layout and workflow opinions would not survive contact
  with diverse downstream repos.
- **Per-type numbering matches incumbent practice** and is the correct shared
  choice — downstream repos number independently within type, with no shared
  global counter to coordinate.
- **One canonical source** is the same anti-drift discipline ADR-0002 applied to
  a security-relevant schema registry, applied here to the governance vocabulary.

## Consequences

**Positive**

- Adopting repositories share one decision-record vocabulary and one naming rule, while each
  repo keeps full freedom over where records live.
- PDR and EPR become available, giving process choices and durable principles a
  first-class home instead of being lost in chat or PR threads.
- The drift hazard of multiple divergent taxonomies is closed by naming a single
  canonical source.

**Negative / costs**

- A small reconciliation edit to `docs/decisions/README.md` and the catalog.
- The domain/lifecycle asymmetry (EPR) is a known rough edge carried deliberately;
  it must be documented so it is not mistaken for an oversight.
- Status model is recommended-not-mandated, so downstream lifecycle vocab can
  still diverge; the conformance note mitigates but does not eliminate this.

## References

- [Decision & Governance Records — the `*DR` family](../repository/decision-records.md) — the normative catalog this ADR ratifies
- [ADR-0002: Key-Material Fingerprint Contract as a Portable Schema](ADR-0002-keymaterial-fingerprint-portable-contract.md) — single-canonical-source precedent
- [Decisions index](README.md) — this repo's decision lane
- Michael Nygard, "Documenting Architecture Decisions" (2011) — the root ADR convention

## Revision History

| Date       | Status Change | Summary                                                    | Updated By |
| ---------- | ------------- | ---------------------------------------------------------- | ---------- |
| 2026-06-29 | → accepted    | Ratify the `*DR` family catalog; mandate type set + naming | cxotech    |
