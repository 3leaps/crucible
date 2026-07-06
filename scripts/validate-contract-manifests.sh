#!/usr/bin/env sh
set -eu

if [ "$#" -eq 0 ]; then
    echo "usage: validate-contract-manifests.sh <contract.json>..." >&2
    exit 2
fi

failures=0

fail() {
    failures=$((failures + 1))
    printf '    [!!] %s: %s\n' "$1" "$2" >&2
}

for manifest_path in "$@"; do
    printf '    Validating %s...\n' "$manifest_path"

    if [ ! -f "$manifest_path" ]; then
        fail "$manifest_path" "manifest is missing"
        continue
    fi

    if ! capability=$(jq -r 'if (.capability | type) == "string" then .capability else "" end' "$manifest_path"); then
        fail "$manifest_path" "invalid JSON"
        continue
    fi

    if ! entry_schema=$(jq -r 'if (.entry_schema | type) == "string" then .entry_schema else "" end' "$manifest_path"); then
        fail "$manifest_path" "invalid JSON"
        continue
    fi

    if [ -z "$capability" ]; then
        fail "$manifest_path" "capability must be a non-empty string"
    fi

    if [ -z "$entry_schema" ]; then
        fail "$manifest_path" "entry_schema must be a non-empty string"
        continue
    fi

    case "$entry_schema" in
        /* | *../* | *'\'* | */*)
            fail "$manifest_path" "entry_schema must be a file relative to the manifest directory"
            continue
            ;;
    esac

    entry_path="$(dirname "$manifest_path")/$entry_schema"
    if [ ! -f "$entry_path" ]; then
        fail "$manifest_path" "entry_schema target is missing: $entry_schema"
        continue
    fi

    if ! advertised_capability=$(jq -r '.properties.capabilities.contains.const // ""' "$entry_path"); then
        fail "$manifest_path" "entry_schema target is invalid JSON: $entry_schema"
        continue
    fi

    if [ "$advertised_capability" != "$capability" ]; then
        fail "$manifest_path" "capability mismatch: manifest has $capability, entry schema advertises $advertised_capability"
    fi
done

if [ "$failures" -gt 0 ]; then
    exit 1
fi
