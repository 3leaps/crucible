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

.PHONY: all help bootstrap bootstrap-force tools check test test-bootstrap-engine-verification fmt fmt-check lint lint-schemas lint-config lint-config-data lint-contracts lint-role-prompts lint-coverage-attestation lint-inference-path-taxonomy build clean version
# lint-config added as dependency of lint - validates config/*.yaml against schemas
.PHONY: version-set version-patch version-minor version-major
.PHONY: precommit prepush deps-check
.PHONY: release-tag release-verify-tag release-guard-tag-version release-guard-tag-ruleset release-guard-release-surfaces sync-version-badge sync-changelog-links

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

VERSION := $(shell cat VERSION 2>/dev/null || echo "dev")

# Tool installation directory
# Bootstrap installs to repo-local bin/ by default
BIN_DIR := $(CURDIR)/bin
SFETCH_CACHE_DIR ?= $(CURDIR)/.cache/sfetch
# Prefer repo-local bootstrap pins in every recipe and child control script.
export PATH := $(BIN_DIR):$(PATH)

# Pinned tool versions (repo-local bootstrap; never float)
SFETCH_VERSION := v0.4.12
# Immutable sfetch revision containing bootstrap-sfetch-verified.sh, coupled to
# SFETCH_VERSION through the engine's fail-closed supported-version range.
SFETCH_ENGINE_SHA := bd0e7a0e68ef5a3dc7cda862fc74e4e8bc5125f8
SFETCH_ENGINE_SHA256 := 6114b7b6c1b4f01b5dcab55de635127301a09bc456eb9094656810300b363532
SFETCH_ENGINE_REPO := 3leaps/sfetch
GONEAT_VERSION ?= v0.6.0

# Tool paths
# Bootstrap installs trust-chain tools repo-locally. Quality targets prefer those
# exact pins but retain PATH fallback for an already-provisioned environment.
SFETCH_LOCAL := $(BIN_DIR)/sfetch
GONEAT_LOCAL := $(BIN_DIR)/goneat
SFETCH = $(shell [ -x "$(SFETCH_LOCAL)" ] && echo "$(SFETCH_LOCAL)" || command -v sfetch 2>/dev/null)
GONEAT = $(shell [ -x "$(GONEAT_LOCAL)" ] && echo "$(GONEAT_LOCAL)" || command -v goneat 2>/dev/null)

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
	@echo "  check           Run non-mutating quality checks"
	@echo "  test            Run release-control negative tests"
	@echo "  fmt             Apply the goneat assessment policy"
	@echo "  lint            Run goneat lint and schema validation"
	@echo "  lint-schemas    Validate JSON Schema files against meta-schema"
	@echo "  build           Build artifacts (validation is the build)"
	@echo "  clean           Remove build artifacts"
	@echo "  version         Print current version"
	@echo "  precommit       Pre-commit checks (assess + schema validation)"
	@echo "  prepush         Pre-push checks (assess + schema validation)"
	@echo "  deps-check      Check dependencies for cooling-policy violations"
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
	@echo "  release-guard-tag-ruleset Verify version-tag ruleset policy"
	@echo "  release-guard-release-surfaces Verify release notes and changelog match VERSION"
	@echo "  sync-changelog-links    Sync CHANGELOG compare-link footers to VERSION"
	@echo ""
	@echo "Current version: $(VERSION)"

