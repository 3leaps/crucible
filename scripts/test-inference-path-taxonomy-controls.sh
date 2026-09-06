#!/usr/bin/env sh
# Controls for contract: inference-path-taxonomy/v0.
set -eu

base="schemas/inference-path-taxonomy/v0"
schema="$base/inference-path-taxonomy.schema.json"

for fixture in "$base"/examples/*.json; do
    goneat schema validate-data \
        --schema-file "$schema" \
        --ref-dir "$base" \
        --data "$fixture" >/dev/null
    echo "    [ok] example passes: $fixture"

    kind=$(jq -r '.kind' "$fixture")
    case "$kind" in
        party)
            selector='{kind,party_id,revision,display_name,aliases,roles}'
            ;;
        model_family)
            selector='{kind,model_family_id,revision,author_party_ref,slug,display_name}'
            ;;
        model_pin)
            selector='{kind,model_pin_id,revision,source_party_ref,model_id,canonical_model_id,family_ref,resolution_state,source_evidence}'
            ;;
        path_identity)
            selector='{kind,path_id,revision,model_family_ref,model_pin_ref,route,execution_host_mode,endpoint_ref,service_region,access_class,source_evidence}'
            ;;
        *)
            echo "    [!!] unknown example kind: $kind" >&2
            exit 1
            ;;
    esac

    expected=$(jq -r '.identity_digest | sub("^sha256:"; "")' "$fixture")
    actual=$(
        jq -c "$selector | with_entries(select(.value != null))" "$fixture" |
            python3 scripts/rfc8785-canonicalize.py |
            sha256sum |
            awk '{print $1}'
    )
    if [ "$actual" != "$expected" ]; then
        echo "    [!!] identity digest mismatch: $fixture" >&2
        exit 1
    fi
    echo "    [ok] identity digest: $fixture"
done

for fixture in "$base"/rejects/*.json; do
    if goneat schema validate-data \
        --schema-file "$schema" \
        --ref-dir "$base" \
        --data "$fixture" >/dev/null 2>&1; then
        echo "    [!!] reject passed validation: $fixture" >&2
        exit 1
    fi
    echo "    [ok] rejected: $fixture"
done

echo "    [ok] inference-path-taxonomy control battery passed"
