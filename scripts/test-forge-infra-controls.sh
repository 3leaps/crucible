#!/bin/sh
# Structural and cross-document controls for contract: forge-infra/v0.
# Uses the repository RFC 8785 and RFC 3339 helpers for digest and instant
# comparisons; lexical JSON/timestamp ordering is not a security oracle.

set -eu

base="schemas/forge-infra/v0"
examples="$base/examples"
rejects="$base/rejects"
catalog="$base/forge-capability-catalog.json"
tmpd="$(mktemp -d)"
authority_index="$tmpd/authority-index.json"
trap 'rm -rf "$tmpd"' EXIT HUP INT TERM

jq -s '
  map({key: .authority_profile_id, value: .provider_context})
  | from_entries
' "$examples"/authority-profile.*.example.json >"$authority_index"

validate() {
    schema="$1"
    data="$2"
    goneat validate data \
        --schema-file "$base/$schema" \
        --ref-dir "$base" \
        --data "$data" >/dev/null
}

expect_rejected() {
    schema="$1"
    data="$2"
    if validate "$schema" "$data" 2>/dev/null; then
        echo "    [!!] forge-infra reject unexpectedly passed: $data" >&2
        exit 1
    fi
    echo "    [ok] rejected: $data"
}

redigest_plan() {
    source_plan="$1"
    output_plan="$2"
    updated_digest="$(jq -c .plan_spec "$source_plan" |
        python3 scripts/rfc8785-canonicalize.py |
        sha256sum |
        awk '{print "sha256:" $1}')"
    jq --arg digest "$updated_digest" \
        '.plan_spec_digest = $digest' \
        "$source_plan" >"$output_plan"
}

check_catalog() {
    data="$1"
    jq -e '
      .neutral_capabilities as $capabilities
      | [$capabilities[].capability_id] as $ids
      | (($ids | length) == ($ids | unique | length))
        and all(
          $capabilities[];
          . as $capability
          | (($capability.parent_id == null)
            or ($ids | index($capability.parent_id) != null))
        )
    ' "$data" >/dev/null
}

check_catalog_ref() {
    data="$1"
    jq -e --slurpfile catalog_data "$catalog" '
      .catalog_ref.catalog_id == $catalog_data[0].catalog_id
        and .catalog_ref.revision == $catalog_data[0].revision
    ' "$data" >/dev/null
}

check_authority_profile() {
    data="$1"
    jq -e '
      [.evidence[].evidence_id] as $evidence_ids
      | (($evidence_ids | length) == ($evidence_ids | unique | length))
        and all(
          .acquisition.evidence_refs[];
          . as $evidence_ref
          | ($evidence_ids | index($evidence_ref)) != null
        )
    ' "$data" >/dev/null
}

check_provider_profile() {
    data="$1"
    jq -e \
        --slurpfile catalog_data "$catalog" \
        --slurpfile authority_data "$authority_index" '
      . as $profile
      | ($catalog_data[0].neutral_capabilities
          | map({key: .capability_id, value: .operations})
          | from_entries) as $catalog
      | $authority_data[0] as $authorities
      | [.evidence[].evidence_id] as $evidence_ids
      | [
          .mappings[] as $mapping
          | $mapping.operation_cells[]
          | [
              $mapping.capability_id,
              .operation,
              .authority_profile_id
            ]
          | join("|")
        ] as $cell_keys
      | ($profile.catalog_ref.catalog_id == $catalog_data[0].catalog_id)
        and ($profile.catalog_ref.revision == $catalog_data[0].revision)
        and (($evidence_ids | length) == ($evidence_ids | unique | length))
        and (($cell_keys | length) == ($cell_keys | unique | length))
        and all(
          .mappings[];
          . as $mapping
          | ($catalog | has($mapping.capability_id))
            and all(
              $mapping.operation_cells[];
              . as $cell
              | (($catalog[$mapping.capability_id]
                    | index($cell.operation)) != null)
                and ($authorities | has($cell.authority_profile_id))
                and ($authorities[$cell.authority_profile_id]
                      == $profile.provider_context)
                and all(
                  $cell.evidence_refs[];
                  . as $evidence_ref
                  | (($evidence_ids | index($evidence_ref)) != null)
                )
                and (($cell.fallback_capability_id == null)
                  or ($catalog | has($cell.fallback_capability_id)))
            )
        )
    ' "$data" >/dev/null
}

