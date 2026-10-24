#!/usr/bin/env bash
# release-env.sh - Explicit release inputs (PDR-0008 §2.3, §2.4)
#
# Source this file; it defines functions only.
#
# - refuse_legacy_release_env: fail if a retired or unprefixed release variable
#   is set, so an inherited bare name never silently wins or is silently ignored.
# - require_release_tag: print THREELEAPS_CRUCIBLE_RELEASE_TAG, which must be a
#   canonical vMAJOR.MINOR.PATCH tag. There is no default from VERSION, git
#   describe, or the branch.
# - resolve_release_decernor: set RELEASE_DECERNOR_BIN from
#   THREELEAPS_CRUCIBLE_DECERNOR_BIN, an absolute path to a regular,
#   executable, non-symlink decernor >= RELEASE_DECERNOR_MIN_VERSION. There is
#   no fallback to PATH or to another variable.
# - require_signing_keyring: set RELEASE_GNUPGHOME from
#   THREELEAPS_CRUCIBLE_GPG_HOMEDIR, a dedicated signing keyring. The default
#   keyring is never used: an unset value, the default location (however it
#   is spelled), a symlink, or an inherited GNUPGHOME naming a different
#   directory is refused.

RELEASE_DECERNOR_MIN_VERSION="0.1.8"

RELEASE_RETIRED_VARIABLES=(
    RELEASE_TAG
    CRUCIBLE_RELEASE_TAG
    CRUCIBLE_GPG_HOMEDIR
    CRUCIBLE_PGP_KEY_ID
    CRUCIBLE_TAGGER_NAME
    CRUCIBLE_TAGGER_EMAIL
    CRUCIBLE_ALLOW_NON_MAIN
    CRUCIBLE_REQUIRE_TAG
    THREELEAPS_CRUCIBLE_REQUIRE_TAG
    CRUCIBLE_DECERNOR_BIN
    DECERNOR_BIN
)

refuse_legacy_release_env() {
    local name found=()
    for name in "${RELEASE_RETIRED_VARIABLES[@]}"; do
        if [[ -n "${!name+set}" ]]; then
            found+=("$name")
        fi
    done
    if ((${#found[@]})); then
        echo "error: retired or unprefixed release variable set: ${found[*]}" >&2
        echo "hint: unset it; release inputs use the THREELEAPS_CRUCIBLE_ prefix (RELEASE_CHECKLIST.md)" >&2
        return 1
    fi
}

require_release_tag() {
    local tag="${THREELEAPS_CRUCIBLE_RELEASE_TAG:-}"
    if [[ -z "$tag" ]]; then
        echo "error: THREELEAPS_CRUCIBLE_RELEASE_TAG is required (e.g. v1.2.3); the tag is never derived" >&2
        return 1
    fi
    if ! [[ "$tag" =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]]; then
        echo "error: invalid release tag '$tag' (expected vMAJOR.MINOR.PATCH)" >&2
        return 1
    fi
    printf '%s\n' "$tag"
}

resolve_release_decernor() {
    local candidate="${THREELEAPS_CRUCIBLE_DECERNOR_BIN:-}" short extended version
    if [[ -z "$candidate" ]]; then
        echo "error: THREELEAPS_CRUCIBLE_DECERNOR_BIN is required (absolute path to decernor >= ${RELEASE_DECERNOR_MIN_VERSION})" >&2
        return 1
    fi
    if ! [[ "$candidate" == /* && -f "$candidate" && ! -L "$candidate" && -x "$candidate" ]]; then
        echo "error: THREELEAPS_CRUCIBLE_DECERNOR_BIN must be an absolute path to a regular, executable, non-symlink file" >&2
        return 1
    fi
    short="$("$candidate" version 2>/dev/null)" || {
        echo "error: decernor identity check failed" >&2
        return 1
    }
    if ! [[ "$short" =~ ^decernor\ ((0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*))$ ]]; then
        echo "error: THREELEAPS_CRUCIBLE_DECERNOR_BIN is not decernor (reported '${short%%$'\n'*}')" >&2
        return 1
    fi
    version="${BASH_REMATCH[1]}"
    extended="$("$candidate" version -e 2>/dev/null)" || {
        echo "error: decernor extended identity check failed" >&2
        return 1
    }
    local labels=("Version" "Commit" "Build Date" "Go Version" "Gofulmen" "Crucible") line count=0
    while IFS= read -r line; do
        if ((count >= ${#labels[@]})) || ! [[ "$line" =~ ^${labels[count]}:[[:space:]]+[^[:space:]] ]]; then
            echo "error: invalid decernor extended identity" >&2
            return 1
        fi
        count=$((count + 1))
    done <<<"$extended"
    if ((count != ${#labels[@]})) || ! [[ "$extended" =~ ^Version:[[:space:]]+${version//./\\.}($'\n') ]]; then
        echo "error: invalid decernor extended identity" >&2
        return 1
    fi
    local have want i
    IFS=. read -r -a have <<<"$version"
    IFS=. read -r -a want <<<"$RELEASE_DECERNOR_MIN_VERSION"
    for i in 0 1 2; do
        if ((have[i] > want[i])); then
            break
        fi
        if ((have[i] < want[i])); then
            echo "error: decernor >= ${RELEASE_DECERNOR_MIN_VERSION} required (found ${version})" >&2
            return 1
        fi
    done
    # shellcheck disable=SC2034 # Consumed by scripts that source this file.
    RELEASE_DECERNOR_BIN="$candidate"
}

require_signing_keyring() {
    local homedir="${THREELEAPS_CRUCIBLE_GPG_HOMEDIR:-}" resolved default_home
    if [[ -z "$homedir" ]]; then
        echo "error: THREELEAPS_CRUCIBLE_GPG_HOMEDIR is required; the default GPG keyring is never used" >&2
        echo "hint: point it at a dedicated signing keyring, such as a throwaway directory you remove afterwards" >&2
        return 1
    fi
    if ! [[ "$homedir" == /* && -d "$homedir" && ! -L "$homedir" ]]; then
        echo "error: THREELEAPS_CRUCIBLE_GPG_HOMEDIR must be an absolute path to an existing, non-symlink directory" >&2
        return 1
    fi
    resolved="$(cd "$homedir" && pwd -P)"
    if [[ -n "${HOME:-}" && -d "$HOME/.gnupg" ]]; then
        default_home="$(cd "$HOME/.gnupg" && pwd -P)"
        if [[ "$resolved" == "$default_home" ]]; then
            echo "error: THREELEAPS_CRUCIBLE_GPG_HOMEDIR resolves to the default GPG keyring; use a dedicated keyring" >&2
            return 1
        fi
    fi
    if [[ -n "${GNUPGHOME:-}" ]]; then
        if ! [[ -d "$GNUPGHOME" ]] || [[ "$(cd "$GNUPGHOME" && pwd -P)" != "$resolved" ]]; then
            echo "error: GNUPGHOME is set to a different directory than THREELEAPS_CRUCIBLE_GPG_HOMEDIR" >&2
            echo "hint: unset GNUPGHOME, or set it to the same keyring" >&2
            return 1
        fi
    fi
    # shellcheck disable=SC2034 # Consumed by scripts that source this file.
    RELEASE_GNUPGHOME="$resolved"
}
