#!/bin/sh

set -eu

packet_schema="schemas/project-work/v0/ready-packet.schema.json"
project_schema="schemas/project-work/v0/project-state.schema.json"
control_schema="schemas/project-work/v0/control-record.schema.json"
event_schema="schemas/project-work/v0/progress-event.schema.json"

goneat validate data --schema-file "$packet_schema" --data schemas/project-work/v0/examples/ready-packet.example.json >/dev/null
echo "    [ok] project-work ready-packet example passes"

goneat validate data --schema-file "$project_schema" --data schemas/project-work/v0/examples/project-state.example.json >/dev/null
echo "    [ok] project-work project-state example passes"

goneat validate data --schema-file "$control_schema" --data schemas/project-work/v0/examples/control-record.blocker.example.json >/dev/null
echo "    [ok] project-work control-record example passes"

goneat validate data --schema-file "$control_schema" --data schemas/project-work/v0/examples/control-record.decision.example.json >/dev/null
echo "    [ok] project-work control-record decision example passes"

tmpd=$(mktemp -d)
tmp="$tmpd/event.json"
while IFS= read -r line; do
    [ -n "$line" ] || continue
    printf '%s\n' "$line" >"$tmp"
    goneat validate data --schema-file "$event_schema" --data "$tmp" >/dev/null
done <schemas/project-work/v0/examples/progress-events.example.ndjson
rm -rf "$tmpd"
echo "    [ok] project-work progress-event example lines pass"

reject_dir() {
    schema="$1"
    dir="$2"
    for candidate in "$dir"/reject-*.json; do
        [ -f "$candidate" ] || continue
        if goneat validate data --schema-file "$schema" --data "$candidate" >/dev/null 2>&1; then
            echo "    [!!] project-work reject unexpectedly passed: $candidate"
            exit 1
        fi
        echo "    [ok] project-work rejected: $candidate"
    done
}

reject_dir "$packet_schema" schemas/project-work/v0/rejects/ready-packet
reject_dir "$event_schema" schemas/project-work/v0/rejects/progress-event
reject_dir "$control_schema" schemas/project-work/v0/rejects/control-record
reject_dir "$project_schema" schemas/project-work/v0/rejects/project-state

# Inlined classifier keys must match catalog dimensions (anti-fork).
dim_keys() {
    jq -r '.categorical.values[].key' "$1" | sort | tr '\n' ' '
}

schema_enum() {
    jq -r --arg field "$2" '."$defs".classifiers.properties[$field].enum[]' "$1" | sort | tr '\n' ' '
}

sens_dim=$(dim_keys config/classifiers/dimensions/sensitivity.dimension.json)
tier_dim=$(dim_keys config/classifiers/dimensions/access-tier.dimension.json)
ret_dim=$(dim_keys config/classifiers/dimensions/retention-lifecycle.dimension.json)

for schema_file in "$packet_schema" "$project_schema"; do
    sens_schema=$(schema_enum "$schema_file" sensitivity)
    tier_schema=$(schema_enum "$schema_file" "access-tier")
    ret_schema=$(schema_enum "$schema_file" "retention-lifecycle")
    if [ "$sens_dim" != "$sens_schema" ]; then
        echo "    [!!] sensitivity enum drifted in $schema_file" >&2
        echo "         dim:    $sens_dim" >&2
        echo "         schema: $sens_schema" >&2
        exit 1
    fi
    if [ "$tier_dim" != "$tier_schema" ]; then
        echo "    [!!] access-tier enum drifted in $schema_file" >&2
        exit 1
    fi
    if [ "$ret_dim" != "$ret_schema" ]; then
        echo "    [!!] retention-lifecycle enum drifted in $schema_file" >&2
        exit 1
    fi
done
echo "    [ok] project-work classifier keys match catalog dimensions (packet + project)"

echo "    [ok] project-work controls passed"
