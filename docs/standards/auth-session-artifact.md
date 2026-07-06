---
title: "Auth Session Artifact"
description: "Versioned contract for non-secret, inspectable auth session metadata"
category: "standards"
status: "draft"
version: "0.1.0"
lastUpdated: "2026-06-17"
maintainer: "3leaps-core"
reviewers: ["consuming-teams", "3leaps"]
approvers: ["3leapsdave"]
tags: ["auth", "schema", "credentials", "metadata", "contract", "versioning"]
content_license: "CC0"
relatedDocs:
  - "schemas/auth/v0/session-artifact.schema.json"
  - "schemas/auth/v0/session-artifact.example.json"
  - "docs/decisions/ADR-0001-schema-config-versioning.md"
---

# Auth Session Artifact

> **Status: draft (v0).** Co-authored by the consuming teams and held in
> Crucible as a cross-cutting contract. The field shape and invariants below are
> settled; the schema rides Crucible's in-flight release and both consuming teams
> review before it lands.

## Purpose

A single versioned schema describing **non-secret, inspectable metadata about an
acquired auth session**. It is the decoupling contract between:

- **Acquirers** — tools that obtain credentials and emit a conforming artifact
  (e.g. in Go).
- **Inspectors** — tools that validate and parse the artifact (e.g. in Rust).

No shell-out, no FFI: both sides pin the same schema (and a shared synthetic
fixture) and communicate through a value-stripped projection of the session.

- **Schema:** [`schemas/auth/v0/session-artifact.schema.json`](../../schemas/auth/v0/session-artifact.schema.json)
- **URI:** `https://schemas.3leaps.dev/auth/v0/session-artifact.schema.json`
- **Draft:** JSON Schema **2020-12**
- **Fixture:** [`schemas/auth/v0/session-artifact.example.json`](../../schemas/auth/v0/session-artifact.example.json)

## Invariants

These are the point of the design and are enforced **structurally**, not by
convention.

1. **No value/secret fields, ever.** `additionalProperties: false` on the root and
   the token object. A stray `value` / `SecretAccessKey` / `SessionToken` / raw-JWT
   field makes the artifact **non-conforming** — consumers reject it loudly and
   never normalize it. **Permanent across all schema versions; never relax it.**
2. **Metadata only; no identifiers.** Expirations plus structural/provenance
   metadata. A free-text `label` was deliberately **dropped**: free text can embed
   client identifiers and cannot be policed by `additionalProperties: false`.
   Display names resolve **consumer-side** from `kind` + `source`, or are read live
   at inspect time under the consumer's own redaction.
3. **JWT = decoded payload claims only.** Non-PII subset (`iss`, `aud`, `exp`,
   `iat`, `nbf`). **No signature, no verification key**; `sub`/`email` and other PII
   are redacted or omitted by default.
4. **`unmeasured` is first-class.** Present in both `kind` and `expiry_basis` for
   off-disk, browser-held upstream-IdP sessions. `unmeasured` is **not** "healthy"
   and is **excluded from the weakest-link**; the top-level `expires_at` is the
   weakest **observable** expiry.

## Field shape

### Top level

| Field            | Required | Type                 | Notes                                                                 |
| ---------------- | -------- | -------------------- | --------------------------------------------------------------------- |
| `schema_version` | yes      | string `MAJOR.MINOR` | Contract version (e.g. `0.1`).                                        |
| `emitted_at`     | no       | date-time            | When the emitter produced the artifact.                               |
| `emitter`        | no       | object               | `{ name, version }` — provenance of the emitting tool. Not a secret.  |
| `expires_at`     | yes      | date-time \| null    | Weakest **observable** expiry; `null` if none. Excludes `unmeasured`. |
| `tokens`         | yes      | array of token       | Per-layer value-stripped metadata.                                    |

`expires_at` is **required and nullable**: it is present in every conforming
artifact and carries `null` when no observable layer has a known expiry. Requiring
it (rather than allowing omission) removes the omitted-vs-`null` ambiguity so the
weakest-observable expiry is always explicitly reported.

### Token

| Field          | Required | Type              | Notes                                                                                                                 |
| -------------- | -------- | ----------------- | --------------------------------------------------------------------------------------------------------------------- |
| `kind`         | yes      | enum              | `sso-access` \| `client-reg` \| `role-cred` \| `jwt` \| `bearer` \| `unmeasured`                                      |
| `source`       | no       | enum              | Provenance category, not a secret/identifier: `aws-sso-cache` \| `aws-sts-cache` \| `session-file` \| `upstream-idp`. |
| `expires_at`   | no       | date-time \| null | Observable expiry for this layer.                                                                                     |
| `expiry_basis` | yes      | enum              | `metadata` \| `jwt-exp` \| `unmeasured`                                                                               |
| `claims`       | no       | object            | Decoded JWT payload, non-PII subset only.                                                                             |

`additionalProperties: false` applies on the root, `emitter`, `token`, and
`claims`. `source` is a **closed enum**, not free text — the same identifier
hardening as dropping `label`; new provenance categories extend via a minor bump.

**`unmeasured` coherence (enforced structurally).** An `unmeasured` layer is
unmeasured in **both** `kind` and `expiry_basis` and carries no observable expiry:
`kind: unmeasured` ⇔ `expiry_basis: unmeasured`, and either implies
`expires_at: null`. Schema conditionals reject incoherent combinations (e.g.
`kind: unmeasured` with `expiry_basis: metadata` or a timestamp).

## Compatibility

Versioning follows [ADR-0001](../decisions/ADR-0001-schema-config-versioning.md)
(v0 + SemVer), applied to `schema_version`:

- **Minor** (`0.1` → `0.2`): additive/optional fields only. `additionalProperties`
  stays `false`; new optional fields are permitted.
- **Major** (`0.x` → `1.0`): required-field add/rename/remove, or any semantic
  change to existing fields.
- The **no-value-fields invariant is version-independent** and is never relaxed in
  any minor or major release.

The schema lives under the `auth/v0/` path namespace; `v0` may change without notice
regardless of the repository's lifecycle phase. Pin to a specific commit (and SHA256)
for stability.

## Governance / validation split

- **Crucible owns the contract.** Source of truth for the schema, `schema_version`,
  and authoritative metaschema validation at publish — `goneat schema
validate-schema --schema-id json-schema-2020-12` runs in `make lint-schemas`, and
  the synthetic fixture is round-trip-validated against the schema in
  `make lint-config`.
- **Consumers validate, they do not own the file.** Each consuming repo vendors a
  **SHA256-pinned copy** (not a live git ref — a live ref breaks offline and
  standalone-binary determinism), runs goneat meta-validation (2020-12) at build
  (failing on malformed schema or SHA drift), and validates every artifact at
  runtime with loud rejection on non-conformance.

## OSS-safety

The schema, fixture, examples, and this document are **sterile**: synthetic
fixtures only, no client/proprietary identifiers, no deny-references. The
`session-artifact.example.json` fixture is a 4-layer AWS cascade (including an
`unmeasured` upstream-IdP layer) using `example-*`-class placeholders with zero
real account IDs, start URLs, or client names.

## Consuming repositories

The contract is consumed by an **acquirer** (emits a conforming artifact) and an
**inspector** (validates and parses it), implemented as separate 3leaps tools.
Future acquirers and inspectors adopt the same contract.
