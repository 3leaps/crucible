# Forge Infrastructure Schemas v0

Machine-readable companion schemas for the portable forge-infrastructure
contract.

The normative standard is
[`docs/standards/forge-infrastructure-contract.md`](../../../docs/standards/forge-infrastructure-contract.md).
The contract identity is the hostless capability token
`contract: forge-infra/v0`.

## Contract shape

The contract separates seven lanes that evolve at different rates:

1. **L1 intent and resolution** uses requirement profiles and digest-bound
   binding plans.
2. **L2 authority control** uses evidence-backed authority profiles and
   immutable non-secret transition receipts.
3. **L3–L6 capabilities** use a canonical neutral catalog plus curated
   provider mappings for native git, forge resources, automation, events, and
   telemetry.
4. **L7 assurance** uses time-bounded verification receipts for live
   conformance and drift.

Provider differences remain first-class. A provider profile may mark an
operation `partial`, `emulated`, `unsupported`, or `unknown`; it must not claim
parity merely because another provider exposes a similarly named feature.

## Objects

| Schema                             | Governs                                                               |
| ---------------------------------- | --------------------------------------------------------------------- |
| `contract.json`                    | Registry entry point exposing the catalog and object schemas          |
| `forge-capability-catalog.json`    | Canonical neutral capability catalog                                  |
| `capability-catalog.schema.json`   | Neutral capability vocabulary and operations                          |
| `provider-profile.schema.json`     | Evidence-backed native-to-neutral mappings                            |
| `authority-profile.schema.json`    | Acquisition, scope, grant model, and lifecycle for one authority kind |
| `binding-plan.schema.json`         | Digest-bound resolution, policy input, and ordered authority actions  |
| `binding-receipt.schema.json`      | One immutable, non-secret authority transition                        |
| `verification-receipt.schema.json` | Time-bounded live grant and capability verification                   |
| `requirement-profile.schema.json`  | Provider-neutral adopter requirements and prohibitions                |
| `forge-object-ref.schema.json`     | Stable locator for a provider-native forge object                     |
| `common.schema.json`               | Shared definitions used by the object schemas                         |

The schema-registry entry point is `contract.json`. Consumers resolve the
capability token to that manifest, verify its `capability`, and load its
relative `entry_schema`, `catalog`, and `object_schemas` targets.

## Cross-document controls

JSON Schema validates each document. The fixture and control battery at
[`scripts/test-forge-infra-controls.sh`](../../../scripts/test-forge-infra-controls.sh)
additionally checks that:

- catalog references, neutral capability ids, and provider operation cells are
  consistent and unique;
- provider mappings and fallbacks resolve to the neutral catalog;
- mapped operations exist on the neutral capability;
- provider and authority acquisition evidence references resolve;
- authority-profile references use the same provider context;
- requirement-profile operations exist on the neutral capability;
- binding-plan refs, revisions, digests, resolutions, and actions resolve;
- transition receipts match a specific contiguous plan action and successful
  predecessor;
- verification receipts match the binding, plan grants, required operation
  checks, outcome semantics, and validity interval; and
- object references resolve to the canonical catalog.

Implementations publishing multiple documents MUST enforce equivalent
cross-document checks.

## Secret boundary

Binding and verification receipts contain identifiers, grant names, and
observations, never credential material. Access tokens, refresh tokens, client
secrets, private keys, PEM material, webhook secrets, signing tokens,
passwords, and runner registration tokens remain out of band.

The schema rejects recognizably secret property names under
`public_identifiers`, but that is defense in depth. Producers are responsible
for ensuring that values are non-secret before publication or persistence.

## Examples and rejects

Worked examples are under [`examples/`](examples/). Structural and semantic
negative controls are under [`rejects/`](rejects/).
