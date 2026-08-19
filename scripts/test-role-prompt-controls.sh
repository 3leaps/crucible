#!/bin/sh

set -eu

schema="schemas/agentic/v0/role-prompt.schema.json"
baseline="schemas/agentic/v0/rejects/baseline-bounded-role.yaml"

goneat validate data --schema-file "$schema" --data "$baseline" >/dev/null
echo "    [ok] role-prompt baseline passes"

for candidate in schemas/agentic/v0/rejects/reject-*.yaml; do
    if goneat validate data --schema-file "$schema" --data "$candidate" >/dev/null 2>&1; then
        echo "    [!!] role-prompt reject unexpectedly passed: $candidate"
        exit 1
    fi
    echo "    [ok] role-prompt rejected: $candidate"
done

echo "    [ok] role-prompt negative controls passed"