check_requirement_profile() {
    data="$1"
    jq -e --slurpfile catalog_data "$catalog" '
      ($catalog_data[0].neutral_capabilities
        | map({key: .capability_id, value: .operations})
        | from_entries) as $catalog
      | (.catalog_ref.catalog_id == $catalog_data[0].catalog_id)
        and (.catalog_ref.revision == $catalog_data[0].revision)
        and all(
          .requirements[];
          . as $requirement
          | ($catalog | has($requirement.capability_id))
            and all(
              $requirement.operations[];
              . as $operation
              | (($catalog[$requirement.capability_id]
                  | index($operation)) != null)
            )
        )
    ' "$data" >/dev/null
}

check_capability_ref() {
    data="$1"
    jq -e --slurpfile catalog_data "$catalog" '
      . as $reference
      | ($catalog_data[0].neutral_capabilities
        | map(.capability_id)) as $capability_ids
      | ($reference.catalog_ref.catalog_id == $catalog_data[0].catalog_id)
        and ($reference.catalog_ref.revision == $catalog_data[0].revision)
        and (($capability_ids | index($reference.capability_id)) != null)
    ' "$data" >/dev/null
}

check_binding_plan() {
    data="$1"
    requirement="$2"
    provider="$3"
    requirement_digest="$(jq -c . "$requirement" |
        python3 scripts/rfc8785-canonicalize.py |
        sha256sum |
        awk '{print "sha256:" $1}')"
    plan_digest="$(jq -c .plan_spec "$data" |
        python3 scripts/rfc8785-canonicalize.py |
        sha256sum |
        awk '{print "sha256:" $1}')"
    jq -e \
        --arg requirement_digest "$requirement_digest" \
        --arg plan_digest "$plan_digest" \
        --slurpfile catalog_data "$catalog" \
        --slurpfile requirement_data "$requirement" \
        --slurpfile provider_data "$provider" \
        --slurpfile authority_data "$authority_index" '
      . as $plan
      | $requirement_data[0] as $requirement
      | $provider_data[0] as $provider
      | $authority_data[0] as $authorities
      | ([
          $provider.mappings[] as $mapping
          | $mapping.operation_cells[]
          | {
              key: ([$mapping.capability_id, .operation, .authority_profile_id]
                | join("|")),
              value: .
            }
        ] | from_entries) as $provider_cells
      | ([
          $requirement.requirements[] as $requirement_row
          | $requirement_row.operations[]
          | {
              key: ([$requirement_row.capability_id, .] | join("|")),
              value: $requirement_row.disposition
            }
        ] | from_entries) as $requirement_cells
      | [
          $plan.plan_spec.resolutions[]
          | [.capability_id, .operation]
          | join("|")
        ] as $resolution_keys
      | [
          $plan.plan_spec.gaps[]
          | [.capability_id, .operation]
          | join("|")
        ] as $gap_keys
      | ([
          $plan.plan_spec.resolutions[]
          | select(.resolution == "satisfied" or .resolution == "partial")
          | select(.disposition != "forbidden")
          | {
              capability_id,
              operation,
              authority_profile_id,
              required_grants: (.required_grants
                | sort_by([.kind, .name, .access, .resource_scope]))
            }
        ] | sort_by([.capability_id, .operation, .authority_profile_id]))
          as $resolved_policy_operations
      | ([
          $plan.plan_spec.authority_actions[]
          | del(.notes)
        ] | sort_by(.seq)) as $planned_policy_actions
      | def transition_for($action):
          {
            register: "registered",
            install: "installed",
            consent: "consented",
            provision: "provisioned",
            bind: "bound",
            rotate: "rotated",
            reconcile: "reconciled",
            revoke: "revoked",
            teardown: "torn_down"
          }[$action];
      ($plan.catalog_ref.catalog_id == $catalog_data[0].catalog_id)
        and ($plan.catalog_ref.revision == $catalog_data[0].revision)
        and ($plan.requirement_profile_ref.requirement_profile_id
          == $requirement.requirement_profile_id)
        and ($plan.requirement_profile_ref.digest == $requirement_digest)
        and ($plan.provider_profile_ref.provider_profile_id
          == $provider.provider_profile_id)
        and ($plan.provider_profile_ref.revision == $provider.revision)
        and ($plan.provider_context == $provider.provider_context)
        and ($plan.plan_spec_digest == $plan_digest)
        and (([$plan.plan_spec.authority_actions[].seq] | sort)
          == [range(1; ($plan.plan_spec.authority_actions | length) + 1)])
        and all(
          $plan.plan_spec.resolutions[];
          . as $resolution
          | ([$resolution.capability_id, $resolution.operation]
              | join("|")) as $requirement_key
          | ([$resolution.capability_id, $resolution.operation,
              $resolution.authority_profile_id] | join("|")) as $provider_key
          | ($requirement_cells | has($requirement_key))
            and ($requirement_cells[$requirement_key]
              == $resolution.disposition)
            and ($authorities | has($resolution.authority_profile_id))
            and ($authorities[$resolution.authority_profile_id]
              == $plan.provider_context)
            and ($provider_cells | has($provider_key))
            and ($provider_cells[$provider_key].required_grants
              == $resolution.required_grants)
            and (if $resolution.disposition == "forbidden"
              then $resolution.resolution == "unsatisfied"
              elif $resolution.resolution == "satisfied"
              then $provider_cells[$provider_key].availability == "supported"
              elif $resolution.resolution == "partial"
              then ($provider_cells[$provider_key].availability == "partial"
                or $provider_cells[$provider_key].availability == "emulated")
              elif $resolution.resolution == "unsatisfied"
              then $provider_cells[$provider_key].availability == "unsupported"
              else $provider_cells[$provider_key].availability == "unknown"
              end)
        )
        and all(
          $requirement_cells | to_entries[]
            | select(.value == "required");
          .key as $required_key
          | (($resolution_keys | index($required_key)) != null)
            or (($gap_keys | index($required_key)) != null)
        )
        and all(
          $plan.plan_spec.authority_actions[];
          . as $action
          | ($authorities | has($action.authority_profile_id))
            and (if $action.action == "verify"
              then $action.produces_transition == null
              else $action.produces_transition
                == transition_for($action.action)
              end)
        )
        and ($plan.plan_spec.policy_input.target == $plan.target)
        and (($plan.plan_spec.policy_input.requested_operations
            | map(.required_grants |=
                sort_by([.kind, .name, .access, .resource_scope]))
            | sort_by([.capability_id, .operation, .authority_profile_id]))
          == $resolved_policy_operations)
        and (($plan.plan_spec.policy_input.authority_actions | sort_by(.seq))
          == $planned_policy_actions)
    ' "$data" >/dev/null
}

