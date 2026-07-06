# Process Run Schemas v0

Machine-readable companion schemas for the local process telemetry & control
contract.

The normative standard is
[`docs/standards/process-run-contract.md`](../../../docs/standards/process-run-contract.md).
These schemas provide a structural validation surface for consumers.
Behavioral rules — fail-open emission, constant-time token verification,
staleness sweeping, unknown-verb rejection — are enforced by producers and
consumers, not by schema validation.

The contract identity is the opaque capability token
`contract: process-run/v0`. Consumers resolve that token through local
configuration, a vendored copy, or another trusted registry. Instances must
not embed a schema host as their identity.

The L2 contract entry point is `contract.json`. Consumers resolve the
capability to that manifest, verify its `capability`, and load the relative
`entry_schema` (`process-card.schema.json` — the card is the discovery root).
Resolution fails closed when the manifest is missing, the capability does not
match, or the entry schema is missing. Direct `$id` lookup remains valid for
schema-aware tooling, but it is not the contract-entry mechanism.

| Schema                         | Governs                                                                                        |
| ------------------------------ | ---------------------------------------------------------------------------------------------- |
| `process-card.schema.json`     | The card — one running process's discovery root (identity, telemetry pointer, control pointer) |
| `process-event.schema.json`    | One line of the append-only NDJSON event stream                                                |
| `control-exchange.schema.json` | One request or response line on the control channel                                            |

Worked examples in [`examples/`](examples/).
