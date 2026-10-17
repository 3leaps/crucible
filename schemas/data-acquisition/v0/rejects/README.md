# data-acquisition/v0 — reject fixtures

These fixtures prove the gates can **fail** —
[EPR-0002](../../../../docs/decisions/EPR-0002-verification-gate-integrity.md)
obligation 3. `make check` runs
`scripts/test-data-acquisition-controls.py`, which asserts the rules below and
that this table, the fixtures and the standard's refusal-reason table agree.

## schema/

Each `reject-<object>--<name>.json` fails its object's schema and differs from a
passing example in exactly one field.

| Reject | Must fail because |
| --- | --- |
| `source-policy--inline-credential` | credential references carry no inline `value` |
| `source-policy--missing-paging` | a `paged_api` target declares paging |
| `source-policy--unknown-budget-algorithm` | v0 meters are `rolling_window` only |
| `source-policy--export-default` | redistribution default is always `block_export` |
| `source-policy--retry-after-ignored` | `honor_retry_after` is always true |
| `acquisition-plan--execution-claim` | plans carry `execution_authorization: none` |
| `acquisition-plan--missing-chosen-by` | a compromise names its chooser |
| `acquisition-plan--missing-declared-scope-limit` | a compromise declares its scope limit |
| `acquisition-plan--one-off-with-cadence` | a one-off plan declares no cadence |
| `registration-result--unavailable-allocation` | only `registered` carries an allocation |
| `registration-result--indeterminate-without-key` | `indeterminate` requires `reconcile_key` |
| `registration-result--registered-execution-claim` | even a registered result grants no execution |
| `acquisition-plan--scope-over-256-targets` | one plan scope selects at most 256 targets |

## semantic/

Each `reject-<reason>--<name>/` directory holds only the objects that differ from
the baseline (`examples/source-policy.json`, `examples/acquisition-plan.json`).
Every object is shape-valid and pins bind the exact fixture bytes, so the named
semantic rule, not a schema gate or a stale digest, is what refuses. The
checker must refuse with the reason before `--`; see the
[refusal reasons](../../../../docs/standards/data-acquisition-contract.md#refusal-reasons).

| Vector | Objects |
| --- | --- |
| `allocation_exceeds_policy--partial-window-over-ceiling` | registration-result |
| `allocation_exceeds_policy--requests-over-ceiling` | registration-result |
| `allocation_missing_meter--byte-meter-without-quantity` | acquisition-plan, registration-result, source-policy |
| `allocation_unconfigured_meter--byte-quantity-unconfigured` | registration-result |
| `burst_exceeds_window--burst-over-limit` | acquisition-plan, source-policy |
| `cadence_reaches_deletion--daily-cadence-daily-deletion` | acquisition-plan, source-policy |
| `choice_after_plan--chosen-after-created` | acquisition-plan |
| `compromise_required_or_spurious--changed-scope-without-choice` | acquisition-plan |
| `compromise_required_or_spurious--choice-without-change` | acquisition-plan |
| `duplicate_dimension--dimension-declared-twice` | acquisition-plan, source-policy |
| `duplicate_key--repeated-member` | acquisition-plan, source-policy |
| `duplicate_target--target-declared-twice` | acquisition-plan, source-policy |
| `invalid_allocation_window--allocation-window-empty` | registration-result |
| `invalid_allocation_window--opens-one-microsecond-before-start` | registration-result |
| `invalid_frequency_choice--cadence-increased-frequency` | acquisition-plan |
| `invalid_target_choice--fewer-targets-label-on-cadence` | acquisition-plan |
| `invalid_time--timestamp-variant-invalid` | acquisition-plan, source-policy |
| `invalid_time--timestamp-variant-space-separator` | acquisition-plan, source-policy |
| `invalid_time_scope_choice--time-scope-label-on-cadence` | acquisition-plan |
| `missing_variant--declared-dimension-omitted` | acquisition-plan, source-policy |
| `plan_time_order--created-after-start` | acquisition-plan |
| `plan_time_order--created-one-microsecond-after-start` | acquisition-plan |
| `policy_pin_mismatch--fabricated-policy-digest` | acquisition-plan |
| `registration_plan_binding--fabricated-plan-digest` | registration-result |
| `registration_policy_binding--source-differs` | registration-result |
| `registration_time_order--recorded-before-plan` | registration-result |
| `review_after_start--terms-reviewed-after-start` | acquisition-plan, source-policy |
| `scope_limit_mismatch--declared-cadence-differs` | acquisition-plan |
| `target_set_version--plan-names-other-version` | acquisition-plan |
| `terms_changed--current-digest-differs` | acquisition-plan, source-policy |
| `undeclared_target--effective-target-missing` | acquisition-plan |
| `unknown_variant--variant-dimension-undeclared` | acquisition-plan, source-policy |
| `unrepresentable_precision--created-after-start-submicrosecond` | acquisition-plan |
| `unreviewed_meter_absence--absent-meters-not-listed` | acquisition-plan, source-policy |
| `unsafe_target_url--plain-http` | acquisition-plan, source-policy |
| `unsafe_target_url--query-string-key` | acquisition-plan, source-policy |
| `unsupported_meter_basis--transfer-basis-unqualified` | acquisition-plan, source-policy |
| `utc_required--timestamp-variant-offset` | acquisition-plan, source-policy |
| `variant_outside_vocabulary--enum-value-undeclared` | acquisition-plan, source-policy |
| `zero_allocation--zero-requests` | registration-result |
| `zero_concurrency--concurrency-zero` | acquisition-plan, source-policy |
| `zero_meter--body-byte-limit-zero` | acquisition-plan, source-policy |
| `zero_meter--request-limit-zero` | acquisition-plan, source-policy |

## multiple/

Each `reject-<name>/` directory breaks more than one rule. The checker must refuse
it with one of the reasons in `applicable-reasons.json`; the vocabulary sets no
precedence between them.

| Vector | Applicable reasons |
| --- | --- |
| `created-after-start-and-variant-offset` | `plan_time_order`, `utc_required` |

Fixture data is synthetic. Identifiers are public-safe tokens.
