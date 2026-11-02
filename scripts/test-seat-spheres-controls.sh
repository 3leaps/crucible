#!/bin/sh

set -eu

seat_schema="schemas/seat-spheres/v0/seat-view.schema.json"

for example in schemas/seat-spheres/v0/examples/seat-view.*.example.json; do
    [ -f "$example" ] || continue
    goneat validate data --schema-file "$seat_schema" --data "$example" >/dev/null
    echo "    [ok] seat-spheres example passes: $example"
done

reject_dir() {
    schema="$1"
    dir="$2"
    for candidate in "$dir"/reject-*.json; do
        [ -f "$candidate" ] || continue
        if goneat validate data --schema-file "$schema" --data "$candidate" >/dev/null 2>&1; then
            echo "    [!!] seat-spheres reject unexpectedly passed: $candidate"
            exit 1
        fi
        echo "    [ok] seat-spheres rejected: $candidate"
    done
}

reject_dir "$seat_schema" schemas/seat-spheres/v0/rejects/seat-view

echo "    [ok] seat-spheres controls passed"
