---
id: "EPR-0004"
title: "Publication surfaces preserve domains of concern"
status: "proposed"
date: "2026-08-19"
last_updated: "2026-08-19"
deciders:
  - "@3leapsdave"
  - "entarch"
scope: "Crucible foundation / shared governance — durable engineering principle"
tags:
  - "principles"
  - "publication"
  - "interfaces"
  - "web"
  - "governance"
relates-to:
  - "crucible ADR-0003 (the *DR taxonomy; EPR = a durable engineering principle)"
  - "crucible EPR-0003 (proposed; one durable claim remains level with its resolved state)"
  - "crucible PDR-0004 (a signed release authorizes publication)"
  - "crucible ADR-0007 (proposed; Crucible application of this principle)"
---

# EPR-0004: Publication Surfaces Preserve Domains of Concern

## Status

**Proposed.** Estate-wide engineering principle. It graduates to accepted when
the Crucible schema registry and human documentation site demonstrate the
two-surface pattern and one independent estate service records a conforming
adoption.

## Context

A single body of source material often produces several public products:

- a raw schema consumed by validators;
- rendered documentation read by people;
- a machine-readable catalog consumed by discovery tooling;
- a download intended to remain byte-stable;
- an interactive application whose representation changes continuously.

It is attractive to place these products behind one URL and choose a response by
content negotiation, user agent, rewrite rule, or fallback behavior. The source
is shared, and the pages may describe the same subject, so a single surface can
look simpler.

They are not necessarily the same resource. A JSON Schema is an executable
contract with an identity, media type, reference graph, version policy, and
cache expectations. A rendered HTML page explaining that schema is a
presentation with navigation, prose, search, accessibility, and a different
release cadence. Serving one when a consumer asked for the other is not a
cosmetic error: a validator may cache HTML under a schema identifier, a browser
may receive raw data without a usable explanation, or an application fallback
may convert a missing machine artifact into a successful `200 text/html`.

The same hazard appears beyond JSON and HTML. A control plane and a data plane
may share a product name but not an authority boundary. A mutable discovery
alias and an immutable release artifact may share content but not cache
semantics. A public status surface and an authenticated application may describe
one system but must remain available under different failure conditions.

The recurring mistake is treating **shared subject matter** or **shared source**
as proof of a shared publication contract.

This record uses two terms:

- A **domain of concern** is a coherent set of consumers, semantics, lifecycle,
  authority, and operational expectations. It is not necessarily a DNS domain.
- A **publication surface** is the canonical addressable namespace through which
  that contract is delivered: an origin, path family, registry, feed, or other
  public interface.

The standing tension this record arbitrates is **fewer visible endpoints and
less deployment machinery** versus **unambiguous identity, bounded authority,
and behavior consumers can safely automate against**. When the contracts differ,
clarity wins.

## Principle

> **Each canonical public identifier MUST resolve to one declared publication
> contract. Products with materially different consumer, semantic, lifecycle,
> authority, or failure contracts MUST have distinct canonical resources; when
> those differences create independent operational boundaries, they SHOULD have
> distinct origins.**

Six obligations make the principle inspectable.

### 1. One identifier has one primary contract

A canonical URL declares what the resource is, not merely where some source
material can be rendered. Its primary audience, representation semantics,
media type, version behavior, and mutability are stable enough for a consumer to
act on without guessing.

Compression, transport encoding, or genuinely equivalent serializations may be
negotiated. A human explanation and an executable machine contract are not
equivalent serializations. They receive distinct canonical URLs.

### 2. Separate the resource before separating the infrastructure

Distinct canonical paths are the minimum boundary. Use distinct origins when
one or more of these differ materially:

| Concern              | Examples of a material difference                         |
| -------------------- | --------------------------------------------------------- |
| Consumer             | browser reader versus unattended validator                |
| Semantics            | explanatory page versus executable contract               |
| Version and mutation | continuously revised page versus immutable release object |
| Caching              | short-lived navigation versus long-lived pinned artifact  |
| Authority            | public read versus privileged control or mutation         |
| Availability         | application failure versus independent status or recovery |
| Failure behavior     | navigational fallback versus exact status and media type  |
| Deployment           | separate release gate, owner, or credential boundary      |

An origin is not required merely to organize navigation. Sections of one
documentation product can remain paths on one documentation origin. Conversely,
a path prefix does not provide meaningful separation when its deployment
authority, fallback router, cache policy, or failure domain remains inseparable
from the rest of the origin.

### 3. Machine surfaces fail as machines

A machine publication surface:

- returns the declared media type and exact artifact bytes;
- uses truthful HTTP status codes;
- never replaces a missing resource with an application shell or HTML error
  carrying a success status;
- makes mutation and cache semantics explicit;
- is usable without browser execution, cookies, or user-agent detection.

