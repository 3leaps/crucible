# 3leaps Crucible Makefile
# Lightweight standards repository
#
# Compliant with docs/repository/makefile-minimum.md
#
# Quick Reference:
#   make help       - Show all available targets
#   make bootstrap  - Install tools (sfetch -> goneat -> others)
#   make check      - Run all quality checks
#   make fmt        - Format all files

.PHONY: all help bootstrap bootstrap-force tools check test fmt lint lint-schemas lint-config build clean version
# lint-config added as dependency of lint - validates config/*.yaml against schemas
.PHONY: version-set version-patch version-minor version-major
.PHONY: precommit prepush deps-check
.PHONY: release-tag release-verify-tag release-guard-tag-version sync-version-badge sync-changelog-links

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

VERSION := $(shell cat VERSION 2>/dev/null || echo "dev")

# Tool installation directory
# Bootstrap installs to repo-local bin/ by default
BIN_DIR := $(CURDIR)/bin

# Pinned tool versions (minimum - won't downgrade existing installs)
SFETCH_VERSION := latest
GONEAT_VERSION ?= v0.5.1

# Tool paths
# sfetch: repo-local (trust anchor) or PATH
# goneat: user-space PATH only (like prettier, biome, ruff)
SFETCH = $(shell [ -x "$(BIN_DIR)/sfetch" ] && echo "$(BIN_DIR)/sfetch" || command -v sfetch 2>/dev/null)
GONEAT = $(shell command -v goneat 2>/dev/null)

# -----------------------------------------------------------------------------
# Default and Help
# -----------------------------------------------------------------------------

all: check

help: ## Show available targets
	@echo "3leaps Crucible - Standards Repository"
	@echo "The common ground for uncommon tools."
	@echo ""
	@echo "Required targets:"
	@echo "  help            Show this help message"
	@echo "  bootstrap       Install tools (sfetch -> goneat -> others)"
	@echo "  check           Run all quality checks (fmt, lint)"
	@echo "  test            Run test suite (placeholder)"
	@echo "  fmt             Format code (prettier, yamlfmt)"
	@echo "  lint            Run linting (yamllint, schema validation)"
	@echo "  lint-schemas    Validate JSON Schema files against meta-schema"
	@echo "  build           Build artifacts (validation is the build)"
	@echo "  clean           Remove build artifacts"
	@echo "  version         Print current version"
	@echo "  precommit       Pre-commit checks (assess + schema validation)"
	@echo "  prepush         Pre-push checks (assess + schema validation)"
	@echo "  deps-check      Check dev dependencies for cooling violations"
	@echo ""
	@echo "Version management:"
	@echo "  version-set     Set version (make version-set V=x.y.z)"
	@echo "  version-patch   Bump patch version (0.1.0 -> 0.1.1)"
	@echo "  version-minor   Bump minor version (0.1.0 -> 0.2.0)"
	@echo "  version-major   Bump major version (0.1.0 -> 1.0.0)"
	@echo ""
	@echo "Release management:"
	@echo "  release-tag             Create signed git tag with safety checks"
	@echo "  release-verify-tag      Verify signed tag signature"
	@echo "  release-guard-tag-version  Verify tag matches VERSION file"
	@echo "  sync-changelog-links    Sync CHANGELOG compare-link footers to VERSION"
	@echo ""
	@echo "Current version: $(VERSION)"

# -----------------------------------------------------------------------------
# Bootstrap - Trust Anchor Chain
# -----------------------------------------------------------------------------
#
# Trust chain: curl -> sfetch -> goneat -> other tools
#
# sfetch (3leaps/sfetch) is the trust anchor - a minimal, auditable binary fetcher.
# goneat (fulmenhq/goneat) is installed via sfetch and manages additional tooling.

