# Application control v0 semantic validation

**Layer id:** `application-control/v0-semantics`
**Layer version:** `0.1.0`

JSON Schema validates individual artifacts. Implementations also enforce the
following cross-artifact rules and run the shared fixtures.

| Rule      | Requirement                                                                                                                                                                                                                           |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SEM-C01` | Operation identifiers, information-source identifiers, rule identifiers, and non-controllable surface references are unique within their respective catalog or policy.                                                                |
| `SEM-C02` | Each user-visible control surface appears exactly once: as a `surface_ref` on one operation, or as one `non_controllable_surfaces` entry. A programmatic-only operation may omit `surface_refs`.                                    |
| `SEM-C03` | Each application surface that emits or displays information appears exactly once in the information-source catalog. A programmatic-only source may omit `surface_refs`.                                                              |
| `SEM-C04` | Every request operation and target kind exists in the descriptor-pinned operation catalog.                                                                                                                                            |
| `SEM-C05` | Request and result payload schema URI and digest equal the operation's pinned request or result payload contract.                                                                                                                     |
| `SEM-C06` | A `mutate` or `destructive` operation requires `idempotency_key` and `request_fingerprint`; it also requires `expected_generation` when its catalog precondition is `generation_required`.                                            |
| `SEM-C07` | Reuse of an idempotency key with a different request fingerprint is rejected. A replay returns the original result and sets `original_result_hash`.                                                                                   |
| `SEM-C08` | Every result references the policy artifact actually evaluated; `denied` and `confirmation_required` decisions have `effect: not_applied`.                                                                                            |
| `SEM-C09` | Every emitted observation source exists in the descriptor-pinned source catalog and its mode, payload schema, payload digest, and provenance match that entry. `scrape` and `client_derived` sources never emit observation messages. |
| `SEM-C10` | `recorded_at` is not earlier than `occurred_at`. A source advertising replay supplies a cursor; detected stream gaps are explicit.                                                                                                    |
| `SEM-C11` | Each operation's `emitted_sources` exists in the information-source catalog.                                                                                                                                                          |
| `SEM-C12` | A policy rule references only cataloged applications and, according to its kind, operations and target kinds or information sources. Deny rules take precedence over allow rules. No matching allow means deny.                       |
| `SEM-C13` | The receiver derives principal identity from its authenticated connection or local peer credentials. Payload values that attempt to assert identity have no authority.                                                                |
| `SEM-C14` | Evidence source is valid for its stage: user interface for interaction; controller for request; policy engine for decision; application for effect. Interaction evidence names a cataloged surface for the same operation.            |
| `SEM-C15` | A non-null control endpoint requires a non-null policy reference. A null endpoint means no control listener is available.                                                                                                             |
| `SEM-C16` | Descriptor catalog and policy digests match the exact artifacts used for validation and execution.                                                                                                                                    |

The reference validator implements the rules exercised by
`fixtures/semantic/manifest.json`. Product profiles add fixtures that prove
their complete control-surface and information-source inventories against
`SEM-C02` and `SEM-C03`.
