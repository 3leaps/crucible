#!/usr/bin/env bash
# Negative controls for release-guard-tag-ruleset.sh.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The source path is resolved relative to this script at runtime.
# shellcheck disable=SC1091
source "${script_dir}/release-guard-tag-ruleset.sh"

valid_ruleset='{
  "name": "Tag Publish Protection",
  "target": "tag",
  "source_type": "Repository",
  "source": "3leaps/crucible",
  "enforcement": "active",
  "conditions": {"ref_name": {"exclude": [], "include": ["refs/tags/v*"]}},
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "creation"},
    {"type": "update"}
  ],
  "bypass_actors": [
    {"actor_id": null, "actor_type": "OrganizationAdmin", "bypass_mode": "always"}
  ]
}'

expect_rejected() {
    local description="$1"
    local candidate="$2"
    if validate_ruleset_json "${candidate}" >/dev/null 2>&1; then
        echo "error: negative control was accepted: ${description}" >&2
        exit 1
    fi
    echo "[ok] rejected: ${description}"
}

expect_rejected_read_only() {
    local description="$1"
    local candidate="$2"
    if validate_ruleset_json "${candidate}" read-only >/dev/null 2>&1; then
        echo "error: read-only negative control was accepted: ${description}" >&2
        exit 1
    fi
    echo "[ok] read-only rejected: ${description}"
}

validate_ruleset_json "${valid_ruleset}" full
echo "[ok] accepted: exact publication policy"

expect_rejected "repository-admin bypass" \
    "$(jq '.bypass_actors += [{"actor_id":5,"actor_type":"RepositoryRole","bypass_mode":"always"}]' <<<"${valid_ruleset}")"
expect_rejected "wrong tag-ref pattern" \
    "$(jq '.conditions.ref_name.include = ["refs/tags/*"]' <<<"${valid_ruleset}")"
expect_rejected "missing update protection" \
    "$(jq '.rules |= map(select(.type != "update"))' <<<"${valid_ruleset}")"
expect_rejected "additional required-status-check rule" \
    "$(jq '.rules += [{"type":"required_status_checks","parameters":{"required_status_checks":[]}}]' <<<"${valid_ruleset}")"
expect_rejected "inactive enforcement" \
    "$(jq '.enforcement = "disabled"' <<<"${valid_ruleset}")"
expect_rejected "missing API response" ""
expect_rejected "malformed API response" "not-json"

expect_rejected_read_only "wrong tag-ref pattern" \
    "$(jq '.conditions.ref_name.include = ["refs/tags/*"]' <<<"${valid_ruleset}")"
expect_rejected_read_only "missing update protection" \
    "$(jq '.rules |= map(select(.type != "update"))' <<<"${valid_ruleset}")"
expect_rejected_read_only "additional required-status-check rule" \
    "$(jq '.rules += [{"type":"required_status_checks","parameters":{"required_status_checks":[]}}]' <<<"${valid_ruleset}")"
expect_rejected_read_only "inactive enforcement" \
    "$(jq '.enforcement = "disabled"' <<<"${valid_ruleset}")"

redacted_ruleset="$(jq 'del(.bypass_actors)' <<<"${valid_ruleset}")"
empty_bypass_ruleset="$(jq '.bypass_actors = []' <<<"${valid_ruleset}")"
unexpected_visible_bypass="$(jq '.bypass_actors = [{"actor_id":5,"actor_type":"RepositoryRole","bypass_mode":"always"}]' <<<"${valid_ruleset}")"

expect_rejected "omitted bypass actors in full mode" "${redacted_ruleset}"
expect_rejected "empty bypass actors in full mode" "${empty_bypass_ruleset}"

validate_ruleset_json "${redacted_ruleset}" read-only
echo "[ok] read-only mode accepted: omitted bypass actors"
validate_ruleset_json "${empty_bypass_ruleset}" read-only
echo "[ok] read-only mode accepted: redacted empty bypass actors"
validate_ruleset_json "${valid_ruleset}" read-only
echo "[ok] read-only mode accepted: exact visible bypass actors"
expect_rejected_read_only "unexpected visible repository-role bypass" "${unexpected_visible_bypass}"

policy_attestation="$(expected_policy_attestation)"
expected_attestation="Tag-Publish-Policy-SHA256: e1bd867dd4958d7d412506a2f0f9964984a7e5127e776206e4136c57d8d1903d"
if [[ "${policy_attestation}" != "${expected_attestation}" ]]; then
    echo "error: canonical policy fingerprint changed unexpectedly" >&2
    exit 1
fi
if ! [[ "${policy_attestation}" =~ ^Tag-Publish-Policy-SHA256:\ [0-9a-f]{64}$ ]]; then
    echo "error: malformed expected policy attestation" >&2
    exit 1
fi
validate_policy_attestation_text "Release v0.1.21

${policy_attestation}"
echo "[ok] accepted: exact signed policy attestation text"
if validate_policy_attestation_text "Release v0.1.21"; then
    echo "error: missing policy attestation was accepted" >&2
    exit 1
fi
echo "[ok] rejected: missing policy attestation"
if validate_policy_attestation_text "Tag-Publish-Policy-SHA256: $(printf '0%.0s' {1..64})"; then
    echo "error: wrong policy attestation was accepted" >&2
    exit 1
fi
echo "[ok] rejected: wrong policy attestation"

echo "[ok] tag-ruleset guard negative controls passed"
