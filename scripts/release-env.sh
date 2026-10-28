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
#   directory is refused. The default is resolved twice: gpgconf's homedir
#   (which follows HOME) and the account home's .gnupg from the user database
#   (which does not). A failure to resolve either is a refusal.

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

# Print the default homedir of the gpg that signs, with GNUPGHOME unset. The
# gpgconf beside the gpg found on PATH answers for that gpg.
release_gpg_default_homedir() {
    local gpg_path gpgconf_path homedir
    if ! gpg_path="$(command -v gpg)" || [[ -z "$gpg_path" ]]; then
        echo "error: gpg not found in PATH; the default keyring could not be resolved" >&2
        return 1
    fi
    gpgconf_path="$(dirname "$gpg_path")/gpgconf"
    if ! [[ -f "$gpgconf_path" && -x "$gpgconf_path" ]]; then
        echo "error: no gpgconf beside $gpg_path; the default keyring could not be resolved" >&2
        return 1
    fi
    if ! homedir="$(env -u GNUPGHOME "$gpgconf_path" --list-dirs homedir)" || [[ "$homedir" != /* ]]; then
        echo "error: gpgconf did not report an absolute default homedir" >&2
        return 1
    fi
    printf '%s\n' "$homedir"
}

# Print the account's home directory from the user database, not from HOME.
release_account_home() {
    local os user record home
    if ! os="$(uname -s)" || [[ -z "$os" ]]; then
        echo "error: uname failed; the account home could not be resolved" >&2
        return 1
    fi
    if ! user="$(id -un)" || [[ -z "$user" ]]; then
        echo "error: id failed; the account home could not be resolved" >&2
        return 1
    fi
    case "$os" in
        Darwin)
            if ! record="$(dscl . -read "/Users/$user" NFSHomeDirectory)"; then
                echo "error: account lookup for $user failed; the account home could not be resolved" >&2
                return 1
            fi
            home="$(printf '%s' "$record" | tr -d '\n' | sed 's/^NFSHomeDirectory:[[:space:]]*//')"
            ;;
        *)
            if ! record="$(getent passwd "$user")"; then
                echo "error: account lookup for $user failed; the account home could not be resolved" >&2
                return 1
            fi
            home="$(printf '%s\n' "$record" | head -n 1 | cut -d: -f6)"
            ;;
    esac
    if [[ "$home" != /* ]]; then
        echo "error: the account home for $user is not an absolute path" >&2
        return 1
    fi
    printf '%s\n' "$home"
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
    if ! resolved="$(cd "$homedir" && pwd -P)" || [[ -z "$resolved" ]]; then
        echo "error: THREELEAPS_CRUCIBLE_GPG_HOMEDIR did not resolve to a physical path" >&2
        return 1
    fi
    # Two resolutions of the default keyring: gpg's own default, which
    # follows HOME, and the account home's .gnupg from the user database,
    # which does not. Either one matching is a refusal; either one failing to
    # resolve is a refusal.
    local gpg_default account_home candidate
    if ! gpg_default="$(release_gpg_default_homedir)"; then
        return 1
    fi
    if ! account_home="$(release_account_home)"; then
        return 1
    fi
    for candidate in "$gpg_default" "$account_home/.gnupg"; do
        [[ -e "$candidate" ]] || continue
        if ! default_home="$(cd "$candidate" && pwd -P)" || [[ -z "$default_home" ]]; then
            echo "error: could not resolve the default keyring location $candidate" >&2
            return 1
        fi
        if [[ "$resolved" == "$default_home" ]]; then
            echo "error: THREELEAPS_CRUCIBLE_GPG_HOMEDIR resolves to the default GPG keyring ($candidate); use a dedicated keyring" >&2
            return 1
        fi
    done
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

# The signing call uses OpenPGP through the gpg found on PATH, and nothing
# else: release_signing_git pins gpg.format, gpg.program and
# gpg.openpgp.program on the command line, which overrides every config file
# and the environment. A configured value the pin overrides is reported, not
# refused, so a machine whose global config names a gpg wrapper can release
# unchanged. The check refuses only if the value the signing command would use
# is not the pin, which means the pin itself did not take effect.
require_signing_program() {
    local key want value effective rc
    for key in gpg.format gpg.program gpg.openpgp.program; do
        want=gpg
        [[ "$key" == gpg.format ]] && want=openpgp
        rc=0
        effective="$(release_signing_git config --get "$key")" || rc=$?
        if ((rc != 0)) || [[ "$effective" != "$want" ]]; then
            echo "error: release signing would not use $key=$want; not signing" >&2
            return 1
        fi
        rc=0
        value="$(git config --get-all "$key")" || rc=$?
        if ((rc == 1)); then
            continue
        fi
        if ((rc != 0)); then
            echo "error: could not read git config $key" >&2
            return 1
        fi
        if [[ "$value" != "$want" ]]; then
            echo "note: git config $key is '${value//$'\n'/, }'; release signing uses $want" >&2
        fi
    done
}

release_signing_git() {
    git -c gpg.format=openpgp -c gpg.program=gpg -c gpg.openpgp.program=gpg "$@"
}

# Release transport (repo decision, RELEASE_CHECKLIST.md "Push"): one explicit
# HTTPS URL, authenticated only by the organization token that direnv loads
# for the directory above this repository, through gh's credential helper.
# shellcheck disable=SC2034 # Consumed by scripts that source this file.
RELEASE_PUSH_URL="https://github.com/3leaps/crucible.git"

# Refuse git configuration that could send the push to another URL or attach
# other credentials, or that names another account. git -c cannot clear
# URL-scoped keys, so these are refused.
# Only the kind of setting and its scope are reported: both the values and a
# url.<base> key name can carry credentials.
refuse_release_transport_overrides() {
    local found rc=0
    found="$(git config --show-scope --name-only --get-regexp \
        '^(url\..*\.(insteadof|pushinsteadof)|http\..*\.?(extraheader|cookiefile|proxy|proxyauthmethod|sslverify|sslcainfo|sslcapath|sslcert|sslkey|sslbackend)|credential\..*\.?username)$')" ||
        rc=$?
    if ((rc == 0)); then
        echo "error: git configuration rewrites, proxies or adds credentials to release transport:" >&2
        printf '%s\n' "$found" | sed -E 's/^([a-z]+)[[:space:]]+(url|http|credential)\.(.*\.)?([a-z]+)$/  \1 \2.*.\4/' |
            sort -u >&2
        echo "hint: unset it for the release shell (git config --show-origin --name-only --get-regexp '^(url|http)\\.')" >&2
        return 1
    fi
    if ((rc != 1)); then
        echo "error: could not read git config for transport overrides" >&2
        return 1
    fi
}

# Run one git command against RELEASE_PUSH_URL under the org environment.
# Usage: release_remote_git REPO_ROOT GIT_ARGS...
# Inherited tokens and askpass helpers are removed first; direnv then loads
# the .envrc above REPO_ROOT. Without that file, or without a token in it,
# the command stops before git runs.
release_remote_git() {
    local root="$1"
    shift
    if ! command -v direnv >/dev/null 2>&1; then
        echo "error: direnv not found; the release push uses only the org token direnv loads" >&2
        return 1
    fi
    # shellcheck disable=SC2016 # Expanded by the inner shell, by design.
    env -u GH_TOKEN -u GITHUB_TOKEN -u DIRENV_FILE -u GIT_ASKPASS -u SSH_ASKPASS GIT_TERMINAL_PROMPT=0 \
        direnv exec "$root" bash -c 'source "$1/scripts/release-env.sh" && release_transport_git "$@"' \
        _ "$root" "$@"
}

# Called by release_remote_git inside the org environment; not for direct use.
release_transport_git() {
    local root="$1"
    shift
    if [[ -z "${DIRENV_FILE:-}" ]]; then
        echo "error: no .envrc was loaded above $root; not contacting GitHub" >&2
        return 1
    fi
    # The .envrc must sit in a directory above the repository, compared as
    # physical paths; one inside the repository is under the control of
    # whatever is checked out.
    local envrc_dir root_dir
    if ! envrc_dir="$(cd "$(dirname "$DIRENV_FILE")" && pwd -P)" || [[ -z "$envrc_dir" ]] ||
        ! root_dir="$(cd "$root" && pwd -P)" || [[ -z "$root_dir" ]]; then
        echo "error: could not resolve the loaded .envrc or the repository root; not contacting GitHub" >&2
        return 1
    fi
    case "$root_dir" in
        "${envrc_dir%/}"/*) ;;
        *)
            echo "error: the loaded .envrc ($DIRENV_FILE) is not above the repository; not contacting GitHub" >&2
            return 1
            ;;
    esac
    if [[ -z "${GH_TOKEN:-}" ]]; then
        echo "error: $DIRENV_FILE did not set GH_TOKEN; not contacting GitHub" >&2
        echo "hint: do not retry over origin, SSH or a stored gh login" >&2
        return 1
    fi
    if ! command -v gh >/dev/null 2>&1; then
        echo "error: gh not found; it is the only credential helper the release push uses" >&2
        return 1
    fi
    # git's HTTP layer also sends credentials it finds in the home directory's
    # .netrc or _netrc, ahead of any credential helper, and global config can
    # name another account. git runs with HOME set to a new empty directory
    # (not unset: libcurl then falls back to the account home) and with no
    # global or system config; git does not read NETRC or CURL_HOME. The
    # override check reads the same configuration git will, so what remains
    # (repository config and GIT_CONFIG_* from the environment) is refused.
    # Proxy and TLS environment that libcurl or git would honor is removed
    # here, after direnv, so neither the release shell nor the .envrc can
    # route the org token through a proxy or weaken certificate checks.
    local isolated rc=0
    if ! isolated="$(mktemp -d)" || [[ -z "$isolated" ]]; then
        echo "error: could not create an isolated home for git; not contacting GitHub" >&2
        return 1
    fi
    (
        export HOME="$isolated" XDG_CONFIG_HOME="$isolated/.config" GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
        local name
        for name in $(compgen -e); do
            case "$name" in
                GIT_SSL_* | GIT_PROXY_* | GIT_HTTP_PROXY_AUTHMETHOD | GIT_CURL_VERBOSE | GIT_TRACE_CURL* | \
                    [Hh][Tt][Tt][Pp][Ss]_[Pp][Rr][Oo][Xx][Yy] | [Hh][Tt][Tt][Pp]_[Pp][Rr][Oo][Xx][Yy] | \
                    [Aa][Ll][Ll]_[Pp][Rr][Oo][Xx][Yy] | [Nn][Oo]_[Pp][Rr][Oo][Xx][Yy])
                    unset "$name"
                    ;;
            esac
        done
        refuse_release_transport_overrides || exit 1
        git -c credential.helper= -c 'credential.helper=!gh auth git-credential' -c core.askPass= "$@"
    ) || rc=$?
    rm -rf "$isolated"
    return "$rc"
}
