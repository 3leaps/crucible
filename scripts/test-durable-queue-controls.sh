#!/usr/bin/env sh
# Conformance battery for contract: durable-queue/v0.
#
# Declared invocation set (PDR-0006 Rule 2b):
#   sh, coreutils, find, mktemp — baseline
#   goneat — subject-matter (JSON Schema validation the contract names)
#   jq — structural inspection of contract fixtures (house pattern)
#   python3 — stdlib-only RFC 8785 payload digest check on vectors
#
# Asserts:
#   - every golden example validates against its schema
#   - every ledger example line validates
#   - schema-labeled baseline-* pass and reject-* fail schema validation
#   - schema pairs differ in exactly one field
#   - every vector's expected ledger lines validate, seq is gap-free from 1,
#     and every enqueued payload_digest matches the RFC 8785 digest of the op payload
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

echo "    durable-queue: schema baselines pass, rejects fail..."
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
done

echo "    durable-queue: reject pairs differ in exactly one field..."
for f in "$base"/rejects/schema/reject-*.json; do
    name=${f##*/reject-}
    case "$name" in
        message-*) twin="$base/rejects/schema/baseline-message.json" ;;
        ledger-*) twin="$base/rejects/schema/baseline-ledger.json" ;;
        profile-*) twin="$base/rejects/schema/baseline-profile.json" ;;
        control-response-*) twin="$base/rejects/schema/baseline-control-response.json" ;;
        control-*) twin="$base/rejects/schema/baseline-control.json" ;;
    esac
    diffc=$(
        python3 -I - "$twin" "$f" <<'PY2'
import json, sys
def flat(o, p=()):
    if isinstance(o, dict):
        for k, v in o.items(): yield from flat(v, p + (k,))
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from flat(v, p + (i,))
    else:
        yield p, o
a = dict(flat(json.load(open(sys.argv[1])))); b = dict(flat(json.load(open(sys.argv[2]))))
print(sum(1 for k in set(a) | set(b) if a.get(k, object()) != b.get(k, object())))
PY2
    )
    [ "$diffc" -eq 1 ] || {
        echo "[!!] $f differs from its baseline in $diffc fields, expected 1" >&2
        exit 1
    }
done

echo "    durable-queue: vectors (ledger lines valid, seq gap-free, digests match)..."
for v in "$base"/vectors/*/*.json; do
    jq -c '.ledger[]' "$v" | while IFS= read -r line; do
        printf '%s\n' "$line" >"$tmpd/line.json"
        validate "$base/ledger-event.schema.json" "$tmpd/line.json" || {
            echo "[!!] vector ledger line failed in $v: $line" >&2
            exit 1
        }
    done
    python3 -I - "$v" <<'PY' || exit 1
import json, sys, hashlib
v = json.load(open(sys.argv[1]))
seqs = [e["seq"] for e in v["ledger"]]
assert seqs == list(range(1, len(seqs) + 1)), f"{sys.argv[1]}: seq not gap-free from 1: {seqs}"
assert all("token" not in e and "fence_token" not in e for e in v["ledger"]), "fencing token leaked into ledger"
def jcs(o): return json.dumps(o, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode()
payloads = {}
for op in v["ops"]:
    if op["op"] in ("enqueue", "fan_out"):
        msgs = op["params"].get("messages") or op["params"].get("children") or []
        for m in msgs:
            payloads.setdefault(m["idempotency_key"], "sha256:" + hashlib.sha256(jcs(m["payload"])).hexdigest())  # first enqueue wins; a dedup retry never changes the digest
for e in v["ledger"]:
    if e["type"] == "enqueued":
        k = e.get("idempotency_key")
        assert k in payloads, f"enqueued without a matching op key: {e}"
        assert e["payload_digest"] == payloads[k], f"digest mismatch for {k}"
for cap in v.get("requires", []):
    assert cap in ("transactional_enqueue","atomic_fanout","delay","fenced_ack","ordering_key","priority","payload_ref","long_poll","virtual_clock"), cap
PY
done

echo "    durable-queue: hygiene (no credentials, tokens, machine paths)..."
if grep -rEn -i '(password|secret|bearer |/users/|/home/|c:\\\\users)' "$base" >/dev/null; then
    echo "[!!] hygiene: sensitive-looking content in fixtures" >&2
    exit 1
fi
echo "[ok] durable-queue controls passed"
