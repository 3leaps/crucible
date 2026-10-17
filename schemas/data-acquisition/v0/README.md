# Data acquisition schema family v0

**Proposed / experimental.** Capability: `contract: data-acquisition/v0`.
Resolve a trusted pinned `contract.json`; instance values do not choose a registry.
The normative [Data Acquisition Contract](../../../docs/standards/data-acquisition-contract.md)
and [ADR-0014](../../../docs/decisions/ADR-0014-data-acquisition-contract.md)
define the boundary.

| Artifact | Purpose |
| --- | --- |
| `source-policy.schema.json` | Entry: reviewed source policy, parent meters, transport and target vocabulary |
| `acquisition-plan.schema.json` | Policy/work pins, original/effective scope, cadence and attributed compromise |
| `registration-result.schema.json` | Unavailable, rejected, indeterminate or persisted allocation result |
| `examples/` | Synthetic policy, plans, registration outcomes and a planning-scope coverage declaration |
| `rejects/` | Schema and semantic reject fixtures with expected refusal reasons ([index](rejects/README.md)) |

All pins bind exact UTF-8 bytes by SHA-256, not reserialized JSON. Shape acceptance
is separate from semantic checks and authority qualification. Plans/results grant
no execution authorization; redistribution defaults to block_export.

The initial meter profile is rolling-window and the authority shape is
single-owner. Runtime enforcement, trusted terms observation, authentication,
remote ownership/fencing and behavioral qualification belong to adopters.
The unavailable example is suitable for a stub: it allocates nothing. The
registered example illustrates a claimed receipt shape; it does not qualify a
backend or prove that any capacity was reserved.

Run `python3 scripts/test-data-acquisition-controls.py` for structural and
fixture-semantic controls. The fixtures are the vectors: each schema reject must
fail its schema, and each semantic reject must be refused with the reason in its
name, drawn from the standard's refusal-reason table. Duplicate member names are
refused while reading bytes. The controls do not validate an actual
work-manifest implementation, execute a scheduler or make a completeness claim.
The coverage example retains the plan pin, chooser, scope limit and exclusions,
with unknown coverage, no acquired-volume claim and block_export protection.
