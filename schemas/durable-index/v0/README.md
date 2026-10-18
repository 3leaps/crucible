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

`python3 scripts/test-durable-index-controls.py` runs 19 shape cases (six passing
objects and 13 rejects), six authored plan/framing vectors, and 33 authored
logical transition vectors. `cases.json` inventories every JSON fixture; missing
or unlisted files fail. JSON duplicate keys, non-finite numbers and lone
surrogates refuse. The script uses Python stdlib and the existing goneat JSON
Schema validator, with offline references limited to these contract families.
Validator execution failures cannot satisfy negative cases.

Examples are **standalone structural objects**. The plan/row/coverage/index
metadata show a synthetic baseline; the publication example demonstrates the
schema specialization using the existing snapshot fixture bindings. They do not
constitute one complete durable-index graph. No R2 claim is made for them.

The logical model receives already-normalized input evidence. In particular,
`absence_authority` is the set of scopes that passed I3, **not a wire field or a
trusted producer boolean**. Plan-discovery completion, the admitted parent digest
and logical rows are explicit test inputs. These controls exercise decisions
once those facts are verified; they do not verify the physical graph, coverage
subject/volume, actor authorization or a storage backend. Their status message
makes that limit explicit. Full file-backed graph rejects and physical twins
are required before release under the conformance requirements.

## Schema and pin composition

Vendor this family with the exact segmented-snapshot, coverage-attestation and
data-artifact dependencies from the same reviewed release. Resolve logical
`contract:` ids offline. A pin inventory must include standard/DDR/schema/corpus
bytes and exact source commit/tag provenance. No runtime library is shipped.

The new segmented-snapshot field is optional in its base schema and required by
the index semantic profile. Older closed-schema readers may refuse it. A reader
must never ignore an unsupported required profile and report full verification.

## Limits of present controls

R2/W1/W2/W3 evidence requires complete graphs with real Parquet members and
independent logical twins, all profile rules, refusal inventories and mutation
controls. Physical decoder invocation remains subject to PDR-0006. A released experimental contract still does not qualify adopter runtime
fencing, durability, recovery, source coverage or reclamation.
