#!/usr/bin/env bash
# test-release-identity.sh - End-to-end controls for the release identity chain
#
# Builds a throwaway repository carrying this repository's release scripts and
# an ephemeral OpenPGP primary + signing subkey, derives the anchors with the
# designated checker, signs a tag, and proves that verify-pinned-tag.sh accepts
# it and refuses each tampered input (PDR-0008 §2.1-§2.4; EPR-0002).
#
# Requires gpg and THREELEAPS_CRUCIBLE_DECERNOR_BIN (the digest-pinned checker).
# Missing prerequisites fail; this control never skips.

set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

die() {
    echo "error: $*" >&2
    exit 1
}
command -v gpg >/dev/null 2>&1 || die "gpg is required for the release identity controls"
[[ -n "${THREELEAPS_CRUCIBLE_DECERNOR_BIN:-}" ]] ||
    die "THREELEAPS_CRUCIBLE_DECERNOR_BIN is required for the release identity controls"
checker="$THREELEAPS_CRUCIBLE_DECERNOR_BIN"

work="$(mktemp -d)"
cleanup() {
    gpgconf --homedir "$work/gnupg" --kill all >/dev/null 2>&1 || true
    rm -rf "$work"
}
trap cleanup EXIT
chmod 700 "$work"

failures=0
pass() { echo "[ok] $1"; }
fail() {
    echo "[!!] $1" >&2
    failures=$((failures + 1))
}

# --- ephemeral signing identity ---------------------------------------------
tagger_name="Release Control Fixture"
tagger_email="release-control@example.invalid"
export GNUPGHOME="$work/gnupg"
mkdir -m 700 "$GNUPGHOME"
gpg --batch --quiet --passphrase '' --quick-generate-key "$tagger_name <$tagger_email>" ed25519 cert 1d 2>/dev/null
primary="$(gpg --batch --with-colons --list-keys "$tagger_email" | awk -F: '$1=="fpr" {print $10; exit}')"
gpg --batch --quiet --passphrase '' --quick-add-key "$primary" ed25519 sign 1d 2>/dev/null
signing="$(gpg --batch --with-colons --with-subkey-fingerprint --list-keys "$primary" |
    awk -F: '$1=="sub" {s=1; next} s && $1=="fpr" {print $10; exit}')"
[[ "$primary" =~ ^[0-9A-F]{40}$ && "$signing" =~ ^[0-9A-F]{40}$ ]] || die "fixture key generation failed"

# --- fixture repository -------------------------------------------------------
repo="$work/repo"
mkdir -p "$repo/scripts" "$repo/docs/security" "$repo/config/release" "$repo/keys"
for script in release-env.sh release-verify-anchors.sh release-derive-anchors.sh verify-pinned-tag.sh \
    release-verify-tag.sh; do
    cp "$root/scripts/$script" "$repo/scripts/$script"
done
gpg --batch --armor --export "$primary" >"$repo/docs/security/release-signing-keys.asc"
# Fixture minisign pin: this repository's public key (public data; the
# control proves anchoring, not minisign signing).
cp "$root/docs/security/crucible-minisign.pub" "$repo/docs/security/crucible-minisign.pub"
printf '%s <%s>\n' "$tagger_name" "$tagger_email" >"$repo/config/release/tagger-identity.txt"

git_fixture() { git -C "$repo" -c user.name="$tagger_name" -c user.email="$tagger_email" "$@"; }
git_fixture init --quiet --initial-branch=main
(cd "$repo" && THREELEAPS_CRUCIBLE_DECERNOR_BIN="$checker" ./scripts/release-derive-anchors.sh --write) >/dev/null
git_fixture add -A
git_fixture commit --quiet -m "fixture"
base="$(git -C "$repo" rev-parse HEAD)"

sign_tag() {
    git_fixture -c gpg.program=gpg tag -s -a "$1" -u "$signing!" -m "Release $1"
}