check_binding_receipt_set() {
    plan="$1"
    shift
    jq -s -e \
        --slurpfile authority_data "$authority_index" \
        --slurpfile plan_data "$plan" '
      . as $receipts
      | $authority_data[0] as $authorities
      | $plan_data[0] as $plan
      | ($receipts
          | map({key: .binding_receipt_id, value: .})
          | from_entries) as $receipt_index
      | ($plan.plan_spec.authority_actions
          | map({key: (.seq | tostring), value: .})
          | from_entries) as $actions
      | (($receipts | map(.binding_receipt_id) | length)
          == ($receipts | map(.binding_receipt_id) | unique | length))
        and (($receipts | map(.idempotency_key) | length)
          == ($receipts | map(.idempotency_key) | unique | length))
        and all(
          $receipts[];
          . as $receipt
          | ([
              $plan.plan_spec.authority_actions[]
              | select(.produces_transition != null)
              | select(.seq < $receipt.binding_plan_action_seq)
              | .seq
            ] | max) as $expected_previous_action_seq
          | ($receipt.binding_plan_ref.binding_plan_id
              == $plan.binding_plan_id)
            and ($receipt.binding_plan_ref.plan_spec_digest
              == $plan.plan_spec_digest)
            and ($actions | has($receipt.binding_plan_action_seq | tostring))
            and ($actions[$receipt.binding_plan_action_seq | tostring]
              .produces_transition == $receipt.transition)
            and ($actions[$receipt.binding_plan_action_seq | tostring]
              .authority_profile_id == $receipt.authority_profile_id)
            and ($authorities | has($receipt.authority_profile_id))
            and ($authorities[$receipt.authority_profile_id]
              == $receipt.provider_context)
            and ($receipt.target == $plan.target)
            and (if $receipt.binding_plan_action_seq == 1
              then ($receipt.history_basis == "imported")
                or ($receipt.previous_receipt_ref == null)
              else
                ($receipt.previous_receipt_ref != null)
                and ($receipt_index
                  | has($receipt.previous_receipt_ref))
                and ($receipt_index[$receipt.previous_receipt_ref].outcome
                  == "succeeded")
                and ($receipt_index[$receipt.previous_receipt_ref]
                  .binding_plan_action_seq
                    == $expected_previous_action_seq)
                and ($receipt_index[$receipt.previous_receipt_ref]
                  .binding_plan_ref == $receipt.binding_plan_ref)
                and ($receipt_index[$receipt.previous_receipt_ref]
                  .provider_context == $receipt.provider_context)
                and ($receipt_index[$receipt.previous_receipt_ref]
                  .authority_profile_id == $receipt.authority_profile_id)
                and ($receipt_index[$receipt.previous_receipt_ref]
                  .target == $receipt.target)
              end)
        )
    ' "$@" >/dev/null
}

