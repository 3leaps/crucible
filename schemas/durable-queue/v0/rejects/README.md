# durable-queue/v0 — reject fixtures

These fixtures prove the gates can **fail** —
[EPR-0002](../../../../docs/decisions/EPR-0002-verification-gate-integrity.md)
obligation 3. `make check` asserts each `schema/reject-*` fails schema
validation with its `baseline-*` passing and the pair differing in exactly one
field, and that each `semantic/reject-*` vector is detected by the
fixture-integrity checker with the reason named in its `expect_reject`.

## schema/

| Reject | Must fail because |
| --- | --- |
| message-unknown-version | `v` is not 0 |
| message-payload-and-ref | both `payload` and `payload_ref` |
| message-hosted-contract | `payload_contract` embeds a host |
| message-ref-without-digest | `payload_ref.digest` is required |
| message-ref-path | `artifact_id` is a filesystem path, not a token |
| ledger-unknown-type | type outside the closed vocabulary |
| ledger-leased-without-attempt | `leased` requires `attempt` |
| ledger-fencing-token | the fencing token never appears in the ledger |
| ledger-missing-group-size | every event carries `group_size` |
| ledger-nacked-without-reason | `nacked` requires `reason` |
| profile-unknown-capability | capability outside the closed set |
| profile-unknown-origin | origin is not harness or declared |
| profile-missing-window | `idempotency_window_ms` is required |
| profile-deterministic-without-clock | deterministic requires `virtual_clock` enabled |
| profile-deterministic-inferred | deterministic requires `ledger: recorded` |
| profile-deterministic-declared | deterministic requires `origin: harness` |
| profile-tolerant-conformance | tolerant mode is deferred, not in the vocabulary |
| profile-durability-strategy-as-model | a commit strategy name is not a failure model |
| control-unknown-op | op outside the closed vocabulary |
| control-empty-params | typed params are required per op |
| control-lease-without-queue | a lease carries its queue |
| control-lease-zero-attempt | attempt is at least 1 |
| control-replay-op | `replay` is deferred, not in the vocabulary |
| control-claim-negative-wait | durations are non-negative |
| control-claim-missing-lease-ms | typed params are required |
| control-fanout-child-queue | children go to the parent's queue; no child queue param |
| control-fanout-child-with-id | producer input carries no broker-assigned id |
| control-response-unknown-outcome | outcome outside the closed vocabulary |
| control-response-extra-result | results are closed per op |
| control-response-missing-op | responses echo `op` |
| control-response-error-without-code | error requires `code` |

## semantic/

Each is a vector the consistency-model checker must reject with the reason
in its `expect_reject`. The baseline vector passes.

| Reject | Checker reason |
| --- | --- |
| empty-script | `empty_vector` |
| unknown-op-in-script | `op_schema` |
| duplicate-member-payload | `ingest` (strict RFC 8785 loader) |
| payload-outside-ijson | `payload_domain` |
| bind-path-out-of-range | `binding` |
| unbound-id | `unbound_binding` |
| negative-delivery-count, negative-expected-attempt, invented-redrive-outcome, boolean-delivery-count, boolean-expected-attempt, symbolic-outcome, symbolic-payload, ack-after-lease-expiry, ack-at-lease-expiry-boundary, fanout-after-parent-expiry, delivery-after-message-expiry, purge-wrong-queue, compounded-redrive-budget, symbolic-payload-id-key, redelivery-after-message-expiry-on-lease-lapse | `expectation_mismatch` (model produced a different result) |
| bare-symbolic-expect | `expect_shape` |
| fanout-without-capability, long-poll-without-capability | `capability_admission` |
| ack-attempt-never-leased, digest-mismatch, event-after-terminal, leased-without-prior-enqueue, redelivery-without-expiry, seq-gap, truncated-group, ack-op-removed-acked-kept, fanout-group-split | `ledger_mismatch` (hand-authored history does not match the model's) |

Fixture data is synthetic. Identifiers are public-safe tokens.