# Run verify-pinned-tag.sh in the fixture with a clean environment.
verify() {
    local tag="$1"
    shift
    (cd "$repo" && env -i PATH="$PATH" HOME="$work" GNUPGHOME="$work/verify-gnupg" \
        THREELEAPS_CRUCIBLE_DECERNOR_BIN="$checker" "$@" ./scripts/verify-pinned-tag.sh "$tag") \
        >"$work/out" 2>"$work/err"
}
expect_ok() {
    if verify "$@"; then pass "$label: accepted"; else fail "$label: refused: $(cat "$work/err")"; fi
}
expect_refused() {
    local pattern="$1"
    shift
    if verify "$@"; then
        fail "$label: accepted"
    elif ! grep -q -- "$pattern" "$work/err"; then
        fail "$label: refused for the wrong reason: $(cat "$work/err")"
    else
        pass "$label: refused"
    fi
}

# Commit a tampered tree on a side branch and tag it. Usage: tampered TAG CMD...
tampered() {
    local tag="$1"
    shift
    git_fixture checkout --quiet -B "side-$tag" "$base"
    (cd "$repo" && "$@")
    git_fixture add -A
    git_fixture commit --quiet -m "tamper $tag"
    sign_tag "$tag"
    git_fixture checkout --quiet main
}

# --- positive control ---------------------------------------------------------
sign_tag v1.0.0
label="pinned tag" expect_ok v1.0.0
label="committed anchors re-derive" && if (cd "$repo" && THREELEAPS_CRUCIBLE_DECERNOR_BIN="$checker" \
    ./scripts/release-derive-anchors.sh --check) >"$work/out" 2>"$work/err"; then
    pass "$label"
else
    fail "$label: $(cat "$work/err")"
fi

# --- the ambient keyring is never consulted ---------------------------------
# An ambient keyring holding a key outside the pin, which signed a forged tag,
# must not make that tag verify; an empty ambient keyring must not stop the
# pinned tag verifying. Run through the release-verify-tag.sh entry point.
mkdir -m 700 "$work/rogue-gnupg" "$work/empty-gnupg"
GNUPGHOME="$work/rogue-gnupg" gpg --batch --quiet --passphrase '' \
    --quick-generate-key "$tagger_name <$tagger_email>" ed25519 sign 1d 2>/dev/null
rogue="$(GNUPGHOME="$work/rogue-gnupg" gpg --batch --with-colons --list-keys "$tagger_email" |
    awk -F: '$1=="fpr" {print $10; exit}')"
GNUPGHOME="$work/rogue-gnupg" git_fixture -c gpg.program=gpg tag -s -a v1.0.8 -u "$rogue!" -m "Release v1.0.8"
entry() {
    local tag="$1" ambient="$2"
    rc=0
    (cd "$repo" && env -i PATH="$PATH" HOME="$work" GNUPGHOME="$ambient" \
        THREELEAPS_CRUCIBLE_DECERNOR_BIN="$checker" THREELEAPS_CRUCIBLE_RELEASE_TAG="$tag" \
        ./scripts/release-verify-tag.sh) >"$work/out" 2>"$work/err" || rc=$?
}
entry v1.0.0 "$work/empty-gnupg"
if ((rc == 0)); then pass "pinned tag with an empty ambient keyring: accepted"; else
    fail "pinned tag with an empty ambient keyring: refused: $(cat "$work/err")"
fi
entry v1.0.8 "$work/rogue-gnupg"
if ((rc == 0)); then
    fail "tag signed by an ambient-only key: accepted"
elif ! grep -q "tag signature invalid under pin\|not a single good signature by the pinned signing subkey" "$work/err"; then
    fail "tag signed by an ambient-only key: refused for the wrong reason: $(cat "$work/err")"
else
    pass "tag signed by an ambient-only key: refused"
fi
gpgconf --homedir "$work/rogue-gnupg" --kill all >/dev/null 2>&1 || true

# --- checker binding at verify time -------------------------------------------
label="verify without a checker" expect_refused "THREELEAPS_CRUCIBLE_DECERNOR_BIN is required" v1.0.0 \
    THREELEAPS_CRUCIBLE_DECERNOR_BIN=
ln -s "$checker" "$work/decernor-link"
label="verify with a symlinked checker" expect_refused "non-symlink" v1.0.0 \
    THREELEAPS_CRUCIBLE_DECERNOR_BIN="$work/decernor-link"
label="verify with a legacy variable set" expect_refused "retired or unprefixed" v1.0.0 \
    CRUCIBLE_RELEASE_TAG=v1.0.0