check_verification_receipt() {
    data="$1"
    binding="$2"
    plan="$3"
    verified_at="$(jq -r '.verified_at' "$data")"
    valid_until="$(jq -r '.valid_until' "$data")"
    instant_order="$(python3 scripts/rfc3339-instant.py \
        --compare "$verified_at" "$valid_until")" || return 1
    [ "$instant_order" = "-1" ] || return 1
    jq -e \
        --slurpfile binding_data "$binding" \
        --slurpfile plan_data "$plan" \
        --slurpfile catalog_data "$catalog" '
      . as $verification
      | $binding_data[0] as $binding
      | $plan_data[0] as $plan
      | ($plan.plan_spec.authority_actions
          | map({key: (.seq | tostring), value: .})
          | from_entries) as $actions
      | ($plan.plan_spec.resolutions
          | map(select(.resolution == "satisfied" or .resolution == "partial"))
          | map(.required_grants[])
          | unique
          | sort_by([.kind, .name, .access, .resource_scope])) as $planned_grants
      | ($plan.plan_spec.resolutions
          | map(select(.resolution == "satisfied" or .resolution == "partial"))
          | map([.capability_id, .operation] | join("|"))
          | unique) as $planned_checks
      | ($verification.capability_checks
          | map([.capability_id, .operation] | join("|"))) as $observed_checks
      | ($verification.binding_receipt_ref == $binding.binding_receipt_id)
        and ($verification.binding_plan_ref.binding_plan_id
          == $plan.binding_plan_id)
        and ($verification.binding_plan_ref.plan_spec_digest
          == $plan.plan_spec_digest)
        and ($verification.binding_plan_ref == $binding.binding_plan_ref)
        and ($actions | has($verification.binding_plan_action_seq | tostring))
        and ($actions[$verification.binding_plan_action_seq | tostring]
          .action == "verify")
        and ($actions[$verification.binding_plan_action_seq | tostring]
          .authority_profile_id == $verification.authority_profile_id)
        and ($verification.catalog_ref.catalog_id
          == $catalog_data[0].catalog_id)
        and ($verification.catalog_ref.revision
          == $catalog_data[0].revision)
        and ($verification.provider_context == $binding.provider_context)
        and ($verification.authority_profile_id
          == $binding.authority_profile_id)
        and ($verification.target == $binding.target)
        and (($verification.expected_grants
          | sort_by([.kind, .name, .access, .resource_scope]))
            == $planned_grants)
        and (($binding.grants
          | sort_by([.kind, .name, .access, .resource_scope]))
            == $planned_grants)
        and (($observed_checks | length)
          == ($observed_checks | unique | length))
        and all(
          $observed_checks[];
          . as $observed_check
          | ($planned_checks | index($observed_check)) != null
        )
        and all(
          $plan.plan_spec.resolutions[]
            | select(.disposition == "required"
                and .resolution == "satisfied");
          ([.capability_id, .operation] | join("|")) as $required_check
          | ($observed_checks | index($required_check)) != null
        )
        and (if $verification.outcome == "conformant"
          then ($binding.outcome == "succeeded")
            and ($binding.transition == "bound"
              or $binding.transition == "rotated"
              or $binding.transition == "reconciled")
            and (($verification.observed_grants
              | sort_by([.kind, .name, .access, .resource_scope]))
                == $planned_grants)
            and ($verification.missing_grants | length) == 0
            and ($verification.unexpected_grants | length) == 0
            and all($verification.capability_checks[];
              .result == "allowed")
          elif $verification.outcome == "drift"
          then (($verification.missing_grants | length) > 0)
            or (($verification.unexpected_grants | length) > 0)
            or any($verification.capability_checks[];
              .result == "denied" or .result == "unknown")
          else true
          end)
    ' "$data" >/dev/null
}

