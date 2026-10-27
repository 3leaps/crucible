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

expected_policy_json() {
    # The pinned fingerprint includes an LF terminator on every platform.
    jq -b -cnS \
        --arg repository "${EXPECTED_REPOSITORY}" \
        --arg ruleset_name "${EXPECTED_RULESET_NAME}" \
        '{
            repository: $repository,
            ruleset_name: $ruleset_name,
            source_type: "Repository",
            target: "tag",
            enforcement: "active",
            conditions: {ref_name: {exclude: [], include: ["refs/tags/v*"]}},
            rules: ["creation", "deletion", "non_fast_forward", "update"],
            bypass_actors: [{actor_id: null, actor_type: "OrganizationAdmin", bypass_mode: "always"}]
        }'
}

expected_policy_digest() {
    if command -v sha256sum >/dev/null 2>&1; then
        expected_policy_json | sha256sum | awk '{print $1}'
        return 0
    fi
    if command -v shasum >/dev/null 2>&1; then
        expected_policy_json | shasum -a 256 | awk '{print $1}'
        return 0
    fi
    echo "error: sha256sum or shasum is required for policy attestation" >&2
    return 1
}

expected_policy_attestation() {
    printf 'Tag-Publish-Policy-SHA256: %s\n' "$(expected_policy_digest)"
}

validate_policy_attestation_text() {
    local tag_text="${1:-}"
    local expected_attestation
    expected_attestation="$(expected_policy_attestation)"
    grep -qxF "${expected_attestation}" <<<"${tag_text}"
}

validate_ruleset_json() {
    local ruleset_json="${1:-}"
    local validation_mode="${2:-full}"
    local failed=0
    local expected_bypass_filter='.bypass_actors == [{"actor_id":null,"actor_type":"OrganizationAdmin","bypass_mode":"always"}]'

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
    # Set only when the exact expected bypass list was seen. A read-only
    # response with a null or empty list is not a match: it says nothing
    # about who may bypass.
    RULESET_BYPASS_ACTORS_CHECKED=0
    case "${validation_mode}" in
        full)
            assert_shape "must allow only organization administrators to bypass, always" \
                "${expected_bypass_filter}"
            ;;
        read-only)
            # A read-only credential may see no bypass actors. A list that is
            # visible must still be exactly the expected one.
            assert_shape "contains unexpected visible bypass actors" \
                "(.bypass_actors == null) or (.bypass_actors == []) or (${expected_bypass_filter})"
            ;;
        *)
            echo "error: unknown validation mode: ${validation_mode}" >&2
            return 1
            ;;
    esac
    if [ "${failed}" -eq 0 ] && jq -e "${expected_bypass_filter}" >/dev/null 2>&1 <<<"${ruleset_json}"; then
        RULESET_BYPASS_ACTORS_CHECKED=1
    fi

    if [ "${failed}" -ne 0 ]; then
        return 1
    fi
}

# Report what validate_ruleset_json established. Only a visible, exact bypass
# list is reported as a match in read-only mode.
report_ruleset_validation() {
    local validation_mode="$1"
    if [ "${validation_mode}" = "full" ]; then
        echo "[ok] tag ruleset: ${EXPECTED_RULESET_NAME} matches the full publication policy"
    elif [ "${RULESET_BYPASS_ACTORS_CHECKED}" = 1 ]; then
        echo "[ok] tag ruleset: ${EXPECTED_RULESET_NAME} matches the full publication policy, including visible bypass actors"
    else
        echo "[ok] tag ruleset: ${EXPECTED_RULESET_NAME} name, repository, target, enforcement, ref conditions and rules are as expected"
        echo "[--] bypass actors were not visible to this credential and were not checked"
        echo "[--] the full policy, including bypass actors, is checked before tagging and carried by the signed tag attestation"
    fi
}

# Report a failed GitHub API read as a read failure. Without this, an
# authentication error yields empty output that parses as zero rulesets.
github_read_failed() {
    local what="$1"
    echo "error: could not read ${what} from GitHub; the ruleset was not checked" >&2
    echo "hint: this is usually an expired, revoked or under-scoped credential" >&2
    echo "hint: gh uses GH_TOKEN or GITHUB_TOKEN when set, otherwise its stored login;" >&2
    echo "hint: run 'gh auth status' with the same environment to see which one" >&2
    exit 1
}

resolve_live_ruleset() {
    require_command gh
    require_command jq

    local ruleset_pages ruleset_ids ruleset_count ruleset_id ruleset_json
    ruleset_pages="$(gh api --paginate --slurp \
        "repos/${EXPECTED_REPOSITORY}/rulesets?per_page=100")" ||
        github_read_failed "the ${EXPECTED_REPOSITORY} ruleset list"
    ruleset_ids="$(jq -b -r \
        --arg name "${EXPECTED_RULESET_NAME}" \
        'flatten | map(select(.name == $name)) | .[].id' \
        <<<"${ruleset_pages}")"
    ruleset_count="$(awk 'NF { count++ } END { print count + 0 }' <<<"${ruleset_ids}")"

    if [ "${ruleset_count}" -ne 1 ]; then
        echo "error: expected exactly one '${EXPECTED_RULESET_NAME}' ruleset; found ${ruleset_count}" >&2
        exit 1
    fi

    ruleset_id="$(awk 'NF { print; exit }' <<<"${ruleset_ids}")"
    ruleset_json="$(gh api "repos/${EXPECTED_REPOSITORY}/rulesets/${ruleset_id}")" ||
        github_read_failed "ruleset ${ruleset_id}"

    printf '%s\n' "${ruleset_json}"
}

main() {
    local action="validate"
    local validation_mode="full"
    local tag_object=""

    while [ "$#" -gt 0 ]; do
        case "$1" in
            --read-only)
                validation_mode="read-only"
                ;;
            --print-attestation)
                action="print-attestation"
                ;;
            --verify-tag-attestation)
                action="verify-tag-attestation"
                shift
                tag_object="${1:-}"
                ;;
            *)
                echo "error: unknown argument: $1" >&2
                exit 1
                ;;
        esac
        shift
    done

    require_command jq

    case "${action}" in
        verify-tag-attestation)
            require_command git
            if [ -z "${tag_object}" ]; then
                echo "error: --verify-tag-attestation requires a tag object" >&2
                exit 1
            fi
            local tag_text
            tag_text="$(git cat-file tag "${tag_object}")"
            if ! validate_policy_attestation_text "${tag_text}"; then
                echo "error: signed tag object lacks the expected publication-policy attestation" >&2
                exit 1
            fi
            echo "[ok] signed tag object carries the expected publication-policy attestation"
            exit 0
            ;;
    esac

    if [ "${action}" = "print-attestation" ] && [ "${validation_mode}" != "full" ]; then
        echo "error: policy attestations require full ruleset validation" >&2
        exit 1
    fi

    local ruleset_json
    ruleset_json="$(resolve_live_ruleset)"
    validate_ruleset_json "${ruleset_json}" "${validation_mode}"

    if [ "${action}" = "print-attestation" ]; then
        echo "[ok] tag ruleset: ${EXPECTED_RULESET_NAME} matches the full publication policy" >&2
        expected_policy_attestation
        exit 0
    fi

    report_ruleset_validation "${validation_mode}"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
