# Durable queue schema family v0

**Proposed / experimental.** The capability is `contract: durable-queue/v0`.
Resolve it through a trusted, pinned `contract.json`; never treat
instance-provided retrieval addresses as a schema registry. The normative
companion is the
[durable queue standard](../../../docs/standards/durable-queue-contract.md).
Decision record: [ADR-0012](../../../docs/decisions/ADR-0012-durable-queue-contract.md).

The contract is logical only, and this first publication is narrowed to an
audit and lifecycle fold: portable restore, `replay`, cross-queue fan-out and
tolerant conformance are deferred. Storage layouts, drivers, daemons and worker
runtimes belong to adopting repositories.

| Artifact | Responsibility |
| --- | --- |
| `contract.json` | Capability manifest; entry is the capability profile |
| `capability-profile.schema.json` | Discovery root: build facts, runtime facts, conformance and ledger mode |
| `queue-message.schema.json` | The message envelope as stored and delivered |
| `ledger-event.schema.json` | One line of the append-only NDJSON ledger; closed event vocabulary |
| `control-exchange.schema.json` | One request or response line of the wire binding; typed per-op params and results, closed vocabulary |
| `examples/` | One golden per object, an error response, a payload-ref message, and a service-job composition message |
| `rejects/schema/` | Baseline and reject pairs differing in exactly one field |
| `rejects/semantic/` | Reject vectors the fixture-integrity checker must detect, each labeled with its reason |
| `vectors/core/` | Behavioral vectors every implementation must pass |
| `vectors/fanout/` | Vectors requiring the `atomic_fanout` capability |
| `vectors/canonicalization/` | The identity-digest vector with exponent, negative-zero and UTF-16 key-order cases |

## Vectors

A vector is an op script with expected results and the exact expected ledger.
`$name` tokens bind to ids and leases returned by earlier ops; `{"$rebind":
"$l", field: v}` presents a bound lease with one field altered. Timestamps
derive from `clock_start` plus each op's `at_ms` under `virtual_clock`.
`scripts/validate-durable-queue-vectors.py` checks every vector: requests and
results validate against the control schema, bindings resolve, the ledger is
gap-free with contiguous atomic groups, transitions are legal, attempts
correspond to leases, and identity digests match the repository's RFC 8785
materializer. A required inventory is enforced and empty vectors are rejected.
Vectors are hand-authored from the standard; an implementation's own receipts
are never the oracle. The harness that executes vectors lives in the adopting
repository, not here.

Fixture data is synthetic. Identifiers are public-safe tokens.
