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

## Vectors and the consistency model

A vector is an op script with expected results and the exact expected ledger,
hand-authored from the standard. `$name` tokens bind to ids and leases
returned by earlier ops; substitution happens only in the declared lease and
id positions (`leases[]`, `parent`, `message_ids[]`, receipt and ledger ids),
never inside queue names, workers, messages, children or payloads, so an
opaque payload string that looks like a token stays data. `{"$rebind": "$l",
field: v}` presents a bound lease with one field altered. `bind` paths are
restricted to `deliveries[n].lease|message` on a `claim`. Every vector states
`min_idempotency_window_ms`; a profile whose window is smaller is not
admissible for the core suite and cannot claim deterministic conformance.

`scripts/validate-durable-queue-vectors.py` **executes each op script against
a reference consistency model**: an in-memory fold of the normative rules
under the virtual clock. It requires the hand-authored receipts, delivery
counts, lease outcomes and every ledger event and atomic group to match the
model exactly, so an op removed while its event is kept, a split group, a
fabricated digest, an invented outcome or an out-of-range bind path is
rejected as `ledger_mismatch`, `expectation_mismatch` or `binding`. Fixtures
are loaded with the repository's strict RFC 8785 loader (`ingest`), and a
payload outside the I-JSON domain is `payload_domain`.

**Assurance boundary.** The model covers `enqueue`, `claim`, `extend`, `ack`,
`nack`, `fail`, `fan_out`, `sweep`, `stats`, `redrive` and `purge` on the
vector's queue, with a second queue admitted only so wrong-queue leases can be
exercised. `peek`, `export_ledger`, `capabilities` and `advance_clock` may
appear in a script but may not carry `expect` or `bind`; the checker fails
closed on any attempt. The model is a checker for fixtures. It is not a
conformance oracle for implementations, which is why the expected histories
remain hand-authored and the committed semantic rejects demonstrate that the
model detects defects rather than regenerating expectations from it. A
required inventory is enforced and empty vectors are rejected. The harness
that executes vectors against a real implementation lives in the adopting
repository, not here.

Fixture data is synthetic. Identifiers are public-safe tokens.
