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
gpg --batch --quiet --passphrase '' --quick-generate-key "$tagger_name <$tagger_email>" ed25519 cert 90d 2>/dev/null
primary="$(gpg --batch --with-colons --list-keys "$tagger_email" | awk -F: '$1=="fpr" {print $10; exit}')"
gpg --batch --quiet --passphrase '' --quick-add-key "$primary" ed25519 sign 90d 2>/dev/null
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

# --- key expiration horizon (<30d warning, <=0d fail-closed) -----------------
mkdir -m 700 "$work/soon-gnupg"
GNUPGHOME="$work/soon-gnupg" gpg --batch --quiet --passphrase '' \
    --quick-generate-key "$tagger_name <$tagger_email>" ed25519 cert 10d 2>/dev/null
soon_primary="$(GNUPGHOME="$work/soon-gnupg" gpg --batch --with-colons --list-keys "$tagger_email" |
    awk -F: '$1=="fpr" {print $10; exit}')"
GNUPGHOME="$work/soon-gnupg" gpg --batch --quiet --passphrase '' \
    --quick-add-key "$soon_primary" ed25519 sign 10d 2>/dev/null
soon_signing="$(GNUPGHOME="$work/soon-gnupg" gpg --batch --with-colons --with-subkey-fingerprint --list-keys "$soon_primary" |
    awk -F: '$1=="sub" {s=1; next} s && $1=="fpr" {print $10; exit}')"
git_fixture checkout --quiet -B side-soon "$base"
GNUPGHOME="$work/soon-gnupg" gpg --batch --armor --export "$soon_primary" >"$repo/docs/security/release-signing-keys.asc"
rm -f "$repo/keys/expected-fingerprints.txt" "$repo/keys/expected-fingerprints.ndjson"
if (cd "$repo" && THREELEAPS_CRUCIBLE_DECERNOR_BIN="$checker" ./scripts/release-derive-anchors.sh --write) >"$work/out" 2>"$work/err" &&
    grep -q "warning: pinned release signing subkey $soon_signing expires within 30 days" "$work/err"; then
    pass "key expiring within 30 days emits warning on derive"
else
    fail "key expiring within 30 days did not emit expected warning on derive: $(cat "$work/err")"
fi
git_fixture add -A
git_fixture commit --quiet -m "soon-expiring key"
GNUPGHOME="$work/soon-gnupg" git_fixture -c gpg.program=gpg tag -s -a v1.0.9 -u "$soon_signing!" -m "Release v1.0.9"
git_fixture checkout --quiet main
if verify v1.0.9 && grep -q "warning: pinned release signing subkey $soon_signing expires within 30 days" "$work/err"; then
    pass "key expiring within 30 days accepted with warning on verify-pinned-tag"
else
    fail "key expiring within 30 days failed or missed warning on verify-pinned-tag: $(cat "$work/err")"
fi
gpgconf --homedir "$work/soon-gnupg" --kill all >/dev/null 2>&1 || true

mkdir -m 700 "$work/exp-gnupg"
cat >"$work/gpg-past" <<'EOF'
#!/usr/bin/env bash
exec gpg --faked-system-time 20240101T000000 "$@"
EOF
chmod +x "$work/gpg-past"
GNUPGHOME="$work/exp-gnupg" "$work/gpg-past" --batch --quiet --passphrase '' \
    --quick-generate-key "$tagger_name <$tagger_email>" ed25519 cert 1d 2>/dev/null
exp_primary="$(GNUPGHOME="$work/exp-gnupg" gpg --batch --with-colons --list-keys "$tagger_email" |
    awk -F: '$1=="fpr" {print $10; exit}')"
GNUPGHOME="$work/exp-gnupg" "$work/gpg-past" --batch --quiet --passphrase '' \
    --quick-add-key "$exp_primary" ed25519 sign 1d 2>/dev/null
exp_signing="$(GNUPGHOME="$work/exp-gnupg" gpg --batch --with-colons --with-subkey-fingerprint --list-keys "$exp_primary" |
    awk -F: '$1=="sub" {s=1; next} s && $1=="fpr" {print $10; exit}')"
git_fixture checkout --quiet -B side-expired "$base"
GNUPGHOME="$work/exp-gnupg" gpg --batch --armor --export "$exp_primary" >"$repo/docs/security/release-signing-keys.asc"
rc=0 && (cd "$repo" && THREELEAPS_CRUCIBLE_DECERNOR_BIN="$checker" ./scripts/release-derive-anchors.sh --check) \
    >"$work/out" 2>"$work/err" || rc=$?
expect_reason "expired key refused by release-derive-anchors" "expired at 2024-01-02T00:00:00Z"
"$checker" fingerprint "$repo/docs/security/release-signing-keys.asc" --class public --kind gpg \
    --format ndjson --path-mode none --gpg-role primary >"$work/exp-gpg.ndjson"
"$checker" fingerprint "$repo/docs/security/crucible-minisign.pub" --class public --kind minisign \
    --format ndjson --path-mode none >"$work/exp-minisign.ndjson"
