#!/usr/bin/env bash
# test-release-env.sh - Negative controls for explicit release inputs
#
# Proves each refusal in scripts/release-env.sh fires (PDR-0008 §2.3, §2.4;
# EPR-0002), and that the Makefile entry point does not let a bare variable
# win. Needs neither gpg nor a real checker: fake checker binaries stand in.

# Stand-in tools and inner shells are written in single quotes on purpose:
# they expand when they run.
# shellcheck disable=SC2016

set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

failures=0
pass() { echo "[ok] $1"; }
fail() {
    echo "[!!] $1" >&2
    failures=$((failures + 1))
}

# Run a release-env.sh function in a clean environment plus the given
# assignments. Usage: in_env FUNCTION [NAME=VALUE ...]
in_env() {
    local fn="$1"
    shift
    # shellcheck disable=SC2016 # Expanded by the inner shell, by design.
    env -i PATH="$PATH" HOME="$work" "$@" bash -c \
        'source "$1"; "$2"' _ "$root/scripts/release-env.sh" "$fn" >"$work/out" 2>"$work/err"
}

expect_refused() {
    local label="$1" pattern="$2"
    shift 2
    if in_env "$@"; then
        fail "$label: accepted"
    elif ! grep -q -- "$pattern" "$work/err"; then
        fail "$label: refused for the wrong reason: $(cat "$work/err")"
    else
        pass "$label: refused"
    fi
}

expect_accepted() {
    local label="$1"
    shift
    if in_env "$@"; then
        pass "$label: accepted"
    else
        fail "$label: refused: $(cat "$work/err")"
    fi
}

# A fake checker that reports the given short and extended identity.
fake_checker() {
    local path="$1" short="$2" version="$3"
    cat >"$path" <<EOF
#!/usr/bin/env bash
case "\$*" in
  "version") echo "$short" ;;
  "version -e") printf 'Version:         %s\nCommit:          0000000\nBuild Date:      2026-01-01T00:00:00Z\nGo Version:      go1.0\nGofulmen:        v0.0.0\nCrucible:        v0.0.0\n' "$version" ;;
  *) exit 2 ;;
esac
EOF
    chmod 755 "$path"
}

# --- retired and unprefixed variables ---------------------------------------
for name in RELEASE_TAG CRUCIBLE_RELEASE_TAG CRUCIBLE_GPG_HOMEDIR CRUCIBLE_PGP_KEY_ID \
    CRUCIBLE_TAGGER_NAME CRUCIBLE_TAGGER_EMAIL CRUCIBLE_ALLOW_NON_MAIN CRUCIBLE_REQUIRE_TAG \
    THREELEAPS_CRUCIBLE_REQUIRE_TAG CRUCIBLE_DECERNOR_BIN DECERNOR_BIN; do
    expect_refused "retired $name" "retired or unprefixed" refuse_legacy_release_env "$name=v0.0.1"
done
expect_refused "retired name set but empty" "retired or unprefixed" refuse_legacy_release_env "RELEASE_TAG="
expect_accepted "no retired names" refuse_legacy_release_env

# --- tag input ---------------------------------------------------------------
expect_refused "tag unset" "is required" require_release_tag
expect_refused "tag empty" "is required" require_release_tag THREELEAPS_CRUCIBLE_RELEASE_TAG=
for bad in 0.2.1 v0.2 v0.2.1-rc.1 v01.2.3 "v0.2.1 " latest; do
    expect_refused "tag '$bad'" "invalid release tag" require_release_tag "THREELEAPS_CRUCIBLE_RELEASE_TAG=$bad"
done
expect_accepted "tag v0.2.1" require_release_tag THREELEAPS_CRUCIBLE_RELEASE_TAG=v0.2.1
[[ "$(cat "$work/out")" == v0.2.1 ]] || fail "tag v0.2.1: printed '$(cat "$work/out")'"

# --- checker binding ---------------------------------------------------------
mkdir "$work/bin"
fake_checker "$work/bin/decernor" "decernor 0.1.9" 0.1.9
fake_checker "$work/bin/at-minimum" "decernor 0.1.8" 0.1.8
fake_checker "$work/bin/too-old" "decernor 0.1.7" 0.1.7
fake_checker "$work/bin/impostor" "other 0.1.9" 0.1.9
fake_checker "$work/bin/version-skew" "decernor 0.1.9" 0.1.8
cat >"$work/bin/no-extended" <<'EOF'
#!/usr/bin/env bash
[ "$*" = version ] && echo "decernor 0.1.9" || exit 2
EOF
chmod 755 "$work/bin/no-extended"
cp "$work/bin/decernor" "$work/bin/not-executable"
chmod 644 "$work/bin/not-executable"
ln -s "$work/bin/decernor" "$work/bin/symlinked"
mkdir "$work/bin/a-directory"

