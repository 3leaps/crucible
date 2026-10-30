#!/usr/bin/env sh
# Controls for contract: durable-record/v0.
#
# Declared invocation set (PDR-0006 Rule 2b):
#   sh, coreutils, find, mktemp — baseline
#   goneat — subject-matter (batched JSON Schema suite validation the contract names)
#   jq — structural inspection of contract fixtures (house pattern)
#   python3 — stdlib-only fixture-integrity checker (scripts/validate-durable-record-fixtures.py),
#             which reuses scripts/rfc8785-canonicalize.py for revision digests
#
# Asserts:
#   - every golden example, journal example line, benchmark window rule, schema baseline/reject pair,
#     receipt reject schema check, and raw-wire integral/boundary/payload case passes batched
#     `goneat validate suite` with strict membership and error-vs-invalid verdict checks
#   - shared $defs are identical across record, journal-entry and write-receipt schemas
#   - profile semantic rules: enabled ⊆ compiled capabilities; stratum is compiled
#   - checker self-test: multi-field pairs, raw numeric_domain/ingest preflight, and suite error guards
#   - golden journal: seq gap-free, atomic groups tracked across rows, final cut consistent, digests
#     match RFC 8785 bytes, revision chain linear, conflicted.current is the head
#   - every golden receipt and reconciliation matches the journal (stream, key, outcome, pin,
#     body status, failure model; found embeds the accepted original; not_found coverage contains the attempt)
#   - every semantic/ingest/numeric_domain reject-<reason>--* journal and schema-valid receipt reject
#     is detected with its labeled reason; baselines pass
#   - fixtures contain no credentials, raw tokens, or machine-local paths
set -eu

base="schemas/durable-record/v0"
chk="scripts/validate-durable-record-fixtures.py"
tmpd=$(mktemp -d)
trap 'rm -rf "$tmpd"' EXIT

echo "    durable-record: batched schema suite (examples, pairs, receipt rejects, raw wire)..."
python3 -I "$chk" v0-suite "$base" || exit 1

echo "    durable-record: shared definitions identical across schemas..."
for d in digest revisionPin pin bodyRef provenance classification link record; do
    jq -S ".\"\$defs\".$d" "$base/record.schema.json" >"$tmpd/a.json"
    jq -S ".\"\$defs\".$d" "$base/journal-entry.schema.json" >"$tmpd/b.json"
    cmp -s "$tmpd/a.json" "$tmpd/b.json" || {
        echo "[!!] \$defs.$d differs between record and journal-entry schemas" >&2
        exit 1
    }
done
for d in digest pin; do
    jq -S ".\"\$defs\".$d" "$base/record.schema.json" >"$tmpd/a.json"
    jq -S ".\"\$defs\".$d" "$base/write-receipt.schema.json" >"$tmpd/b.json"
    [ "$(jq 'type' "$tmpd/a.json")" = '"object"' ] || {
        echo "[!!] \$defs.$d missing from record schema" >&2
        exit 1
    }
    cmp -s "$tmpd/a.json" "$tmpd/b.json" || {
        echo "[!!] \$defs.$d differs between record and write-receipt schemas" >&2
        exit 1
    }
done

echo "    durable-record: profile semantic rules..."
python3 -I "$chk" profile "$base/examples/stratum-profile.example.json" || exit 1
jq '.runtime.enabled_capabilities += ["unverified_bodies"]' "$base/examples/stratum-profile.example.json" >"$tmpd/p.json"
if python3 -I "$chk" profile "$tmpd/p.json" >/dev/null 2>&1; then
    echo "[!!] profile with enabled capability not compiled was accepted" >&2
    exit 1
fi

echo "    durable-record: checker self-test (pairs, raw numeric_domain, suite error guards)..."
python3 -I "$chk" self-test >/dev/null || exit 1

echo "    durable-record: golden journal integrity; every golden receipt and reconciliation matches it..."
python3 -I "$chk" journal "$base/examples/journal.example.ndjson" || exit 1
python3 -I "$chk" entry "$base/examples/journal-entry.stage-result.example.json" || exit 1
n=0
for f in "$base"/examples/write-receipt*.example.json "$base"/examples/reconciliation*.example.json; do
    python3 -I "$chk" receipt "$f" "$base/examples/journal.example.ndjson" || exit 1
    n=$((n + 1))
done
[ "$n" -ge 5 ] || {
    echo "[!!] expected at least 5 golden receipts/reconciliations, found $n" >&2
    exit 1
}

echo "    durable-record: semantic rejects detected with labeled reason, baseline passes..."
python3 -I "$chk" journal "$base/rejects/semantic/baseline-journal.ndjson" || exit 1
python3 -I "$chk" journal "$base/rejects/semantic/baseline-journal-canceled-exponents.ndjson" || exit 1
for f in "$base"/rejects/semantic/reject-*.ndjson; do
    name=${f##*/reject-}
    want=${name%%--*}
    if python3 -I "$chk" journal "$f" 2>"$tmpd/err"; then
        echo "[!!] semantic reject accepted: $f" >&2
        exit 1
    fi
    got=$(sed -n 's/^\[!!\] \([a-z_]*\):.*/\1/p' "$tmpd/err" | head -n 1)
    [ "$got" = "$want" ] || {
        echo "[!!] $f rejected as '$got', expected '$want'" >&2
        exit 1
    }
done

echo "    durable-record: receipt rejects schema-valid, detected with labeled reason..."
python3 -I "$chk" receipt "$base/rejects/receipt/baseline-receipt.json" "$base/examples/journal.example.ndjson" || exit 1
for f in "$base"/rejects/receipt/reject-*.json; do
    name=${f##*/reject-}
    want=${name%%--*}
    if python3 -I "$chk" receipt "$f" "$base/examples/journal.example.ndjson" 2>"$tmpd/err"; then
        echo "[!!] receipt reject accepted: $f" >&2
        exit 1
    fi
    got=$(sed -n 's/^\[!!\] \([a-z_]*\):.*/\1/p' "$tmpd/err" | head -n 1)
    [ "$got" = "$want" ] || {
        echo "[!!] $f rejected as '$got', expected '$want'" >&2
        exit 1
    }
done

echo "    durable-record: fixtures carry no credentials or machine-local paths..."
if grep -rEl '(/Users/|/home/|[A-Za-z]:\\\\|AGE-SECRET-KEY-1[0-9A-Z]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN)' "$base/examples" "$base/rejects/semantic" "$base"/rejects/schema/baseline-*.json >/dev/null 2>&1; then
    echo "[!!] fixture contains a credential or machine-local path" >&2
    exit 1
fi

echo "[ok] durable-record controls passed"