echo "    Forge-infra positive examples..."
validate capability-catalog.schema.json \
    "$catalog"
validate authority-profile.schema.json \
    "$examples/authority-profile.github-app-installation.example.json"
validate authority-profile.schema.json \
    "$examples/authority-profile.github-pat.example.json"
validate provider-profile.schema.json \
    "$examples/provider-profile.github.example.json"
validate binding-plan.schema.json \
    "$examples/binding-plan.github-installation.example.json"
validate binding-receipt.schema.json \
    "$examples/binding-receipt.github-installation-installed.example.json"
validate binding-receipt.schema.json \
    "$examples/binding-receipt.github-installation.example.json"
validate verification-receipt.schema.json \
    "$examples/verification-receipt.github-installation.example.json"
validate forge-object-ref.schema.json \
    "$examples/forge-object-ref.issue.example.json"
validate requirement-profile.schema.json \
    "$examples/requirement-profile.agent-memory.example.json"

echo "    Forge-infra structural rejects..."
expect_rejected authority-profile.schema.json \
    "$rejects/authority-profile.handoff-without-uri.json"
expect_rejected binding-receipt.schema.json \
    "$rejects/binding-receipt.secret-field.json"
expect_rejected forge-object-ref.schema.json \
    "$rejects/forge-object-ref.missing-provider.json"
expect_rejected provider-profile.schema.json \
    "$rejects/provider-profile.supported-without-mode.json"
jq '.missing_grants = [.expected_grants[0]]' \
    "$examples/verification-receipt.github-installation.example.json" \
    >"$tmpd/conformant-with-missing-grant.json"
expect_rejected verification-receipt.schema.json \
    "$tmpd/conformant-with-missing-grant.json"
jq '.outcome = "drift"' \
    "$examples/verification-receipt.github-installation.example.json" \
    >"$tmpd/drift-without-delta.json"
expect_rejected verification-receipt.schema.json \
    "$tmpd/drift-without-delta.json"

echo "    Forge-infra cross-document controls..."
check_catalog "$catalog"
check_authority_profile \
    "$examples/authority-profile.github-app-installation.example.json"
check_authority_profile \
    "$examples/authority-profile.github-pat.example.json"
check_provider_profile "$examples/provider-profile.github.example.json"
check_requirement_profile \
    "$examples/requirement-profile.agent-memory.example.json"