expect_refused "checker unset" "is required" resolve_release_decernor
expect_refused "checker relative path" "absolute path" resolve_release_decernor THREELEAPS_CRUCIBLE_DECERNOR_BIN=decernor
expect_refused "checker missing file" "absolute path" resolve_release_decernor "THREELEAPS_CRUCIBLE_DECERNOR_BIN=$work/bin/absent"
expect_refused "checker symlink" "non-symlink" resolve_release_decernor "THREELEAPS_CRUCIBLE_DECERNOR_BIN=$work/bin/symlinked"
expect_refused "checker not executable" "executable" resolve_release_decernor "THREELEAPS_CRUCIBLE_DECERNOR_BIN=$work/bin/not-executable"
expect_refused "checker is a directory" "regular" resolve_release_decernor "THREELEAPS_CRUCIBLE_DECERNOR_BIN=$work/bin/a-directory"
expect_refused "checker wrong identity" "is not decernor" resolve_release_decernor "THREELEAPS_CRUCIBLE_DECERNOR_BIN=$work/bin/impostor"
expect_refused "checker below minimum" ">= 0.1.8 required" resolve_release_decernor "THREELEAPS_CRUCIBLE_DECERNOR_BIN=$work/bin/too-old"
expect_refused "checker version skew" "extended identity" resolve_release_decernor "THREELEAPS_CRUCIBLE_DECERNOR_BIN=$work/bin/version-skew"
expect_refused "checker no extended identity" "extended identity" resolve_release_decernor "THREELEAPS_CRUCIBLE_DECERNOR_BIN=$work/bin/no-extended"
# A checker on PATH must not be found when the variable is unset.
PATH="$work/bin:$PATH" expect_refused "checker on PATH only" "is required" resolve_release_decernor
expect_accepted "checker 0.1.9" resolve_release_decernor "THREELEAPS_CRUCIBLE_DECERNOR_BIN=$work/bin/decernor"
expect_accepted "checker at minimum" resolve_release_decernor "THREELEAPS_CRUCIBLE_DECERNOR_BIN=$work/bin/at-minimum"

# Usage: expect_reason LABEL PATTERN (after a command wrote $work/err and set $rc)
expect_reason() {
    if ((rc == 0)); then
        fail "$1: accepted"
    elif ! grep -q -- "$2" "$work/err"; then
        fail "$1: refused for the wrong reason: $(cat "$work/err")"
    else
        pass "$1: refused"
    fi
}

# --- signing keyring: the default keyring is never used ---------------------
# Stand-ins for gpg, gpgconf and the user database resolve the default keyring
# to fixture directories, so these run without gpg and never touch the real
# keyring. FAKE_GPGCONF_HOME is what gpgconf reports (real gpgconf follows
# HOME); FAKE_ACCOUNT_HOME is the user-database home; FAKE_OS selects dscl
# (Darwin) or getent; FAKE_FAIL names one lookup that fails.
mkdir "$work/fakebin"
fake_tool() {
    printf '#!/usr/bin/env bash\n%s\n' "$2" >"$work/fakebin/$1"
    chmod 755 "$work/fakebin/$1"
}
fake_tool gpg 'exit 0'
fake_tool gpgconf '[ "${FAKE_FAIL:-}" = gpgconf ] && exit 2
[ "$*" = "--list-dirs homedir" ] && [ -z "${GNUPGHOME:-}" ] && { echo "$FAKE_GPGCONF_HOME"; exit 0; }
exit 3'
fake_tool uname '[ "${FAKE_FAIL:-}" = uname ] && exit 1; echo "${FAKE_OS:-Linux}"'
fake_tool id '[ "${FAKE_FAIL:-}" = id ] && exit 1; [ "$*" = -un ] && echo releaser'
fake_tool dscl '[ "${FAKE_FAIL:-}" = account ] && exit 1
[ "$*" = ". -read /Users/releaser NFSHomeDirectory" ] && echo "NFSHomeDirectory: $FAKE_ACCOUNT_HOME"'
fake_tool getent '[ "${FAKE_FAIL:-}" = account ] && exit 2
[ "$*" = "passwd releaser" ] && echo "releaser:x:501:20:Releaser:$FAKE_ACCOUNT_HOME:/bin/sh"'
fakepath="$work/fakebin:$PATH"

