---
title: "Data-Pipeline Engineering Principles"
description: "Client-neutral, durable engineering principles for data pipelines — 28 principles across 5 orthogonal axes. Domain-scoped, opt-in; EPR-class lifecycle."
author: "Claude Opus 4.8"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-06-29"
status: "accepted"
domain: "data-engineering"
lifecycle: "EPR-class (principle; replaced only deliberately)"
scope: "domain-scoped, opt-in (not universal baseline)"
stability: "stable"
version: "1.0.0"
ratified_by: "PDR-0001"
tags: ["data-engineering", "pipelines", "principles", "epr", "standards"]
related_docs:
  - "../../decisions/PDR-0001-adopt-data-pipeline-principles.md"
  - "../../repository/decision-records.md"
  - "../../repository/secure-commits.md"
---

# Data-Pipeline Engineering Principles

**Canonical URL** (hosted site planned — v0.1.x): `https://crucible.3leaps.dev/standards/data-engineering/data-pipeline-principles`

> **Scope & altitude.** This is a **domain-scoped, opt-in** standard for repositories
> that build or operate **data pipelines** — _not_ universal baseline (unlike the
> cross-cutting classification standards alongside it, which every relevant repo
> inherits). A repo adopts it **by reference**; it is not inherited automatically.
> It is **EPR-class**: a set of durable engineering _principles_, replaced only
> deliberately, never quietly drifted — the _set_ carries one lifecycle status, and
> the `GP-<axis>.<n>` ids are stable anchors, not independently-tracked records.
> Crucible is the **single canonical source**: downstream pipeline repos **link or
> vendor** this set and re-attach their own instance specifics (vendor quirks,
> thresholds, mappings) that this generic set deliberately omits. Adopted via
> [PDR-0001](../../decisions/PDR-0001-adopt-data-pipeline-principles.md).

A client-neutral distillation, developed through work on OSS and client projects. Each
principle has a stable id (`GP-<axis>.<n>`), a **statement** (the rule), and a **Why**
(the trade-off or failure it arbitrates). Statements are written tool- and
instance-neutral; read them as constraints any data pipeline should be able to satisfy
regardless of stack.

The 5 axes are orthogonal and span the principle space:

1. **Idempotency & Determinism** — byte-stable, reproducible outputs across runs and environments.
2. **Completeness & Quality Gates** — prove correctness through attestations and independent re-validation.
3. **Governance & Auditability** — record decisions and exceptions durably, with reversibility and transparency.
4. **One-Emitter & Isolation** — prevent hidden divergence by centralizing each fact and decoupling concerns.
5. **Resource & Operational Safety** — protect against resource leaks, cascading failures, and operational hazards.

---

## Axis 1 — Idempotency & Determinism

_Byte-stable, reproducible outputs across runs and environments._

**GP-1.1 — Explicit typed sinks; inference is for discovery, never for the artifact.**
Column types in a published artifact are pinned from a single authoritative declaration and cast
explicitly. Type _inference_ (auto-detection on read) is permitted only while exploring; the artifact of
record never depends on it.
**Why:** inference drifts silently as data changes (a column that was all-integer gains a decimal), which
breaks downstream type-safety and makes "the same input" produce a differently-typed output. Trades
authoring overhead for determinism.

**GP-1.2 — The partition is the atomic unit of replacement, not the file.**
Re-publishing a logical partition replaces its **entire** file set; per-file additive sync is prohibited
wherever the file set is non-deterministic (counts/sizes vary run to run).
**Why:** additive overwrite of a re-sharded partition duplicates rows (old parts linger beside new ones).
Whole-partition replace is the only idempotent cutover when part files aren't 1:1 stable.

**GP-1.3 — A hard-killed operation is always safe to re-run; re-run, don't resume.**
Stages run into a fresh working directory and are designed so a hard kill (no cleanup hook runs) leaves
no partial state a re-run won't supersede. Recovery is "run it again," not "resume from a checkpoint."
**Why:** resume-after-kill is fragile (in-flight state is ambiguous — e.g. a half-written tail can false-
positive a collision check); idempotent re-run converges deterministically. Correctness recovery, not
mere convenience.

**GP-1.4 — Deduplication is tiered and its meaning is operator-selectable per run.**
Identity is checked cheapest-first (destination-path/URI → content hash → optional byte-for-byte), and the
operator chooses what "duplicate" means for a run (skip-if-exists / re-process-if-content-differs /
re-process-if-record-shape-differs / always).
**Why:** catches retransmissions without reading every object in full, while letting a forensic run be
exhaustive. One fixed dedup rule is wrong for both the cheap idempotent case and the paranoid case.

