#!/usr/bin/env bash
# release-push-tag.sh - Verify and push the signed version tag
#
# Safety checks:
# - Local tag exists and its signature verifies (release-verify-tag.sh)
# - Tagged commit is on origin/main
# - Remote tag does not already exist
# - Pushes only the tag ref, then confirms the remote tag object matches local
# - When gh is available, confirms GitHub reports the tag verified
#
# Environment variables:
# - THREELEAPS_CRUCIBLE_RELEASE_TAG: override tag (default: v$(cat VERSION))
# - THREELEAPS_CRUCIBLE_GPG_HOMEDIR: dedicated signing keyring directory

set -euo pipefail

die() {
    echo "error: $*" >&2
    exit 1
}

cd "$(git rev-parse --show-toplevel)"
[ -f VERSION ] || die "VERSION file not found"
version="$(tr -d ' \t\r\n' <VERSION)"
tag="${THREELEAPS_CRUCIBLE_RELEASE_TAG:-${CRUCIBLE_RELEASE_TAG:-${RELEASE_TAG:-v${version}}}}"

git rev-parse -q --verify "refs/tags/${tag}^{tag}" >/dev/null ||
    die "${tag} is not a local annotated tag (run 'make release-tag' first)"
THREELEAPS_CRUCIBLE_RELEASE_TAG="$tag" ./scripts/release-verify-tag.sh

git fetch --quiet origin main
tag_commit="$(git rev-parse "refs/tags/${tag}^{commit}")"
git merge-base --is-ancestor "$tag_commit" origin/main ||
    die "${tag} points at ${tag_commit}, which is not on origin/main"

[ -z "$(git ls-remote --tags origin "refs/tags/${tag}")" ] ||
    die "remote tag ${tag} already exists"

echo "Pushing tag: ${tag}"
git push origin "refs/tags/${tag}"

local_object="$(git rev-parse "refs/tags/${tag}")"
remote_object="$(git ls-remote origin "refs/tags/${tag}" | awk '{print $1}')"
[ "$remote_object" = "$local_object" ] ||
    die "remote tag object (${remote_object:-missing}) differs from local (${local_object})"

if command -v gh >/dev/null 2>&1; then
    repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
    verified="$(gh api "repos/${repo}/git/tags/${local_object}" --jq .verification.verified)"
    [ "$verified" = "true" ] ||
        die "GitHub does not report ${tag} verified (verification.verified=${verified})"
    echo "[ok] GitHub reports ${tag} verified"
else
    echo "[--] gh not found; skipped GitHub verification check"
fi

echo "[ok] Pushed ${tag} (${local_object}); release workflow will publish"