mkdir -m 700 "$work/home" "$work/signing" "$work/other" "$work/account" "$work/bare-home"
mkdir -m 700 "$work/home/.gnupg" "$work/account/.gnupg"
ln -s "$work/signing" "$work/signing-link"
ln -s "$work/home/.gnupg" "$work/default-link"
# Baseline: gpgconf's default is HOME's .gnupg, and the account home differs
# from HOME.
keyring() {
    in_env require_signing_keyring PATH="$fakepath" HOME="$work/home" \
        FAKE_GPGCONF_HOME="$work/home/.gnupg" FAKE_ACCOUNT_HOME="$work/account" "$@"
}
expect_keyring_refused() {
    local label="$1" pattern="$2"
    shift 2
    if keyring "$@"; then
        fail "$label: accepted"
    elif ! grep -q -- "$pattern" "$work/err"; then
        fail "$label: refused for the wrong reason: $(cat "$work/err")"
    else
        pass "$label: refused"
    fi
}
expect_keyring_accepted() {
    local label="$1"
    shift
    if keyring "$@"; then
        pass "$label: accepted"
    else
        fail "$label: refused: $(cat "$work/err")"
    fi
}
signing="THREELEAPS_CRUCIBLE_GPG_HOMEDIR=$work/signing"
expect_keyring_refused "keyring unset" "the default GPG keyring is never used"
expect_keyring_refused "keyring empty" "the default GPG keyring is never used" THREELEAPS_CRUCIBLE_GPG_HOMEDIR=
expect_keyring_refused "keyring relative path" "absolute path" THREELEAPS_CRUCIBLE_GPG_HOMEDIR=signing
expect_keyring_refused "keyring missing" "absolute path" "THREELEAPS_CRUCIBLE_GPG_HOMEDIR=$work/absent"
expect_keyring_refused "keyring symlink" "non-symlink" "THREELEAPS_CRUCIBLE_GPG_HOMEDIR=$work/signing-link"
expect_keyring_refused "keyring is gpgconf's default" "resolves to the default GPG keyring" \
    "THREELEAPS_CRUCIBLE_GPG_HOMEDIR=$work/home/.gnupg"
expect_keyring_refused "keyring is gpgconf's default, other spelling" "resolves to the default GPG keyring" \
    "THREELEAPS_CRUCIBLE_GPG_HOMEDIR=$work/home/.gnupg/../.gnupg"
expect_keyring_refused "keyring reached through a symlinked parent" "non-symlink" \
    "THREELEAPS_CRUCIBLE_GPG_HOMEDIR=$work/default-link"
# HOME without a .gnupg: gpgconf follows HOME and reports a directory that
# does not exist, so only the user-database home sees the real keyring.
bare=(HOME="$work/bare-home" FAKE_GPGCONF_HOME="$work/bare-home/.gnupg")
expect_keyring_refused "HOME without .gnupg, keyring is the account keyring" \
    "resolves to the default GPG keyring" "${bare[@]}" "THREELEAPS_CRUCIBLE_GPG_HOMEDIR=$work/account/.gnupg"
expect_keyring_refused "HOME without .gnupg, keyring is the account keyring (dscl)" \
    "resolves to the default GPG keyring" "${bare[@]}" FAKE_OS=Darwin \
    "THREELEAPS_CRUCIBLE_GPG_HOMEDIR=$work/account/.gnupg"
expect_keyring_refused "HOME unset, keyring is the account keyring" "resolves to the default GPG keyring" \
    FAKE_GPGCONF_HOME=/nonexistent/.gnupg "THREELEAPS_CRUCIBLE_GPG_HOMEDIR=$work/account/.gnupg"
# A resolution that cannot be made is a refusal, never a skipped comparison.
expect_keyring_refused "gpgconf fails" "gpgconf did not report" FAKE_FAIL=gpgconf "$signing"
expect_keyring_refused "gpgconf reports a relative homedir" "gpgconf did not report" FAKE_GPGCONF_HOME=.gnupg "$signing"
expect_keyring_refused "account lookup fails (getent)" "account lookup for releaser failed" FAKE_FAIL=account "$signing"
expect_keyring_refused "account lookup fails (dscl)" "account lookup for releaser failed" FAKE_FAIL=account \
    FAKE_OS=Darwin "$signing"
