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
# - require_signing_identity: set RELEASE_TAGGER_NAME, RELEASE_TAGGER_EMAIL and
#   RELEASE_PGP_KEY_ID after requiring THREELEAPS_CRUCIBLE_TAGGER_NAME,
#   THREELEAPS_CRUCIBLE_TAGGER_EMAIL and THREELEAPS_CRUCIBLE_PGP_KEY_ID
#   (^[0-9A-F]{40}!$) and verifying they match config/release/tagger-identity.txt
#   and the signing subkey and UID in docs/security/release-signing-keys.asc
#   before gpg is invoked.

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

# Require explicit tagger identity and signing subkey selector before invoking
# gpg. Never falls back to git config user.name/user.email or the default GPG
# key. Validates THREELEAPS_CRUCIBLE_TAGGER_NAME,
# THREELEAPS_CRUCIBLE_TAGGER_EMAIL, and THREELEAPS_CRUCIBLE_PGP_KEY_ID against
# config/release/tagger-identity.txt and docs/security/release-signing-keys.asc.
require_signing_identity() {
    local root="${RELEASE_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)}"
    local tagger_name="${THREELEAPS_CRUCIBLE_TAGGER_NAME:-}"
    local tagger_email="${THREELEAPS_CRUCIBLE_TAGGER_EMAIL:-}"
    local key_id="${THREELEAPS_CRUCIBLE_PGP_KEY_ID:-}"

    if [[ -z "$tagger_name" ]]; then
        echo "error: THREELEAPS_CRUCIBLE_TAGGER_NAME is required; tagger identity is never derived from git config" >&2
        return 1
    fi
    if [[ -z "$tagger_email" ]]; then
        echo "error: THREELEAPS_CRUCIBLE_TAGGER_EMAIL is required; tagger identity is never derived from git config" >&2
        return 1
    fi
    local value
    for value in "$tagger_name" "$tagger_email"; do
        if [[ "$value" == *$'\n'* || "$value" == *$'\r'* || "$value" == *'<'* || "$value" == *'>'* ]]; then
            echo "error: invalid tagger identity (must not contain angle brackets or newlines)" >&2
            return 1
        fi
    done

    if [[ -z "$key_id" ]]; then
        echo "error: THREELEAPS_CRUCIBLE_PGP_KEY_ID is required; the default GPG key is never used" >&2
        return 1
    fi
    if ! [[ "$key_id" =~ ^[0-9A-F]{40}!$ ]]; then
        echo "error: THREELEAPS_CRUCIBLE_PGP_KEY_ID must be the exact uppercase 40-hex signing subkey fingerprint followed by !" >&2
        return 1
    fi

    local tagger_file="$root/config/release/tagger-identity.txt"
    local pin_file="$root/docs/security/release-signing-keys.asc"
    if ! [[ -f "$tagger_file" && ! -L "$tagger_file" && -s "$tagger_file" ]]; then
        echo "error: config/release/tagger-identity.txt must be a non-empty regular file" >&2
        return 1
    fi
    if ! [[ -f "$pin_file" && ! -L "$pin_file" && -s "$pin_file" ]]; then
        echo "error: docs/security/release-signing-keys.asc must be a non-empty regular file" >&2
        return 1
    fi

    local expected_tagger actual_tagger
    expected_tagger="$(tr -d '\r\n' <"$tagger_file")"
    actual_tagger="${tagger_name} <${tagger_email}>"
    if [[ "$actual_tagger" != "$expected_tagger" ]]; then
        echo "error: tagger '$actual_tagger' does not match config/release/tagger-identity.txt ('$expected_tagger')" >&2
        return 1
    fi

    local pin_info expected_subkey
    if ! pin_info="$(
        python3 -I - "$pin_file" "$tagger_email" <<'PY'
import base64
import binascii
import hashlib
import pathlib
import sys

pin_path = pathlib.Path(sys.argv[1])
expected_email = sys.argv[2]

try:
    text = pin_path.read_text(encoding="utf-8")
except OSError as exc:
    sys.exit(f"error: could not read {pin_path}: {exc}")

if "PRIVATE KEY BLOCK" in text:
    sys.exit("error: private material in docs/security/release-signing-keys.asc")

lines = [
    line.strip()
    for line in text.splitlines()
    if line.strip()
    and not line.startswith("-----")
    and ":" not in line
    and not line.startswith("=")
]
try:
    raw = base64.b64decode("".join(lines), validate=True)
except (binascii.Error, ValueError):
    sys.exit("error: docs/security/release-signing-keys.asc is not valid ASCII-armored OpenPGP data")


def read_subpackets(buf: bytes) -> int:
    j = 0
    flags = 0
    while j < len(buf):
        b0 = buf[j]
        j += 1
        if b0 < 192:
            slen = b0
        elif b0 < 255:
            if j >= len(buf):
                sys.exit("error: truncated OpenPGP signature subpacket")
            slen = ((b0 - 192) << 8) + buf[j] + 192
            j += 1
        else:
            if j + 4 > len(buf):
                sys.exit("error: truncated OpenPGP signature subpacket")
            slen = int.from_bytes(buf[j : j + 4], "big")
            j += 4
        if slen < 1 or j + slen > len(buf):
            sys.exit("error: malformed OpenPGP signature subpacket")
        stype = buf[j] & 0x7F
        sdata = buf[j + 1 : j + slen]
        j += slen
        if stype == 27 and sdata:
            flags |= sdata[0]
    return flags


i = 0
primaries = []
uids = []
signing_subkeys = []
current_subkey = None
current_subkey_signing = False

while i < len(raw):
    ctb = raw[i]
    i += 1
    if not (ctb & 0x80):
        sys.exit("error: invalid OpenPGP packet header in docs/security/release-signing-keys.asc")
    if ctb & 0x40:
        tag = ctb & 0x3F
        if i >= len(raw):
            sys.exit("error: truncated OpenPGP packet header")
        l0 = raw[i]
        i += 1
        if l0 < 192:
            body_len = l0
        elif l0 < 224:
            if i >= len(raw):
                sys.exit("error: truncated OpenPGP packet length")
            body_len = ((l0 - 192) << 8) + raw[i] + 192
            i += 1
        elif l0 == 255:
            if i + 4 > len(raw):
                sys.exit("error: truncated OpenPGP packet length")
            body_len = int.from_bytes(raw[i : i + 4], "big")
            i += 4
        else:
            sys.exit("error: unsupported partial-length OpenPGP packet")
    else:
        tag = (ctb >> 2) & 0x0F
        ltype = ctb & 0x03
        if ltype == 0:
            body_len = raw[i]
            i += 1
        elif ltype == 1:
            body_len = int.from_bytes(raw[i : i + 2], "big")
            i += 2
        elif ltype == 2:
            body_len = int.from_bytes(raw[i : i + 4], "big")
            i += 4
        else:
            sys.exit("error: unsupported indeterminate-length OpenPGP packet")
    if i + body_len > len(raw):
        sys.exit("error: truncated OpenPGP packet body")
    body = raw[i : i + body_len]
    i += body_len
    if tag in (5, 7):
        sys.exit("error: private material in docs/security/release-signing-keys.asc")
    if tag in (6, 14):
        if current_subkey is not None and current_subkey_signing:
            signing_subkeys.append(current_subkey)
        current_subkey = None
        current_subkey_signing = False
        if not body or body[0] != 4:
            sys.exit("error: unsupported OpenPGP key version in docs/security/release-signing-keys.asc")
        fpr = hashlib.sha1(b"\x99" + len(body).to_bytes(2, "big") + body).hexdigest().upper()
        if tag == 6:
            primaries.append(fpr)
        else:
            current_subkey = fpr
    elif tag == 13:
        uids.append(body.decode("utf-8", errors="replace"))
    elif tag == 2 and current_subkey is not None and len(body) >= 6 and body[0] == 4 and body[1] == 0x18:
        hashed_len = int.from_bytes(body[4:6], "big")
        if 6 + hashed_len > len(body):
            sys.exit("error: malformed subkey binding signature")
        if read_subpackets(body[6 : 6 + hashed_len]) & 0x02:
            current_subkey_signing = True

if current_subkey is not None and current_subkey_signing:
    signing_subkeys.append(current_subkey)

if len(primaries) != 1 or len(signing_subkeys) != 1:
    sys.exit("error: docs/security/release-signing-keys.asc must hold exactly one primary key and one signing subkey")
uid_emails = [
    u.split("<", 1)[1].split(">", 1)[0]
    for u in uids
    if "<" in u and ">" in u.split("<", 1)[1]
]
if expected_email not in uid_emails:
    sys.exit(
        f"error: tagger email '{expected_email}' matches no UID on docs/security/release-signing-keys.asc"
    )
print(signing_subkeys[0])
PY
    )"; then
        return 1
    fi
    expected_subkey="$pin_info"
    if [[ "${key_id%!}" != "$expected_subkey" ]]; then
        echo "error: THREELEAPS_CRUCIBLE_PGP_KEY_ID (${key_id%!}) does not match the signing subkey in docs/security/release-signing-keys.asc ($expected_subkey)" >&2
        return 1
    fi

    # shellcheck disable=SC2034 # Consumed by scripts that source this file.
    RELEASE_TAGGER_NAME="$tagger_name"
    # shellcheck disable=SC2034 # Consumed by scripts that source this file.
    RELEASE_TAGGER_EMAIL="$tagger_email"
    # shellcheck disable=SC2034 # Consumed by scripts that source this file.
    RELEASE_PGP_KEY_ID="$key_id"
}