bootstrap: ## Install required tools (sfetch -> goneat -> others)
	@echo "Bootstrapping crucible development environment..."
	@echo ""
	@# Step 0: Verify curl is available (required trust anchor)
	@if ! command -v curl >/dev/null 2>&1; then \
		echo "curl not found (required for bootstrap)"; \
		echo ""; \
		echo "Install curl for your platform:"; \
		echo "  macOS:  brew install curl"; \
		echo "  Ubuntu: sudo apt install curl"; \
		echo "  Fedora: sudo dnf install curl"; \
		exit 1; \
	fi
	@echo "[ok] curl found"
	@echo ""
	@# Step 1: Install sfetch (trust anchor)
	@mkdir -p "$(BIN_DIR)"
	@if [ ! -x "$(BIN_DIR)/sfetch" ] && ! command -v sfetch >/dev/null 2>&1; then \
		echo "[..] Installing sfetch (trust anchor)..."; \
		curl -fsSL https://github.com/3leaps/sfetch/releases/download/$(SFETCH_VERSION)/install-sfetch.sh | bash -s -- --dest "$(BIN_DIR)"; \
	else \
		echo "[ok] sfetch already installed"; \
	fi
	@# Verify sfetch
	@SFETCH_BIN=""; \
	if [ -x "$(BIN_DIR)/sfetch" ]; then SFETCH_BIN="$(BIN_DIR)/sfetch"; \
	elif command -v sfetch >/dev/null 2>&1; then SFETCH_BIN="$$(command -v sfetch)"; fi; \
	if [ -z "$$SFETCH_BIN" ]; then echo "[!!] sfetch installation failed"; exit 1; fi; \
	echo "[ok] sfetch: $$SFETCH_BIN"
	@echo ""
	@# Step 2: Install goneat via sfetch
	@SFETCH_BIN=""; \
	if [ -x "$(BIN_DIR)/sfetch" ]; then SFETCH_BIN="$(BIN_DIR)/sfetch"; \
	elif command -v sfetch >/dev/null 2>&1; then SFETCH_BIN="$$(command -v sfetch)"; fi; \
	if [ "$(FORCE)" = "1" ] || ! command -v goneat >/dev/null 2>&1; then \
		echo "[..] Installing goneat $(GONEAT_VERSION) via sfetch (user-space)..."; \
		$$SFETCH_BIN --repo fulmenhq/goneat --tag $(GONEAT_VERSION); \
	else \
		echo "[ok] goneat already installed"; \
	fi
	@# Verify goneat (user-space only, not repo-local)
	@if command -v goneat >/dev/null 2>&1; then \
		echo "[ok] goneat: $$(goneat version 2>&1 | head -n1)"; \
	else \
		echo "[!!] goneat installation failed"; exit 1; \
	fi
	@echo ""
	@# Step 3: Install foundation tools via goneat
	@echo "[..] Installing foundation tools via goneat..."
	@goneat doctor tools --scope foundation --install --install-package-managers --yes --no-cooling 2>/dev/null || \
	goneat doctor tools --install --yes 2>/dev/null || \
	echo "[!!] goneat doctor tools not available, skipping"
	@echo ""
	@# Step 4: Verify bun is available (required for 3leaps development)
	@if ! command -v bun >/dev/null 2>&1; then \
		echo "[!!] bun not found (required for 3leaps development)"; \
		echo ""; \
		echo "Install bun:"; \
		echo "  curl -fsSL https://bun.sh/install | bash"; \
		echo ""; \
		echo "Or via Homebrew:"; \
		echo "  brew install oven-sh/bun/bun"; \
		exit 1; \
	fi
	@echo "[ok] bun: $$(bun --version)"
	@echo ""
	@# Step 5: Install bun dependencies
	@echo "[..] Installing bun dependencies..."
	@bun install --silent
	@echo "[ok] bun dependencies installed"
	@echo ""
	@echo "[ok] Bootstrap complete"
	@echo ""
	@echo "Ensure $(BIN_DIR) is in your PATH, or tools will be found automatically."

bootstrap-force: ## Force reinstall all tools
	@$(MAKE) bootstrap FORCE=1

