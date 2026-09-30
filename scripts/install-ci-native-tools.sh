#!/usr/bin/env bash
# Native macOS/Windows quality tools; release tools retain the verified trust chain.
set -euo pipefail

test "$(go env GOHOSTARCH)" = "${EXPECTED_ARCH:?}"
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

# These pins match the v0.5.7 runner inventory. Go verifies module checksums;
# npm uses registry integrity metadata; pip uses the HTTPS index. These supporting
# tools are not release trust anchors or a hash-locked transitive dependency set.
go install github.com/google/yamlfmt/cmd/yamlfmt@v0.21.0
go install mvdan.cc/sh/v3/cmd/shfmt@v3.13.1
go install github.com/checkmake/checkmake/cmd/checkmake@v0.3.2
go install github.com/rhysd/actionlint/cmd/actionlint@v1.7.12
go install github.com/mikefarah/yq/v4@v4.53.3
python -m pip install --disable-pip-version-check yamllint==1.37.1
npm install --global prettier@3.9.6

for tool in make jq rg yq yamlfmt yamllint shfmt checkmake actionlint prettier; do
    command -v "$tool"
done
yamlfmt --version
yamllint --version
shfmt --version
checkmake --version
actionlint --version
prettier --version
jq --version
rg --version
yq --version
printf '%s\n' "$native_tools" >>"${GITHUB_PATH:?}"
