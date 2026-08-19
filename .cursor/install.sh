#!/usr/bin/env bash
# Cloud Agent bootstrap for 3leaps/crucible.
#
# Installs the toolchain that `make check`, `make precommit`, and `make prepush`
# rely on, on top of Cursor's default base image (which already provides go,
# node, curl, make, jq, yq, ripgrep, pip, git, and sudo).
#
# This mirrors `make bootstrap` / .goneat/tools.yaml, but installs deterministically
# without Homebrew (absent on the Cloud Agent image). It is idempotent: re-running
# it is safe and skips work that is already done.
set -euo pipefail

GONEAT_VERSION="v0.5.1"  # keep in sync with Makefile GONEAT_VERSION
BIN_DIR="/usr/local/bin" # on PATH for every shell type in the Cloud Agent VM
REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || pwd)"

log() { printf '[install] %s\n' "$*"; }

# 1. bun -- JavaScript runtime + package manager required by 3leaps dev flow.
if ! command -v bun >/dev/null 2>&1; then
    log "Installing bun..."
    curl -fsSL https://bun.sh/install | bash >/dev/null
fi
BUN_BIN="$HOME/.bun/bin/bun"
[ -x "$BUN_BIN" ] || BUN_BIN="$(command -v bun)"
sudo ln -sf "$BUN_BIN" "$BIN_DIR/bun"

# 2. goneat -- schema/config validation + assess (curl -> goneat trust chain).
if ! command -v goneat >/dev/null 2>&1; then
    log "Installing goneat ${GONEAT_VERSION}..."
    tmp="$(mktemp -d)"
    curl -fsSL -o "$tmp/goneat.tar.gz" \
        "https://github.com/fulmenhq/goneat/releases/download/${GONEAT_VERSION}/goneat_${GONEAT_VERSION}_linux_amd64.tar.gz"
    tar -xzf "$tmp/goneat.tar.gz" -C "$tmp"
    sudo install -m 0755 "$tmp/goneat" "$BIN_DIR/goneat"
    rm -rf "$tmp"
fi

# 3. Go-based foundation tools (formatters/linters used by make check/precommit).
GOBIN="$(go env GOPATH)/bin"
export GOBIN
install_go_tool() { # <binary> <module@version>
    if [ ! -x "$GOBIN/$1" ]; then
        log "Installing $1..."
        go install "$2"
    fi
    sudo ln -sf "$GOBIN/$1" "$BIN_DIR/$1"
}
install_go_tool yamlfmt github.com/google/yamlfmt/cmd/yamlfmt@latest
install_go_tool shfmt mvdan.cc/sh/v3/cmd/shfmt@latest
install_go_tool actionlint github.com/rhysd/actionlint/cmd/actionlint@latest
install_go_tool checkmake github.com/checkmake/checkmake/cmd/checkmake@latest

# 4. yamllint -- YAML linter used by make lint.
if ! command -v yamllint >/dev/null 2>&1; then
    log "Installing yamllint..."
    sudo pip3 install --quiet yamllint
fi

# 5. prettier -- markdown/JSON formatter used by `make fmt`/`make check` and the
#    package.json scripts.
#
#    Installed globally (durable) rather than only into the repo's node_modules,
#    because a prebuilt-environment agent re-checks-out the repo cold on every
#    boot, which wipes a repo-local node_modules. The Makefile prefers
#    ./node_modules/.bin/prettier and falls back to prettier on PATH, so a global
#    install keeps `make check` fully functional without node_modules.
PRETTIER_VERSION="3.7.4" # keep in sync with bun.lock / package.json
if ! command -v prettier >/dev/null 2>&1; then
    log "Installing prettier ${PRETTIER_VERSION}..."
    bun install -g "prettier@${PRETTIER_VERSION}"
fi
sudo ln -sf "$HOME/.bun/bin/prettier" "$BIN_DIR/prettier"

# Also install the repo's JS deps for local convenience (present for just-in-time
# agents; harmless when a fresh checkout later removes node_modules).
log "Installing repo JS dependencies..."
(cd "$REPO_ROOT" && bun install)

log "Bootstrap complete. Run 'make check' to verify."