tools: ## Verify external tools are available
	@echo "Verifying tools..."
	@# Check bun (required)
	@if command -v bun >/dev/null 2>&1; then \
		echo "[ok] bun: $$(bun --version)"; \
	else \
		echo "[!!] bun not found (required - run 'make bootstrap')"; \
	fi
	@# Check sfetch
	@if [ -x "$(BIN_DIR)/sfetch" ]; then \
		echo "[ok] sfetch: $(BIN_DIR)/sfetch"; \
	elif command -v sfetch >/dev/null 2>&1; then \
		echo "[ok] sfetch: $$(command -v sfetch)"; \
	else \
		echo "[!!] sfetch not found (run 'make bootstrap')"; \
	fi
	@# Check goneat (user-space)
	@if command -v goneat >/dev/null 2>&1; then \
		echo "[ok] goneat: $$(goneat version 2>&1 | head -n1)"; \
	else \
		echo "[!!] goneat not found - run 'make bootstrap'"; \
	fi
	@# Check prettier (via bun)
	@if [ -x "./node_modules/.bin/prettier" ]; then \
		echo "[ok] prettier: $$(./node_modules/.bin/prettier --version) (bun)"; \
	elif command -v prettier >/dev/null 2>&1; then \
		echo "[ok] prettier: $$(prettier --version)"; \
	else \
		echo "[!!] prettier not found"; \
	fi
	@# Check yamlfmt
	@if command -v yamlfmt >/dev/null 2>&1; then \
		echo "[ok] yamlfmt: $$(yamlfmt --version 2>&1 | head -n1)"; \
	else \
		echo "[!!] yamlfmt not found"; \
	fi
	@# Check yamllint
	@if command -v yamllint >/dev/null 2>&1; then \
		echo "[ok] yamllint found"; \
	else \
		echo "[!!] yamllint not found"; \
	fi
	@echo ""

# -----------------------------------------------------------------------------
# Quality Gates
# -----------------------------------------------------------------------------

check: fmt lint ## Run all quality checks
	@echo "[ok] All quality checks passed"

test: ## Run test suite (placeholder for standards repo)
	@echo "No tests configured (standards repository)"

fmt: ## Format code (prettier for md/json, yamlfmt for yaml)
	@echo "Formatting..."
	@# Format markdown and JSON with prettier (prefer bun-installed)
	@if [ -x "./node_modules/.bin/prettier" ]; then \
		echo "[..] Formatting markdown and JSON (prettier via bun)..."; \
		./node_modules/.bin/prettier --write "**/*.md" "**/*.json" --ignore-path .gitignore 2>/dev/null || true; \
	elif command -v prettier >/dev/null 2>&1; then \
		echo "[..] Formatting markdown and JSON (prettier system)..."; \
		prettier --write "**/*.md" "**/*.json" --ignore-path .gitignore 2>/dev/null || true; \
	else \
		echo "[!!] prettier not found, skipping md/json formatting"; \
	fi
	@# Format YAML with yamlfmt
	@if command -v yamlfmt >/dev/null 2>&1; then \
		echo "[..] Formatting YAML (yamlfmt)..."; \
		yamlfmt . 2>/dev/null || true; \
	else \
		echo "[!!] yamlfmt not found, skipping YAML formatting"; \
	fi
	@echo "[ok] Formatting complete"

lint: lint-schemas lint-config ## Run linting checks
	@echo "Linting..."
	@# Lint YAML with yamllint
	@if command -v yamllint >/dev/null 2>&1; then \
		echo "[..] Linting YAML (yamllint)..."; \
		yamllint -c .yamllint . 2>&1 | grep -v "^$$" || true; \
	else \
		echo "[!!] yamllint not found, skipping YAML linting"; \
	fi
	@echo "[ok] Linting complete"

lint-schemas: ## Validate JSON Schema files against meta-schema
	@echo "[..] Validating JSON Schema files..."
	@if command -v goneat >/dev/null 2>&1; then \
		SCHEMA_FILES=$$(find schemas -name "*.schema.json" 2>/dev/null); \
		if [ -n "$$SCHEMA_FILES" ]; then \
			goneat schema validate-schema --schema-id json-schema-2020-12 $$SCHEMA_FILES; \
		else \
			echo "[--] No schema files found in schemas/"; \
		fi \
	else \
		echo "[!!] goneat not found, skipping schema validation"; \
	fi

