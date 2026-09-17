#!/usr/bin/env bash
# Fetch, authenticate, and execute the pinned sfetch bootstrap engine.

set -euo pipefail

version=''
install_dir=''
engine_sha=''
engine_sha256=''
repo='3leaps/sfetch'
engine_file=''

usage() {
    echo "usage: $0 --version vX.Y.Z --dir PATH --engine-sha SHA --engine-sha256 SHA256 [--repo OWNER/REPO]" >&2
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --version)
            version="${2:-}"
            shift 2
            ;;
        --dir)
            install_dir="${2:-}"
            shift 2
            ;;
        --engine-sha)
            engine_sha="${2:-}"
            shift 2
            ;;
        --engine-sha256)
            engine_sha256="${2:-}"
            shift 2
            ;;
        --repo)
            repo="${2:-}"
            shift 2
            ;;
        --engine-file)
            [ "${SFETCH_BOOTSTRAP_TESTING:-}" = '1' ] || {
                echo 'error: --engine-file is available only to the negative-control harness' >&2
                exit 2
            }
            engine_file="${2:-}"
            shift 2
            ;;
        *) usage ;;
    esac
done

[[ "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
    echo 'error: --version must be an exact vMAJOR.MINOR.PATCH tag' >&2
    exit 2
}
[[ "$engine_sha" =~ ^[0-9a-f]{40}$ ]] || {
    echo 'error: --engine-sha must be a full lowercase commit SHA' >&2
    exit 2
}
[[ "$engine_sha256" =~ ^[0-9a-f]{64}$ ]] || {
    echo 'error: --engine-sha256 must be a lowercase SHA-256 digest' >&2
    exit 2
}
[ -n "$install_dir" ] || usage

work="$(mktemp -d "${TMPDIR:-/tmp}/crucible-sfetch-engine.XXXXXX")"
cleanup() { rm -rf "$work"; }
trap cleanup EXIT HUP INT TERM
engine="$work/bootstrap-sfetch-verified.sh"

if [ -n "$engine_file" ]; then
    cp "$engine_file" "$engine"
else
    command -v curl >/dev/null 2>&1 || {
        echo 'error: curl is required' >&2
        exit 1
    }
    curl -fsSL --retry 3 --retry-delay 1 \
        "https://raw.githubusercontent.com/${repo}/${engine_sha}/scripts/bootstrap-sfetch-verified.sh" \
        -o "$engine"
fi

if command -v sha256sum >/dev/null 2>&1; then
    actual_sha256="$(sha256sum "$engine" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
    actual_sha256="$(shasum -a 256 "$engine" | awk '{print $1}')"
elif command -v openssl >/dev/null 2>&1; then
    actual_sha256="$(openssl dgst -sha256 "$engine" | awk '{print $NF}')"
else
    echo 'error: sha256sum, shasum, or openssl is required' >&2
    exit 1
fi

if [ "$actual_sha256" != "$engine_sha256" ]; then
    echo 'error: sfetch bootstrap engine SHA-256 mismatch' >&2
    echo "  expected: $engine_sha256" >&2
    echo "  actual:   $actual_sha256" >&2
    exit 1
fi
echo '[ok] sfetch bootstrap engine digest verified'

mkdir -p "$install_dir"
bash "$engine" --version "$version" --dir "$install_dir" --yes
