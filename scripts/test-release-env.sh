#!/usr/bin/env bash
# test-release-env.sh - Negative controls for explicit release inputs
#
# Proves each refusal in scripts/release-env.sh fires (PDR-0008 §2.3, §2.4;
# EPR-0002), and that the Makefile entry point does not let a bare variable
# win. Needs neither gpg nor a real checker: fake checker binaries stand in.

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

# --- entry points refuse before side effects --------------------------------
# The outermost layer the maintainer invokes must refuse a bare variable,
# including one passed on the make command line (PDR-0008 §2.4).
version="$(tr -d ' \t\r\n' <"$root/VERSION")"
run_make() {
    env -i PATH="$PATH" HOME="$work" "$@" make --no-print-directory -s -C "$root" release-guard-tag-version \
        >"$work/out" 2>"$work/err"
}
if run_make; then fail "make guard without tag: accepted"; else pass "make guard without tag: refused"; fi
if env -i PATH="$PATH" HOME="$work" make --no-print-directory -s -C "$root" release-guard-tag-version \
    "RELEASE_TAG=v$version" >"$work/out" 2>"$work/err"; then
    fail "make guard with RELEASE_TAG on the command line: accepted"
else
    pass "make guard with RELEASE_TAG on the command line: refused"
fi
if run_make "CRUCIBLE_RELEASE_TAG=v$version"; then
    fail "make guard with legacy CRUCIBLE_RELEASE_TAG: accepted"
else
    pass "make guard with legacy CRUCIBLE_RELEASE_TAG: refused"
fi
if run_make "THREELEAPS_CRUCIBLE_RELEASE_TAG=v0.0.0"; then
    fail "make guard with a tag that is not VERSION: accepted"
else
    pass "make guard with a tag that is not VERSION: refused"
fi
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
if "$root/scripts/verify-pinned-tag.sh" >"$work/out" 2>"$work/err"; then
    fail "verify-pinned-tag.sh without a tag: accepted"
else
    pass "verify-pinned-tag.sh without a tag: refused"
fi

if ((failures)); then
    echo "[!!] release input controls: $failures failure(s)" >&2
    exit 1
fi
echo "[ok] release input controls passed"
