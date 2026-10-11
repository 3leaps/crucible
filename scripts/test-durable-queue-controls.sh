#!/usr/bin/env sh
# Conformance battery for contract: durable-queue/v0.
#
# Declared invocation set (PDR-0006 Rule 2b):
#   sh, coreutils, find, mktemp — baseline
#   goneat — subject-matter (JSON Schema validation the contract names)
#   jq — structural inspection of contract fixtures (house pattern)
#   python3 — stdlib-only fixture-integrity checker (scripts/validate-durable-queue-vectors.py),
#             which reuses scripts/rfc8785-canonicalize.py for identity digests
#
# Asserts:
#   - every golden example validates against its schema; ledger example lines validate
#   - the service-job composition example's payload validates against the service-job entry schema
#   - the stored-message definition in control-exchange is identical to queue-message.schema.json
#   - schema-labeled baseline-* pass and reject-* fail; pairs differ in exactly one field
#   - profile semantic rule: runtime.enabled_capabilities ⊆ build.compiled_capabilities
#   - every vector: ops validate as requests, results validate as responses, bindings resolve,
#     ledger lines validate, seq gap-free, atomic groups contiguous, fold legal, attempts
#     correspond to leases, identity digests match RFC 8785 canonical bytes
#   - the required vector inventory is present and no vector is empty
#   - every semantic reject-* vector is detected with its labeled reason; baseline passes
#   - fixtures contain no credentials, raw tokens, or machine-local paths
set -eu

base="schemas/durable-queue/v0"
tmpd=$(mktemp -d)
trap 'rm -rf "$tmpd"' EXIT

validate() { goneat validate data --schema-file "$1" --data "$2" >/dev/null 2>&1; }
schema_for() {
    case "$1" in
        *message*) echo "$base/queue-message.schema.json" ;;
        *ledger*) echo "$base/ledger-event.schema.json" ;;
        *profile*) echo "$base/capability-profile.schema.json" ;;
        *control*) echo "$base/control-exchange.schema.json" ;;
        *)
            echo ""
            return 1
            ;;
    esac
}

echo "    durable-queue: golden examples..."
validate "$base/capability-profile.schema.json" "$base/examples/capability-profile.example.json"
for f in "$base"/examples/queue-message*.example.json; do
    validate "$base/queue-message.schema.json" "$f" || {
        echo "[!!] $f failed" >&2
        exit 1
    }
done
for f in "$base"/examples/control-*.example.json; do
    validate "$base/control-exchange.schema.json" "$f" || {
        echo "[!!] $f failed" >&2
        exit 1
    }
done
n=0
while IFS= read -r line; do
    [ -n "$line" ] || continue
    printf '%s\n' "$line" >"$tmpd/line.json"
    validate "$base/ledger-event.schema.json" "$tmpd/line.json" || {
        echo "[!!] ledger example line failed: $line" >&2
        exit 1
    }
    n=$((n + 1))
done <"$base/examples/ledger.example.ndjson"
[ "$n" -gt 0 ] || {
    echo "[!!] ledger example is empty" >&2
    exit 1
}

echo "    durable-queue: service-job composition payload validates against service-job..."
jq '.payload' "$base/examples/queue-message.service-job.example.json" >"$tmpd/sj.json"
validate "schemas/service-job/v0/service-job-message.schema.json" "$tmpd/sj.json" || {
    echo "[!!] composition payload is not a valid service-job message" >&2
    exit 1
}

echo "    durable-queue: stored-message mirror is identical..."
jq -S '{properties, required, oneOf}' "$base/queue-message.schema.json" >"$tmpd/a.json"
jq -S '."$defs".storedMessage | {properties, required, oneOf}' "$base/control-exchange.schema.json" >"$tmpd/b.json"
cmp -s "$tmpd/a.json" "$tmpd/b.json" || {
    echo "[!!] control-exchange storedMessage drifted from queue-message.schema.json" >&2
    exit 1
}

echo "    durable-queue: schema baselines pass, rejects fail, pairs differ in one field..."
for f in "$base"/rejects/schema/baseline-*.json; do
    s=$(schema_for "$f")
    validate "$s" "$f" || {
        echo "[!!] baseline failed: $f" >&2
        exit 1
    }
done
for f in "$base"/rejects/schema/reject-*.json; do
    s=$(schema_for "$f")
    if validate "$s" "$f"; then
        echo "[!!] reject was accepted: $f" >&2
        exit 1
    fi
    twin="$(dirname "$f")/baseline-${f##*/reject-}"
    [ -f "$twin" ] || {
        echo "[!!] no baseline twin for $f" >&2
        exit 1
    }
    python3 -I scripts/validate-durable-queue-vectors.py pair "$twin" "$f" || exit 1
done

echo "    durable-queue: profile semantic rule (enabled ⊆ compiled)..."
python3 -I scripts/validate-durable-queue-vectors.py profile "$base/examples/capability-profile.example.json" || exit 1
jq '.runtime.enabled_capabilities += ["priority"]' "$base/examples/capability-profile.example.json" >"$tmpd/p.json"
if python3 -I scripts/validate-durable-queue-vectors.py profile "$tmpd/p.json" >/dev/null 2>&1; then
    echo "[!!] profile with enabled capability not compiled was accepted" >&2
    exit 1
fi

echo "    durable-queue: vectors (requests, responses, bindings, ledger, groups, fold, digests)..."
python3 -I scripts/validate-durable-queue-vectors.py vectors "$base" || exit 1

echo "    durable-queue: semantic rejects detected with labeled reason, baseline passes..."
python3 -I scripts/validate-durable-queue-vectors.py vector "$base" "$base/rejects/semantic/baseline-enqueue-claim-ack.json" || exit 1
for f in "$base"/rejects/semantic/reject-*.json; do
    want=$(jq -r '.expect_reject' "$f")
    if got=$(python3 -I scripts/validate-durable-queue-vectors.py vector "$base" "$f" 2>&1); then
        echo "[!!] semantic reject was accepted: $f" >&2
        exit 1
    fi
    printf '%s\n' "$got" | grep -q "reject:$want" || {
        echo "[!!] $f rejected for the wrong reason; wanted $want, got: $got" >&2
        exit 1
    }
done

echo "    durable-queue: hygiene (no credentials, tokens, machine paths)..."
if grep -rEn -i '(password|secret|bearer |/users/|/home/|c:\\\\users)' "$base" >/dev/null; then
    echo "[!!] hygiene: sensitive-looking content in fixtures" >&2
    exit 1
fi
echo "[ok] durable-queue controls passed"
