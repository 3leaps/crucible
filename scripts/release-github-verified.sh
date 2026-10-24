#!/usr/bin/env bash
# release-github-verified.sh - Confirm GitHub's verified flag for a pushed tag
#
# Source this file; it defines check_github_verified TAG OBJECT. Call it only
# after the tag is pushed and the remote tag object matches. GitHub's flag is a
# secondary check, so a failure to read it is reported as a read failure of an
# already-pushed tag, never as a failed push.

check_github_verified() {
    local tag="$1" object="$2" verified
    if ! command -v gh >/dev/null 2>&1; then
        echo "[--] gh not found; GitHub's verified flag was not checked"
        return 0
    fi
    if ! verified="$(gh api "repos/3leaps/crucible/git/tags/${object}" --jq .verification.verified)"; then
        echo "error: ${tag} is pushed, but GitHub's verified flag could not be read" >&2
        echo "hint: do not push or delete the tag again; this is usually a rejected or under-scoped gh credential," >&2
        echo "hint: or a GH_TOKEN/GITHUB_TOKEN in the environment that gh prefers over its stored login" >&2
        echo "hint: re-check with: gh api repos/3leaps/crucible/git/tags/${object} --jq .verification" >&2
        return 1
    fi
    if [ "$verified" != "true" ]; then
        echo "error: ${tag} is pushed, but GitHub does not report it verified (verification.verified=${verified})" >&2
        return 1
    fi
    echo "[ok] GitHub reports ${tag} verified"
}