check_capability_ref "$examples/forge-object-ref.issue.example.json"
check_binding_plan \
    "$examples/binding-plan.github-installation.example.json" \
    "$examples/requirement-profile.agent-memory.example.json" \
    "$examples/provider-profile.github.example.json"

jq '.plan_spec.policy_input.target.structure_ref = "other/repository"' \
    "$examples/binding-plan.github-installation.example.json" \
    >"$tmpd/policy-target-mismatch.raw.json"
redigest_plan \
    "$tmpd/policy-target-mismatch.raw.json" \
    "$tmpd/policy-target-mismatch.json"
validate binding-plan.schema.json "$tmpd/policy-target-mismatch.json"
if check_binding_plan \
    "$tmpd/policy-target-mismatch.json" \
    "$examples/requirement-profile.agent-memory.example.json" \
    "$examples/provider-profile.github.example.json"; then
    echo "    [!!] policy target diverged from execution target" >&2
    exit 1
fi
echo "    [ok] rejected policy/execution target mismatch"

jq '.plan_spec.policy_input.requested_operations[0].operation = "delete"' \
    "$examples/binding-plan.github-installation.example.json" \
    >"$tmpd/policy-operation-mismatch.raw.json"
redigest_plan \
    "$tmpd/policy-operation-mismatch.raw.json" \
    "$tmpd/policy-operation-mismatch.json"
validate binding-plan.schema.json "$tmpd/policy-operation-mismatch.json"
if check_binding_plan \
    "$tmpd/policy-operation-mismatch.json" \
    "$examples/requirement-profile.agent-memory.example.json" \
    "$examples/provider-profile.github.example.json"; then
    echo "    [!!] policy operation diverged from resolved set" >&2
    exit 1
fi
echo "    [ok] rejected policy/resolution operation mismatch"

jq '.plan_spec.policy_input.requested_operations[0].required_grants[0].access = "admin"' \
    "$examples/binding-plan.github-installation.example.json" \
    >"$tmpd/policy-grant-escalation.raw.json"
redigest_plan \
    "$tmpd/policy-grant-escalation.raw.json" \
    "$tmpd/policy-grant-escalation.json"
validate binding-plan.schema.json "$tmpd/policy-grant-escalation.json"
if check_binding_plan \
    "$tmpd/policy-grant-escalation.json" \
    "$examples/requirement-profile.agent-memory.example.json" \
    "$examples/provider-profile.github.example.json"; then
    echo "    [!!] policy grant exceeded resolved provider grants" >&2
    exit 1
fi
echo "    [ok] rejected policy/provider grant escalation"

jq '.plan_spec.policy_input.authority_actions[1].action = "revoke"' \
    "$examples/binding-plan.github-installation.example.json" \
    >"$tmpd/policy-action-mismatch.raw.json"
redigest_plan \
    "$tmpd/policy-action-mismatch.raw.json" \
    "$tmpd/policy-action-mismatch.json"
validate binding-plan.schema.json "$tmpd/policy-action-mismatch.json"
if check_binding_plan \
    "$tmpd/policy-action-mismatch.json" \
    "$examples/requirement-profile.agent-memory.example.json" \
    "$examples/provider-profile.github.example.json"; then
    echo "    [!!] policy action diverged from planned authority action" >&2
    exit 1
fi
echo "    [ok] rejected policy/authority action mismatch"

check_binding_receipt_set \
    "$examples/binding-plan.github-installation.example.json" \
    "$examples/binding-receipt.github-installation-installed.example.json" \
    "$examples/binding-receipt.github-installation.example.json"
check_verification_receipt \
    "$examples/verification-receipt.github-installation.example.json" \
    "$examples/binding-receipt.github-installation.example.json" \
    "$examples/binding-plan.github-installation.example.json"