---

## Axis 2 — Completeness & Quality Gates

_Prove correctness through attestations and independent re-validation._

**GP-2.1 — Prove uniqueness at two independent layers: materialized and declared.**
Every published row carries a materialized identity-key column tested `COUNT(*) == COUNT(DISTINCT key)`
(config-independent — blocks on every subject without needing to know the declared key), **and** the
declared identity-key columns are independently re-derived and tested.
**Why:** the two catch each other when the materialized key and the declared key diverge (over- or
under-disambiguation). A single check can't see its own blind spot.

**GP-2.2 — No silent skip: emit a verdict or fail.**
A gate that cannot run says so loudly — a keyless subject emits an explicit `not_guaranteed`, never an
invisible pass; every missing cell in a completeness check is _classified_ (confirmed-absent-upstream vs
inferred vs pipeline-gap), and a pipeline-gap blocks.
**Why:** a silent skip is indistinguishable from proven coverage to a downstream consumer who already
distrusts upstream keys — it is worse than a loud failure.

**GP-2.3 — Completeness is present/absent, not volume; volume deficits need an independent witness.**
Presence classification answers "is this cell here?" but not "is all of it here?" A present-but-volume-
short cell passes silently unless a separate witness checks magnitude (a baseline/control-relative count,
or a construction invariant like "row count equals the upstream event count").
**Why:** a partial-data failure (a truncated load that still lands _some_ rows) reads as "present" and
escapes a binary classifier. The volume witness is what makes it loud.

**GP-2.4 — Validation is defense-in-depth: independent bands re-prove each other from independent evidence.**
The pipeline validates at multiple points (post-extract over intermediate form, post-publish over the
published form, pre-release over the served layout), and later bands **re-prove** earlier claims from
_different_ evidence — not by trusting the earlier band's verdict.
**Why:** a defect that fools one band's evidence (the intermediate file) is usually caught by another's
(the published artifact). Re-proving from independent evidence is the point, not redundancy.

**GP-2.5 — Every stage honors one uniform operation contract.**
Each capability exposes the same shape: pre-flight (resource/credential check) → run into a fresh working
dir → fail-loud gates (no half-success) → verify-complete (provable from output state) → structured,
machine-readable status. Conformance to this contract is the price of admission to the shared run-surface
— which is the mechanism that hardens every stage.
**Why:** one mental model for operators, automation, and newcomers; and "you only get a verb if you
conform" forces each stage to grow pre-flight/verify/structured-status it would otherwise skip.

---

## Axis 3 — Governance & Auditability

_Record decisions and exceptions durably, with reversibility and transparency._

**GP-3.1 — Decisions are records that travel with the code.**
The architecture/data decisions that govern how the code behaves are versioned alongside it (decision
records + design docs in-repo), so a given commit reproduces a given result and the _why_ is discoverable
without tribal knowledge.
**Why:** decisions in chat/heads die with the session; in-repo records make the work auditable and
replicable by anyone with the repo.
**Shared standard:** this is the pipeline-domain application of the
[decision & governance record taxonomy](../../repository/decision-records.md)
([ADR-0003](../../decisions/ADR-0003-decision-record-taxonomy.md)) — use the `*DR` family for the records.

**GP-3.2 — Exceptions are fail-closed but waivable, with explicit, value-pinned, auto-reversing waivers.**
A reconciliation/quality gate blocks by default; an irreducible, understood anomaly is unblocked only by
an explicit waiver keyed to identity **and pinned to the observed values**. If the data changes, the pin
no longer matches and the gate re-blocks automatically.
**Why:** lets a real source-side anomaly ship without disabling the gate, while guaranteeing the waiver
can't silently mask a _new_ problem (a threshold nudge or a different break re-blocks).

**GP-3.3 — Waivers (and other exceptions) are data records in a durable registry, not code edits.**
Exceptions conform to a schema and live in a reviewable append-only registry; adding or retiring one is a
data change reviewable in isolation, not a buried conditional in code.
**Why:** auditability and reversibility — you can see every active exception, who approved it, and why, and
retire it cleanly when the source is fixed.

**GP-3.4 — Progress is a schema-backed, append-only log — a pipeline artifact, not operator notes.**
"Where is this batch?" is answered by a structured, append-only run log (one per run), emitted and read by
operators _and_ automation alike — not reconstructed from chat or stdout-grep.
**Why:** makes progress inspectable and machine-drivable (an orchestrator can branch/retry on it), and the
record travels with the pipeline rather than the person.

