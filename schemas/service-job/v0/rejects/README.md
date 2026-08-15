# service-job/v0 — reject fixtures

These fixtures prove the contract's gates can **fail** —
[EPR-0002](../../../docs/decisions/EPR-0002-verification-gate-integrity.md)
obligation 3. `make check` asserts each `reject-*` fails at the labeled
layer with the expected reason, and that each `baseline-*` passes.

Schema pairs differ in exactly one field.

| Directory | Layer     | Reject must fail because                                                                                                                                                                                                       |
| --------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `schema/` | schema    | `x-` kind · hosted without egress · `observe_hint` start position · accepted without `job_id` · succeeded without outputs                                                                                                      |
| `set/`    | normative | pagination revision cross · offer revision mismatch · local→hosted fallback · hosted backend mismatch · idempotency conflict · unknown-admission retry · illegal / terminal transitions · cancel-accepted treated as cancelled |

`interpretation.json` sidecars are not messages; they record an incorrect
equivalence claim (`cancel_admission=accepted` ⇒ `cancelled`) so that claim
can fail in daylight.

Fixture data is synthetic. Identifiers are public-safe tokens.