for unusable_outcome in failed partial unknown; do
    jq --arg outcome "$unusable_outcome" \
        '.outcome = $outcome' \
        "$examples/binding-receipt.github-installation.example.json" \
        >"$tmpd/unusable-binding-$unusable_outcome.json"
    validate binding-receipt.schema.json \
        "$tmpd/unusable-binding-$unusable_outcome.json"
    if check_verification_receipt \
        "$examples/verification-receipt.github-installation.example.json" \
        "$tmpd/unusable-binding-$unusable_outcome.json" \
        "$examples/binding-plan.github-installation.example.json"; then
        echo "    [!!] conformant verification accepted $unusable_outcome binding" >&2
        exit 1
    fi
    echo "    [ok] rejected conformant verification of $unusable_outcome binding"
done

jq '.binding_receipt_ref = "example-github-installation-installed"' \
    "$examples/verification-receipt.github-installation.example.json" \
    >"$tmpd/pre-bind-verification.json"
validate verification-receipt.schema.json "$tmpd/pre-bind-verification.json"
if check_verification_receipt \
    "$tmpd/pre-bind-verification.json" \
    "$examples/binding-receipt.github-installation-installed.example.json" \
    "$examples/binding-plan.github-installation.example.json"; then
    echo "    [!!] conformant verification accepted pre-bind receipt" >&2
    exit 1
fi
echo "    [ok] rejected conformant verification of pre-bind receipt"

jq '
  .verified_at = "2026-08-27T02:00:00-04:00"
  | .valid_until = "2026-08-27T03:00:00Z"
' "$examples/verification-receipt.github-installation.example.json" \
    >"$tmpd/reversed-offset-instants.json"
validate verification-receipt.schema.json "$tmpd/reversed-offset-instants.json"
if check_verification_receipt \
    "$tmpd/reversed-offset-instants.json" \
    "$examples/binding-receipt.github-installation.example.json" \
    "$examples/binding-plan.github-installation.example.json"; then
    echo "    [!!] verification accepted reversed RFC3339 instants" >&2
    exit 1
fi
echo "    [ok] rejected reversed mixed-offset validity interval"

jq '.outcome = "failed"' \
    "$examples/binding-receipt.github-installation-installed.example.json" \
    >"$tmpd/failed-predecessor.json"
if check_binding_receipt_set \
    "$examples/binding-plan.github-installation.example.json" \
    "$tmpd/failed-predecessor.json" \
    "$examples/binding-receipt.github-installation.example.json"; then
    echo "    [!!] receipt advanced a failed predecessor" >&2
    exit 1
fi
echo "    [ok] rejected advancement from failed predecessor"

jq '.transition = "installed"' \
    "$examples/binding-receipt.github-installation.example.json" \
    >"$tmpd/action-transition-mismatch.json"
if check_binding_receipt_set \
    "$examples/binding-plan.github-installation.example.json" \
    "$examples/binding-receipt.github-installation-installed.example.json" \
    "$tmpd/action-transition-mismatch.json"; then
    echo "    [!!] receipt transition did not match planned action" >&2
    exit 1
fi
echo "    [ok] rejected action/transition mismatch"

jq '
  .plan_spec.authority_actions += [{
    "seq": 4,
    "action": "rotate",
    "produces_transition": "rotated",
    "authority_profile_id": "github-app-installation",
    "execution_mode": "service_job",
    "service_offer_ref": "forge-authority-rotation/v0"
  }]
  | .plan_spec.policy_input.authority_actions += [{
    "seq": 4,
    "action": "rotate",
    "produces_transition": "rotated",
    "authority_profile_id": "github-app-installation",
    "execution_mode": "service_job",
    "service_offer_ref": "forge-authority-rotation/v0"
  }]
' "$examples/binding-plan.github-installation.example.json" \
    >"$tmpd/extended-chain-plan.raw.json"
redigest_plan \
    "$tmpd/extended-chain-plan.raw.json" \
    "$tmpd/extended-chain-plan.json"
validate binding-plan.schema.json "$tmpd/extended-chain-plan.json"
check_binding_plan \
    "$tmpd/extended-chain-plan.json" \
    "$examples/requirement-profile.agent-memory.example.json" \
    "$examples/provider-profile.github.example.json"
extended_chain_digest="$(jq -r '.plan_spec_digest' \
    "$tmpd/extended-chain-plan.json")"
