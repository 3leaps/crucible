---
title: "Modern TypeScript Stack (2026)"
description: "The modern TypeScript development stack: bun, biome, vitest"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["typescript", "bun", "biome", "vitest", "toolchains"]
upstream_source: "fulmenhq/crucible docs/standards/repository-structure/typescript/"
---

# Modern TypeScript Stack (2026)

The TypeScript ecosystem has matured around faster, more integrated tools. This document covers the recommended stack for new TypeScript projects.

## The Stack

| Tool   | Purpose              | Replaces                      |
| ------ | -------------------- | ----------------------------- |
| bun    | Runtime + PM + Build | node, npm, pnpm, esbuild, tsx |
| biome  | Linting + formatting | eslint, prettier              |
| vitest | Testing              | jest                          |

## bun: All-in-One Runtime

### Why bun

- **Speed**: 4x faster than Node for many workloads
- **Unified**: Runtime, package manager, bundler
- **TypeScript**: Native TypeScript/JSX support (no transpilation step)
- **npm compatible**: Works with existing npm packages

### Installation

```bash
curl -fsSL https://bun.sh/install | bash
```

### Essential Commands

```bash
# Create new project
bun init

# Install dependencies
bun install

# Add dependencies
bun add zod fastify
bun add -d vitest @vitest/coverage-v8 @types/node

# Run TypeScript directly
bun run src/index.ts

# Run scripts
bun run build
bun run test

# Execute a package binary
bunx tsc --noEmit
```

### Project Structure

```
project/
├── src/
│   ├── index.ts           # Entry point
│   ├── cli/               # CLI commands
│   └── core/              # Business logic
├── test/
│   └── *.test.ts
├── package.json
├── tsconfig.json
├── biome.json
└── bunfig.toml            # Optional bun config
```

### package.json Example

```json
{
  "name": "my-package",
  "version": "0.1.0",
  "type": "module",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "bun build src/index.ts --outdir dist",
    "dev": "bun --watch src/index.ts",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "biome check .",
    "format": "biome format --write ."
  },
  "devDependencies": {
    "@biomejs/biome": "^1.9.0",
    "@types/node": "^22.0.0",
    "@vitest/coverage-v8": "^2.1.0",
    "typescript": "^5.7.0",
    "vitest": "^2.1.0"
  }
}
```

## biome: Linting and Formatting

### Why biome

- **Speed**: 35x faster than Prettier + ESLint
- **Unified**: Single tool for both formatting and linting
- **Zero config**: Sensible defaults out of the box
- **Rust-based**: Same performance philosophy as uv/ruff

### Configuration (biome.json)

```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.0/schema.json",
  "organizeImports": {
    "enabled": true
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 100
  },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true,
      "correctness": {
        "noUnusedVariables": "error",
        "noUnusedImports": "error"
      }
    }
  },
  "javascript": {
    "formatter": {
      "quoteStyle": "double",
      "semicolons": "always"
    }
  }
}
```

### Essential Commands

```bash
# Check for issues
bunx biome check .

# Fix auto-fixable issues
bunx biome check --write .

# Format only
bunx biome format --write .

# Lint only
bunx biome lint .
```

## vitest: Testing

### Why vitest

- **Speed**: Fast, parallel test execution
- **ESM native**: First-class ES modules support
- **Jest compatible**: Familiar API
- **Watch mode**: Fast feedback loop

### Configuration (vitest.config.ts)

```typescript
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    include: ["test/**/*.test.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
    },
  },
});
```

### Example Test

```typescript
import { describe, it, expect } from "vitest";
import { processData } from "../src/core/processor";

describe("processData", () => {
  it("handles valid input", () => {
    const result = processData({ key: "value" });
    expect(result.success).toBe(true);
  });

  it("throws on empty input", () => {
    expect(() => processData({})).toThrow("empty input");
  });
});
```

### Running Tests

```bash
# Run all tests
bunx vitest run

# Watch mode
bunx vitest

# With coverage
bunx vitest run --coverage
```

## TypeScript Configuration

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": true,
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### Key Settings

- `"module": "ESNext"` - Modern ES modules
- `"moduleResolution": "bundler"` - Works with bun/bundlers
- `"strict": true` - Enable all strict checks

## Node.js Version Policy

### Current Guidance

- **Minimum**: Node 20 LTS (until April 2026)
- **Recommended**: Node 22 LTS (current)
- **Engines**: Specify in package.json

```json
{
  "engines": {
    "node": ">=20.0.0"
  }
}
```

### LTS Schedule

| Version | Status  | End of Life |
| ------- | ------- | ----------- |
| 18      | EOL     | April 2025  |
| 20      | LTS     | April 2026  |
| 22      | LTS     | April 2027  |
| 24      | Current | TBD         |

## Common Makefile

```makefile
.PHONY: install build test lint format clean

install:
	bun install

build:
	bun run build

test:
	bun run test

lint:
	bunx biome check .

format:
	bunx biome format --write .

check:
	bunx biome check .
	bunx tsc --noEmit
	bun run test

clean:
	rm -rf dist node_modules
```

## GitHub Actions

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: oven-sh/setup-bun@v2
        with:
          bun-version: latest

      - name: Install dependencies
        run: bun install

      - name: Type check
        run: bunx tsc --noEmit

      - name: Lint
        run: bunx biome check .

      - name: Test
        run: bun run test
```

## Migration from Legacy Tools

### From npm/yarn to bun

```bash
# Remove lock files
rm package-lock.json yarn.lock

# Install with bun
bun install

# Verify
bun run test
```

### From ESLint/Prettier to biome

```bash
# Remove old tools
bun remove eslint prettier @typescript-eslint/parser

# Add biome
bun add -d @biomejs/biome

# Create config
bunx biome init

# Migrate rules (many are auto-converted)
# Manual review needed for custom ESLint rules
```

## Attribution

Adapted from [FulmenHQ Crucible](https://github.com/fulmenhq/crucible) TypeScript patterns.
