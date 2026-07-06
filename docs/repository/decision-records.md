---
title: "Decision & Governance Records — the *DR family"
description: "Catalog of 3leaps decision-record and governance-record document types (ADR, DDR, SecDR, EPR, PDR): when to use each, naming, status, and lifecycle."
author: "Claude Opus 4.8"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-06-28"
status: "approved"
tags: ["decision-records", "governance", "adr", "documentation"]
related_docs: ["commit-style.md", "secure-commits.md", "frontmatter.md"]
---

# Decision & Governance Records — the `*DR` family

**Canonical URL** (hosted site planned — v0.1.x): `https://crucible.3leaps.dev/repository/decision-records`

**Status:** Normative standard, ratified by
[ADR-0003](../decisions/ADR-0003-decision-record-taxonomy.md). This published
catalog is the **single canonical source** for the taxonomy across adopting repositories;
downstream repos link or vendor it rather than maintaining divergent copies.

> **Normative core — two things are mandated:** the **supported type set**
> (`{ADR, DDR, SecDR, PDR, EPR}`) and the **naming convention**
> (`<TYPE>-<NNNN>-<kebab-slug>.md`). Everything else here — storage homes, the
> status/lifecycle model, optional fields, per-project audience rules — is a
> **recommended default, not a rule.** This thin mandate is what lets the standard
> travel downstream: a consuming repo adopts the vocabulary and naming, then
> files records wherever its own documentation layout puts them.

A small, consistent set of record types for capturing **decisions** and **governing rules** so a
project's intent survives the people and agents who made it. All share one shape (short, numbered,
status-tracked, append-only history) and differ only in **what** they capture. Use the smallest one
that fits; don't invent a new letter when an existing type works.

## Why records at all

A decision that lives only in someone's head, a chat thread, or a PR comment is lost the moment
context resets. A record is the durable, greppable answer to _"why is it this way, and can I change
it?"_ — written once, at decision time, by whoever made the call.

## The family at a glance

| Type      | Name                          | Captures                                                                             | Lifecycle                           | Example home (non-binding)       |
| --------- | ----------------------------- | ------------------------------------------------------------------------------------ | ----------------------------------- | -------------------------------- |
| **ADR**   | Architecture Decision Record  | A significant **architecture/technical** choice and its trade-offs                   | Dated; supersede-able               | `docs/decisions/` or `docs/adr/` |
| **DDR**   | Design / Data Decision Record | A **design** or **data-model/schema** choice (interface, contract, partitioning)     | Dated; supersede-able               | `docs/decisions/`                |
| **SecDR** | Security Decision Record      | A **security** posture/control choice (threat accepted, mitigation chosen)           | Dated; supersede-able; review-gated | `docs/security/`                 |
| **PDR**   | Process Decision Record       | A **ways-of-working** choice (commit format, CI gates, review flow, release cadence) | Dated; supersede-able               | `docs/governance/`               |
| **EPR**   | Engineering Principle Record  | A **durable principle** — the "constitution" a team honors; _arbitrates trade-offs_  | Durable; replaced only deliberately | `docs/governance/`               |

> ADR is the root convention (Michael Nygard, 2011). DDR / SecDR are domain-scoped siblings. **PDR
> and EPR** extend the family along a different axis — **process** rather than architecture — and
> separate the two process lifecycles (a _durable principle_ vs a _revisable decision_).

## The two axes that pick the type

1. **Domain** — _what is this about?_ Architecture → ADR. Design/data/schema → DDR. Security →
   SecDR. How-we-work → PDR/EPR.
2. **Lifecycle** — _will this change?_ A **decision** is a choice a later choice can revise (dated,
   `Superseded-by:`). A **principle** is a durable rule you expect to hold unchanged — it's
   replaced only by a deliberate successor, never quietly drifted.

The decision-vs-principle split is why **PDR and EPR are separate types**, not one:

- **"Is this a choice we made that a later choice could revise?"** → **PDR**
  (e.g. _"commits use Jira-first `TICKET type(scope): summary`"_).
- **"Would a reasonable engineer expect this to still hold in a year, unchanged?"** → **EPR**
  (e.g. _"runtime env-var names are app-scoped and reveal nothing sensitive"_).

**Why EPR is the lone lifecycle-typed entry — and how to extend it.** Four types
(ADR/DDR/SecDR/PDR) are _domain_-typed; EPR is the only _lifecycle_-typed entry (a
durable principle rather than a revisable decision). This asymmetry is a
**deliberate exception**: process principles earn their own letter because a
team's "constitution" is referenced often enough to warrant it. Other domains that
need a durable principle apply the **same decision-vs-principle axis within that
domain** — e.g. a durable architectural principle recorded as an ADR marked
principle-lifecycle — **without minting new letters** (no `APR`, `SecPR`, …) and
without re-ratifying the taxonomy. A future revision may make lifecycle an
orthogonal _attribute_ across all domains, leaving four domain types; that
evolution is noted, not yet adopted (see
[ADR-0003](../decisions/ADR-0003-decision-record-taxonomy.md)).

