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

# Structural distance between two JSON documents: added/removed/changed
# scalars count 1 each; an added or removed subtree counts 1 at its root; a
# list length change counts 1 PLUS any differences over the shared indices -
# a length change never short-circuits element comparison, or an appended
# element would mask a mutation of an existing one. The reject/baseline
# single-field-mutation claim is asserted with this, not by prose.
ndiff_jq='
def ndiff(a; b):
  if (a | type) != (b | type) then 1
  elif (a | type) == "object" then
    ((((a | keys) + (b | keys)) | unique)
     | map(. as $k |
         if ((a | has($k)) and (b | has($k))) then ndiff(a[$k]; b[$k])
         else 1 end)
     | add) // 0
  elif (a | type) == "array" then
    (if (a | length) != (b | length) then 1 else 0 end)
    + (([range(0; ([(a | length), (b | length)] | min))]
        | map(. as $i | ndiff(a[$i]; b[$i]))
        | add) // 0)
  elif a == b then 0
  else 1
  end;
'

pair_distance() {
    jq -n --slurpfile a "$1" --slurpfile b "$2" "$ndiff_jq ndiff(\$a; \$b)"
}

assert_pair_distance_one() {
    # $1 = baseline path, $2 = reject path, $3 = extra distance already
    # accumulated for multi-file sets (0 for single-file pairs)
    pd=$(pair_distance "$1" "$2")
    pd_total=$((pd + $3))
    if [ "$pd_total" -ne 1 ]; then
        echo "    [!!] reject/baseline pair differs in $pd_total fields, not exactly 1: $2" >&2
        exit 1
    fi
}

# Control-of-the-control for ndiff itself: the distance function is proven
# able to count before anything is measured with it. In particular, an array
# length change must NOT short-circuit element comparison - an appended
# element plus a mutated existing element is distance 2, never 1.
ndiff_case() {
    got=$(jq -n --argjson a "$1" --argjson b "$2" "$ndiff_jq ndiff(\$a; \$b)")
    if [ "$got" -ne "$3" ]; then
        echo "    [!!] ndiff self-test failed: expected $3, got $got for $1 vs $2" >&2
        exit 1
    fi
}
echo "    ndiff self-test (the distance function is proven able to count)..."
ndiff_case '{"x":1}' '{"x":1}' 0
ndiff_case '{"x":1}' '{"x":2}' 1
ndiff_case '{"x":1,"y":{"a":1,"b":2}}' '{"x":1}' 1
ndiff_case '{"s":[{"id":"p1"}]}' '{"s":[{"id":"p1"},{"id":"p2"}]}' 1
ndiff_case '{"s":[{"id":"p1"}]}' '{"s":[{"id":"MUT"},{"id":"p2"}]}' 2
ndiff_case '{"s":[{"id":"p1"},{"id":"p2"}]}' '{"s":[{"id":"p1"},{"id":"MUT"}]}' 1
ndiff_case '{"x":1,"s":[{"id":"p1"}]}' '{"x":2,"s":[{"id":"p1"},{"id":"p2"}]}' 2
echo "    [ok] ndiff self-test passed"

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

echo "    Pair-distance invariant (every reject differs from its baseline twin in exactly one field)..."
for f in "$base"/rejects/manifest/reject-*.json "$base"/rejects/event/reject-*.json; do
    [ -f "$f" ] || continue
    twin="$(dirname "$f")/baseline-${f##*/reject-}"
    [ -f "$twin" ] || {
        echo "    [!!] reject has no baseline twin: $f" >&2
        exit 1
    }
    assert_pair_distance_one "$twin" "$f" 0
    echo "    [ok] pair distance 1: $f"
done
for d in "$base"/rejects/set/reject-*; do
    [ -d "$d" ] || continue
    twin="$(dirname "$d")/baseline-${d##*/reject-}"
    [ -d "$twin" ] || {
        echo "    [!!] set reject has no baseline twin: $d" >&2
        exit 1
    }
    dm=$(pair_distance "$twin/manifest.json" "$d/manifest.json")
    assert_pair_distance_one "$twin/events.ndjson" "$d/events.ndjson" "$dm"
    echo "    [ok] pair distance 1: $d"
done

echo "    Set fixtures are schema-valid (a set reject fails only at the set gate)..."
tmpd=$(mktemp -d)
trap 'rm -rf "$tmpd"' EXIT
for d in "$base"/rejects/set/reject-* "$base"/rejects/set/baseline-*; do
    [ -d "$d" ] || continue
    goneat validate data --schema-file "$base/review-manifest.schema.json" --data "$d/manifest.json" >/dev/null ||
        {
            echo "    [!!] set fixture manifest is not schema-valid: $d" >&2
            exit 1
        }
    evn=0
    while IFS= read -r line; do
        [ -n "$line" ] || continue
        evn=$((evn + 1))
        printf '%s\n' "$line" >"$tmpd/event.json"
        goneat validate data --schema-file "$base/review-event.schema.json" --data "$tmpd/event.json" >/dev/null ||
            {
                echo "    [!!] set fixture event $evn is not schema-valid: $d" >&2
                exit 1
            }
    done <"$d/events.ndjson"
done
echo "    [ok] set fixtures schema-valid"

echo "    [ok] review-journal negative-control battery passed"
