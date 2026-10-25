#!/usr/bin/env bash
# test-release-github-verified.sh - Controls for the post-push verified-flag check
#
# Stubs gh to prove check_github_verified distinguishes a verified tag, a
# failed read of an already-pushed tag, an explicit "not verified", and a
# missing gh. Needs no network and pushes nothing. The check runs with PATH
# set to a controlled directory only, so a gh installed on the host is never
# found or invoked.

set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
bash_bin="$(command -v bash)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir "$work/bin" "$work/sysbin"

# Stands in for a gh installed on the host; it must never run.
cat >"$work/sysbin/gh" <<EOF
#!$bash_bin
echo SYSTEM_GH_WAS_INVOKED >&2
exit 91
EOF
chmod 755 "$work/sysbin/gh"

failures=0
pass() { echo "[ok] $1"; }
fail() {
    echo "[!!] $1" >&2
    failures=$((failures + 1))
}

# Usage: run MODE; MODE is verified | unverified | unreadable | absent.
run() {
    rm -f "$work/bin/gh"
    if [[ "$1" != absent ]]; then
        cat >"$work/bin/gh" <<EOF
#!$bash_bin
case "$1" in
  verified) echo true ;;
  unverified) echo false ;;
  unreadable) echo 'gh: Bad credentials (HTTP 401)' >&2; exit 1 ;;
esac
EOF
        chmod 755 "$work/bin/gh"
    fi
    rc=0
    env -i PATH="$work/bin" "$bash_bin" -c \
        'source "$1"; check_github_verified v9.9.9 0123456789abcdef0123456789abcdef01234567' \
        _ "$root/scripts/release-github-verified.sh" >"$work/out" 2>"$work/err" || rc=$?
}

run verified
if ((rc == 0)) && grep -q 'GitHub reports v9.9.9 verified' "$work/out"; then
    pass "verified tag: accepted"
else
    fail "verified tag: rc=$rc $(cat "$work/out" "$work/err")"
fi

run unreadable
if ((rc == 0)); then
    fail "unreadable flag: accepted"
elif ! grep -q 'is pushed, but GitHub.s verified flag could not be read' "$work/err"; then
    fail "unreadable flag: refused for the wrong reason: $(cat "$work/err")"
elif ! grep -q 'do not push or delete the tag again' "$work/err"; then
    fail "unreadable flag: no warning against re-pushing"
else
    pass "unreadable flag: reported as a read failure of a pushed tag"
fi

run unverified
if ((rc == 0)); then
    fail "unverified tag: accepted"
elif ! grep -q 'GitHub does not report it verified' "$work/err"; then
    fail "unverified tag: refused for the wrong reason: $(cat "$work/err")"
else
    pass "unverified tag: refused"
fi

run absent
if ((rc == 0)) && grep -q 'was not checked' "$work/out"; then
    pass "gh absent: check reported as skipped"
else
    fail "gh absent: rc=$rc $(cat "$work/out" "$work/err")"
fi

# A gh on the caller's PATH must not leak into the absent case.
PATH="$work/sysbin:$PATH" run absent
if grep -q SYSTEM_GH_WAS_INVOKED "$work/out" "$work/err"; then
    fail "gh absent with a host gh: the host gh was invoked"
elif ((rc == 0)) && grep -q 'was not checked' "$work/out"; then
    pass "gh absent with a host gh: host gh not used, check reported as skipped"
else
    fail "gh absent with a host gh: rc=$rc $(cat "$work/out" "$work/err")"
fi

if ((failures)); then
    echo "[!!] GitHub verified-flag controls: $failures failure(s)" >&2
    exit 1
fi
echo "[ok] GitHub verified-flag controls passed"
