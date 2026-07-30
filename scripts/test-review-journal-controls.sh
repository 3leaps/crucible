#!/usr/bin/env sh
# Negative-control battery for contract: review-journal/v0 (EPR-0002 obligation 3).
#
# Asserts, for every reject/baseline fixture pair under
# schemas/review-journal/v0/rejects/:
#   - each baseline-* fixture PASSES its schema (control-of-the-control: the
#     twin differs from its reject in exactly the defective field, so a green
#     baseline pins the rejection to its intended gate);
#   - each reject-* fixture FAILS its schema — a gate never seen to fail is
#     configured, not proven;
#   - each set-level baseline passes and each set-level reject fails the
#     journal-set check (cross-stream ceiling, roster closure,
#     author-does-not-approve at the person level).
#
# Requires goneat and jq. Run from the repository root.
set -eu

base="schemas/review-journal/v0"

for f in "$base"/rejects/manifest/baseline-*.json; do
    [ -f "$f" ] || continue
    goneat validate data --schema-file "$base/review-manifest.schema.json" --data "$f" >/dev/null ||
        {
            echo "    [!!] baseline failed validation: $f" >&2
            exit 1
        }
    echo "    [ok] baseline passes: $f"
done

for f in "$base"/rejects/manifest/reject-*.json; do
    [ -f "$f" ] || continue
    if goneat validate data --schema-file "$base/review-manifest.schema.json" --data "$f" >/dev/null 2>&1; then
        echo "    [!!] negative control passed validation (gate never seen to fail): $f" >&2
        exit 1
    fi
    echo "    [ok] rejected: $f"
done

for f in "$base"/rejects/event/baseline-*.json; do
    [ -f "$f" ] || continue
    goneat validate data --schema-file "$base/review-event.schema.json" --data "$f" >/dev/null ||
        {
            echo "    [!!] baseline failed validation: $f" >&2
            exit 1
        }
    echo "    [ok] baseline passes: $f"
done

for f in "$base"/rejects/event/reject-*.json; do
    [ -f "$f" ] || continue
    if goneat validate data --schema-file "$base/review-event.schema.json" --data "$f" >/dev/null 2>&1; then
        echo "    [!!] negative control passed validation (gate never seen to fail): $f" >&2
        exit 1
    fi
    echo "    [ok] rejected: $f"
done

echo "    Review-journal set properties (cross-stream ceiling, roster closure, author-does-not-approve)..."
sh scripts/validate-review-journal-set.sh \
    "$base/examples/review-manifest.example.json" \
    "$base/examples/review-events.example.ndjson"

for d in "$base"/rejects/set/baseline-*; do
    [ -d "$d" ] || continue
    sh scripts/validate-review-journal-set.sh "$d/manifest.json" "$d/events.ndjson" >/dev/null ||
        {
            echo "    [!!] baseline set failed: $d" >&2
            exit 1
        }
    echo "    [ok] baseline set passes: $d"
done

for d in "$base"/rejects/set/reject-*; do
    [ -d "$d" ] || continue
    if sh scripts/validate-review-journal-set.sh "$d/manifest.json" "$d/events.ndjson" >/dev/null 2>&1; then
        echo "    [!!] negative control passed the set check (gate never seen to fail): $d" >&2
        exit 1
    fi
    echo "    [ok] rejected set: $d"
done

echo "    [ok] review-journal negative-control battery passed"
