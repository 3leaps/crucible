#!/usr/bin/env bash
# release-tag.sh - Create a signed git tag with safety checks
#
# Safety checks:
# - Explicit inputs only: the tag and the checker come from prefixed variables;
#   retired or unprefixed variables are refused (PDR-0008 §2.3, §2.4)
# - Tag format validation (vMAJOR.MINOR.PATCH)
# - Clean working tree required
# - Must be on main branch (overridable)
# - Tag must not already exist
# - Live tag publication ruleset matches the full expected policy
# - Committed pins match their anchors under the designated checker
# - GPG signing key availability
# - Signing uses OpenPGP through the gpg on PATH: the signing command pins
#   gpg.format, gpg.program and gpg.openpgp.program; a configured value it
#   overrides is reported, and the step stops if the pin would not take effect
# - Signed tag carries the validated publication-policy fingerprint
# - Automatic signature verification after creation
#
# Environment variables:
# - THREELEAPS_CRUCIBLE_RELEASE_TAG: the tag to create (required; never derived)
# - THREELEAPS_CRUCIBLE_DECERNOR_BIN: absolute path to the designated checker
#     (required; see scripts/release-env.sh)
# - THREELEAPS_CRUCIBLE_GPG_HOMEDIR: dedicated signing keyring directory
#     (required; the default GPG keyring is never used, see scripts/release-env.sh)
# - THREELEAPS_CRUCIBLE_PGP_KEY_ID: exact uppercase 40-hex signing subkey
#     fingerprint with trailing ! (required; must match the signing subkey in
#     docs/security/release-signing-keys.asc; see scripts/release-env.sh)
# - THREELEAPS_CRUCIBLE_TAGGER_EMAIL: tagger email stamped on the tag object
#     (required; never derived from git config; together with
#     THREELEAPS_CRUCIBLE_TAGGER_NAME must match config/release/tagger-identity.txt,
#     and the email must match a User ID email on
#     docs/security/release-signing-keys.asc)
# - THREELEAPS_CRUCIBLE_TAGGER_NAME: tagger name stamped on the tag object
#     (required; never derived from git config; together with
#     THREELEAPS_CRUCIBLE_TAGGER_EMAIL must match config/release/tagger-identity.txt)
# - THREELEAPS_CRUCIBLE_ALLOW_NON_MAIN: set to 1 to allow tagging from non-main branch
#
# Retired names (refused, see scripts/release-env.sh): RELEASE_TAG and the
# unprefixed CRUCIBLE_* aliases.

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

setup_gpg_tty() {
    # When using passphrase-protected keys, gpg will invoke pinentry.
    # Ensure it has a real TTY to talk to, otherwise signing fails with:
    # "Inappropriate ioctl for device".
    if [ ! -t 0 ] || [ ! -t 1 ]; then
        echo "error: no TTY available for interactive gpg signing" >&2
        echo "hint: run 'make release-tag' in an interactive terminal" >&2
        echo "hint: export GPG_TTY=\"\$(tty)\" && gpg-connect-agent updatestartuptty /bye" >&2
        exit 1
    fi

    if command -v tty >/dev/null 2>&1; then
        local tty_path
        tty_path="$(tty 2>/dev/null || true)"
        if [ -n "${tty_path}" ] && [ "${tty_path}" != "not a tty" ]; then
            export GPG_TTY="${tty_path}"
            gpg-connect-agent updatestartuptty /bye >/dev/null 2>&1 || true
        fi
    fi
}

ensure_gpg_signing_ready() {
    if ! command -v gpg >/dev/null 2>&1; then
        echo "error: gpg not found in PATH (required for signed tags)" >&2
        echo "hint: see RELEASE_CHECKLIST.md (Tagging section)" >&2
        exit 1
    fi

    local key_id="${RELEASE_PGP_KEY_ID}"
    local listing

    listing="$(gpg --list-secret-keys --with-colons --keyid-format=long "${key_id}" 2>/dev/null || true)"
    if ! grep -q '^sec' <<<"${listing}"; then
        echo "error: no usable GPG secret key found for key id: ${key_id}" >&2
        echo "hint: ensure your release env vars are loaded" >&2
        echo "hint: signing keyring: ${GNUPGHOME}" >&2
        echo "hint: run: gpg --list-secret-keys --keyid-format=long" >&2
        echo "hint: see RELEASE_CHECKLIST.md (Tagging section)" >&2
        exit 1
    fi
}