python3 - "$work" "$repo/keys" <<'PY'
import json, pathlib, sys
w = pathlib.Path(sys.argv[1])
k = pathlib.Path(sys.argv[2])
gpg = [json.loads(l) for l in (w / "exp-gpg.ndjson").read_text().splitlines() if l]
ms = [json.loads(l) for l in (w / "exp-minisign.ndjson").read_text().splitlines() if l and "minisign-public-blob-sha256-v1" in l]
(k / "expected-fingerprints.ndjson").write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in (gpg[0], ms[0])))
(k / "expected-fingerprints.txt").write_text(f"gpg {gpg[0]['fingerprint']}\nminisign {ms[0]['fingerprint']}\n")
PY
git_fixture add -A
git_fixture commit --quiet -m "expired key"
GNUPGHOME="$work/exp-gnupg" git_fixture -c gpg.program="$work/gpg-past" tag -s -a v1.0.10 -u "$exp_signing!" -m "Release v1.0.10"
git_fixture checkout --quiet main
label="expired key refused by verify-pinned-tag" expect_refused "expired at 2024-01-02T00:00:00Z" v1.0.10
gpgconf --homedir "$work/exp-gnupg" --kill all >/dev/null 2>&1 || true

mkdir -m 700 "$work/noexp-gnupg"
GNUPGHOME="$work/noexp-gnupg" gpg --batch --quiet --passphrase '' \
    --quick-generate-key "$tagger_name <$tagger_email>" ed25519 cert 0 2>/dev/null
noexp_primary="$(GNUPGHOME="$work/noexp-gnupg" gpg --batch --with-colons --list-keys "$tagger_email" |
    awk -F: '$1=="fpr" {print $10; exit}')"
GNUPGHOME="$work/noexp-gnupg" gpg --batch --quiet --passphrase '' \
    --quick-add-key "$noexp_primary" ed25519 sign 0 2>/dev/null
git_fixture checkout --quiet -B side-noexp "$base"
GNUPGHOME="$work/noexp-gnupg" gpg --batch --armor --export "$noexp_primary" >"$repo/docs/security/release-signing-keys.asc"
rc=0 && (cd "$repo" && THREELEAPS_CRUCIBLE_DECERNOR_BIN="$checker" ./scripts/release-derive-anchors.sh --check) \
    >"$work/out" 2>"$work/err" || rc=$?
expect_reason "no-expiry key refused by release-derive-anchors" "has no expiration timestamp"
gpgconf --homedir "$work/noexp-gnupg" --kill all >/dev/null 2>&1 || true

# Appended duplicate/unverified subkey binding signature packet is refused.
git_fixture checkout --quiet -B side-dupsig "$base"
python3 - "$repo/docs/security/release-signing-keys.asc" <<'PY'
import base64
import pathlib
import sys
import zlib

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
lines = [
    line.strip()
    for line in text.splitlines()
    if line.strip()
    and not line.startswith("-----")
    and ":" not in line
    and not line.startswith("=")
]
raw = base64.b64decode("".join(lines), validate=True)

# Locate the final signature packet (subkey binding sig) and append a copy.
i = 0
last_sig = b""
while i < len(raw):
    start = i
    ctb = raw[i]
    i += 1
    if ctb & 0x40:
        tag = ctb & 0x3F
        l0 = raw[i]
        i += 1
        if l0 < 192:
            body_len = l0
        elif l0 < 224:
            body_len = ((l0 - 192) << 8) + raw[i] + 192
            i += 1
        else:
            body_len = int.from_bytes(raw[i : i + 4], "big")
            i += 4
    else:
        tag = (ctb >> 2) & 0x0F
        ltype = ctb & 0x03
        if ltype == 0:
            body_len = raw[i]
            i += 1
        elif ltype == 1:
            body_len = int.from_bytes(raw[i : i + 2], "big")
            i += 2
        else:
            body_len = int.from_bytes(raw[i : i + 4], "big")
            i += 4
    i += body_len
    if tag == 2:
        last_sig = raw[start:i]

tampered_raw = raw + last_sig
b64 = base64.b64encode(tampered_raw).decode("ascii")
wrapped = "\n".join(b64[j : j + 64] for j in range(0, len(b64), 64))
path.write_text(
    f"-----BEGIN PGP PUBLIC KEY BLOCK-----\n\n{wrapped}\n-----END PGP PUBLIC KEY BLOCK-----\n",
    encoding="utf-8",
)
PY
rc=0 && (cd "$repo" && THREELEAPS_CRUCIBLE_DECERNOR_BIN="$checker" ./scripts/release-derive-anchors.sh --check) \
    >"$work/out" 2>"$work/err" || rc=$?
expect_reason "duplicate subkey binding signature refused" "carries multiple binding signatures"
git_fixture checkout -- docs/security/release-signing-keys.asc
git_fixture checkout --quiet main

# 5. Missing gpg on PATH must fail closed in check_release_key_expiry.
mkdir -p "$work/no-gpg-bin"
ln -sf "$(command -v python3)" "$work/no-gpg-bin/python3"
rc=0 && (
    # shellcheck source=scripts/release-env.sh
    source "$repo/scripts/release-env.sh"
    PATH="$work/no-gpg-bin" check_release_key_expiry "$repo/docs/security/release-signing-keys.asc"
) >"$work/out" 2>"$work/err" || rc=$?
expect_reason "check_release_key_expiry without gpg on PATH refused" "gpg not found in PATH"

if ((failures)); then
    echo "[!!] release identity controls: $failures failure(s)" >&2
    exit 1
fi
echo "[ok] release identity controls passed"