# -----------------------------------------------------------------------------
# Bootstrap - Trust Anchor Chain
# -----------------------------------------------------------------------------
#
# Trust chain: curl -> digest-pinned verification engine -> sfetch -> goneat
#              -> other tools
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
	@# Step 1: Install the exact sfetch pin through the verified bootstrap engine.
	@mkdir -p "$(BIN_DIR)"
	@if [ "$(FORCE)" = "1" ]; then rm -f "$(SFETCH_LOCAL)" "$(GONEAT_LOCAL)"; fi
	@if [ -x "$(SFETCH_LOCAL)" ] && [ "$$($(SFETCH_LOCAL) --version 2>&1 | head -n1)" != "sfetch $(patsubst v%,%,$(SFETCH_VERSION))" ]; then \
		echo "[..] Repo-local sfetch does not match $(SFETCH_VERSION); reinstalling..."; \
		rm -f "$(SFETCH_LOCAL)"; \
	fi
	@if [ ! -x "$(SFETCH_LOCAL)" ]; then \
		echo "[..] Installing sfetch $(SFETCH_VERSION) with verified engine @ $(SFETCH_ENGINE_SHA)..."; \
		./scripts/install-sfetch-verified.sh \
			--version "$(SFETCH_VERSION)" \
			--dir "$(BIN_DIR)" \
			--engine-sha "$(SFETCH_ENGINE_SHA)" \
			--engine-sha256 "$(SFETCH_ENGINE_SHA256)" \
			--repo "$(SFETCH_ENGINE_REPO)"; \
	fi
	@if [ ! -x "$(SFETCH_LOCAL)" ]; then echo "[!!] sfetch installation failed (expected $(SFETCH_LOCAL))"; exit 1; fi
	@if [ "$$($(SFETCH_LOCAL) --version 2>&1 | head -n1)" != "sfetch $(patsubst v%,%,$(SFETCH_VERSION))" ]; then \
		echo "[!!] sfetch version mismatch after bootstrap"; exit 1; \
	fi
	@echo "[ok] sfetch: $$($(SFETCH_LOCAL) --version 2>&1 | head -n1) ($(SFETCH_LOCAL))"
	@echo ""
	@# Step 2: Install goneat via sfetch
	@if [ -x "$(GONEAT_LOCAL)" ] && ! "$(GONEAT_LOCAL)" version 2>&1 | head -n1 | grep -Fq "$(GONEAT_VERSION)"; then \
		echo "[..] Repo-local goneat does not match $(GONEAT_VERSION); reinstalling..."; \
		rm -f "$(GONEAT_LOCAL)"; \
	fi
	@if [ ! -x "$(GONEAT_LOCAL)" ]; then \
		echo "[..] Installing goneat $(GONEAT_VERSION) via verified sfetch..."; \
		"$(SFETCH_LOCAL)" --repo fulmenhq/goneat --tag "$(GONEAT_VERSION)" \
			--dest-dir "$(BIN_DIR)" --cache-dir "$(SFETCH_CACHE_DIR)" --require-minisign; \
	fi
	@if [ ! -x "$(GONEAT_LOCAL)" ]; then echo "[!!] goneat installation failed (expected $(GONEAT_LOCAL))"; exit 1; fi
	@if ! "$(GONEAT_LOCAL)" version 2>&1 | head -n1 | grep -Fq "$(GONEAT_VERSION)"; then \
		echo "[!!] goneat version mismatch after bootstrap"; exit 1; \
	fi
	@echo "[ok] goneat: $$($(GONEAT_LOCAL) version 2>&1 | head -n1) ($(GONEAT_LOCAL))"
	@echo ""
	@# Step 3: Install foundation tools via goneat
	@echo "[..] Installing foundation tools via goneat..."
	@"$(GONEAT_LOCAL)" doctor tools --scope foundation --install --install-package-managers --yes --no-cooling 2>/dev/null || \
	 "$(GONEAT_LOCAL)" doctor tools --install --yes 2>/dev/null || \
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

bootstrap-force: ## Force reinstall repo-local sfetch and goneat
	@rm -f "$(SFETCH_LOCAL)" "$(GONEAT_LOCAL)"
	@$(MAKE) bootstrap

tools: ## Verify external tools are available
	@echo "Verifying tools..."
	@# Check bun (required)
	@if command -v bun >/dev/null 2>&1; then \
		echo "[ok] bun: $$(bun --version)"; \
	else \
		echo "[!!] bun not found (required - run 'make bootstrap')"; \
	fi
	@# Check sfetch
	@if [ -x "$(SFETCH_LOCAL)" ]; then \
		echo "[ok] sfetch: $(SFETCH_LOCAL)"; \
	elif command -v sfetch >/dev/null 2>&1; then \
		echo "[ok] sfetch: $$(command -v sfetch)"; \
	else \
		echo "[!!] sfetch not found (run 'make bootstrap')"; \
	fi
	@# Check goneat
	@if [ -x "$(GONEAT_LOCAL)" ]; then \
		echo "[ok] goneat: $$($(GONEAT_LOCAL) version 2>&1 | head -n1)"; \
	elif command -v goneat >/dev/null 2>&1; then \
		echo "[ok] goneat: $$(goneat version 2>&1 | head -n1)"; \
	else \
		echo "[!!] goneat not found - run 'make bootstrap'"; \
	fi
	@echo ""

# -----------------------------------------------------------------------------
# Quality Gates
# -----------------------------------------------------------------------------

check: fmt-check lint test ## Run all quality checks without modifying files
	@echo "[ok] All quality checks passed"

