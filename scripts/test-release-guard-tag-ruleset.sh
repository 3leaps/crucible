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

# Read-only mode: a bypass list the credential cannot see passes the visible
# fields but is reported as not checked, never as a match.
expect_read_only_report() {
    local description="$1" candidate="$2" checked="$3" report
    if ! validate_ruleset_json "${candidate}" read-only >/dev/null 2>&1; then
        echo "error: read-only mode refused: ${description}" >&2
        exit 1
    fi
    if [ "${RULESET_BYPASS_ACTORS_CHECKED}" != "${checked}" ]; then
        echo "error: read-only ${description}: bypass actors checked=${RULESET_BYPASS_ACTORS_CHECKED}, want ${checked}" >&2
        exit 1
    fi
    report="$(report_ruleset_validation read-only)"
    if [ "${checked}" = 1 ]; then
        grep -q 'matches the full publication policy, including visible bypass actors' <<<"${report}" || {
            echo "error: read-only ${description}: match not reported: ${report}" >&2
            exit 1
        }
    else
        if grep -qi 'match' <<<"${report}"; then
            echo "error: read-only ${description}: reported as a match: ${report}" >&2
            exit 1
        fi
        grep -q 'bypass actors were not visible to this credential and were not checked' <<<"${report}" || {
            echo "error: read-only ${description}: did not say bypass actors were not checked: ${report}" >&2
            exit 1
        }
    fi
    echo "[ok] read-only ${description}: reported as $([ "${checked}" = 1 ] && echo matched || echo 'not checked')"
}
null_bypass_ruleset="$(jq '.bypass_actors = null' <<<"${valid_ruleset}")"
expect_read_only_report "omitted bypass actors" "${redacted_ruleset}" 0
expect_read_only_report "null bypass actors" "${null_bypass_ruleset}" 0
expect_read_only_report "empty bypass actors" "${empty_bypass_ruleset}" 0
expect_read_only_report "exact visible bypass actors" "${valid_ruleset}" 1
expect_rejected_read_only "unexpected visible repository-role bypass" "${unexpected_visible_bypass}"
expect_rejected_read_only "visible admin bypass in pull-request mode" \
    "$(jq '.bypass_actors[0].bypass_mode = "pull_request"' <<<"${valid_ruleset}")"
expect_rejected_read_only "visible admin bypass plus another actor" \
    "$(jq '.bypass_actors += [{"actor_id":5,"actor_type":"RepositoryRole","bypass_mode":"always"}]' <<<"${valid_ruleset}")"
# A failed validation never leaves a stale match behind.
validate_ruleset_json "${valid_ruleset}" read-only >/dev/null
if validate_ruleset_json "$(jq '.enforcement = "disabled"' <<<"${valid_ruleset}")" read-only >/dev/null 2>&1 ||
    [ "${RULESET_BYPASS_ACTORS_CHECKED}" != 0 ]; then
    echo "error: a refused read-only response left bypass actors marked checked" >&2
    exit 1
fi
echo "[ok] read-only refusal clears the bypass-actors match"
expect_rejected "null bypass actors in full mode" "${null_bypass_ruleset}"

policy_attestation="$(expected_policy_attestation)"
expected_attestation="Tag-Publish-Policy-SHA256: e1bd867dd4958d7d412506a2f0f9964984a7e5127e776206e4136c57d8d1903d"
if [[ "${policy_attestation}" != "${expected_attestation}" ]]; then
    echo "error: canonical policy fingerprint changed unexpectedly" >&2
    exit 1
fi
# Require stable byte transport at the producer, not a host-specific hash pin.
binary_attestation="$(
    jq() {
        if [ "${1:-}" != -b ]; then
            echo 'error: canonical policy producer omitted jq binary mode' >&2
            return 2
        fi
        command jq "$@"
    }
    expected_policy_attestation
)"
if [[ "$binary_attestation" != "$expected_attestation" ]]; then
    echo 'error: binary-mode policy fingerprint control failed' >&2
    exit 1
fi
binary_ruleset="$(
    jq() {
        if [ "${1:-}" != -b ]; then
            echo 'error: ruleset ID producer omitted jq binary mode' >&2
            return 2
        fi
        command jq "$@"
    }
    gh() {
        case "${*: -1}" in
            'repos/3leaps/crucible/rulesets?per_page=100')
                printf '%s\n' '[[{"id":123,"name":"Tag Publish Protection"}]]'
                ;;
            repos/3leaps/crucible/rulesets/123) printf '%s\n' "$valid_ruleset" ;;
            *) return 2 ;;
        esac
    }
    resolve_live_ruleset
)"
if [[ "$binary_ruleset" != "$valid_ruleset" ]]; then
    echo 'error: binary-mode ruleset ID control failed' >&2
    exit 1
fi
# A failed GitHub read (for example an authentication error) must refuse as a
# read failure, never parse as an empty ruleset list.
expect_read_failure() {
    local description="$1" failing_call="$2" output
    if output="$(
        gh() {
            case "${*: -1}" in
                'repos/3leaps/crucible/rulesets?per_page=100')
                    [ "$failing_call" = list ] && {
                        echo 'gh: Bad credentials (HTTP 401)' >&2
                        return 1
                    }
                    printf '%s\n' '[[{"id":123,"name":"Tag Publish Protection"}]]'
                    ;;
                repos/3leaps/crucible/rulesets/123)
                    [ "$failing_call" = detail ] && {
                        echo 'gh: Bad credentials (HTTP 401)' >&2
                        return 1
                    }
                    printf '%s\n' "$valid_ruleset"
                    ;;
                *) return 2 ;;
            esac
        }
        resolve_live_ruleset 2>&1
    )"; then
        echo "error: ${description} was accepted" >&2
        exit 1
    fi
    if ! grep -q 'could not read .* from GitHub; the ruleset was not checked' <<<"$output"; then
        echo "error: ${description} refused for the wrong reason: ${output}" >&2
        exit 1
    fi
    if grep -q 'found 0' <<<"$output"; then
        echo "error: ${description} was reported as a missing ruleset" >&2
        exit 1
    fi
    echo "[ok] rejected: ${description}"
}
expect_read_failure "failed ruleset list read" list
expect_read_failure "failed ruleset detail read" detail

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
