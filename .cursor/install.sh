#!/usr/bin/env bash
# Cloud Agent install for 3leaps Crucible.
#
# Idempotent bootstrap of the crucible development toolchain following the
# repository's documented trust chain (curl -> sfetch -> goneat -> tools) plus
# bun for prettier. When a sibling waitprims checkout is present, its Rust
# toolchain requirements are satisfied as well.
#
# Safe to run repeatedly: every step is guarded and only does work when a tool
# or dependency is actually missing.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRUCIBLE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_DIR="$(cd "$CRUCIBLE_DIR/.." && pwd)"

# Pinned tool versions (kept in sync with .goneat/tools.yaml and Makefile).
GONEAT_VERSION="v0.5.1"
YAMLFMT_VERSION="v0.21.0"
SHFMT_VERSION="v3.13.1"
ACTIONLINT_VERSION="v1.7.12"

log() { printf '[install] %s\n' "$*"; }

# ---------------------------------------------------------------------------
# 1. Persist tool paths for login/interactive shells the agent will use.
# ---------------------------------------------------------------------------
PATH_LINE='export PATH="$HOME/.local/bin:$HOME/.bun/bin:$HOME/go/bin:$PATH"'
ensure_path_block() {
    local file="$1"
    [ -e "$file" ] || : >"$file"
    if ! grep -qF 'crucible cloud-agent PATH' "$file" 2>/dev/null; then
        {
            echo ''
            echo '# >>> crucible cloud-agent PATH >>>'
            echo "$PATH_LINE"
            echo '# <<< crucible cloud-agent PATH <<<'
        } >>"$file"
        log "added PATH block to ${file}"
    fi
}
ensure_path_block "$HOME/.bashrc"
ensure_path_block "$HOME/.profile"
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$HOME/go/bin:$PATH"

# ---------------------------------------------------------------------------
# 2. System packages (apt): yamllint (make check), shellcheck + minisign
#    (goneat assess / sfetch verification). Only install what is missing.
# ---------------------------------------------------------------------------
missing_apt=()
command -v yamllint >/dev/null 2>&1 || missing_apt+=(yamllint)
command -v shellcheck >/dev/null 2>&1 || missing_apt+=(shellcheck)
command -v minisign >/dev/null 2>&1 || missing_apt+=(minisign)
if [ "${#missing_apt[@]}" -gt 0 ]; then
    if command -v apt-get >/dev/null 2>&1; then
        SUDO=""
        [ "$(id -u)" -ne 0 ] && SUDO="sudo"
        log "installing system packages: ${missing_apt[*]}"
        $SUDO apt-get update -qq
        DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq "${missing_apt[@]}"
    else
        log "WARN: apt-get unavailable; cannot install: ${missing_apt[*]}"
    fi
fi

# ---------------------------------------------------------------------------
# 3. bun (JavaScript runtime powering prettier).
# ---------------------------------------------------------------------------
if ! command -v bun >/dev/null 2>&1 && [ ! -x "$HOME/.bun/bin/bun" ]; then
    log "installing bun"
    curl -fsSL https://bun.sh/install | bash
fi

# ---------------------------------------------------------------------------
# 4. Go-based lint/format tools (yamlfmt, shfmt, checkmake, actionlint).
# ---------------------------------------------------------------------------
if command -v go >/dev/null 2>&1; then
    command -v yamlfmt >/dev/null 2>&1 || { log "go install yamlfmt"; go install "github.com/google/yamlfmt/cmd/yamlfmt@${YAMLFMT_VERSION}"; }
    command -v shfmt >/dev/null 2>&1 || { log "go install shfmt"; go install "mvdan.cc/sh/v3/cmd/shfmt@${SHFMT_VERSION}"; }
    command -v checkmake >/dev/null 2>&1 || { log "go install checkmake"; go install "github.com/checkmake/checkmake/cmd/checkmake@latest"; }
    command -v actionlint >/dev/null 2>&1 || { log "go install actionlint"; go install "github.com/rhysd/actionlint/cmd/actionlint@${ACTIONLINT_VERSION}"; }
else
    log "WARN: go toolchain not found; skipping yamlfmt/shfmt/checkmake/actionlint"
fi

# ---------------------------------------------------------------------------
# 5. Trust chain: sfetch (repo-local anchor) -> goneat (schema validation).
# ---------------------------------------------------------------------------
mkdir -p "$CRUCIBLE_DIR/bin"
SFETCH=""
if [ -x "$CRUCIBLE_DIR/bin/sfetch" ]; then
    SFETCH="$CRUCIBLE_DIR/bin/sfetch"
elif command -v sfetch >/dev/null 2>&1; then
    SFETCH="$(command -v sfetch)"
else
    log "installing sfetch (trust anchor)"
    curl -fsSL "https://github.com/3leaps/sfetch/releases/latest/download/install-sfetch.sh" \
        | bash -s -- --dir "$CRUCIBLE_DIR/bin" --yes
    SFETCH="$CRUCIBLE_DIR/bin/sfetch"
fi

if ! command -v goneat >/dev/null 2>&1; then
    log "installing goneat ${GONEAT_VERSION} via sfetch"
    mkdir -p "$HOME/.local/bin"
    "$SFETCH" --repo fulmenhq/goneat --tag "$GONEAT_VERSION" --install --yes
fi

# ---------------------------------------------------------------------------
# 6. Crucible bun dependencies (prettier).
# ---------------------------------------------------------------------------
log "installing crucible bun dependencies"
(cd "$CRUCIBLE_DIR" && bun install)

# ---------------------------------------------------------------------------
# 7. Rust toolchain (>= 1.88 MSRV, needed by a sibling waitprims checkout).
#    The stock image ships 1.83, which is too old for edition2024 deps.
# ---------------------------------------------------------------------------
if command -v rustup >/dev/null 2>&1; then
    if ! rustup toolchain list 2>/dev/null | grep -q '^stable'; then
        log "installing Rust stable toolchain"
        rustup toolchain install stable --profile minimal
    fi
    rustup component add rustfmt clippy --toolchain stable >/dev/null 2>&1 || true
    rustup default stable >/dev/null 2>&1 || true
    log "Rust default: $(rustc --version 2>/dev/null || echo unknown)"
fi

# ---------------------------------------------------------------------------
# 8. Optional sibling waitprims checkout: pre-fetch locked dependencies.
# ---------------------------------------------------------------------------
if [ -f "$WORKSPACE_DIR/waitprims/Cargo.toml" ] && command -v cargo >/dev/null 2>&1; then
    log "pre-fetching waitprims Rust dependencies"
    (cd "$WORKSPACE_DIR/waitprims" && cargo fetch --locked)
fi

log "install complete"