expect_keyring_refused "account home is relative" "not an absolute path" FAKE_ACCOUNT_HOME=relative "$signing"
expect_keyring_refused "account home is empty" "not an absolute path" FAKE_ACCOUNT_HOME= "$signing"
expect_keyring_refused "id fails" "id failed" FAKE_FAIL=id "$signing"
expect_keyring_refused "uname fails" "uname failed" FAKE_FAIL=uname "$signing"
mkdir "$work/gpg-only"
ln -s "$work/fakebin/gpg" "$work/gpg-only/gpg"
expect_keyring_refused "no gpgconf beside gpg" "no gpgconf beside" PATH="$work/gpg-only:$fakepath" "$signing"
expect_keyring_refused "inherited GNUPGHOME differs" "GNUPGHOME is set to a different directory" \
    "$signing" "GNUPGHOME=$work/other"
expect_keyring_refused "inherited GNUPGHOME missing" "GNUPGHOME is set to a different directory" \
    "$signing" "GNUPGHOME=$work/absent"
expect_keyring_accepted "dedicated keyring (getent)" "$signing"
expect_keyring_accepted "dedicated keyring (dscl)" FAKE_OS=Darwin "$signing"
expect_keyring_accepted "dedicated keyring, HOME without .gnupg" "${bare[@]}" "$signing"
expect_keyring_accepted "dedicated keyring with matching GNUPGHOME" "$signing" "GNUPGHOME=$work/signing"

# --- signing program: OpenPGP through gpg, nothing else ----------------------
git init --quiet "$work/sign-repo"
signing_program() {
    rc=0
    (cd "$work/sign-repo" && env -i PATH="$PATH" HOME="$work" GIT_CONFIG_NOSYSTEM=1 "$@" bash -c \
        'source "$1"; require_signing_program' _ "$root/scripts/release-env.sh") >"$work/out" 2>"$work/err" || rc=$?
}
expect_signing_refused() {
    local label="$1" key="$2" value="$3"
    git -C "$work/sign-repo" config "$key" "$value"
    signing_program
    git -C "$work/sign-repo" config --unset-all "$key"
    expect_reason "$label" "git config $key is"
}
expect_signing_refused "gpg.program is another program" gpg.program "$work/fakebin/gpg"
expect_signing_refused "gpg.program is gpg2" gpg.program gpg2
expect_signing_refused "gpg.format is ssh" gpg.format ssh
expect_signing_refused "gpg.format is x509" gpg.format x509
expect_signing_refused "gpg.openpgp.program is another program" gpg.openpgp.program "$work/fakebin/gpg"
signing_program GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=gpg.format GIT_CONFIG_VALUE_0=ssh
expect_reason "gpg.format=ssh from the environment" "git config gpg.format is"
git -C "$work/sign-repo" config gpg.program gpg
git -C "$work/sign-repo" config --add gpg.program /usr/local/bin/other
signing_program
git -C "$work/sign-repo" config --unset-all gpg.program
expect_reason "gpg.program set twice" "git config gpg.program is"
signing_program
if ((rc == 0)); then pass "no signing configuration: accepted"; else
    fail "no signing configuration: refused: $(cat "$work/err")"
fi
git -C "$work/sign-repo" config gpg.program gpg
git -C "$work/sign-repo" config gpg.format openpgp
signing_program
if ((rc == 0)); then pass "gpg.program=gpg, gpg.format=openpgp: accepted"; else
    fail "gpg.program=gpg, gpg.format=openpgp: refused: $(cat "$work/err")"
fi
git -C "$work/sign-repo" config --unset gpg.program
git -C "$work/sign-repo" config --unset gpg.format
# The signing command pins all three keys over any lower-precedence value.
pinned="$(cd "$work/sign-repo" && env -i PATH="$PATH" HOME="$work" GIT_CONFIG_NOSYSTEM=1 \
    GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=gpg.format GIT_CONFIG_VALUE_0=ssh \
    GIT_CONFIG_KEY_1=gpg.openpgp.program GIT_CONFIG_VALUE_1=/elsewhere bash -c \
    'source "$1"; for k in gpg.format gpg.program gpg.openpgp.program; do release_signing_git config --get "$k"; done' \
    _ "$root/scripts/release-env.sh" | tr '\n' ' ')"
