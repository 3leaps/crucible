#!/usr/bin/env bash
# release-guard-tag-version.sh - Verify the release tag matches the VERSION file
#
# Run before tagging. The tag is an explicit input and is never derived from
# git describe, VERSION, or the branch (PDR-0008 §2.4).
#
# Environment variables:
# - THREELEAPS_CRUCIBLE_RELEASE_TAG: the intended tag (required)
#
# Retired names (refused): RELEASE_TAG, THREELEAPS_CRUCIBLE_REQUIRE_TAG and the
# unprefixed CRUCIBLE_* aliases.

set -euo pipefail

main() {
    cd "$(git rev-parse --show-toplevel)"

    # shellcheck source=scripts/release-env.sh
    source scripts/release-env.sh
    refuse_legacy_release_env
    local tag
    tag="$(require_release_tag)"

    if [ ! -f VERSION ]; then
        echo "error: VERSION file not found" >&2
        exit 1
    fi
    local version
    version="$(tr -d ' \t\r\n' <VERSION)"

    if [ "$tag" != "v${version}" ]; then
        echo "error: release tag/version mismatch" >&2
        echo "  tag:     $tag" >&2
        echo "  VERSION: $version (expected tag: v${version})" >&2
        exit 1
    fi

    echo "[ok] release guard: tag matches VERSION ($tag)"
}

main "$@"
