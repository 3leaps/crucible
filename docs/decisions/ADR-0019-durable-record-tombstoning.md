---
id: "ADR-0019"
title: "Durable record tombstoning with retained audit history"
status: "proposed"
date: "2026-10-20"
last_updated: "2026-10-20"
deciders:
  - "@3leapsdave"
  - "cxotech"
  - "entarch"
scope: "Crucible foundation / portable storage contracts"
tags: ["records", "journal", "retention", "interchange-contract"]
---

# ADR-0019: Durable Record Tombstoning with Retained Audit History

## Status

Listed deciders are prospective; their assent is not recorded by this draft.

Proposed. Defines an experimental `contract: durable-record/v1` family.

## Context

A retained record can remain necessary for authorized audit while its use,
export or reuse must stop. Retirement withdraws an individual record from
current reads; it does not express this restriction. Byte removal belongs to
the separately reserved managed-redaction capability.

## Decision

Add `tombstoned` and `untombstoned` journal operations in v1. Retain the v0
record envelope and revision digests unchanged. V1 readers refuse v0 journals
and receipts. Implementations may expose both capabilities through distinct
version-aware entry points. No automatic migration or relabeling is defined. Require exact targets,
attributed evidence, observations, independent holds and targeted restoration.
Use one key namespace across content and protection operations, with original
receipt replay preceding mutable-state checks.

Require authoritative current protection before ordinary serving, export or
reuse. Declare omissions explicitly and keep closure independent of permission.
Inherited restrictions remain binding. Audit access requires separate
authorization and cannot be selected as a public export bypass.

The [standard](../standards/durable-record-v1-contract.md), schemas and logical
vectors define the candidate. Physical migration, erasure and adopter
qualification remain outside this decision. This repository follows the
[3 Leaps OSS Sensitive Local Data Policy](https://github.com/3leaps/oss-policies/blob/main/SENSITIVE-LOCAL-DATA.md);
all examples are synthetic.

## Consequences

Readers must negotiate v1 before interpreting its journal. Existing v0 data
and contracts remain valid. Held content and its immutable pins remain available
for authorized audit. Consumers must enforce restrictions through derived
artifacts; schema validation alone cannot establish release authorization or
revoke previously released copies.