jq --arg digest "$extended_chain_digest" \
    '.binding_plan_ref.plan_spec_digest = $digest' \
    "$examples/binding-receipt.github-installation-installed.example.json" \
    >"$tmpd/extended-installed.json"
jq --arg digest "$extended_chain_digest" \
    '.binding_plan_ref.plan_spec_digest = $digest | .outcome = "failed"' \
    "$examples/binding-receipt.github-installation.example.json" \
    >"$tmpd/extended-bound.json"
jq --arg digest "$extended_chain_digest" '
  .binding_receipt_id = "example-github-installation-rotated"
  | .binding_plan_ref.plan_spec_digest = $digest
  | .binding_plan_action_seq = 4
  | .previous_receipt_ref = "example-github-installation-installed"
  | .idempotency_key = "github-installation-example-rotate-1"
  | .transition = "rotated"
  | .occurred_at = "2026-08-27T01:32:00Z"
' "$examples/binding-receipt.github-installation.example.json" \
    >"$tmpd/bypass-failed-intermediate.json"
validate binding-receipt.schema.json "$tmpd/extended-installed.json"
validate binding-receipt.schema.json "$tmpd/extended-bound.json"
validate binding-receipt.schema.json "$tmpd/bypass-failed-intermediate.json"
if check_binding_receipt_set \
    "$tmpd/extended-chain-plan.json" \
    "$tmpd/extended-installed.json" \
    "$tmpd/extended-bound.json" \
    "$tmpd/bypass-failed-intermediate.json"; then
    echo "    [!!] receipt skipped the immediate prior transition" >&2
    exit 1
fi
echo "    [ok] rejected skipped intermediate transition"

jq '.plan_spec.authority_actions[2].seq = 4' \
    "$examples/binding-plan.github-installation.example.json" \
    >"$tmpd/noncontiguous-plan.raw.json"
noncontiguous_digest="$(jq -c .plan_spec "$tmpd/noncontiguous-plan.raw.json" |
    python3 scripts/rfc8785-canonicalize.py |
    sha256sum |
    awk '{print "sha256:" $1}')"
jq --arg digest "$noncontiguous_digest" \
    '.plan_spec_digest = $digest' \
    "$tmpd/noncontiguous-plan.raw.json" \
    >"$tmpd/noncontiguous-plan.json"
if check_binding_plan \
    "$tmpd/noncontiguous-plan.json" \
    "$examples/requirement-profile.agent-memory.example.json" \
    "$examples/provider-profile.github.example.json"; then
    echo "    [!!] noncontiguous binding-plan actions passed" >&2
    exit 1
fi
echo "    [ok] rejected noncontiguous binding-plan actions"

jq '.expected_grants = [] | .observed_grants = []' \
    "$examples/verification-receipt.github-installation.example.json" \
    >"$tmpd/verification-plan-grant-mismatch.json"
validate verification-receipt.schema.json \
    "$tmpd/verification-plan-grant-mismatch.json"
if check_verification_receipt \
    "$tmpd/verification-plan-grant-mismatch.json" \
    "$examples/binding-receipt.github-installation.example.json" \
    "$examples/binding-plan.github-installation.example.json"; then
    echo "    [!!] verification grants diverged from the plan" >&2
    exit 1
fi
echo "    [ok] rejected verification/plan grant mismatch"

validate provider-profile.schema.json \
    "$rejects/provider-profile.unknown-capability.semantic.json"
if check_provider_profile \
    "$rejects/provider-profile.unknown-capability.semantic.json"; then
    echo "    [!!] unknown provider capability unexpectedly passed" >&2
    exit 1
fi
echo "    [ok] rejected unknown provider capability"

validate requirement-profile.schema.json \
    "$rejects/requirement-profile.unknown-operation.semantic.json"
if check_requirement_profile \
    "$rejects/requirement-profile.unknown-operation.semantic.json"; then
    echo "    [!!] unknown requirement operation unexpectedly passed" >&2
    exit 1
fi
echo "    [ok] rejected unknown requirement operation"

echo "    [ok] forge-infra controls passed"
