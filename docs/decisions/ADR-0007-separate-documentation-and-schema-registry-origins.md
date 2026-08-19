---
id: "ADR-0007"
title: "Separate Crucible documentation and schema registry origins"
status: "proposed"
date: "2026-08-19"
last_updated: "2026-08-19"
deciders:
  - "@3leapsdave"
  - "entarch"
scope: "Crucible publication architecture"
tags:
  - "architecture"
  - "publication"
  - "schemas"
  - "documentation"
  - "web"
relates-to:
  - "crucible ADR-0001 (schema and configuration version paths)"
  - "crucible EPR-0004 (proposed; publication surfaces preserve domains of concern)"
  - "crucible PDR-0004 (the signed tag authorizes publication)"
  - "crucible PDR-0006 (repository shipping charter)"
---

# ADR-0007: Separate Crucible Documentation and Schema Registry Origins

## Status

**Proposed.** Records the publication architecture before either public surface
is implemented. It graduates to accepted when the two static artifacts can be
built from one pinned Crucible source and independently validated against the
contracts below.

## Context

Crucible has two planned public uses:

1. a browsable static website presenting standards, guides, role catalogs, and
   rendered schema documentation;
2. a schema registry serving canonical raw schemas and related machine-readable
   contract artifacts.

The repository already publishes intended canonical URLs in both namespaces:

```text
https://crucible.3leaps.dev/standards/...
https://crucible.3leaps.dev/catalog/roles

https://schemas.3leaps.dev/<domain>/v0/<name>.schema.json
https://schemas.3leaps.dev/<domain>/vX.Y.Z/<name>.schema.json
```

No deployed site currently makes those promises resolvable. This is the point at
which a convenient implementation choice could accidentally redefine the
contract: a single static application could serve HTML and raw schemas under one
origin, or the human site could become a runtime proxy for repository content.

That coupling would violate
[EPR-0004](EPR-0004-publication-surfaces-preserve-domains-of-concern.md).
Crucible's HTML site and raw registry differ in primary consumer, media
semantics, cache policy, failure behavior, release artifact, and publication
authority. They share source material, not a publication contract.

The schema origin is also an organization-wide namespace. Crucible curates and
publishes the registry, but repository ownership is not the conceptual identity
of every schema. Encoding the current source repository into every public path
would bind durable contract identities to an implementation detail and would
replace already documented domain-first URLs.

## Decision

### 1. Publish two independent static surfaces

| Origin                        | Primary contract                                                |
| ----------------------------- | --------------------------------------------------------------- |
| `https://crucible.3leaps.dev` | Human documentation, catalogs, navigation, and rendered context |
| `https://schemas.3leaps.dev`  | Raw schemas, contract manifests, and machine discovery data     |

They may use the same infrastructure provider, but they are separate deployment
artifacts with separate validation, cache, error, and publication policies.

### 2. The human site presents Crucible

The human origin includes:

- standards, repository guidance, and adoption guides;
- the active role catalog;
- a browsable schema catalog and rendered schema pages;
- release and lifecycle context;
- links to canonical raw artifacts.

Suggested canonical catalog paths are:

```text
https://crucible.3leaps.dev/catalog/roles
https://crucible.3leaps.dev/catalog/schemas
https://crucible.3leaps.dev/catalog/schemas/<domain>/<name>
```

The site is generated at build time from a pinned Crucible release or generated
catalog artifact. It does not fetch a moving branch at request time and is not
authoritative for raw schema bytes.

The site implementation lives outside the standards repository so presentation
dependencies, visual design, and deployment cadence do not become part of
Crucible's contract or dependency surface.

### 3. The schema registry serves exact machine artifacts

The machine origin serves:

- canonical JSON Schemas;
- explicitly registered contract manifests and associated machine data;
- a generated machine-readable catalog with ownership, lifecycle, source
  revision, retrieval URL, logical identifier, media type, and checksum.

Canonical schema URLs remain domain-first:

```text
https://schemas.3leaps.dev/agentic/v0/role-prompt.schema.json
https://schemas.3leaps.dev/foundation/v0/types.schema.json
```

No `/crucible/` prefix is added. Crucible is the registry curator and publisher;
the public path identifies the contract domain. Ownership and source provenance
belong in the registry manifest.

The plural hostname is canonical. A singular convenience hostname may redirect
permanently to it, but does not acquire independent identifiers.

### 4. Retrieval address and logical identity are separate fields

An HTTPS retrieval URL does not rewrite a resource's declared logical identity.
A JSON Schema whose `$id` is its canonical HTTPS URL uses the same value in both
fields. A portable contract with a hostless `contract:` identifier may be
retrieved from the HTTPS registry while preserving that logical identity.

The publication manifest records both values and validates their relationship.
It does not assume every registered artifact uses its retrieval address as its
identity.

### 5. One publication manifest generates both views

Crucible owns a central publication manifest that declares:

- public path and media type;
- logical identifier and retrieval URL;
- owning project and immutable source revision;
- source path and checksum;
- lifecycle and stability;
- human documentation URL.

