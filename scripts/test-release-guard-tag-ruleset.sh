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

validate_ruleset_json "${valid_ruleset}"
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

echo "[ok] tag-ruleset guard negative controls passed"
