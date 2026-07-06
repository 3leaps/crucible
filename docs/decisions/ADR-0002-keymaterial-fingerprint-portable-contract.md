---
id: "ADR-0002"
title: "Key-Material Fingerprint Contract as a Portable Schema"
status: "proposed"
date: "2026-06-09"
last_updated: "2026-06-17"
scope: "Crucible foundation / key-material interchange contracts"
tags:
  - "schemas"
  - "key-material"
  - "fingerprint"
  - "interchange-contract"
relates-to:
  - "crucible ADR-0001 (schema/config versioning — the promotion gate)"
---

# ADR-0002: Key-Material Fingerprint Contract as a Portable Schema

## Status

**Proposed.** Draft architectural position recorded in crucible's decision lane;
not yet accepted.

## Context

A key-material scanning tool emits a schema-backed **fingerprint record** — one
record per detected, in-scope key artifact — carrying public fingerprints and
metadata only (never secret or identifying material). The record is a _product
surface_: it is committed to repositories, diffed in CI, and consumed downstream.
Its field-level contract currently lives entirely inside the producing tool's own
repository, versioned at `v0`.

The record already has a **separate consumer in another repository** that projects
committed trust anchors over these records. That consumer currently **hard-codes
its own copy of the producer's `fingerprint_scheme` enum** — a closed,
security-relevant set of scheme identifiers (e.g. `minisign-public-blob-sha256-v1`,
`ssh-rfc4253-public-blob-sha256-v1`, plus an intentionally-excluded weak
`*-key-id-*` form). Two independently-maintained copies of the same
security-relevant enum are a guaranteed drift hazard.

crucible already serves as the shared foundation for schemas, standards, and
configuration that flow downstream to adopting repositories (ADR-0001), with
established schema domains (`foundation`, `agentic`, `classifiers`, `ailink`), a
published `$id` convention
(`https://schemas.3leaps.dev/{domain}/v{ver}/{name}.schema.json`), and a defined
v0→v1.0.0 promotion process (ADR-0001). The question is whether the fingerprint
contract should graduate into that foundation, and if so, what moves and when.

## Decision

### 1. Promote the _contract_, not the _tooling_

Establish crucible as the canonical home for the **key-material fingerprint
contract** under a new schema domain: **`keymaterial`**. Draw the line between the
cross-cutting _interchange contract_ (graduates up to crucible) and _tool
invocation / engine behavior_ (stays with the producing tool).

| Artifact                                                                                | Home                                | Rationale                                                                                            |
| --------------------------------------------------------------------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `fingerprint-record` schema                                                             | **crucible** `schemas/keymaterial/` | Interchange contract; outlives any single tool that emits it; has multiple consumers.                |
| `fingerprint_scheme` **registry** (enum + scheme semantics)                             | **crucible** (highest priority)     | Single source of truth `$ref`'d by both producer and consumer. Eliminates the duplicated-enum drift. |
| Normative contract core (fields, closed enums, safe-output invariants, versioning gate) | **crucible**, graduated             | The portable spec travels with the schema.                                                           |
| Producer implementation notes (detector behavior, which commands emit the record)       | **producing tool**                  | Tool-specific realization, not contract.                                                             |
| Tool-invocation config schemas (include/exclude, path mode)                             | **producing tool**                  | Configure one tool's invocation; no external consumer.                                               |
| Engine behavior policy (filesystem walk / symlink policy)                               | **producing tool**                  | Inherits the shared baseline; the reusable floor is upstream, the tool's extension is local.         |

**Principle: contracts and registries go up; tool config and engine behavior stay
down.** The producing tool remains the reference _producer_; crucible owns the
_agreement_.

### 2. Registry-first, schema-at-the-gate sequencing

Do **not** move the full schema today. The record is deliberately `v0`, and
crucible ADR-0001 gates `v1.0.0` promotion on a proven downstream consumer.
Sequence accordingly:

**Phase 1 — now (cheap, high-value):** Publish the scheme registry in crucible:

```
schemas/keymaterial/v0/fingerprint-scheme.schema.json   # the closed, versioned enum (+ $defs)
docs/decisions/ (this ADR) + a scheme-semantics companion
```

Both the producer's record schema and the external consumer `$ref` this single
enum instead of hard-coding it. This kills the drift hazard immediately while the
record schema itself stays `v0` in the producing tool.

**Phase 2 — at the v1.0.0 gate (when a consumer proves the contract end-to-end):**
Graduate the full record schema + normative core into
`schemas/keymaterial/v1.0.0/fingerprint-record.schema.json`, following crucible
ADR-0001's promotion process (review → changelog → copy to `v1.0.0/` → announce).

### 3. `$id` alignment

Adopt crucible's house convention (version in the **path**, not the filename):

```
https://schemas.3leaps.dev/keymaterial/v0/fingerprint-scheme.schema.json
https://schemas.3leaps.dev/keymaterial/v1.0.0/fingerprint-record.schema.json
```

This corrects the producer's current version-in-filename form as part of the
graduation.

## Rationale

- **The drift hazard is concrete, not hypothetical.** A security-relevant closed
  enum is already duplicated across two repositories. The registry is the minimal,
  highest-value move.
- **It matches how shared standards already work.** crucible publishes reusable
  contracts that adopting repositories can link or vendor. Adding a
  `keymaterial` domain alongside `foundation`/`agentic`/`classifiers` is
  structurally consistent.
- **Promote-the-contract-not-the-tooling keeps churn down.** The producing tool
  keeps iterating its engine and tool config freely at `v0`; only the agreed wire
  format is frozen and shared.
- **Sequencing respects the existing gate.** crucible ADR-0001 already requires a
  contract to be proven in at least one downstream consumer before `v1.0.0`. We do
  not pre-promote.

## Consequences

**Positive**

- One canonical `fingerprint_scheme` registry; producer and consumer cannot drift.
- The fingerprint record becomes a first-class portable contract with a clear
  promotion path, discoverable alongside other crucible schemas.
- Tool-local concerns stay tool-local — no premature freezing.

**Negative / costs**

- A downstream consumer gains a `$ref` dependency on crucible (coordination plus a
  resolution path that must exist).
- A one-time `$id` migration for the record schema at the `v1.0.0` gate.
- Two homes during the transition (registry in crucible, record still in the
  producing tool) — must be clearly documented so consumers know what is canonical
  when.

## Open questions

1. **Domain and registry shape** — the domain name (`keymaterial`) and whether the
   scheme registry is a standalone schema or a `$defs` block, to be confirmed under
   schema-governance review.
2. **Cross-repo `$ref` resolution** — the `schemas.3leaps.dev` domain is not yet
   deployed (schemas are currently served from version control). Confirm how a
   cross-repo `$ref` resolves (published URL, committed-vendored copy, or
   build-time fetch) before any consumer depends on it. This is the practical
   prerequisite for Phase 1.
3. **Scheme coverage** — fold any additional fingerprint schemes surfaced during
   real-world validation into the registry from day one rather than amending
   post-publish.