The registry build and human catalog build derive from this manifest. A build
rejects divergent artifacts claiming the same public URL. Byte-identical
vendored copies are accepted only when the manifest names one authority and
declares the relationship.

The shared manifest prevents drift. It does not couple the two deployments.

### 6. Build in Crucible; publish through a protected boundary

Crucible contains the deterministic, credential-free tooling that:

- assembles the complete registry directory;
- validates schema identities, references, versions, and meta-schemas;
- detects path and ownership collisions;
- emits checksums and machine catalog data;
- produces the catalog input consumed by the human site.

Ordinary pull-request CI builds and checks the artifact without production
authority. A signed release authorizes publication under
[PDR-0004](PDR-0004-release-publication-gate.md). A protected publisher promotes
the exact previously validated artifact; production credentials and environment
configuration do not live in the repository or enter untrusted build steps.

The human-site publisher and schema-registry publisher use separate,
least-privilege identities. Rendering documentation does not grant authority to
replace machine contracts.

This build tooling is repository infrastructure under
[PDR-0006](PDR-0006-shipping-charter.md), not consumer-linked runtime code.

### 7. Each surface has explicit HTTP behavior

The registry:

- returns exact bytes with the declared machine media type;
- supports unauthenticated `GET` and `HEAD` with an explicit cross-origin policy;
- returns real error statuses and never falls back to HTML;
- applies short caching to mutable `v0` paths;
- applies long-lived immutable caching to SemVer paths;
- is smoke-tested after atomic publication for identity, checksum, media type,
  cache policy, cross-origin access, and missing-resource behavior.

The human site may use browser navigation and friendly error pages, but those
behaviors cannot intercept registry requests because it is a distinct origin.

## Consequences

**Positive**

- Schema validators receive a small, deterministic machine surface.
- The human site can change generators, navigation, and visual treatment without
  changing schema identifiers.
- One manifest keeps rendered documentation and raw artifacts tied to the same
  source revision.
- Registry publication authority remains narrower than general website
  deployment authority.
- Domain-first schema URLs survive changes in repository layout or registry
  implementation.

**Negative / costs accepted**

- Two origins require separate artifacts, deployment policies, monitoring, and
  smoke tests.
- The central manifest becomes governed infrastructure and must resolve
  organization-wide URL ownership conflicts before publication.
- The human site must carry explicit links and version context rather than
  relying on same-origin relative paths.
- A schema release and a website refresh can temporarily occur at different
  times; version and digest labels must make that lag visible.

## Alternatives considered

### One origin with HTML and JSON selected by content negotiation

Rejected. The representations serve different products rather than equivalent
serializations. It introduces cache variance, user-agent dependence, and the
possibility that a schema identifier resolves to HTML.

### Serve raw schemas below `crucible.3leaps.dev/schemas/`

Rejected as the canonical form. It couples machine identifiers to the human
product origin and its routing, deployment, and availability behavior. It also
abandons the already documented `schemas.3leaps.dev` namespace.

The human site may expose `/catalog/schemas/` as a browsing experience, but raw
links point to the registry origin.

### Add `/crucible/` below the schema origin

Rejected. Repository ownership is provenance, not schema identity. The registry
is an organization-wide namespace, and existing identifiers are domain-first.

### Let each source repository publish directly to the shared registry

Rejected. Independent writers make collision handling, atomic catalogs,
credential scoping, and rollback ambiguous. Source repositories produce pinned
inputs; one governed registry publisher owns the public namespace.

### Keep all deployment tooling outside Crucible

Rejected. The repository must be able to deterministically construct and
validate what it claims to publish. Otherwise the public artifact contract lives
only in privileged infrastructure that ordinary contributors cannot reproduce.

Credentialed promotion remains outside the unprivileged build boundary.

## Implementation framing

The first implementation slice should produce, without publishing:

1. a publication-manifest schema and initial manifest;
2. deterministic registry and human-catalog build outputs;
3. collision, identity, reference, and checksum validation;
4. negative controls proving the gates reject divergent ownership and invalid
   identity mappings;
5. an artifact manifest suitable for protected promotion.

Hosting, DNS, and production promotion follow in a separate slice after the
artifact contract is reviewable locally.

## References

- [ADR-0001: Schema and Config Versioning with v0 and SemVer](ADR-0001-schema-config-versioning.md)
- [EPR-0004: Publication Surfaces Preserve Domains of Concern](EPR-0004-publication-surfaces-preserve-domains-of-concern.md)
- [PDR-0004: The Signed Tag Authorizes Publication](PDR-0004-release-publication-gate.md)
- [PDR-0006: Crucible Ships No Consumer-Linked Code](PDR-0006-shipping-charter.md)
- [Decision & Governance Records — the `*DR` family](../repository/decision-records.md)

## Revision History

| Date       | Status Change | Summary                                                 | Updated By |
| ---------- | ------------- | ------------------------------------------------------- | ---------- |
| 2026-08-19 | → proposed    | Define the two-origin Crucible publication architecture | entarch    |