test: test-bootstrap-engine-verification ## Run release-control negative tests
	@./scripts/test-release-guard-tag-ruleset.sh
	@./scripts/test-release-guard-release-surfaces.sh
	@./scripts/release-guard-release-surfaces.sh

test-bootstrap-engine-verification: ## Prove engine digest failure prevents execution
	@./scripts/test-bootstrap-engine-verification.sh

fmt: ## Format files using the repository goneat assessment policy
	@echo "Formatting..."
	@if command -v goneat >/dev/null 2>&1; then \
		goneat assess --categories format --fix --fail-on low --ci-summary; \
		goneat assess --categories lint --fix --lint-shell-fix --fail-on low --ci-summary; \
	else \
		echo "[!!] goneat not found; run make bootstrap"; \
		exit 1; \
	fi
	@echo "[ok] Formatting complete"

fmt-check: ## Verify canonical formatting without modifying files
	@echo "Checking formatting..."
	@if command -v goneat >/dev/null 2>&1; then \
		goneat assess --categories format --mode check --fail-on low --ci-summary; \
	else \
		echo "[!!] goneat not found, cannot verify formatting"; \
		exit 1; \
	fi
	@echo "[ok] Formatting checks passed"

lint: lint-schemas lint-config ## Run linting checks
	@echo "Linting..."
	@if command -v goneat >/dev/null 2>&1; then \
		goneat assess --categories lint --mode check --fail-on low --ci-summary; \
	else \
		echo "[!!] goneat not found, cannot run lint assessment"; \
		exit 1; \
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

lint-config: lint-role-prompts lint-coverage-attestation lint-inference-path-taxonomy lint-config-data lint-contracts ## Validate config data files against schemas

