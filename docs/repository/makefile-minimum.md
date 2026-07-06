# Makefile Minimum

**Canonical URL** (hosted site planned — v0.1.x): `https://crucible.3leaps.dev/repository/makefile-minimum`

Essential make targets every 3leaps repository must implement.

## Required Targets

| Target       | Purpose                                  |
| ------------ | ---------------------------------------- |
| `make help`  | List available targets with descriptions |
| `make check` | Run all quality checks (fmt, lint)       |
| `make fmt`   | Apply code formatting                    |
| `make lint`  | Run linting and style checks             |
| `make test`  | Execute test suite                       |
| `make build` | Produce distributable artifacts          |
| `make clean` | Remove build artifacts                   |

## Implementation

### help

```makefile
.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
```

### Standard Pattern

```makefile
.PHONY: lint
lint: ## Run linters
	@echo "Running linters..."
	# language-specific linting

.PHONY: test
test: ## Run tests
	@echo "Running tests..."
	# language-specific testing

.PHONY: build
build: ## Build artifacts
	@echo "Building..."
	# language-specific build

.PHONY: clean
clean: ## Clean build artifacts
	@rm -rf dist/ bin/ coverage.*

.PHONY: fmt
fmt: ## Format code
	# language-specific formatting

.PHONY: check
check: fmt lint ## Run all quality checks
	@echo "All checks passed"
```

## Clean Target Safety

**Delete** (reproducible artifacts):

- `dist/`, `bin/`, `build/`
- Generated code
- `node_modules/` (restorable)
- Build caches

**Never delete** (user content):

- `.plans/` - planning workspace
- `.env` - user config
- IDE settings

## Optional Targets

For more complex projects:

| Target               | Purpose                    |
| -------------------- | -------------------------- |
| `make bootstrap`     | Install dependencies/tools |
| `make version`       | Print current version      |
| `make release-check` | Validate release readiness |

## References

For comprehensive Makefile standards:

- [FulmenHQ Crucible - Makefile Standard](https://github.com/fulmenhq/crucible/blob/main/docs/standards/makefile-standard.md)
