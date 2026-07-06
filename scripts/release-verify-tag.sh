#!/usr/bin/env bash
# release-verify-tag.sh - Verify a signed git tag
#
# Environment variables:
# - THREELEAPS_CRUCIBLE_RELEASE_TAG: override tag to verify (default: v$(cat VERSION))
# - THREELEAPS_CRUCIBLE_GPG_HOMEDIR: dedicated signing keyring directory
#
# Legacy aliases (still supported):
# - CRUCIBLE_RELEASE_TAG, CRUCIBLE_GPG_HOMEDIR

set -euo pipefail

repo_root() {
    git rev-parse --show-toplevel
}

read_version() {
    if [ ! -f VERSION ]; then
        echo "error: VERSION file not found" >&2
        exit 1
    fi
    tr -d ' \t\r\n' <VERSION
}

main() {
    local root
    root="$(repo_root)"
    cd "$root"

    local version
    version="$(read_version)"

    # Tag precedence: THREELEAPS_CRUCIBLE_RELEASE_TAG > CRUCIBLE_RELEASE_TAG (legacy) > RELEASE_TAG > v${version}
    local tag="${THREELEAPS_CRUCIBLE_RELEASE_TAG:-${CRUCIBLE_RELEASE_TAG:-${RELEASE_TAG:-v${version}}}}"

    # Set up GPG homedir if specified (THREELEAPS_CRUCIBLE_ takes precedence)
    local gpg_homedir="${THREELEAPS_CRUCIBLE_GPG_HOMEDIR:-${CRUCIBLE_GPG_HOMEDIR:-}}"

    if [ -n "${gpg_homedir}" ]; then
        if [ ! -d "${gpg_homedir}" ]; then
            echo "error: GPG homedir '${gpg_homedir}' is not a directory" >&2
            exit 1
        fi
        export GNUPGHOME="${gpg_homedir}"
    fi

    echo "Verifying tag signature: $tag"
    if git verify-tag "$tag" 2>/dev/null; then
        echo ""
        echo "[ok] Tag verified: $tag"
    else
        echo "error: tag verification failed for $tag" >&2
        exit 1
    fi
}

main "$@"
