# Durable runner schema family v0

**Proposed / experimental.** The capability is `contract: durable-runner/v0`.
Resolve it through a trusted, pinned `contract.json`; never treat
instance-provided retrieval addresses as a schema registry. The normative
companion is the
[durable runner standard](../../../docs/standards/durable-runner-contract.md).
Decision record:
[ADR-0021](../../../docs/decisions/ADR-0021-durable-runner-contract.md).

The contract is logical only. It admits the modes `basic`, `retrying`,
`journaled` and `scheduled`, and reserves `sealed`, which no profile may
advertise yet. Process supervision, storage layouts, schedulers and runtimes
belong to adopting repositories.

| Artifact | Responsibility |
| --- | --- |
| `contract.json` | Capability manifest; entry is the runner profile |
| `runner-profile.schema.json` | Discovery root: modes, authority, independent durability properties, journal pin, idempotency windows |
| `task-definition.schema.json` | The immutable specification whose canonical digest is `task_spec_digest` |
| `task-submission.schema.json` | Authority, invocation key and derived identities around one definition |
| `transition.schema.json` | Payload of one single-revision durable-record/v1 record: state change plus attempt fact |
| `checkpoint.schema.json` | Journal cursor and verified state body pin as one payload |
| `supplied-slot.schema.json` | Caller-supplied slot, occurrence set or coverage, and catch-up link |
| `examples/` | One golden per object, plus a governed-acquisition composition |
| `rejects/schema/` | Baseline and reject pairs differing in exactly one field |
| `rejects/semantic/` | Vectors with a deliberately wrong expectation; the checker must detect each with its labeled reason |
| `vectors/<mode>/` | Behavioral vectors, by the lowest mode that must pass them; a mode's suite includes every lower mode |
| `vectors/INVENTORY.json` | Minimum inventory topic to covering vector ids |

`task-submission` embeds the task-definition schema under `$defs.taskDefinition`
so it validates standalone; the controls fail if the copy drifts. Run
`python3 scripts/test-durable-runner-controls.py`, also included in
`make check`. It validates every example, recomputes `task_id`,
`task_spec_digest` and `attempt_id` from RFC 8785 canonical bytes, and
asserts each reject pair differs in exactly one field.

## Vectors and the consistency model

A vector is an ordered script of ops against a runner, with expectations
authored by hand from the standard. Each op carries `expect`: `{"ok": {...}}`
(listed members must match; unlisted result members are not asserted) or
`{"refused": "<reason>"}` (an exact closed reason). A refused op changes no
state. A vector also states the final projection (`expected.tasks`: state and
attempts) and the exact committed history (`expected.history`: task, state and
attempt fact). Refusal vectors name the competing limits they checked cannot
fire, and each is paired with an acceptance twin that differs only in the
guarded condition.

`definitions` bind names to task definitions: each starts from the golden
acquisition definition and applies a flat map of dotted paths to values (`null`
deletes). The virtual clock starts at `requires_clock` and moves only with
`advance_clock`. `submit` binds a task label with `as`; slot and catch-up ops
bind labels with `as` or `labels` and pick a definition.

| Op | Result members | Refusals |
| --- | --- | --- |
| `profile_admit` | | `sealed_mode_reserved`, `mode_not_cumulative`, `remote_coverage_claimed`, `replication_claimed`, `journal_ack_insufficient`, `journal_contract_not_v1`, `authority_scope_unsupported`, `store_window_too_short`, `window_out_of_range` |
| `submit` | `disposition`, `task_id`, `state` | `identity_conflict`, `identity_unresolved`, `definition_invalid`, `unsupported_requirement`, `mode_unsupported` |
| `transition` | `revision`, `state` | `predecessor_mismatch`, `first_not_pending`, `illegal_transition`, `terminal_resurrection`, `attempt_not_contiguous`, `attempt_limit_exhausted`, `retry_not_permitted`, `unknown_outcome_code`, `outcome_mapping_mismatch`, `unknown_effects_not_retryable`, `success_unverified_outputs`, `cancellation_not_confirmed`, `cancellation_precedes_success`, `generation_stale`, `deadline_exceeded`, `horizon_exceeded`, `jitter_not_persisted` |
| `request_cancel`, `confirm_cancel` | `effect`, `state` | `task_terminal`, `quiescence_not_established`, `cancel_not_requested` |
| `advance_clock`, `parse_duration`, `parse_instant`, `format_instant` | `now`, `us`, `canonical` | `duration_invalid`, `syntax`, `overflow`, `fractional_loss`, `format`, `nonrepresentable` |
| `crash`, `recover`, `replay`, `checkpoint`, `reconcile`, `retire_output` | `task_states`, `heads`, `outcomes`, `effects_performed`, `status` | `mode_unsupported`, `predecessor_not_quiescent`, `body_unverified`, `body_after_record`, `cursor_not_in_chain`, `checkpoint_not_eligible`, `checkpoint_body_held`, `hold_active`, `retirement_refused` |
| `admission` | `reserved` | `rate_denied`, `shared_quota_needs_shared_authority`, `unsettled_reservation` |
| `supply_slot`, `evaluate_slots`, `catch_up` | `slot_id`, `eligible`, `missed`, `task_id` | `mode_unsupported`, `slot_identity_mismatch`, `slot_outside_window`, `dst_non_slot`, `coverage_not_supplied`, `lag_exceeded`, `catch_up_not_permitted`, `missed_not_terminal` |

`scripts/validate-durable-runner-vectors.py` executes each script against a
reference consistency model: an in-memory fold of the standard's rules under
the virtual clock. It requires every authored result, the final projection and
the exact history to match, so a fabricated receipt, an invented transition or
a missing guard is a mismatch. Every rule it enforces is a named guard, and
`--disable <guard>` removes one. `scripts/test-durable-runner-vector-controls.py`
(in `make check`) runs the suite, disables each guard in turn and requires a
checker verdict from at least one vector (a crash does not count), requires
each `rejects/semantic/` fixture to fail for its labeled reason with its
baseline passing, and checks the inventory.

**Assurance boundary.** The model is a checker for fixtures. It is not a
conformance oracle for an implementation, which is why the expected histories
are authored independently of it. Its time-zone table is limited to the one
zone the DST vectors use. The harness that runs these vectors against a real
runner lives in the adopting repository.

Fixture data is synthetic. Identifiers are public-safe tokens.
