---
id: "ADR-0014"
title: "Data acquisition policy and planning as a portable contract"
status: "proposed"
date: "2026-10-17"
last_updated: "2026-10-17"
deciders: ["@3leapsdave", "entarch"]
scope: "Crucible foundation / portable data contracts"
tags: ["acquisition", "budgets", "provenance", "interchange-contract"]
---

# ADR-0014: Data Acquisition Policy and Planning as a Portable Contract

## Status

**Proposed.** The candidate `contract: data-acquisition/v0` family has a prose
standard, structural schemas and synthetic fixture controls. Publication does
not qualify a runner, admission authority or storage backend.

## Context

Acquiring a source requires agreements beyond a download URL: who shares the
provider budget, which terms were reviewed, what a byte meter measures, what
scope and cadence were selected, and whether capacity was registered. A schema
that combines those declarations with an unqualified execution claim hides the
difference between planning and authority. Independent planners can otherwise
each promise the same source's full capacity.

## Decision

Define a thin language-neutral family with a source policy, acquisition plan and
registration result. Bind exact policy and work documents with digest pins. Keep
original scope beside effective scope and require attributed compromises to flow
into coverage evidence. Separate access review from redistribution permission.

Name the family `data-acquisition`: it identifies the governed activity beside
`data-artifact`, while remaining distinct from application telemetry's
information-source catalog. `contract:` already supplies the contract namespace.

Registration records allocation under a declared authority; runtime admission
still checks each request. Unavailable and indeterminate are explicit outcomes.
A stub cannot claim registered capacity. The initial profile is rolling-window,
single-owner and experimental. Backend, scheduler, query expansion, response
validation and storage layout remain adopter concerns.

## Alternatives

- A downloader-specific configuration freezes one runtime and failure model.
- Extending data-artifact mixes acquisition authority with sealed-output metadata.
- Reusing the application information-source catalog conflates upstream policy
  with the application's own state emitters.
- Treating every accepted forecast as admission allows cross-plan overbooking.

## Consequences

Consumers can inspect the exact reviewed policy and scope of a plan without
embedding a downloader. Adopters must still qualify meter semantics, trusted
terms observation, ownership, durable idempotency and reconciliation. Synthetic
fixture controls establish structural and limited semantic agreement only.
Existing consumers are unchanged; adoption and stable promotion are separate.

## References

- [Data Acquisition Contract](../standards/data-acquisition-contract.md)
- [Schema family](../../schemas/data-acquisition/v0/README.md)
- [Data artifact contract](../standards/data-artifact-contract.md)
- [Coverage attestation contract](../../schemas/coverage-attestation/v0/README.md)
- [Shipping charter](PDR-0006-shipping-charter.md)
