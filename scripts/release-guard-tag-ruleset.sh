#!/usr/bin/env bash
# release-guard-tag-ruleset.sh - Verify the version-tag publication boundary

set -euo pipefail

readonly EXPECTED_REPOSITORY="3leaps/crucible"
readonly EXPECTED_RULESET_NAME="Tag Publish Protection"

require_command() {
    local command_name="$1"
    if ! command -v "${command_name}" >/dev/null 2>&1; then
        echo "error: ${command_name} not found in PATH" >&2
        exit 1
    fi
}

validate_ruleset_json() {
    local ruleset_json="${1:-}"
    local failed=0

    assert_shape() {
        local description="$1"
        local filter="$2"
        if ! jq -e "${filter}" >/dev/null 2>&1 <<<"${ruleset_json}"; then
            echo "error: tag ruleset ${description}" >&2
            failed=1
        fi
    }

    assert_shape "must be named '${EXPECTED_RULESET_NAME}'" \
        ".name == \"${EXPECTED_RULESET_NAME}\""
    assert_shape "must belong to repository '${EXPECTED_REPOSITORY}'" \
        ".source_type == \"Repository\" and .source == \"${EXPECTED_REPOSITORY}\""
    assert_shape "must target tags and be active" \
        '.target == "tag" and .enforcement == "active"'
    assert_shape "must include only refs/tags/v* with no exclusions" \
        '.conditions == {"ref_name":{"exclude":[],"include":["refs/tags/v*"]}}'
    assert_shape "must contain only creation, deletion, non-fast-forward, and update protections" \
        '(.rules | length) == 4 and
         ([.rules[].type] | sort) == ["creation","deletion","non_fast_forward","update"] and
         all(.rules[]; (keys | sort) == ["type"])'
    assert_shape "must allow only organization administrators to bypass, always" \
        '.bypass_actors == [{"actor_id":null,"actor_type":"OrganizationAdmin","bypass_mode":"always"}]'

    if [ "${failed}" -ne 0 ]; then
        return 1
    fi
}

main() {
    require_command gh
    require_command jq

    local ruleset_pages ruleset_ids ruleset_count ruleset_id ruleset_json
    ruleset_pages="$(gh api --paginate --slurp \
        "repos/${EXPECTED_REPOSITORY}/rulesets?per_page=100")"
    ruleset_ids="$(jq -r \
        --arg name "${EXPECTED_RULESET_NAME}" \
        'flatten | map(select(.name == $name)) | .[].id' \
        <<<"${ruleset_pages}")"
    ruleset_count="$(awk 'NF { count++ } END { print count + 0 }' <<<"${ruleset_ids}")"

    if [ "${ruleset_count}" -ne 1 ]; then
        echo "error: expected exactly one '${EXPECTED_RULESET_NAME}' ruleset; found ${ruleset_count}" >&2
        exit 1
    fi

    ruleset_id="$(awk 'NF { print; exit }' <<<"${ruleset_ids}")"
    ruleset_json="$(gh api "repos/${EXPECTED_REPOSITORY}/rulesets/${ruleset_id}")"

    validate_ruleset_json "${ruleset_json}"
    echo "[ok] tag ruleset: ${EXPECTED_RULESET_NAME} matches the publication policy"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
