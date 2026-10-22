#!/usr/bin/env bash
# release-verify-tag.sh - Verify a signed git tag
#
# Environment variables:
# - THREELEAPS_CRUCIBLE_RELEASE_TAG: the tag to verify (required; never derived)
# - THREELEAPS_CRUCIBLE_DECERNOR_BIN: absolute path to the designated checker
#     (required; see scripts/release-env.sh)
# - THREELEAPS_CRUCIBLE_GPG_HOMEDIR: dedicated signing keyring directory
#
# Retired names (refused): RELEASE_TAG and the unprefixed CRUCIBLE_* aliases.

set -euo pipefail

main() {
    cd "$(git rev-parse --show-toplevel)"

    # shellcheck source=scripts/release-env.sh
    source scripts/release-env.sh
    refuse_legacy_release_env
    local tag
    tag="$(require_release_tag)"
    resolve_release_decernor

    local gpg_homedir="${THREELEAPS_CRUCIBLE_GPG_HOMEDIR:-}"
    if [ -n "${gpg_homedir}" ]; then
        if [ ! -d "${gpg_homedir}" ]; then
            echo "error: GPG homedir '${gpg_homedir}' is not a directory" >&2
            exit 1
        fi
        export GNUPGHOME="${gpg_homedir}"
    fi

    echo "Verifying tag signature: $tag"
    if ! git verify-tag "$tag" 2>/dev/null; then
        echo "error: tag verification failed for $tag" >&2
        exit 1
    fi
    # The same pinned-key check the release workflow applies before publication.
    ./scripts/verify-pinned-tag.sh "$tag"
}

main "$@"