main() {
    local root
    root="$(repo_root)"
    cd "$root"

    # Explicit inputs, checked before any side effect (PDR-0008 §2.3, §2.4).
    # shellcheck source=scripts/release-env.sh
    source scripts/release-env.sh
    refuse_legacy_release_env
    local tag
    tag="$(require_release_tag)"
    resolve_release_decernor
    require_signing_keyring
    require_signing_program
    require_signing_identity

    local version
    version="$(read_version)"
    if [ "$tag" != "v${version}" ]; then
        echo "error: release tag $tag does not match VERSION $version" >&2
        exit 1
    fi

    # Check clean working tree
    if [ -n "$(git status --porcelain)" ]; then
        echo "error: working tree is not clean (commit or stash changes before tagging)" >&2
        git status --porcelain >&2
        exit 1
    fi

    # Check branch (must be main unless overridden)
    local branch
    branch="$(git branch --show-current 2>/dev/null || true)"
    local allow_non_main="${THREELEAPS_CRUCIBLE_ALLOW_NON_MAIN:-}"
    if [ "$branch" != "main" ] && [ "${allow_non_main}" != "1" ]; then
        echo "error: refusing to tag from branch '$branch' (set THREELEAPS_CRUCIBLE_ALLOW_NON_MAIN=1 to override)" >&2
        exit 1
    fi

    # Check tag doesn't already exist
    if git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
        echo "error: tag $tag already exists" >&2
        exit 1
    fi

    # The pins this tag will carry must match their anchors under the
    # designated checker before anything is signed.
    local pins
    pins="$(mktemp -d)"
    if ! ./scripts/release-verify-anchors.sh HEAD "${pins}"; then
        rm -rf "${pins}"
        exit 1
    fi
    rm -rf "${pins}"

    # Validate the complete ruleset and bind its canonical policy fingerprint
    # into the signed tag object for publication verification.
    local policy_attestation
    policy_attestation="$(./scripts/release-guard-tag-ruleset.sh --print-attestation)"
    if ! [[ "${policy_attestation}" =~ ^Tag-Publish-Policy-SHA256:\ [0-9a-f]{64}$ ]]; then
        echo "error: publication-policy attestation is missing or malformed" >&2
        exit 1
    fi

    # Every gpg and git signing call below uses only the dedicated keyring.
    export GNUPGHOME="${RELEASE_GNUPGHOME}"

    setup_gpg_tty
    ensure_gpg_signing_ready

    echo "Creating signed tag: $tag"

    export GIT_COMMITTER_NAME="${RELEASE_TAGGER_NAME}"
    export GIT_COMMITTER_EMAIL="${RELEASE_TAGGER_EMAIL}"

    local tag_err
    tag_err="$(mktemp)"

    if ! release_signing_git tag -s -a "$tag" -u "${RELEASE_PGP_KEY_ID}" -m "Release $tag" -m "${policy_attestation}" 2>"${tag_err}"; then
        cat "${tag_err}" >&2
        if grep -qi "no secret key" "${tag_err}"; then
            echo "hint: no secret key available for signing" >&2
            echo "hint: see RELEASE_CHECKLIST.md (Tagging section)" >&2
        fi
        rm -f "${tag_err}"
        exit 1
    fi

    rm -f "${tag_err}"

    echo "Verifying tag signature: $tag"
    release_signing_git verify-tag "$tag" >/dev/null
    ./scripts/verify-pinned-tag.sh "$tag"

    echo ""
    echo "[ok] Created and verified signed tag: $tag"
    echo ""
    echo "Next steps:"
    echo "  make release-push-tag"
}

main "$@"