**GP-3.5 — Public/handoff surfaces carry no internal tooling, process, or codename vocabulary.**
Anything delivered to a client or published externally is scrubbed of internal tool names, process
references, codenames, and internal paths — keeping vendor/domain/standard vocabulary that legitimately
belongs to the subject. Enforced by a two-layer check (author + reviewer), never one regex.
**Why:** public surfaces are permanent and outside our control; an internal identifier that leaks there is
not retractable and can reveal how the work is actually done.
**Shared standard:** the same discipline as the [Secure Commit Policy](../../repository/secure-commits.md)
and this repository's public-surface rules.

---

## Axis 4 — One-Emitter & Isolation

_Prevent hidden divergence by centralizing each fact and decoupling concerns._

**GP-4.1 — One source of truth per fact; reconcile downstream, never re-derive.**
When a quantity must agree across stages, a later stage reconciles against the **attestation the earlier
stage emitted**, rather than independently re-deriving it from raw source.
**Why:** independent re-derivation diverges silently when inputs are non-trivial (e.g. multi-period
catch-up files undercount a naive re-count). One emitter, many reconcilers.

**GP-4.2 — Deduplicate once, at the source; downstream reconciles, never re-dedupes.**
Dedup happens one time at ingest; later stages reconcile against the deduplicated set (or its attestation)
and never independently collapse rows again.
**Why:** cascading, stage-local dedup produces inconsistent row sets and makes "how many real records are
there?" unanswerable. Centralizing it keeps the answer stable.

**GP-4.3 — Derived/blended datasets are additive, non-destructive, version-stamped, and restate-able.**
A dataset produced by joining canonical data with another source never mutates the canonical fact; it is a
separate, version-stamped published dataset, and an "enriched" combined view is a join — never an edited
copy. Improving the join (or reprocessing history) restates only the derivative.
**Why:** a fuzzy/probabilistic enrichment is an _interpretation_, not a fact; letting it live inside the
canonical record would force restating immutable facts every time the interpretation improves.

**GP-4.4 — A derived dataset's identity is its natural anchor-grain composite, not the match outcome.**
The identity key of a derivative is the natural grain it is anchored to (including rows where no match was
found); the canonical link and the match-model version are **value/provenance columns, never key
components**.
**Why:** keying on the match outcome means a better matcher mints new keys that coexist with the old ones
(the exact accumulation a restate-able design exists to prevent), and unmatched rows — often the whole
point — carry a null link that can't be a key.

**GP-4.5 — Bound external-source payload by tier: reference-link / forensic-allowlist / aggregate.**
A derivative declares a payload tier: a strict reference link (our keys + a single lookup reference + our
verdict), a bounded forensic tier (an enumerated allowlist of evidence fields), or aggregate-only
(counts/rates). A hard identity/PII denylist never relaxes in any tier. Payload outside the declared tier
is rejected at the gate.
**Why:** balances forensic usefulness against data minimization and re-hosting risk, and makes "what may
this dataset carry" an enforced declaration rather than drift.

**GP-4.6 — Decouple concerns structurally, not by convention.**
When two concerns must not contaminate each other (e.g. core identity vs derivative identity), separate
them at the structural level — distinct files/sidecars one side reads and the other cannot — rather than a
shared file with a "don't touch this part" marker.
**Why:** a convention marker guards only the readers that remember to check it; a structural split is
blind-by-construction and can't be bypassed by a forgotten check.

**GP-4.7 — Late arrivals: a cadence-free, period-keyed ledger that carries each record exactly once.**
Records arriving outside their window are deposited to a pending ledger keyed by their content period; a
later run incorporates them via partition-scoped replacement of only the affected periods, marking them
incorporated so they are carried forward exactly once.
**Why:** handles late/out-of-window data without silent loss or double-counting, independent of run cadence
(daily/weekly/monthly use the same protocol).

**GP-4.8 — Reconcile and partition by the record's content period, not its arrival/folder date.**
Grouping, dedup, and partition assignment key on the business/event period inside the record body, not the
date it happened to arrive or the folder it landed in.
**Why:** a record's true period is a property of the event, not of when/where it was delivered; keying on
arrival misfiles boundary-crossing and catch-up data.