if [[ "$pinned" == "openpgp gpg gpg " ]]; then
    pass "signing command pins gpg.format, gpg.program and gpg.openpgp.program"
else
    fail "signing command pins: got '$pinned'"
fi
if grep -nE '(^|[^_])git( -c [^ ]+)* (tag -s|verify-tag)' "$root/scripts/release-tag.sh" >"$work/out"; then
    fail "release-tag.sh signs or verifies without release_signing_git: $(cat "$work/out")"
else
    pass "release-tag.sh signs and verifies only through release_signing_git"
fi

# --- release transport: one URL, the org token, nothing else -----------------
# Fixture: an org directory with a repository below it. A stand-in direnv
# exports FAKE_ENVRC as DIRENV_FILE and FAKE_ENVRC_TOKEN as GH_TOKEN, or
# fails when FAKE_DIRENV_BLOCKED is set. A stand-in git runs real git for
# config; for any other command it asks real git, under the same -c options,
# which credential answers for github.com, and logs the subcommand, its last
# two arguments and that answer. A stray helper in the repository config
# answers if the helper reset does not hold.
real_git="$(command -v git)"
mkdir -p "$work/org/repo/scripts" "$work/transport-bin"
"$real_git" init --quiet "$work/org/repo"
cp "$root/scripts/release-env.sh" "$work/org/repo/scripts/release-env.sh"
printf '#!/usr/bin/env bash\n[ "$1" = get ] && printf "username=stray\\npassword=stray-secret\\n"\nexit 0\n' \
    >"$work/stray-helper"
chmod 755 "$work/stray-helper"
"$real_git" -C "$work/org/repo" config credential.helper "$work/stray-helper"
"$real_git" -C "$work/org/repo" config credential.https://github.com.helper "$work/stray-helper"
printf '%s\n' '#!/usr/bin/env bash' \
    '[ "$1" = exec ] || exit 2' \
    '[ -n "${FAKE_DIRENV_BLOCKED:-}" ] && { echo "direnv: error .envrc is blocked" >&2; exit 1; }' \
    'shift 2' \
    '[ -n "${FAKE_ENVRC:-}" ] && export DIRENV_FILE="$FAKE_ENVRC"' \
    '[ -n "${FAKE_ENVRC_TOKEN:-}" ] && export GH_TOKEN="$FAKE_ENVRC_TOKEN"' \
    'exec "$@"' >"$work/transport-bin/direnv"
printf '%s\n' '#!/usr/bin/env bash' \
    '[ "$*" = "auth git-credential get" ] && printf "username=x-access-token\npassword=%s\n" "$GH_TOKEN"' \
    'exit 0' >"$work/transport-bin/gh"
printf '%s\n' '#!/usr/bin/env bash' \
    "real_git='$real_git' log='$work/git.log'" \
    'opts=()' \
    'while [ "${1:-}" = -c ]; do opts+=(-c "$2"); shift 2; done' \
    'if [ "${1:-}" = config ] || [ "${#opts[@]}" -eq 0 ]; then exec "$real_git" "${opts[@]}" "$@"; fi' \
    'answer="$(printf "protocol=https\nhost=github.com\npath=3leaps/crucible.git\n\n" |' \
    '    "$real_git" "${opts[@]}" credential fill 2>/dev/null | grep -E "^(username|password)=" | tr "\n" " ")"' \
    'echo "$1 ${*: -2:1} ${*: -1} | $answer" >>"$log"' >"$work/transport-bin/git"
chmod 755 "$work/transport-bin/direnv" "$work/transport-bin/gh" "$work/transport-bin/git"
transport_path="$work/transport-bin:$PATH"
transport() {
    rc=0
    : >"$work/git.log"
    (cd "$work/org/repo" && env -i PATH="$transport_path" HOME="$work" GIT_CONFIG_NOSYSTEM=1 \
        FAKE_ENVRC="$work/org/.envrc" FAKE_ENVRC_TOKEN=org-token "$@" bash -c \
        'source scripts/release-env.sh; release_remote_git "$PWD" ls-remote --tags "$RELEASE_PUSH_URL" refs/tags/v0.0.0') \
        >"$work/out" 2>"$work/err" || rc=$?
}
expect_no_contact() {
    local label="$1" pattern="$2"
    shift 2
    transport "$@"
    if [ -s "$work/git.log" ]; then
        fail "$label: git contacted the remote: $(cat "$work/git.log")"
    else
        expect_reason "$label" "$pattern"
    fi
}
expected_contact="ls-remote https://github.com/3leaps/crucible.git refs/tags/v0.0.0 | username=x-access-token password=org-token "
transport
if ((rc == 0)) && [[ "$(cat "$work/git.log")" == "$expected_contact" ]]; then
    pass "transport: explicit URL, org token through gh only"