# --- pins come from the tagged commit, not the working tree or environment ----
cp "$repo/keys/expected-fingerprints.txt" "$work/anchors.saved"
printf 'gpg %040d\nminisign %064d\n' 0 0 >"$repo/keys/expected-fingerprints.txt"
label="working-tree anchor edit ignored" expect_ok v1.0.0
cp "$work/anchors.saved" "$repo/keys/expected-fingerprints.txt"
# A different, valid key offered through plausible override names is not read.
label="environment pin override ignored" expect_ok v1.0.0 \
    THREELEAPS_CRUCIBLE_MINISIGN_PUB="$root/docs/security/fulmenhq-goneat-minisign.pub" \
    THREELEAPS_CRUCIBLE_ANCHORS="$work/absent.txt"

# --- tampered committed inputs ----------------------------------------------
tampered v1.0.1 sed -i.bak "s/^minisign .*/minisign $(printf '%064d' 1)/" keys/expected-fingerprints.txt
rm -f "$repo/keys/expected-fingerprints.txt.bak"
label="minisign anchor mismatch" expect_refused "differ from their anchors" v1.0.1

tampered v1.0.2 sed -i.bak "s/^gpg .*/gpg $(printf '%040d' 2)/" keys/expected-fingerprints.txt
rm -f "$repo/keys/expected-fingerprints.txt.bak"
label="gpg anchor mismatch" expect_refused "differ from their anchors" v1.0.2

tampered v1.0.3 cp "$root/docs/security/fulmenhq-goneat-minisign.pub" docs/security/crucible-minisign.pub
label="minisign pin swapped" expect_refused "differ from their anchors" v1.0.3

tampered v1.0.4 rm keys/expected-fingerprints.ndjson
label="NDJSON anchors missing" expect_refused "expected-fingerprints.ndjson required" v1.0.4

tampered v1.0.5 git mv docs/security/crucible-minisign.pub docs/security/release-minisign.pub
label="pin under its retired name" expect_refused "crucible-minisign.pub required" v1.0.5

tampered v1.0.6 sh -c 'printf "Someone Else <other@example.invalid>\n" >config/release/tagger-identity.txt'
label="tagger identity mismatch" expect_refused "does not match committed tagger identity" v1.0.6

# --- tag input ------------------------------------------------------------
label="absent tag" expect_refused "tag v9.9.9 absent" v9.9.9
git_fixture tag v1.0.7
label="lightweight tag" expect_refused "annotated tag required" v1.0.7
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
rc=0 && (cd "$repo" && env -i PATH="$PATH" HOME="$work" THREELEAPS_CRUCIBLE_DECERNOR_BIN="$checker" \
    ./scripts/verify-pinned-tag.sh) >"$work/out" 2>"$work/err" || rc=$?
expect_reason "verify with no tag argument" "the release tag is never derived"

# --- anchor derivation --------------------------------------------------------
rc=0 && (cd "$repo" && THREELEAPS_CRUCIBLE_DECERNOR_BIN="$checker" ./scripts/release-derive-anchors.sh --write) \
    >"$work/out" 2>"$work/err" || rc=$?
expect_reason "derive --write over existing anchors" "keys/expected-fingerprints.txt exists"
printf 'gpg %040d\nminisign %064d\n' 0 0 >"$repo/keys/expected-fingerprints.txt"
rc=0 && (cd "$repo" && THREELEAPS_CRUCIBLE_DECERNOR_BIN="$checker" ./scripts/release-derive-anchors.sh --check) \
    >"$work/out" 2>"$work/err" || rc=$?
expect_reason "derive --check against an edited anchor" "keys/expected-fingerprints.txt differs from the checker's derivation"
cp "$work/anchors.saved" "$repo/keys/expected-fingerprints.txt"

# --- this repository's committed pins ----------------------------------------
label="repository anchors re-derive"
if (cd "$root" && ./scripts/release-derive-anchors.sh --check) >"$work/out" 2>"$work/err"; then
    pass "$label"
else
    fail "$label: $(cat "$work/err")"
fi
mkdir "$work/head-pins"
label="repository HEAD pins match anchors"
if (cd "$root" && ./scripts/release-verify-anchors.sh HEAD "$work/head-pins") >"$work/out" 2>"$work/err"; then
    pass "$label"
else
    fail "$label: $(cat "$work/err")"
fi

if ((failures)); then
    echo "[!!] release identity controls: $failures failure(s)" >&2
    exit 1
fi
echo "[ok] release identity controls passed"
