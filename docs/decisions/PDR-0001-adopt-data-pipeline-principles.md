---
id: "PDR-0001"
title: "Adopt the Data-Pipeline Engineering Principles as a domain-scoped, EPR-class standard set"
status: "accepted"
date: "2026-06-29"
last_updated: "2026-06-29"
deciders:
  - "@3leapsdave"
  - "cxotech"
scope: "Crucible foundation / shared governance — domain standard-set ingestion"
tags:
  - "process"
  - "data-engineering"
  - "principles"
  - "governance"
relates-to:
  - "crucible standards/data-engineering/data-pipeline-principles.md (the set this PDR ratifies)"
  - "crucible ADR-0003 (the *DR taxonomy; this is the inaugural PDR and first domain standard-set)"
  - "crucible ADR-0002 (single canonical source; consumers link-or-vendor)"
---

# PDR-0001: Adopt the Data-Pipeline Engineering Principles

## Status

**Accepted.** Inaugural Process Decision Record. Ratifies the
[Data-Pipeline Engineering Principles](../standards/data-engineering/data-pipeline-principles.md)
as a shared standard and establishes the pattern for ingesting future domain
standard-sets.

## Context

Crucible's standards to date are all **cross-cutting** — versioning, frontmatter,
commit style, the `*DR` taxonomy, the key-material contract — inherited by every
relevant repo. A client-neutral set of durable **data-pipeline** engineering
principles (28 principles across 5 orthogonal axes, each a rule plus the trade-off it
arbitrates) is ready to graduate in as reusable IP. It is the **first domain-specific
standard set** crucible would host, which raises a governance question the existing
standards never had to answer: how does a shared foundation admit a domain-scoped set
without (a) treating it as universal baseline, (b) fragmenting it into individual
records, or (c) reaching for the wrong record type to ratify it.

## Decision

**Use a PDR, not an ADR.** Adopting a standard set and fixing its lifecycle, altitude,
and inheritance is a **process/governance** choice — by the taxonomy ratified in
ADR-0003, that is PDR territory. ADR-0003 was an ADR _only_ because, at genesis, no
other ratified type existed; PDR now exists, so this — the first real exercise of the
taxonomy — uses the correct type. This is the **inaugural PDR**.

1. **One standard-set doc, not individual records.** Adopt the set as a single
   normative document at
   [`docs/standards/data-engineering/data-pipeline-principles.md`](../standards/data-engineering/data-pipeline-principles.md).
   The `GP-<axis>.<n>` ids are stable in-doc anchors; the corpus moves as one body and
   is **not** split into per-principle files.

2. **EPR-class lifecycle.** The set is a body of durable engineering _principles_ —
   replaced only deliberately, never quietly drifted. The **set** carries one lifecycle
   status (`accepted`); individual `GP-` ids do not carry independent status. (This is
   the "lifecycle as an attribute applicable in any domain" path noted in ADR-0003,
   here `domain = data-engineering`, `lifecycle = principle`.)

3. **Domain-scoped and opt-in (pull, not push).** Unlike the universal classification
   frameworks in `docs/standards/`, this set is **not** inherited automatically. It
   binds only repositories that build or operate data pipelines, and only by explicit
   adoption (cite it in the adopting repo's `AGENTS.md` / standards list). It is filed
   under a `data-engineering/` domain namespace to keep its altitude distinct from
   universal baseline.

4. **Single canonical source; downstream link-or-vendor.** Crucible is the one
   canonical home (the same anti-drift discipline as ADR-0002). Downstream pipeline
   repos link or vendor the set and re-attach the instance specifics (vendor quirks,
   thresholds, mappings) that the generic set deliberately omits. A `version` +
   `stability` tag on the doc gives downstream a pin target.

5. **Cite up, don't restate.** Where a principle restates an existing shared standard
   — **GP-3.1** ≈ the decision-record taxonomy (ADR-0003); **GP-3.5** ≈ the Secure
   Commit Policy — the set **defers** to the shared standard rather than forking it.
   The mixed-altitude subset (GP-3.1, GP-3.5, GP-3.3/3.4, GP-5.1–5.4 read as
   near-universal) is kept whole for now and flagged for future factoring up to the
   baseline, recorded in the doc.

### The reusable ingestion pattern (for future domain standard-sets)

This PDR establishes the paved road so the next domain set (web, ML, …) follows it
rather than improvising:

> **Domain namespace** under `docs/standards/<domain>/` · **altitude tag**
> (domain-scoped, opt-in — not universal baseline) · **EPR-class lifecycle** where the
> content is durable principles · **single canonical source** with a version/stability
> pin · **opt-in inheritance** (named in the adopting repo, not auto-applied) ·
> **cite-up** of any overlap with cross-cutting standards.

## Consequences

**Positive**

- The principles become reusable shared IP without fragmenting into records or
  polluting the universal baseline.
- Future domain standard-sets have a defined ingestion pattern; Layer 0 does not become
  an unscoped junk drawer of every domain's standards.
- Downstream pipeline projects get one canonical, pinnable source to consume and extend.

**Negative / costs**

- The set is intentionally mixed-altitude; the future-factoring of its near-universal
  principles is deferred work, recorded but not yet done.
- Opt-in inheritance needs a discoverability signal (the standards index + adopting
  repos naming it); a repo that should adopt it but doesn't get no automatic nudge.

## References

- [Data-Pipeline Engineering Principles](../standards/data-engineering/data-pipeline-principles.md) — the ratified set
- [Decision & Governance Record Taxonomy (ADR-0003)](ADR-0003-decision-record-taxonomy.md) — defines PDR; this is the first one
- [ADR-0002: Key-Material Fingerprint Contract as a Portable Schema](ADR-0002-keymaterial-fingerprint-portable-contract.md) — single-canonical-source precedent

## Revision History

| Date       | Status Change | Summary                                                            | Updated By |
| ---------- | ------------- | ------------------------------------------------------------------ | ---------- |
| 2026-06-29 | → accepted    | Adopt the data-pipeline principles; establish domain-set ingestion | cxotech    |