Browsable indexes may exist, but they do not change the contract of canonical
machine artifact URLs.

### 4. Human surfaces explain and link; they do not impersonate

A human surface may render, annotate, search, compare, and contextualize a
machine artifact. It links to the artifact's canonical machine URL and identifies
the version or digest it describes.

It does not become an undocumented second authority for the raw bytes. A proxy
or convenience download is labelled as such and redirects or links to the
canonical resource unless it has an independently declared publication
contract.

### 5. Shared source produces coordinated artifacts, not coupled runtimes

One governed manifest or source release SHOULD generate both machine and human
outputs when they describe the same material. The outputs record cross-links and
the same source revision, version, and digest where applicable.

This single-source rule prevents drift; it does not require one deployment,
runtime, origin, cache, or credential. Build-time coordination is preferred to
runtime dependence on a moving source.

### 6. Publication authority follows the surface

Credentials and mutation rights are bounded to the publication surface they
control. A human site renderer does not acquire authority to replace canonical
machine artifacts merely because it presents them. An artifact builder does not
receive production credentials merely because its output may later be
published.

Where a protected publisher is required, unprivileged work produces a
deterministic artifact first. The privileged step promotes that exact artifact
under the surface's own authorization policy.

## Decision test

Before assigning two products to one surface, answer:

1. Do they have the same primary consumer and semantic contract?
2. Can they share media-type and failure behavior without negotiation or
   guessing?
3. Do they have the same mutation, version, and cache policy?
4. Should compromise or failure of one grant control of or remove the other?
5. Are they authorized and released by the same act?

If questions 1 or 2 are **no**, use distinct canonical resources. If questions
3 through 5 expose an operational boundary, prefer distinct origins as well.

## Consequences

**Makes easier**

- Automated consumers receive deterministic content and truthful failures.
- Human interfaces can evolve without destabilizing machine identifiers.
- Cache, availability, and security controls are scoped to the resource they
  protect.
- A product can replace its site generator or hosting provider without changing
  its machine contract.
- Incident diagnosis starts with a declared surface owner and behavior rather
  than a rewrite chain.

**Makes harder / costs accepted**

- One source product may require several static builds, origins, certificates,
  deployment policies, and smoke-test suites.
- Cross-links and source-version parity become explicit build outputs that must
  be verified.
- Teams must make the publication boundary decision early, before convenient
  URLs become durable dependencies.
- A small deployment may use more infrastructure than a single catch-all site.
  The additional machinery is accepted when it buys a real contract or authority
  boundary; this record does not require ceremonial subdomains.

## Adoption and propagation

This principle is canonical in Crucible. Adopting repositories link or vendor it
and record their local surface map; they do not maintain a divergent restatement.

A conforming surface map identifies:

- the canonical origin or path family;
- the resource and primary consumer;
- representation and failure contract;
- mutation, version, and cache policy;
- publication authority and release trigger;
- authoritative source and cross-links to related surfaces.

The map may be an ADR, deployment manifest, or public operations document. The
principle fixes the questions, not the file format or hosting provider.

## Not this record

- Choosing a hosting provider, CDN, static-site generator, or DNS operator →
  implementation ADR or infrastructure record.
- Choosing a particular product's hostnames and paths → that product's ADR.
- Defining the exact release trigger and human approval sequence → PDR.
- Threat-specific credential scopes and residual risks → SecDR.
- Declaring the version semantics of a schema family → schema ADR or DDR.

## Rationale for the record type

**EPR, not ADR.** The motivating instance is a web architecture choice, but the
rule survives every current hostname, generator, provider, and repository. It
applies equally to APIs, downloads, registries, control planes, and status
surfaces. Reversing it would mean accepting ambiguous resource identity and
coupled authority as an estate default, not selecting a different component.

**Not a web standard.** HTML and JSON make the distinction easy to see, but file
format is evidence of a boundary rather than the boundary itself. Two JSON
resources can have different authority and lifecycle contracts; two HTML
sections can belong to one coherent surface.

## References

- [ADR-0003: Decision & Governance Record Taxonomy](ADR-0003-decision-record-taxonomy.md)
- [EPR-0003: Durable Claims Assert on What Exists and Move When It Moves](EPR-0003-claim-integrity.md)
- [PDR-0004: The Signed Tag Authorizes Publication](PDR-0004-release-publication-gate.md)
- [ADR-0007: Separate Crucible Documentation and Schema Registry Origins](ADR-0007-separate-documentation-and-schema-registry-origins.md)
- [Decision & Governance Records — the `*DR` family](../repository/decision-records.md)

## Revision History

| Date       | Status Change | Summary                                                | Updated By |
| ---------- | ------------- | ------------------------------------------------------ | ---------- |
| 2026-08-19 | → proposed    | Establish the estate-wide publication concern boundary | entarch    |