else
    fail "transport: rc=$rc log='$(cat "$work/git.log")' err='$(cat "$work/err")'"
fi
transport GH_TOKEN=ambient-token GITHUB_TOKEN=ambient-token
if ((rc == 0)) && [[ "$(cat "$work/git.log")" == "$expected_contact" ]]; then
    pass "transport: an inherited GH_TOKEN is replaced by the org token"
else
    fail "transport with an inherited token: rc=$rc log='$(cat "$work/git.log")'"
fi
expect_no_contact "transport: no org token, inherited GH_TOKEN" "did not set GH_TOKEN" \
    FAKE_ENVRC_TOKEN= GH_TOKEN=ambient-token
expect_no_contact "transport: no .envrc loaded, inherited DIRENV_FILE and token" "no .envrc was loaded" \
    FAKE_ENVRC= DIRENV_FILE="$work/org/.envrc" GH_TOKEN=ambient-token
expect_no_contact "transport: .envrc inside the repository" "is not above the repository" \
    FAKE_ENVRC="$work/org/repo/.envrc"
mkdir "$work/elsewhere"
expect_no_contact "transport: .envrc beside, not above, the repository" "is not above the repository" \
    FAKE_ENVRC="$work/elsewhere/.envrc"
expect_no_contact "transport: .envrc directory does not exist" "could not resolve the loaded .envrc" \
    FAKE_ENVRC="$work/absent/.envrc"
expect_no_contact "transport: blocked .envrc" ".envrc is blocked" FAKE_DIRENV_BLOCKED=1
mkdir "$work/no-direnv" "$work/no-gh"
ln -s "$work/transport-bin/git" "$work/no-direnv/git"
ln -s "$work/transport-bin/gh" "$work/no-direnv/gh"
ln -s "$work/transport-bin/git" "$work/no-gh/git"
ln -s "$work/transport-bin/direnv" "$work/no-gh/direnv"
expect_no_contact "transport: direnv missing" "direnv not found" PATH="$work/no-direnv:/usr/bin:/bin"
expect_no_contact "transport: gh missing" "gh not found" PATH="$work/no-gh:/usr/bin:/bin"
for setting in "url.git@github.com:.insteadOf=https://github.com/" \
    "url.https://example.invalid/.pushInsteadOf=https://github.com/" \
    "http.https://github.com/.extraHeader=AUTHORIZATION: basic eA==" \
    "http.extraHeader=AUTHORIZATION: basic eA=="; do
    key="${setting%%=*}"
    "$real_git" -C "$work/org/repo" config "$key" "${setting#*=}"
    expect_no_contact "transport: repository $key" "rewrites or adds headers"
    "$real_git" -C "$work/org/repo" config --unset "$key"
done
printf '[url "git@github.com:"]\n\tinsteadOf = https://github.com/\n' >"$work/.gitconfig"
expect_no_contact "transport: global insteadOf" "rewrites or adds headers"
rm "$work/.gitconfig"
expect_no_contact "transport: insteadOf from the environment" "rewrites or adds headers" \
    GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=url.git@github.com:.insteadOf GIT_CONFIG_VALUE_0=https://github.com/
if grep -nE '^[^#"]*\<origin\>' "$root/scripts/release-push-tag.sh" >"$work/out"; then
    fail "release-push-tag.sh uses origin: $(cat "$work/out")"
else
    pass "release-push-tag.sh does not use origin"
fi
if grep -nE '^[^#]*(^|[^_])git ([^ ]+ )*(fetch|push|ls-remote)' "$root/scripts/release-push-tag.sh" >"$work/out"; then
    fail "release-push-tag.sh contacts a remote outside release_remote_git: $(cat "$work/out")"
else
    pass "release-push-tag.sh contacts the remote only through release_remote_git"
fi

