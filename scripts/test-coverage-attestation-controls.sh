#!/usr/bin/env sh
# Negative controls for contract: coverage-attestation/v0.
#
# The published example is the positive control. Each generated reject differs
# from it only in the field named by the test and must fail schema validation.
set -eu

base="schemas/coverage-attestation/v0"
schema="$base/coverage-attestation.schema.json"
example="$base/coverage-attestation.example.json"

goneat validate data --schema-file "$schema" --data "$example" >/dev/null
echo "    [ok] baseline example passes"

tmpd=$(mktemp -d)
trap 'rm -rf "$tmpd"' EXIT

expect_rejected() {
    name=$1
    filter=$2
    output="$tmpd/$name.json"

    jq "$filter" "$example" >"$output"
    if goneat validate data --schema-file "$schema" --data "$output" >/dev/null 2>&1; then
        echo "    [!!] negative control passed validation: $name" >&2
        exit 1
    fi
    echo "    [ok] rejected: $name"
}

expect_rejected "gap-without-code" 'del(.gaps[0].code)'
expect_rejected "negative-observed-volume" '.claims[0].volume.observed = -1'
expect_rejected "negative-expected-volume" '.claims[0].volume.expected = -1'

echo "    [ok] coverage-attestation negative controls passed"