lint-config: ## Validate config data files against schemas
	@echo "[..] Validating config data files..."
	@if command -v goneat >/dev/null 2>&1; then \
		for f in config/agentic/roles/*.yaml; do \
			[ -f "$$f" ] || continue; \
			echo "    Validating $$f..."; \
			goneat validate data --schema-file schemas/agentic/v0/role-prompt.schema.json --data "$$f" || exit 1; \
		done; \
		for f in config/classifiers/dimensions/*.dimension.json; do \
			[ -f "$$f" ] || continue; \
			echo "    Validating $$f..."; \
			goneat validate data --schema-file schemas/classifiers/v0/dimension-definition.schema.json --data "$$f" || exit 1; \
		done; \
		for f in schemas/auth/v0/session-artifact.example.json; do \
			[ -f "$$f" ] || continue; \
			echo "    Validating $$f..."; \
			goneat validate data --schema-file schemas/auth/v0/session-artifact.schema.json --data "$$f" || exit 1; \
		done; \
		for f in schemas/data-artifact/v0/examples/*.descriptor.json; do \
			[ -f "$$f" ] || continue; \
			echo "    Validating $$f..."; \
			goneat validate data --schema-file schemas/data-artifact/v0/artifact-descriptor.schema.json --data "$$f" || exit 1; \
		done; \
		for f in schemas/coverage-attestation/v0/coverage-attestation.example.json; do \
			[ -f "$$f" ] || continue; \
			echo "    Validating $$f..."; \
			goneat validate data --schema-file schemas/coverage-attestation/v0/coverage-attestation.schema.json --data "$$f" || exit 1; \
		done; \
		echo "    Validating contract manifests..."; \
		sh scripts/validate-contract-manifests.sh \
			schemas/data-artifact/v0/contract.json \
			schemas/coverage-attestation/v0/contract.json || exit 1; \
	else \
		echo "[!!] goneat not found, skipping config validation"; \
	fi

build: ## Build artifacts (validation is the build for standards repo)
	@echo "Building..."
	@echo "[ok] Build complete (crucible is docs - validation is the build)"

clean: ## Remove build artifacts
	@echo "Cleaning..."
	@rm -rf node_modules/.cache
	@# Note: bin/ contains bootstrap tools, node_modules/ is restorable
	@echo "[ok] Clean complete"

# -----------------------------------------------------------------------------
# Pre-commit / Pre-push Hooks (via goneat assess + schema validation)
# -----------------------------------------------------------------------------
#
# Both targets run goneat assess AND schema/config validation to ensure
# no invalid schemas or configs slip through (goneat assess doesn't cover these).
#
# precommit: Fast checks suitable for every commit
#   - Categories: format, lint, security
#   - Fail threshold: critical
#   - Plus: lint-schemas, lint-config
#
# prepush: Thorough checks before pushing
#   - Categories: format, lint, security
#   - Fail threshold: low (fail on any issue)
#   - Plus: lint-schemas, lint-config
#
# Install hooks: goneat hooks init && goneat hooks generate && goneat hooks install

precommit: ## Run pre-commit checks (goneat assess --fail-on critical + schema validation)
	@echo "Running pre-commit checks..."
	@if command -v goneat >/dev/null 2>&1; then \
		PATH="$(CURDIR)/node_modules/.bin:$$PATH" goneat assess --categories format,lint,security --fail-on critical --ci-summary; \
	else \
		echo "[!!] goneat not found, falling back to basic checks"; \
		$(MAKE) fmt lint; \
	fi
	@# Always run schema/config validation (goneat assess doesn't cover these)
	@$(MAKE) lint-schemas lint-config
	@echo "[ok] Pre-commit checks passed"

prepush: ## Run pre-push checks (goneat assess --fail-on low + schema validation)
	@echo "Running pre-push checks..."
	@if command -v goneat >/dev/null 2>&1; then \
		PATH="$(CURDIR)/node_modules/.bin:$$PATH" goneat assess --categories format,lint,security --fail-on low --ci-summary; \
	else \
		echo "[!!] goneat not found, falling back to basic checks"; \
		$(MAKE) fmt lint; \
	fi
	@# Always run schema/config validation (goneat assess doesn't cover these)
	@$(MAKE) lint-schemas lint-config
	@echo "[ok] Pre-push checks passed"

deps-check: ## Check dev dependencies for cooling violations
	@echo "Checking dev dependencies..."
	@if command -v goneat >/dev/null 2>&1; then \
		goneat dependencies check --cooling-days 7 --dev-deps-only 2>/dev/null || \
		echo "[--] Dependency cooling check not available"; \
	else \
		echo "[--] goneat not found, skipping dependency check"; \
	fi

# -----------------------------------------------------------------------------
# Version Management
# -----------------------------------------------------------------------------

version: ## Print current version
	@echo "$(VERSION)"

version-set: ## Set version (usage: make version-set V=x.y.z)
	@if [ -z "$(V)" ]; then \
		echo "[!!] V not specified. Usage: make version-set V=x.y.z"; \
		exit 1; \
	fi
	@echo "$(V)" > VERSION
	@# Update package.json if jq available
	@if [ -f "package.json" ] && command -v jq >/dev/null 2>&1; then \
		jq '.version = "$(V)"' package.json > package.json.tmp && mv package.json.tmp package.json; \
	fi
	@$(MAKE) sync-version-badge
	@$(MAKE) sync-changelog-links
	@echo "[ok] Version set to $(V)"

version-patch: ## Bump patch version (0.1.0 -> 0.1.1)
	@current=$(VERSION); \
	major=$$(echo $$current | cut -d. -f1); \
	minor=$$(echo $$current | cut -d. -f2); \
	patch=$$(echo $$current | cut -d. -f3); \
	newpatch=$$((patch + 1)); \
	newver="$$major.$$minor.$$newpatch"; \
	$(MAKE) version-set V=$$newver || exit $$?; \
	echo "[ok] Version bumped: $$current -> $$newver"

version-minor: ## Bump minor version (0.1.0 -> 0.2.0)
	@current=$(VERSION); \
	major=$$(echo $$current | cut -d. -f1); \
	minor=$$(echo $$current | cut -d. -f2); \
	newminor=$$((minor + 1)); \
	newver="$$major.$$newminor.0"; \
	$(MAKE) version-set V=$$newver || exit $$?; \
	echo "[ok] Version bumped: $$current -> $$newver"

version-major: ## Bump major version (0.1.0 -> 1.0.0)
	@current=$(VERSION); \
	major=$$(echo $$current | cut -d. -f1); \
	newmajor=$$((major + 1)); \
	newver="$$newmajor.0.0"; \
	$(MAKE) version-set V=$$newver || exit $$?; \
	echo "[ok] Version bumped: $$current -> $$newver"

# -----------------------------------------------------------------------------
# Release Management
# -----------------------------------------------------------------------------
#
# Safety-first release tagging with automated checks:
# - Tag format validation (vMAJOR.MINOR.PATCH)
# - Clean working tree required
# - Must be on main branch (overridable)
# - Tag must not already exist
# - GPG signing key availability verified
# - Automatic signature verification after creation
#
# Environment variables (see scripts/release-tag.sh for full list):
# - THREELEAPS_CRUCIBLE_GPG_HOMEDIR: dedicated signing keyring directory
# - THREELEAPS_CRUCIBLE_PGP_KEY_ID: specific key id/email/fingerprint
# - THREELEAPS_CRUCIBLE_ALLOW_NON_MAIN: set to 1 to allow tagging from non-main branch

release-tag: ## Create signed git tag with safety checks
	@./scripts/release-tag.sh

release-verify-tag: ## Verify signed tag signature
	@./scripts/release-verify-tag.sh

release-guard-tag-version: ## Verify tag matches VERSION file
	@./scripts/release-guard-tag-version.sh

sync-version-badge: ## Sync README badge to VERSION file
	@./scripts/sync-version-badge.sh

sync-changelog-links: ## Sync CHANGELOG compare-link footers to VERSION
	@./scripts/sync-changelog-links.sh
