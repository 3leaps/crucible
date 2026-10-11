# Durable queue schema family v0

**Proposed / experimental.** The capability is `contract: durable-queue/v0`.
Resolve it through a trusted, pinned `contract.json`; never treat
instance-provided retrieval addresses as a schema registry. The normative
companion is the
[durable queue standard](../../../docs/standards/durable-queue-contract.md).
Decision record: [ADR-0012](../../../docs/decisions/ADR-0012-durable-queue-contract.md).

The contract is logical only. It defines what a queue promises, how it records
what it did, and how any implementation is driven for conformance. Storage
layouts, drivers, daemons and worker runtimes belong to adopting repositories.

| Artifact | Responsibility |
| --- | --- |
| `contract.json` | Capability manifest; entry is the capability profile |
| `capability-profile.schema.json` | Discovery root: build facts, runtime facts, conformance and ledger mode |
| `queue-message.schema.json` | The message envelope as stored and delivered |
| `ledger-event.schema.json` | One line of the append-only NDJSON ledger; closed event vocabulary |
| `control-exchange.schema.json` | One request or response line of the wire binding; closed op vocabulary |
| `examples/` | One golden per object, plus an error response and a payload-ref message |
| `rejects/schema/` | Baseline and reject pairs differing in exactly one field |
| `vectors/core/` | Behavioral vectors every implementation must pass |
| `vectors/fanout/` | Vectors requiring the `atomic_fanout` capability |

## Vectors

A vector is an op script with expected results and the exact expected ledger.
`$name` tokens bind to ids returned by earlier ops. Timestamps derive from
`clock_start` plus each op's `at_ms` under the `virtual_clock` capability.
Vectors are hand-authored from the standard; an implementation's own receipts
are never the oracle. The harness that executes vectors lives in the adopting
repository, not here.

Fixture data is synthetic. Identifiers are public-safe tokens.
