# durable-queue/v0 — reject fixtures

These fixtures prove the schema gates can **fail** —
[EPR-0002](../../../../docs/decisions/EPR-0002-verification-gate-integrity.md)
obligation 3. `make check` asserts each `reject-*` fails schema validation and
each `baseline-*` passes. Pairs differ in exactly one field.

| Reject | Must fail because |
| --- | --- |
| `reject-message-unknown-version` | `v` is not 0 |
| `reject-message-payload-and-ref` | both `payload` and `payload_ref` present |
| `reject-message-hosted-contract` | `payload_contract` embeds a host instead of a capability token |
| `reject-ledger-unknown-type` | event type outside the closed vocabulary |
| `reject-ledger-leased-without-attempt` | `leased` requires `attempt` |
| `reject-ledger-fencing-token` | the fencing token never appears in the ledger |
| `reject-profile-unknown-capability` | capability outside the closed set |
| `reject-profile-unknown-origin` | origin is not `harness` or `declared` |
| `reject-control-unknown-op` | op outside the closed vocabulary |
| `reject-control-response-error-without-code` | error object requires `code` |

Fixture data is synthetic.
