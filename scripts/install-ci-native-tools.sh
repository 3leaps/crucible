#!/usr/bin/env bash
# Native macOS/Windows contract tools; release tools retain the verified trust chain.
set -euo pipefail

test "$(go env GOHOSTARCH)" = "${EXPECTED_ARCH:?}"
for tool in curl sha256sum make jq cmp; do
    command -v "$tool"
done
tools="$(pwd)/bin"
mkdir -p "$tools"

# Git Bash paths must be native absolute paths in Go's environment and GITHUB_PATH.
if [ "${OS:-}" = Windows_NT ]; then
    native_tools="$(cygpath -w "$tools")"
else
    native_tools="$tools"
fi
export GOBIN="$native_tools"
export PATH="$tools:$PATH"

# setup-python exposes python.exe on Windows, while repository controls use python3.
if [ "${OS:-}" = Windows_NT ]; then
    cat >"$tools/python3" <<'EOF'
#!/usr/bin/env bash
exec python "$@"
EOF
    chmod +x "$tools/python3"
fi

case "${GONEAT_ACQUISITION:?}" in
    release) make bootstrap-release-tools SHELL=bash BIN_DIR="$tools" ;;
    source)
        # Explicit Windows ARM64 lane; never a fallback from download failure.
        test "${OS:-}" = Windows_NT
        test "$EXPECTED_ARCH" = arm64
        make bootstrap-sfetch SHELL=bash BIN_DIR="$tools"
        python scripts/ci-platforms.py install-source
        ;;
    *)
        echo 'error: unknown Goneat acquisition route' >&2
        exit 1
        ;;
esac

for tool in make jq python3 goneat; do
    command -v "$tool"
done
jq --version
printf '%s\n' "$native_tools" >>"${GITHUB_PATH:?}"
