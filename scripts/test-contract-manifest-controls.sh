#!/usr/bin/env sh
set -eu

tmpd=$(mktemp -d)
trap 'rm -rf "$tmpd"' EXIT
REAL_JQ=$(command -v jq)
export REAL_JQ
mkdir -p "$tmpd/bin" "$tmpd/probe/v0"
cat >"$tmpd/bin/jq" <<'EOF'
#!/usr/bin/env sh
binary=false
raw=false
for arg in "$@"; do
    case "$arg" in
        -b) binary=true ;;
        -r) raw=true ;;
    esac
done
if [ "$raw" = true ] && [ "$binary" != true ]; then
    echo 'raw jq output must select binary/LF mode' >&2
    exit 2
fi
exec "$REAL_JQ" "$@"
EOF
chmod +x "$tmpd/bin/jq"
cat >"$tmpd/probe/v0/contract.json" <<'EOF'
{"capability":"contract: probe/v0","entry_schema":"entry.json","object_schemas":{"a":"a.json","b":"b.json"},"catalog":"catalog.json"}
EOF
for name in entry a b; do
    cat >"$tmpd/probe/v0/$name.json" <<'EOF'
{"properties":{"capabilities":{"contains":{"const":"contract: probe/v0"}}}}
EOF
done
printf '%s\n' '{"capabilities":["contract: probe/v0"]}' >"$tmpd/probe/v0/catalog.json"
PATH="$tmpd/bin:$PATH" sh scripts/validate-contract-manifests.sh "$tmpd/probe/v0/contract.json"
rm "$tmpd/probe/v0/b.json"
if PATH="$tmpd/bin:$PATH" sh scripts/validate-contract-manifests.sh \
    "$tmpd/probe/v0/contract.json" >"$tmpd/missing.log" 2>&1; then
    echo '[!!] missing object schema was accepted' >&2
    exit 1
fi
grep -q 'object schema target is missing: b.json' "$tmpd/missing.log"
echo '[ok] manifest raw-output mode and missing-object controls passed'
