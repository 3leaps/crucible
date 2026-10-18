# durable-index/v0 — initial design bundle

**Proposed, design review only.** This directory contains a structural candidate
and logical controls, not a complete physical corpus or qualified implementation.
The entry schema specializes segmented-snapshot's publication without creating a
second publication record. That family's optional `profile_metadata` binding is
mandatory for the index profile and carries `index-metadata.schema.json`.

- [Standard](../../../docs/standards/durable-index-contract.md)
- [ADR](../../../docs/decisions/ADR-0017-durable-index-contract.md)
- [Encoding DDR](../../../docs/decisions/DDR-0004-durable-index-row-and-plan-encoding.md)
- [Conformance requirements](../../../docs/standards/durable-index-conformance.md)

## Implemented design controls

`python3 scripts/test-durable-index-controls.py` runs shape checks, authored
plan/framing and transition cases, byte-bound metadata/plan/coverage cases,
cutover receipts, strict parser controls and fixed checker mutations. `cases.json`
inventories every JSON fixture. The standard's refusal table and the
[reject index](rejects/README.md) must agree with the checker and authored cases;
the [vector index](vectors/README.md) inventories positive and parser vectors.
Unknown, missing or unlisted cases fail the gate. All shape inputs pass strict
JSON parsing before the existing offline goneat validator. Tool failures do not
count as data refusals.

Examples are standalone structural objects. Binding scenarios verify an index
metadata/plan/coverage subgraph with actual pinned bytes and authored enumeration
evidence. They check scope order/count/digest, coverage subject/time/volume,
gaps, inherited provenance and omission of returned keys. Transition scenarios
exercise the fold using explicit normalized authority; these are harness inputs,
not wire booleans. Cutover scenarios check receipts and pinned endpoint identities,
not the physical qualification of either endpoint. Cross-member logical rows are
checked in input order. Negative folders overlay only changed input objects from
a named baseline. `store_overlay` supplies only changed dependency bytes and
`omit_refs` names deliberately missing objects. All pin updates are authored in
those overlays; the checker never repairs bindings or derives expected outcomes.

Complete baseline/observe/enrich **logical projection graphs** now accompany the
subgraph cases under `vectors/graphs/`. They bind actual NDJSON twin bytes using
the explicit corpus-only [logical profile](fixtures/logical-profile.md).
Every publication/manifest/profile/descriptor/catalog/schema/metadata/plan/
coverage/member edge is checked; successor verification fetches the exact parent
and checks authored source evidence against independently authored complete rows.
Protection defaults to block_export across all dependencies, including inherited
state; no field-level allow overrides it. The full-graph control tests transition
verification, not a snapshot-only physical reader.

This projection is deliberately **not a conforming Parquet publication**. Its
index metadata names the intended production encoding, while its fixture profile
and descriptor honestly identify NDJSON transport. No fake Parquet bytes or
unresolvable placeholder member pins are used. The result is labeled
`logical_projection`; it cannot establish R2 or qualify either cutover endpoint
physically. Physical twins and independently implemented reader evidence remain
post-publication adoption gates for a logical-only experimental release. Reviewed
integration and publication assent remain required. The checker does not
authenticate actors, prove source completeness or qualify a storage backend.

## Schema and pin composition

Vendor this family with the exact segmented-snapshot, coverage-attestation and
data-artifact dependencies from the same reviewed release. Resolve logical
`contract:` ids offline. A pin inventory must include standard/DDR/schema/corpus
bytes and exact source commit/tag provenance. No runtime library is shipped.

The new segmented-snapshot field is optional in its base schema and required by
the index semantic profile. Readers that do not implement `profile_metadata` MUST refuse it. A reader
must never ignore an unsupported required profile and report full verification.

## Limits of present controls

R2/W1/W2/W3 evidence requires complete graphs with real Parquet members and
independent logical twins, all profile rules, refusal inventories and mutation
controls. Physical decoder invocation remains subject to PDR-0006. A released experimental contract still does not qualify adopter runtime
fencing, durability, recovery, source coverage or reclamation.