## Conventions (all types)

> The first two conventions — **type set** and **naming** — are the **mandated
> core**. The rest are recommended defaults.

- **Type set (mandated)**: the supported vocabulary is the five-type set
  `{ADR, DDR, SecDR, PDR, EPR}`. Use the types you need; don't mint a new letter
  for something an existing type covers.
- **Naming (mandated)**: `<TYPE>-<NNNN>-kebab-title.md`, where `<NNNN>` is
  **4-digit, zero-padded** (`ADR-0001`, not `ADR-001`). Numbering is **per type
  and repo-global per type** — each type carries one monotonic sequence across the
  _whole repo_, independent of where records are filed, so unmandated storage
  homes never collide on a number. Numbers are never reused; a withdrawn record
  keeps its number.
  - Example: `ADR-0014-event-sourced-rollup.md`.
- **Status (recommended default)**: records move from `Proposed` to `Accepted`,
  then optionally to a terminal state: `Superseded`, `Rejected`, or `Withdrawn`.
  Supersedable records carry `Superseded-by: <TYPE>-<NNNN>`; the superseding
  record carries `Supersedes:`. `Rejected` = considered and declined;
  `Withdrawn` = pulled by its author before acceptance.
- **Append-only history**: don't rewrite an accepted record's decision — supersede it. Keep
  disagreements visible (append, don't overwrite).
- **One decision per record**: if you're using "and" a lot, it's two records.

### Minimal front-matter

```
Record:  ADR-0014
Title:   Event-sourced daily rollup
Status:  Accepted
Date:    2026-06-28
Owner:   @handle
Supersedes / Superseded-by:   (optional)
```

(Repos that adopt Crucible's [frontmatter standard](frontmatter.md) may use its YAML form instead;
either is fine as long as `Record`, `Title`, `Status`, `Date` are present.)

### Body template

```
## Context
<the situation and the forces in tension>

## Decision   — or —   ## Principle
<the normative statement, stated plainly>

## Consequences
<what this makes easier / harder; how it is checked or enforced>
```

## Picking the right type — quick examples

| Situation                                                               | Type  |
| ----------------------------------------------------------------------- | ----- |
| "We'll use Postgres LISTEN/NOTIFY instead of a broker."                 | ADR   |
| "The export manifest is `manifest.v1`; record IDs are strings."         | DDR   |
| "We accept read-only credential exposure in CI logs; secrets stay out." | SecDR |
| "PRs require one approval and a green `make precommit`."                | PDR   |
| "Tools never write outside their declared data root."                   | EPR   |

## Scope & confidentiality (per project)

A record's **audience** and whether it can live in a given repo is a project concern, not a
property of the type. Some governance records are fine to publish; others must stay internal
(e.g. a record describing _how a team works_ may be inappropriate for a client-visible repo).
Projects that need this should add a `Graduation` / `Audience` field to their records and decide
per-record where each one lives. The **type** (ADR/DDR/SecDR/PDR/EPR) is independent of where it's
allowed to live.

### SecDR carries the most exposure risk

A `SecDR` records a security choice — an _accepted_ threat, a chosen mitigation, the reasoning
behind a control — which is exactly the material that becomes an attacker's roadmap if published
carelessly. Treat SecDR as **default-internal**: publish one only after a security review clears
it, and apply this repo's [Secure Commit Policy](secure-commits.md) discipline to the record
itself.

- **Describe the control functionally, not the vulnerability.** Record the posture ("inputs are
  length-bounded before parsing"), not the exploit ("closes the overflow an attacker used to…").
- **Keep exploit detail out of the public record.** Full threat analysis, reproduction steps, and
  embargoed specifics belong in an internal advisory; the public SecDR carries a **pointer** to it
  (the secure-commits "pointer method"), not the payload.
- **Designate the repo security-sensitive** in its `AGENTS.md` when it files SecDRs, so reviewers
  know the heightened bar applies.

The example above — _"we accept read-only credential exposure in CI logs; secrets stay out"_ — is
the model: it records the posture and its boundary in functional language, with no exploit path.
When in doubt, keep the SecDR internal and publish only a functional summary.

## Adopting in a repo

1. Pick the homes you need — the standard mandates **no** storage location, so any
   layout works. Common choices: `docs/decisions/` for ADR/DDR, `docs/governance/`
   for PDR/EPR, `docs/security/` for SecDR. Add a short `README.md` index per home.
2. Start one record. Don't backfill history — record decisions from now forward.
3. Reference records by id from docs and implementation notes (`per ADR-0014`)
   where the surface allows rationale. Public commit and PR metadata must still
   follow the repo's public-surface policy.
