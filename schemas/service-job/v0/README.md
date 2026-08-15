# contract: service-job/v0

Machine-readable companion schemas for the portable service-job contract.

The normative standard is
[`docs/standards/service-job-contract.md`](../../../docs/standards/service-job-contract.md).
These schemas provide the structural validation surface. Catalog/offer
integrity, local→hosted non-fallback, hosted backend integrity, idempotency,
and legal transitions are enforced by
`scripts/validate-service-job-normative.sh` and proven able to fail by
`scripts/test-service-job-controls.sh`.

The contract identity is the opaque capability token
`contract: service-job/v0`. Consumers resolve that token through local
configuration, a vendored copy, or another trusted registry. Instances must
not embed a schema host as their identity.

The L2 contract entry point is `contract.json`. Consumers resolve the
capability to that manifest, verify its `capability`, and load the relative
`entry_schema`. Resolution fails closed when the manifest is missing, the
capability does not match, or the entry schema is missing. Direct `$id`
lookup remains valid for schema-aware tooling, but it is not the
contract-entry mechanism.

| File                              | Role                                                   |
| --------------------------------- | ------------------------------------------------------ |
| `service-job-message.schema.json` | Discriminated entry schema (thirteen `message_type`s). |
| `contract.json`                   | Capability manifest and entry pointer.                 |
| `examples/`                       | One golden per kind, plus the audio cross-path.        |
| `canonicalization/`               | RFC 8785 vectors plus the JobSpec integration digest.  |
| `rejects/`                        | Schema-labeled and normative-labeled controls.         |
