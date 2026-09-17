#!/usr/bin/env bash
# Prove a mismatched bootstrap engine cannot execute.

set -euo pipefail

work="$(mktemp -d "${TMPDIR:-/tmp}/crucible-bootstrap-negative.XXXXXX")"
cleanup() { rm -rf "$work"; }
trap cleanup EXIT HUP INT TERM

engine="$work/mock-engine.sh"
marker="$work/executed"
install_dir="$work/install"
cat >"$engine" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${MARKER:?}"
printf 'executed\n' >"$MARKER"
EOF

if command -v sha256sum >/dev/null 2>&1; then
    digest="$(sha256sum "$engine" | awk '{print $1}')"
else
    digest="$(shasum -a 256 "$engine" | awk '{print $1}')"
fi

set +e
MARKER="$marker" SFETCH_BOOTSTRAP_TESTING=1 \
    ./scripts/install-sfetch-verified.sh \
    --version v0.4.12 \
    --dir "$install_dir" \
    --engine-sha bd0e7a0e68ef5a3dc7cda862fc74e4e8bc5125f8 \
    --engine-sha256 0000000000000000000000000000000000000000000000000000000000000000 \
    --engine-file "$engine" >"$work/mismatch.log" 2>&1
status=$?
set -e

[ "$status" -ne 0 ] || {
    echo 'error: mismatched engine digest was accepted' >&2
    exit 1
}
[ ! -e "$marker" ] || {
    echo 'error: mismatched engine was executed' >&2
    exit 1
}
[ ! -e "$install_dir" ] || {
    echo 'error: install directory was created after digest failure' >&2
    exit 1
}
grep -q 'SHA-256 mismatch' "$work/mismatch.log" || {
    echo 'error: digest failure did not report the expected reason' >&2
    exit 1
}
echo '[ok] mismatched sfetch engine fails before execution'

MARKER="$marker" SFETCH_BOOTSTRAP_TESTING=1 \
    ./scripts/install-sfetch-verified.sh \
    --version v0.4.12 \
    --dir "$install_dir" \
    --engine-sha bd0e7a0e68ef5a3dc7cda862fc74e4e8bc5125f8 \
    --engine-sha256 "$digest" \
    --engine-file "$engine" >/dev/null
[ -f "$marker" ] || {
    echo 'error: positive-control engine did not execute' >&2
    exit 1
}
echo '[ok] matching-digest positive control executes the engine'