**GP-4.9 — A declarative registry is the single source of the publishable set, validated at every gate.**
The set of artifacts that publish is declared once in a registry; each gate (extract-time, discover-time,
documentation-sync) checks against that **same** source, so the legs can't drift apart.
**Why:** divergent per-stage lists silently drop or orphan an artifact; one declaration validated three
ways keeps extract, publish, and docs in agreement.

**GP-4.10 — Multi-grain precedence: keep the finer grain, use the coarser as a backstop, never sum both.**
When the same event arrives at two grains (e.g. per-transaction and a daily roll-up), retain the
finer-grained record and use the coarser only as a coverage backstop where the finer is absent — never add
the two.
**Why:** summing overlapping grains double-counts; preferring the finer grain maximizes detail while the
coarser still guarantees coverage.

---

## Axis 5 — Resource & Operational Safety

_Protect against resource leaks, cascading failures, and operational hazards._

**GP-5.1 — The data root is a logical contract (a flag/env var), not a specific volume; fail fast if absent.**
Operational data resolves under a configured logical root, backed differently in different environments
(workstation, server, container). Operations validate the root is present and writable **before** any
work and fail loudly if not.
**Why:** hard-coding a volume makes code non-portable; validating late turns a missing mount into a cryptic
mid-run error instead of an instant, clear failure.

**GP-5.2 — Bulk inputs resolve under the data root; authored source stays repo-relative.**
Large/derived inputs (corpora, indexes, intermediates) resolve under the logical data root; authored,
versioned source (recipes, decision records, config) resolves relative to the repo. The boundary is
explicit.
**Why:** conflating the two either bloats the repo with bulk data or scatters inputs by working directory;
the split keeps both portable and unambiguous.

**GP-5.3 — Scratch/temp resolves under the same logical root, never the system temp or boot disk.**
Ephemeral spill (engine temp dirs, intermediates) is configured under the operational data root, not left
to default into system temp or the OS volume.
**Why:** a large operation's spill silently filling the boot disk is an avoidable, hard-to-diagnose
outage; co-locating scratch with the data root governs it.

**GP-5.4 — Every external-process session inherits resource governance from one shared preamble.**
Tools that spawn heavy subprocesses (query engines, capture/transfer tools) inherit temp location, memory
ceiling, output-buffer limits, and concurrency headroom from a single shared, parameterized preamble —
not ad-hoc per call site.
**Why:** per-site configuration drifts and leaves gaps where a runaway process exhausts memory/disk; one
preamble adopted everywhere closes them uniformly.

---

## Relationship to shared standards (cite up, don't restate)

Several principles are the data-pipeline-domain expression of shared standards that already exist in
crucible. Where they overlap, **this set defers to the shared standard** rather than forking it — a second
copy of a rule drifts:

- **GP-3.1** (decisions travel with the code) → the
  [decision & governance record taxonomy](../../repository/decision-records.md) /
  [ADR-0003](../../decisions/ADR-0003-decision-record-taxonomy.md). Use the `*DR` family for the records.
- **GP-3.5** (no internal vocabulary on public/handoff surfaces) → the
  [Secure Commit Policy](../../repository/secure-commits.md) and this repository's public-surface rules.
- **GP-5.1–5.4** (data root as a logical contract; scratch under the root; one shared resource-governance
  preamble) are near-universal engineering principles applied here to pipelines — see _Future factoring_.

## Future factoring

This set is intentionally kept **whole** — it moves as one corpus, and the orthogonal axes cross-reference
each other. But its altitude is not uniform: a subset — notably **GP-3.1, GP-3.5, GP-3.3/3.4, and
GP-5.1–5.4** — states principles that are **near-universal**, not data-pipeline-specific. They are retained
here for completeness of the pipeline picture, but flagged as candidates to **graduate to the shared
baseline** in a future revision (after which the pipeline set would cite up to them rather than carry
them). Recorded now so the universal principles don't ossify as "data-engineering only." Any such
promotion is a deliberate, recorded change per the EPR-class lifecycle.

## Origin

These principles were developed through work on OSS and client projects — each one earned by a real
failure it now prevents. They are recorded here **evergreen**: stated as the durable rule, free of the
specific systems, datasets, or incidents that taught it, so a team that never worked those problems can
adopt the principle without needing the backstory. By the same discipline, the instance-specific lessons
that _informed_ them — particular vendor or data-format quirks, client-specific mappings and thresholds,
and transitory tooling conventions — are deliberately **not** carried here. Those are situational
know-how, not reusable IP; the principle is what generalizes.
