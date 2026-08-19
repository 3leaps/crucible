#!/usr/bin/env bash
#
# Cloud Agent install script for 3leaps/crucible.
#
# Prepares a fresh machine with the toolchain `make check` / `make precommit`
# need: the sfetch -> goneat trust chain plus the foundation tools declared in
# .goneat/tools.yaml (prettier, yamlfmt, yamllint, shfmt, checkmake, actionlint).
#
# Design notes:
# - Follows the repo trust anchor chain (curl -> sfetch -> goneat) with
#   signature verification (minisign) preserved.
# - Installs Go-based tools with GOBIN=~/.local/bin and Python/pip tools with
#   --user so everything lands on the login PATH (~/.local/bin via ~/.profile,
#   ~/.bun/bin via ~/.bashrc) without needing repo-local bin/ at runtime.
# - Idempotent: every step is guarded so reruns are fast no-ops.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

GONEAT_VERSION="v0.5.1"

log() { printf '[install] %s\n' "$*"; }

export GOBIN="$HOME/.local/bin"
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$REPO_ROOT/bin:$PATH"
mkdir -p "$HOME/.local/bin" bin

# Ensure user-space tool dirs are on PATH for future non-login shells too.
# (~/.profile already adds ~/.local/bin for login shells; the bun installer adds
# ~/.bun/bin. This guard makes interactive shells consistent.)
if ! grep -q 'crucible cloud-agent PATH' "$HOME/.bashrc" 2>/dev/null; then
    cat >>"$HOME/.bashrc" <<'EOF'

# crucible cloud-agent PATH (added by .cursor/install.sh)
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"
EOF
fi

# 1. minisign — required by the sfetch installer to verify release signatures.
if ! command -v minisign >/dev/null 2>&1; then
    log "Installing minisign (sfetch signature verification)"
    sudo apt-get update -qq
    sudo apt-get install -y -qq minisign
fi

# 2. bun — JavaScript runtime; supplies prettier via node_modules/.bin.
if ! command -v bun >/dev/null 2>&1; then
    log "Installing bun"
    curl -fsSL https://bun.sh/install | bash
    export PATH="$HOME/.bun/bin:$PATH"
fi

# 3. sfetch — trust anchor, installed to the repo-local bin/.
if [ ! -x bin/sfetch ] && ! command -v sfetch >/dev/null 2>&1; then
    log "Installing sfetch (trust anchor)"
    curl -fsSL https://github.com/3leaps/sfetch/releases/latest/download/install-sfetch.sh |
        bash -s -- --dir "$REPO_ROOT/bin" --yes
fi

# 4. goneat — schema/config validation engine, installed via sfetch.
if ! command -v goneat >/dev/null 2>&1; then
    log "Installing goneat ${GONEAT_VERSION} via sfetch"
    sfetch --repo fulmenhq/goneat --tag "$GONEAT_VERSION" --install
fi

# 5. Go-based foundation tools (land in $GOBIN = ~/.local/bin).
command -v yamlfmt >/dev/null 2>&1 || { log "Installing yamlfmt"; go install github.com/google/yamlfmt/cmd/yamlfmt@latest; }
command -v shfmt >/dev/null 2>&1 || { log "Installing shfmt"; go install mvdan.cc/sh/v3/cmd/shfmt@latest; }
command -v checkmake >/dev/null 2>&1 || { log "Installing checkmake"; go install github.com/checkmake/checkmake/cmd/checkmake@latest; }
command -v actionlint >/dev/null 2>&1 || { log "Installing actionlint"; go install github.com/rhysd/actionlint/cmd/actionlint@latest; }

# 6. yamllint (Python) — installed for the current user.
if ! command -v yamllint >/dev/null 2>&1; then
    log "Installing yamllint"
    pip install --user --quiet yamllint ||
        pip install --user --break-system-packages --quiet yamllint
fi

# 7. Project JS dependencies (prettier).
log "Installing bun dependencies"
bun install --silent

log "Install complete"
