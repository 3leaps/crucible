---
id: "ADR-0009"
title: "Separate Neutral Forge Capabilities from Curated Provider Profiles"
status: "proposed"
date: "2026-08-27"
last_updated: "2026-08-27"
deciders:
  - "@3leapsdave"
scope: "Crucible foundation / forge-infrastructure contracts"
tags:
  - "schemas"
  - "forge"
  - "authorization"
  - "interchange-contract"
relates-to:
  - "crucible ADR-0001 (schema/config versioning)"
  - "docs/standards/data-artifact-contract.md"
  - "docs/standards/project-work-contract.md"
---

# ADR-0009: Separate Neutral Forge Capabilities from Curated Provider Profiles

## Status

**Current Status**: Proposed — the contract enters review at `v0`.

## Context

Git hosting providers expose useful infrastructure beyond repository storage:
issues, automation, runners, statuses, checks, packages, releases, deployment
governance, webhooks, and other event surfaces.

The providers do not expose one shared feature or authorization model.
Similarly named features differ by operation, principal, resource scope,
grant vocabulary, offering, lifecycle, and event behavior. Application
registration, user consent, installation, token issuance, and runner
registration are distinct transitions.

A single provider-by-feature matrix would either freeze the lowest common
denominator or claim parity that does not exist. A provider-specific contract
per implementation would prevent adopters from expressing portable
requirements.

## Decision

Establish `contract: forge-infra/v0` with:

1. L1 requirement profiles and digest-bound binding plans;
2. L2 authority profiles, closed policy-input facts, and immutable non-secret
   transition receipts;
3. an explicit L3–L6 neutral capability catalog for native git, forge
   resources, automation, events, and telemetry;
4. curated provider profiles mapping native features and authority profiles
   onto that catalog with dated evidence;
5. L7 time-bounded verification receipts for live conformance and drift; and
6. stable forge-object references that exclude access context.

`contract.json` is the schema-registry entry point and exposes the canonical
catalog plus all public object schemas. The catalog is a versioned artifact,
not an illustrative example.

### Operation and authority are the support key

Provider profiles make availability claims per neutral operation and authority
profile. A feature-level boolean is insufficient. The same provider-native
feature may be available to a user token and unavailable to an application
installation.

### Provider vocabulary remains visible

Permission, scope, role, feature, and offering names remain provider-native
data in provider profiles. Neutral capability ids describe jobs and operations
without renaming vendor grants into a fictitious common permission model.

### Consumer policy is an overlay

Information stores, revision stores, long-running agent memory, and other
adopters express requirements against the neutral catalog. Their preferred or
forbidden uses do not become provider facts.

### Evidence is part of a claim

Provider profiles carry observation times and source references. Unknown or
stale evidence does not become support by inference.

### Receipts are non-secret

Binding receipts carry public identifiers and grant names. Credential material
remains outside the contract. Registering an application does not by itself
prove that an authorized principal or usable token exists.

### Binding and verification are distinct

A binding receipt proves that one controlled transition was attempted. It does
not prove current authority. Verification receipts are time-bounded and report
expected, observed, missing, and unexpected grants plus capability checks.
Receipts cite a specific digest-bound plan action; successor transitions cite a
successful predecessor so failed work cannot advance the authority chain.

### Provider and instance identity are extensible

Provider identity is not a closed vendor enum. A shared provider context
distinguishes hosted, self-managed, dedicated, and other instance or offering
contexts.

### Events separate subscription from delivery

Subscription management is a forge capability. Delivery envelopes, retry,
acknowledgement, signature verification, and local receiver execution remain
the responsibility of their respective contracts and integrations.

## Consequences

- Adopters can compare providers without erasing meaningful differences.
- Provider profiles can evolve independently of the neutral vocabulary.
- Authority acquisition and capability use remain connected without becoming
  one credential blob.
- Provider-native limitations and feature names remain representable without
  turning arbitrary extension keys into portable contract vocabulary.
- Cross-document validation is required in addition to JSON Schema.
- Curated provider profiles require ongoing evidence refresh.
- Implementations need a resolver rather than a one-row feature lookup.
- Side-effecting authority operations need digest and idempotency binding.
- Consumers need explicit verification and reconciliation policies.

## Alternatives considered

### One common provider API

Rejected. It would either omit high-value provider capabilities or give
similarly named operations misleadingly identical semantics.

### One provider-by-feature boolean matrix

Rejected. Availability depends on operation, authority, resource scope,
offering, and grants.

### Provider-specific contracts only

Rejected. Adopters could not state portable requirements or evaluate fallback
paths.

### Combine application registration and granted authority

Rejected. Registration, installation, consent, and token issuance have
different principals, outputs, and security boundaries.

### Put adopter use cases in provider rows

Rejected. A provider fact should not change when an information store or
revision store changes policy.

## Review-loop items

1. Whether the canonical neutral catalog should later publish on a separate
   registry release cadence from provider profiles.
2. Whether provider profiles need signed provenance or freshness policy
   metadata beyond source URI and observation time.
3. Whether a later companion contract should normalize webhook delivery and
   retry semantics.
