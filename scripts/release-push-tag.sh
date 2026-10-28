#!/usr/bin/env bash
# release-push-tag.sh - Verify and push the signed version tag
#
# Safety checks:
# - Local tag exists and its signature verifies (release-verify-tag.sh)
# - Every remote call uses https://github.com/3leaps/crucible.git, never
#   origin, with only the organization token direnv loads for the directory
#   above this repository (scripts/release-env.sh, release_remote_git). A
#   missing .envrc or token, or any url.*.insteadOf, url.*.pushInsteadOf or
#   http.*.extraHeader setting, stops before git contacts GitHub; nothing
#   retries another way.
# - Tagged commit is on main at that URL; a failed fetch is an error
# - Remote tag does not already exist; a failed read is an error
# - Pushes only the tag ref, then confirms the remote tag object matches local
# - When gh is available, confirms GitHub reports the tag verified; a failure to
#   read that flag is reported as such, after the push (release-github-verified.sh)
#
# Environment variables:
# - THREELEAPS_CRUCIBLE_RELEASE_TAG: the tag to push (required; never derived)
# - THREELEAPS_CRUCIBLE_DECERNOR_BIN: absolute path to the designated checker
#     (required; see scripts/release-env.sh)
#
# Retired names (refused): RELEASE_TAG and the unprefixed CRUCIBLE_* aliases.

set -euo pipefail

die() {
    echo "error: $*" >&2
    exit 1
}

root="$(git rev-parse --show-toplevel)" || die "not inside a git repository"
[[ -n "$root" ]] || die "not inside a git repository"
cd "$root"
# shellcheck source=scripts/release-env.sh
source scripts/release-env.sh
refuse_legacy_release_env
tag="$(require_release_tag)" || exit 1
resolve_release_decernor

git rev-parse -q --verify "refs/tags/${tag}^{tag}" >/dev/null ||
    die "${tag} is not a local annotated tag (run 'make release-tag' first)"
./scripts/release-verify-tag.sh

# Each remote call below is checked explicitly; errexit is not relied on
# across command substitutions.
release_remote_git "$root" fetch --quiet --no-tags "$RELEASE_PUSH_URL" refs/heads/main ||
    die "fetch of main from ${RELEASE_PUSH_URL} failed; not pushing"
remote_main="$(git rev-parse --verify 'FETCH_HEAD^{commit}')" || die "fetched main did not resolve"
tag_commit="$(git rev-parse --verify "refs/tags/${tag}^{commit}")" || die "${tag} has no commit"
git merge-base --is-ancestor "$tag_commit" "$remote_main" ||
    die "${tag} points at ${tag_commit}, which is not on main at ${RELEASE_PUSH_URL}"

existing="$(release_remote_git "$root" ls-remote --tags "$RELEASE_PUSH_URL" "refs/tags/${tag}")" ||
    die "could not read tags from ${RELEASE_PUSH_URL}; not pushing"
[[ -z "$existing" ]] || die "remote tag ${tag} already exists"

local_object="$(git rev-parse --verify "refs/tags/${tag}")" || die "${tag} did not resolve"

echo "Pushing tag: ${tag} to ${RELEASE_PUSH_URL}"
release_remote_git "$root" push "$RELEASE_PUSH_URL" "refs/tags/${tag}" ||
    die "push of ${tag} failed; do not retry over origin, SSH or a stored gh login"

remote_object="$(release_remote_git "$root" ls-remote "$RELEASE_PUSH_URL" "refs/tags/${tag}")" ||
    die "${tag} was pushed, but ${RELEASE_PUSH_URL} could not be read back"
remote_object="${remote_object%%[[:space:]]*}"
[[ "$remote_object" == "$local_object" ]] ||
    die "remote tag object (${remote_object:-missing}) differs from local (${local_object})"

echo "[ok] Pushed ${tag} (${local_object}); the remote tag object matches"

# shellcheck source=scripts/release-github-verified.sh
source scripts/release-github-verified.sh
check_github_verified "${tag}" "${local_object}"
echo "[ok] release workflow will publish"
