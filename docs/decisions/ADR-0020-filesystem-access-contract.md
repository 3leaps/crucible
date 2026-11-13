---
id: "ADR-0020"
title: "Filesystem access through qualified held-root profiles"
status: "proposed"
date: "2026-11-13"
last_updated: "2026-11-13"
deciders: ["@3leapsdave", "cxotech", "entarch", "secrev"]
scope: "Crucible foundation / portable filesystem contracts"
tags: ["filesystem", "handles", "containment", "contract"]
---

# ADR-0020: Filesystem Access Through Qualified Held-Root Profiles

## Status

Proposed. The `filesystem-access/v0` family is experimental. Listed deciders
identify the required decision perspectives; they do not imply completed approval.

## Context

Portable filesystem callers need to distinguish lexical name admission, runtime
containment, link refusal and object identity. Kernel mechanisms differ by
platform and operation. A directory handle can remain valid after a rename,
while its old pathname or a previously admitted descendant has different
containment properties. A single unqualified "safe path" claim hides these
boundaries.

## Decision

Define a dedicated root-relative name vocabulary, `containment/v0` and
`no-links/v0` profiles, typed outcomes, capability cells and declarative recipe
cases. The [standard](../standards/filesystem-access.md) separates trusted root
acquisition from operations starting at an admitted directory object.

Specify non-blocking directory-only root and intermediate acquisition, physical
link and parent resolution, exclusive creation without final-link following,
bounded reads/listings, and identity comparison over held-handle lifetimes.
Qualify every runtime claim by platform, backend, operation, adversary and
observation point. Optional mount-boundary enforcement is distinct from device
identity. An unsupported requested guarantee is refused without fallback.

Publish schemas, synthetic authored cases and standalone falsification controls.
The logical evaluator does not implement production filesystem access. Native
availability probes and operation qualification remain distinct from logical
corpus agreement. This conforms to
[PDR-0006](PDR-0006-shipping-charter.md).

Examples and evidence follow the
[3 Leaps OSS Sensitive Local Data Policy](https://github.com/3leaps/oss-policies/blob/main/SENSITIVE-LOCAL-DATA.md).
Fixtures are synthetic; proprietary material stays outside working trees.

## Consequences

Adopters share portable error and capability vocabulary while retaining native
implementation and qualification responsibility. Existing generic lexical path
types retain their scope and confer no containment guarantee. v0 adopters pin
an exact released contract and do not infer race resistance from schema validity,
a backend label or a successful availability probe.

The family may ship as proposed/experimental. Stabilization requires independently
authored agreement on its corpus and qualified consumer cells with their negative
and temporal controls. Unresolved disagreements must be closed before tagging.