lint-config-data: ## Validate configuration and example data
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
		for f in schemas/process-run/v0/examples/process-card.example.json; do \
			[ -f "$$f" ] || continue; \
			echo "    Validating $$f..."; \
			goneat validate data --schema-file schemas/process-run/v0/process-card.schema.json --data "$$f" || exit 1; \
		done; \
		for f in schemas/process-run/v0/examples/control-*.example.json; do \
			[ -f "$$f" ] || continue; \
			echo "    Validating $$f..."; \
			goneat validate data --schema-file schemas/process-run/v0/control-exchange.schema.json --data "$$f" || exit 1; \
		done; \
		for f in schemas/process-run/v0/examples/*.ndjson; do \
			[ -f "$$f" ] || continue; \
			echo "    Validating $$f (per line)..."; \
			tmpd=$$(mktemp -d); tmp="$$tmpd/event.json"; \
			while IFS= read -r line; do \
				[ -n "$$line" ] || continue; \
				printf '%s\n' "$$line" > "$$tmp"; \
				goneat validate data --schema-file schemas/process-run/v0/process-event.schema.json --data "$$tmp" || { rm -rf "$$tmpd"; exit 1; }; \
			done < "$$f"; \
			rm -rf "$$tmpd"; \
		done; \
		for f in schemas/review-journal/v0/examples/review-manifest.example.json; do \
			[ -f "$$f" ] || continue; \
			echo "    Validating $$f..."; \
			goneat validate data --schema-file schemas/review-journal/v0/review-manifest.schema.json --data "$$f" || exit 1; \
		done; \
		for f in schemas/review-journal/v0/examples/*.ndjson; do \
			[ -f "$$f" ] || continue; \
			echo "    Validating $$f (per line)..."; \
			tmpd=$$(mktemp -d); tmp="$$tmpd/event.json"; \
			while IFS= read -r line; do \
				[ -n "$$line" ] || continue; \
				printf '%s\n' "$$line" > "$$tmp"; \
				goneat validate data --schema-file schemas/review-journal/v0/review-event.schema.json --data "$$tmp" || { rm -rf "$$tmpd"; exit 1; }; \
			done < "$$f"; \
			rm -rf "$$tmpd"; \
		done; \
		for f in schemas/agent-wait/v0/examples/*.json schemas/agent-wait/v0/examples/outcomes/*.json; do \
			[ -f "$$f" ] || continue; \
			echo "    Validating $$f..."; \
			goneat validate data --schema-file schemas/agent-wait/v0/agent-wait-message.schema.json --data "$$f" || exit 1; \
		done; \
		for f in schemas/service-job/v0/examples/*.json; do \
			[ -f "$$f" ] || continue; \
			echo "    Validating $$f..."; \
			goneat validate data --schema-file schemas/service-job/v0/service-job-message.schema.json --data "$$f" || exit 1; \
		done; \
	else \
		echo "[!!] goneat not found, skipping config validation"; \
	fi

lint-contracts: ## Run contract controls and validate manifests
	@if command -v goneat >/dev/null 2>&1; then \
		echo "    Review-journal negative controls (rejects fail, baselines pass)..."; \
		sh scripts/test-review-journal-controls.sh || exit 1; \
		echo "    Agent-wait controls..."; \
		sh scripts/test-agent-wait-controls.sh || exit 1; \
		echo "    Service-job controls..."; \
		sh scripts/test-service-job-controls.sh || exit 1; \
		echo "    Project-work controls..."; \
		sh scripts/test-project-work-controls.sh || exit 1; \
		echo "    Forge-infra controls..."; \
		sh scripts/test-forge-infra-controls.sh || exit 1; \
		echo "    Application-control controls..."; \
		sh scripts/test-application-control-controls.sh || exit 1; \
		echo "    Validating contract manifests..."; \
		sh scripts/validate-contract-manifests.sh \
			schemas/application-control/v0/contract.json \
			schemas/data-artifact/v0/contract.json \
			schemas/coverage-attestation/v0/contract.json \
			schemas/process-run/v0/contract.json \
			schemas/review-journal/v0/contract.json \
			schemas/agent-wait/v0/contract.json \
			schemas/service-job/v0/contract.json \
			schemas/project-work/v0/contract.json \
			schemas/inference-path-taxonomy/v0/contract.json \
			schemas/forge-infra/v0/contract.json || exit 1; \
	else \
		echo "[!!] goneat not found, skipping contract validation"; \
	fi

lint-role-prompts: ## Run role-prompt negative controls
	@if command -v goneat >/dev/null 2>&1; then \
		echo "    Role-prompt negative controls (rejects fail, baseline passes)..."; \
		sh scripts/test-role-prompt-controls.sh; \
	else \
		echo "[--] goneat not found, skipping role-prompt controls"; \
	fi

lint-coverage-attestation: ## Run coverage-attestation negative controls
	@if command -v goneat >/dev/null 2>&1; then \
		echo "    Coverage-attestation negative controls (rejects fail, baseline passes)..."; \
		sh scripts/test-coverage-attestation-controls.sh; \
	else \
		echo "[--] goneat not found, skipping coverage-attestation controls"; \
	fi

lint-inference-path-taxonomy: ## Run inference-path-taxonomy controls
	@if command -v goneat >/dev/null 2>&1; then \
		echo "    Inference-path-taxonomy controls (examples pass, rejects fail)..."; \
		sh scripts/test-inference-path-taxonomy-controls.sh; \
	else \
		echo "[--] goneat not found, skipping inference-path-taxonomy controls"; \
	fi

build: check ## Build artifacts (validation is the build for standards repo)
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
		goneat assess --categories format,lint,security --mode check --fail-on critical --ci-summary; \
	else \
		echo "[!!] goneat not found; run make bootstrap"; \
		exit 1; \
	fi
	@# Always run schema/config validation (goneat assess doesn't cover these)
	@$(MAKE) lint-schemas lint-config
	@echo "[ok] Pre-commit checks passed"

prepush: ## Run pre-push checks (goneat assess --fail-on low + schema validation)
	@echo "Running pre-push checks..."
	@if command -v goneat >/dev/null 2>&1; then \
		goneat assess --categories format,lint,security --mode check --fail-on low --ci-summary; \
	else \
		echo "[!!] goneat not found; run make bootstrap"; \
		exit 1; \
	fi
	@# Always run schema/config validation (goneat assess doesn't cover these)
	@$(MAKE) lint-schemas lint-config
	@echo "[ok] Pre-push checks passed"

deps-check: ## Check dependencies for cooling-policy violations
	@echo "Checking dependency cooling policy..."
	@if command -v goneat >/dev/null 2>&1; then \
		goneat dependencies --cooling; \
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

release-guard-tag-ruleset: ## Verify version-tag ruleset policy
	@./scripts/release-guard-tag-ruleset.sh

release-guard-release-surfaces: ## Verify release notes and changelog match VERSION
	@./scripts/release-guard-release-surfaces.sh

sync-version-badge: ## Sync README badge to VERSION file
	@./scripts/sync-version-badge.sh

sync-changelog-links: ## Sync CHANGELOG compare-link footers to VERSION
	@./scripts/sync-changelog-links.sh
