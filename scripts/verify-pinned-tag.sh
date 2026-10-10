#!/usr/bin/env bash
# verify-pinned-tag.sh - Verify a signed release tag against the committed pin
#
# Trust data is read as inert git objects from the tagged commit, never from the
# working tree:
# - keys/expected-fingerprints.txt: exactly a gpg line then a minisign line
# - docs/security/release-signing-keys.asc: one primary matching the gpg anchor,
#   exactly one signing subkey
# - docs/security/release-minisign.pub: public key blob matching the minisign anchor
# - config/release/tagger-identity.txt: required tagger name and email
#
# The tag must carry exactly one good, unexpired, unrevoked signature made by
# the pinned signing subkey.
#
# Usage: verify-pinned-tag.sh [TAG]   (default: v$(cat VERSION))

set -euo pipefail

die() {
    echo "error: $*" >&2
    exit 1
}

cd "$(git rev-parse --show-toplevel)"
tag="${1:-v$(tr -d ' \t\r\n' <VERSION)}"
[[ "$tag" =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]] || die "canonical release tag required: $tag"
object="$(git rev-parse -q --verify "refs/tags/$tag")" || die "tag $tag absent"
[[ "$(git cat-file -t "$object")" == tag ]] || die "annotated tag required"
[[ "$(git cat-file tag "$object" | sed -n 's/^tag //p' | head -1)" == "$tag" ]] || die "tag name mismatch"
target="$(git rev-parse "${object}^{commit}")"

work="$(mktemp -d)"
trap 'gpgconf --homedir "$work/home" --kill all >/dev/null 2>&1 || true; rm -rf "$work"' EXIT
chmod 700 "$work"

committed() {
    local path="$1" out="$2" mode
    mode="$(git ls-tree "$target" -- "$path" | awk '{print $1}')"
    [[ "$mode" == 100644 ]] || die "committed regular file $path required in the tagged commit"
    git cat-file blob "$target:$path" >"$out"
    [[ -s "$out" ]] || die "committed $path is empty"
}
committed keys/expected-fingerprints.txt "$work/anchors"
committed docs/security/release-signing-keys.asc "$work/pin.asc"
committed docs/security/release-minisign.pub "$work/minisign.pub"
committed config/release/tagger-identity.txt "$work/tagger"

python3 - "$work/anchors" "$work/minisign.pub" <<'PY'
import base64, hashlib, pathlib, re, sys
anchors = pathlib.Path(sys.argv[1]).read_bytes()
m = re.fullmatch(rb"gpg [0-9A-F]{40}\nminisign ([0-9a-f]{64})\n", anchors)
if not m:
    sys.exit("error: fingerprint anchors must be exactly a gpg line then a minisign line")
lines = pathlib.Path(sys.argv[2]).read_text(encoding="ascii").splitlines()
if len(lines) != 2 or not lines[0].startswith("untrusted comment: "):
    sys.exit("error: minisign public key must be a comment line and a key line")
blob = base64.b64decode(lines[1].strip(), validate=True)
if len(blob) != 42 or blob[:2] != b"Ed":
    sys.exit("error: minisign public key is not an Ed25519 public key")
if hashlib.sha256(blob).hexdigest() != m.group(1).decode():
    sys.exit("error: minisign public key differs from its anchor")
PY

tagger="$(git cat-file tag "$object" | sed -n 's/^tagger \(.*\) [0-9][0-9]* [+-][0-9][0-9][0-9][0-9]$/\1/p' | head -1)"
[[ "$tagger" == "$(cat "$work/tagger")" ]] || die "tagger '$tagger' does not match committed tagger identity"

mkdir -m 700 "$work/home"
export GNUPGHOME="$work/home"
gpg --batch --quiet --import "$work/pin.asc" 2>/dev/null || die "pin import failed"
listing="$(gpg --batch --with-colons --with-subkey-fingerprint --list-keys)"
[[ "$(awk -F: '$1=="sec"' <<<"$listing")" == "" ]] || die "pin contains secret material"
[[ "$(awk -F: '$1=="pub" {n++} END {print n+0}' <<<"$listing")" == 1 ]] || die "pin must hold exactly one primary key"
primary="$(awk '$1=="gpg" {print $2}' "$work/anchors")"
[[ "$(awk -F: '$1=="fpr" {print $10; exit}' <<<"$listing")" == "$primary" ]] || die "pin primary differs from gpg anchor"
signing="$(awk -F: '$1=="sub" {s=1; cap=$12; next} s && $1=="fpr" {if (cap ~ /s/) print $10; s=0}' <<<"$listing")"
[[ "$signing" =~ ^[0-9A-F]{40}$ ]] || die "pin must hold exactly one signing subkey"

git -c gpg.program=gpg verify-tag --raw "$object" >"$work/status" 2>&1 || {
    awk '$1=="[GNUPG:]" {print "signature status:", $2}' "$work/status" >&2
    die "tag signature invalid under pin"
}
awk -v primary="$primary" -v signing="$signing" '
  $1=="[GNUPG:]" && $2=="VALIDSIG" {valid++; subkey=$3; signer_primary=$NF}
  $1=="[GNUPG:]" && $2=="GOODSIG" {good++}
  $1=="[GNUPG:]" && $2 ~ /^(EXPKEYSIG|EXPSIG|REVKEYSIG|KEYREVOKED|BADSIG|ERRSIG)$/ {bad++}
  END { if (bad || good != 1 || valid != 1 || signer_primary != primary || subkey != signing) exit 1 }
' "$work/status" || die "signature is not a single good signature by the pinned signing subkey"

echo "[ok] $tag ($object) signed by pinned subkey $signing; anchors and tagger match"