# --- entry points refuse before side effects --------------------------------
# The outermost layer the maintainer invokes must refuse a bare variable,
# including one passed on the make command line (PDR-0008 §2.4).
version="$(tr -d ' \t\r\n' <"$root/VERSION")"
run_make() {
    env -i PATH="$PATH" HOME="$work" "$@" make --no-print-directory -s -C "$root" release-guard-tag-version \
        >"$work/out" 2>"$work/err"
}
rc=0 && run_make || rc=$?
expect_reason "make guard without tag" "THREELEAPS_CRUCIBLE_RELEASE_TAG is required"
rc=0 && env -i PATH="$PATH" HOME="$work" make --no-print-directory -s -C "$root" release-guard-tag-version \
    "RELEASE_TAG=v$version" >"$work/out" 2>"$work/err" || rc=$?
expect_reason "make guard with RELEASE_TAG on the command line" "retired or unprefixed release variable set: RELEASE_TAG"
rc=0 && run_make "CRUCIBLE_RELEASE_TAG=v$version" || rc=$?
expect_reason "make guard with legacy CRUCIBLE_RELEASE_TAG" "retired or unprefixed release variable set: CRUCIBLE_RELEASE_TAG"
rc=0 && run_make "THREELEAPS_CRUCIBLE_RELEASE_TAG=v0.0.0" || rc=$?
expect_reason "make guard with a tag that is not VERSION" "release tag/version mismatch"
if run_make "THREELEAPS_CRUCIBLE_RELEASE_TAG=v$version"; then
    pass "make guard with the explicit prefixed tag: accepted"
else
    fail "make guard with the explicit prefixed tag: refused: $(cat "$work/err")"
fi

for script in release-tag.sh release-verify-tag.sh release-push-tag.sh; do
    if env -i PATH="$PATH" HOME="$work" "$root/scripts/$script" >"$work/out" 2>"$work/err"; then
        fail "$script without a tag: accepted"
    elif ! grep -q "THREELEAPS_CRUCIBLE_RELEASE_TAG is required" "$work/err"; then
        fail "$script without a tag: refused for the wrong reason: $(cat "$work/err")"
    else
        pass "$script without a tag: refused"
    fi
    if env -i PATH="$PATH" HOME="$work" THREELEAPS_CRUCIBLE_RELEASE_TAG="v$version" \
        "$root/scripts/$script" >"$work/out" 2>"$work/err"; then
        fail "$script without a checker: accepted"
    elif ! grep -q "THREELEAPS_CRUCIBLE_DECERNOR_BIN is required" "$work/err"; then
        fail "$script without a checker: refused for the wrong reason: $(cat "$work/err")"
    else
        pass "$script without a checker: refused"
    fi
done
rc=0 && "$root/scripts/verify-pinned-tag.sh" >"$work/out" 2>"$work/err" || rc=$?
expect_reason "verify-pinned-tag.sh without a tag" "the release tag is never derived"

fake_checker "$work/bin/entry-decernor" "decernor 0.1.9" 0.1.9
if env -i PATH="$PATH" HOME="$work/home" THREELEAPS_CRUCIBLE_RELEASE_TAG="v$version" \
    THREELEAPS_CRUCIBLE_DECERNOR_BIN="$work/bin/entry-decernor" \
    "$root/scripts/release-tag.sh" >"$work/out" 2>"$work/err"; then
    fail "release-tag.sh without a signing keyring: accepted"
elif ! grep -q "the default GPG keyring is never used" "$work/err"; then
    fail "release-tag.sh without a signing keyring: refused for the wrong reason: $(cat "$work/err")"
else
    pass "release-tag.sh without a signing keyring: refused"
fi

# A configured signer other than OpenPGP through gpg stops the tag step
# before anything else runs.
rc=0 && env -i PATH="$fakepath" HOME="$work/home" FAKE_GPGCONF_HOME="$work/home/.gnupg" \
    FAKE_ACCOUNT_HOME="$work/account" THREELEAPS_CRUCIBLE_RELEASE_TAG="v$version" \
    THREELEAPS_CRUCIBLE_DECERNOR_BIN="$work/bin/entry-decernor" THREELEAPS_CRUCIBLE_GPG_HOMEDIR="$work/signing" \
    GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=gpg.format GIT_CONFIG_VALUE_0=ssh \
    "$root/scripts/release-tag.sh" >"$work/out" 2>"$work/err" || rc=$?
expect_reason "release-tag.sh with gpg.format=ssh" "git config gpg.format is 'ssh'"

if ((failures)); then
    echo "[!!] release input controls: $failures failure(s)" >&2
    exit 1
fi
echo "[ok] release input controls passed"