# Check primary and signing subkey expiration horizons on an ASCII-armored
# OpenPGP public key pin (default: docs/security/release-signing-keys.asc):
#   - Every pinned primary key and signing subkey must carry exactly one
#     verified binding signature and a finite positive expiration timestamp.
#   - <= 0s remaining: fail closed (exit 1) naming key role, fingerprint, and UTC expiry.
#   - <= 30d remaining: emit a warning on stderr naming remaining days and UTC expiry.
check_release_key_expiry() {
    local pin_file="${1:-docs/security/release-signing-keys.asc}"
    python3 -I - "$pin_file" <<'PY'
import base64
import binascii
import datetime
import hashlib
import math
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

HORIZON_SECONDS = 30 * 86400
pin_path = pathlib.Path(sys.argv[1])

try:
    text = pin_path.read_text(encoding="utf-8")
except OSError as exc:
    sys.exit(f"error: could not read {pin_path}: {exc}")

if "PRIVATE KEY BLOCK" in text:
    sys.exit(f"error: private material in {pin_path}")

lines = [
    line.strip()
    for line in text.splitlines()
    if line.strip()
    and not line.startswith("-----")
    and ":" not in line
    and not line.startswith("=")
]
try:
    raw = base64.b64decode("".join(lines), validate=True)
except (binascii.Error, ValueError):
    sys.exit(f"error: {pin_path} is not valid ASCII-armored OpenPGP data")


def parse_subpackets(buf: bytes) -> tuple[int, int | None, int | None]:
    j = 0
    flags = 0
    sig_created: int | None = None
    key_exp_offset: int | None = None
    while j < len(buf):
        b0 = buf[j]
        j += 1
        if b0 < 192:
            slen = b0
        elif b0 < 255:
            if j >= len(buf):
                sys.exit("error: truncated OpenPGP signature subpacket")
            slen = ((b0 - 192) << 8) + buf[j] + 192
            j += 1
        else:
            if j + 4 > len(buf):
                sys.exit("error: truncated OpenPGP signature subpacket")
            slen = int.from_bytes(buf[j : j + 4], "big")
            j += 4
        if slen < 1 or j + slen > len(buf):
            sys.exit("error: malformed OpenPGP signature subpacket")
        stype = buf[j] & 0x7F
        sdata = buf[j + 1 : j + slen]
        j += slen
        if stype == 2 and len(sdata) == 4:
            sig_created = int.from_bytes(sdata, "big")
        elif stype == 9 and len(sdata) == 4:
            key_exp_offset = int.from_bytes(sdata, "big")
        elif stype == 27 and sdata:
            flags |= sdata[0]
    return flags, sig_created, key_exp_offset


i = 0
primaries: list[dict[str, object]] = []
subkeys: list[dict[str, object]] = []
current_key: dict[str, object] | None = None

while i < len(raw):
    ctb = raw[i]
    i += 1
    if not (ctb & 0x80):
        sys.exit(f"error: invalid OpenPGP packet header in {pin_path}")
    if ctb & 0x40:
        tag = ctb & 0x3F
        if i >= len(raw):
            sys.exit("error: truncated OpenPGP packet header")
        l0 = raw[i]
        i += 1
        if l0 < 192:
            body_len = l0
        elif l0 < 224:
            if i >= len(raw):
                sys.exit("error: truncated OpenPGP packet length")
            body_len = ((l0 - 192) << 8) + raw[i] + 192
            i += 1
        elif l0 == 255:
            if i + 4 > len(raw):
                sys.exit("error: truncated OpenPGP packet length")
            body_len = int.from_bytes(raw[i : i + 4], "big")
            i += 4
        else:
            sys.exit("error: unsupported partial-length OpenPGP packet")
    else:
        tag = (ctb >> 2) & 0x0F
        ltype = ctb & 0x03
        if ltype == 0:
            body_len = raw[i]
            i += 1
        elif ltype == 1:
            body_len = int.from_bytes(raw[i : i + 2], "big")
            i += 2
        elif ltype == 2:
            body_len = int.from_bytes(raw[i : i + 4], "big")
            i += 4
        else:
            sys.exit("error: unsupported indeterminate-length OpenPGP packet")
    if i + body_len > len(raw):
        sys.exit("error: truncated OpenPGP packet body")
    body = raw[i : i + body_len]
    i += body_len
    if tag in (5, 7):
        sys.exit(f"error: private material in {pin_path}")
    if tag in (6, 14):
        if len(body) < 6 or body[0] != 4:
            sys.exit(f"error: unsupported OpenPGP key version in {pin_path}")
        created = int.from_bytes(body[1:5], "big")
        fpr = hashlib.sha1(b"\x99" + len(body).to_bytes(2, "big") + body).hexdigest().upper()
        entry: dict[str, object] = {
            "role": "primary key" if tag == 6 else "signing subkey",
            "fpr": fpr,
            "created": created,
            "expires": None,
            "sig_count": 0,
            "signing": False,
        }
        current_key = entry
        if tag == 6:
            primaries.append(entry)
        else:
            subkeys.append(entry)
    elif tag == 2:
        if current_key is None or len(body) < 6 or body[0] != 4:
            sys.exit(f"error: unsupported or detached OpenPGP signature packet in {pin_path}")
        sig_type = body[1]
        is_primary_sig = current_key["role"] == "primary key" and sig_type in (0x10, 0x11, 0x12, 0x13, 0x1F)
        is_subkey_sig = current_key["role"] == "signing subkey" and sig_type == 0x18
        if not (is_primary_sig or is_subkey_sig):
            sys.exit(f"error: unexpected OpenPGP signature type 0x{sig_type:02x} in {pin_path}")
        hashed_len = int.from_bytes(body[4:6], "big")
        if 6 + hashed_len > len(body):
            sys.exit("error: malformed OpenPGP binding signature")
        flags, _sig_created, key_exp_offset = parse_subpackets(body[6 : 6 + hashed_len])
        current_key["sig_count"] = int(current_key["sig_count"]) + 1
        if int(current_key["sig_count"]) > 1:
            sys.exit(
                f"error: pinned release {current_key['role']} {current_key['fpr']} "
                "carries multiple binding signatures"
            )
        if flags & 0x02:
            current_key["signing"] = True
        if key_exp_offset is not None and key_exp_offset > 0:
            current_key["expires"] = int(current_key["created"]) + key_exp_offset
        else:
            current_key["expires"] = None

signing_subkeys = [k for k in subkeys if k["signing"]]
if len(primaries) != 1 or len(signing_subkeys) != 1 or len(subkeys) != 1:
    sys.exit(f"error: {pin_path} must hold exactly one primary key and one signing subkey")

for key in (primaries[0], signing_subkeys[0]):
    if int(key["sig_count"]) != 1:
        sys.exit(
            f"error: pinned release {key['role']} {key['fpr']} must carry exactly one binding signature"
        )
    if key["expires"] is None:
        sys.exit(
            f"error: pinned release {key['role']} {key['fpr']} has no expiration timestamp"
        )

gpg_bin = shutil.which("gpg")
if gpg_bin:
    gpgconf_bin = shutil.which("gpgconf")
    tmp_home = tempfile.mkdtemp(prefix="crucible-keycheck.")
    os.chmod(tmp_home, 0o700)
    try:
        env = dict(os.environ, GNUPGHOME=tmp_home)
        imp = subprocess.run(
            [gpg_bin, "--batch", "--quiet", "--import", str(pin_path)],
            env=env,
            capture_output=True,
            text=True,
        )
        if imp.returncode != 0:
            sys.exit(f"error: gpg failed to import {pin_path}")
        chk = subprocess.run(
            [gpg_bin, "--batch", "--with-colons", "--check-sigs"],
            env=env,
            capture_output=True,
            text=True,
        )
        if chk.returncode != 0:
            sys.exit(f"error: gpg signature check failed on {pin_path}")
        good_sigs = 0
        for line in chk.stdout.splitlines():
            parts = line.split(":")
            if parts[0] in ("sig", "rev"):
                if parts[1] != "!":
                    sys.exit(
                        f"error: unverified or bad binding signature ({parts[0]}:{parts[1]}) in {pin_path}"
                    )
                good_sigs += 1
        if good_sigs < 2:
            sys.exit(f"error: expected verified primary and subkey binding signatures in {pin_path}")
        lst = subprocess.run(
            [gpg_bin, "--batch", "--with-colons", "--with-subkey-fingerprint", "--list-keys"],
            env=env,
            capture_output=True,
            text=True,
        )
        if lst.returncode != 0:
            sys.exit(f"error: gpg list-keys failed on {pin_path}")
        gpg_exp: dict[str, int] = {}
        pending_exp: int | None = None
        for line in lst.stdout.splitlines():
            parts = line.split(":")
            if parts[0] in ("pub", "sub"):
                exp_field = parts[6] if len(parts) > 6 else ""
                if not exp_field.isdigit() or int(exp_field) <= 0:
                    sys.exit(f"error: gpg reported missing expiration timestamp in {pin_path}")
                pending_exp = int(exp_field)
            elif parts[0] == "fpr" and pending_exp is not None:
                fpr_val = parts[9] if len(parts) > 9 else ""
                gpg_exp[fpr_val] = pending_exp
                pending_exp = None
        for key in (primaries[0], signing_subkeys[0]):
            fpr_str = str(key["fpr"])
            if gpg_exp.get(fpr_str) != int(key["expires"]):
                sys.exit(
                    f"error: packet expiry for {key['role']} {fpr_str} disagrees with verified gpg expiry"
                )
    finally:
        if gpgconf_bin:
            subprocess.run(
                [gpgconf_bin, "--homedir", tmp_home, "--kill", "all"],
                capture_output=True,
            )
        shutil.rmtree(tmp_home, ignore_errors=True)

now = int(time.time())
for key in (primaries[0], signing_subkeys[0]):
    exp_int = int(key["expires"])
    exp_iso = datetime.datetime.fromtimestamp(exp_int, datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    remaining = exp_int - now
    if remaining <= 0:
        sys.exit(
            f"error: pinned release {key['role']} {key['fpr']} expired at {exp_iso}"
        )
    if remaining <= HORIZON_SECONDS:
        days = max(1, math.ceil(remaining / 86400))
        sys.stderr.write(
            f"warning: pinned release {key['role']} {key['fpr']} expires within 30 days "
            f"({days}d remaining, expires {exp_iso})\n"
        )
PY
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
