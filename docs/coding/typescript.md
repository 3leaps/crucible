---
title: "TypeScript Coding Standards"
description: "TypeScript-specific coding standards including type safety, error handling, and testing patterns"
author: "devlead"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["standards", "coding", "typescript", "type-safety", "testing"]
upstream_source: "fulmenhq/crucible docs/standards/coding/typescript.md"
---

# TypeScript Coding Standards

## Overview

TypeScript-specific coding standards ensuring consistency, quality, and type safety. These standards apply to 3leaps TypeScript projects.

**Core Principle**: Write idiomatic TypeScript code that is simple, readable, and maintainable, with strict type safety and clean output.

**Foundation**: This guide builds upon [Coding Baseline](baseline.md) which establishes:

- Output hygiene (STDERR for logs, STDOUT for data)
- RFC3339 timestamps
- CLI exit codes
- Error handling patterns
- Security practices

Read the baseline first, then apply TypeScript-specific patterns below.

---

## 1. Critical Rules (Zero-Tolerance)

### 1.1 Logger Initialization - Never at Module Level

```typescript
// WRONG - May crash bundled binaries
import { getLogger } from "./logger.js";
const logger = getLogger("my-module"); // Runs during bundling

// CORRECT - Lazy initialization
import { getLogger } from "./logger.js";

let logger: ReturnType<typeof getLogger> | null = null;
function ensureLogger() {
  if (!logger) {
    logger = getLogger("my-module");
  }
  return logger;
}
```

**Why**: Module-level code runs during bundling. Logger registry may not be initialized yet.

### 1.2 No `any` Types

```typescript
// WRONG
function process(data: any): any {
  return data.value;
}

// CORRECT - Be specific
function process(data: Record<string, unknown>): string {
  return String(data.value);
}

// Better - Define types
interface InputData {
  value: string;
  count: number;
}

function process(data: InputData): string {
  return data.value;
}
```

### 1.3 Strict TypeScript Configuration

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "exactOptionalPropertyTypes": true
  }
}
```

---

## 2. Code Organization

### 2.1 Import Organization

```typescript
// WRONG - Mixed imports
import { User } from "./types";
import { readFile } from "node:fs/promises";
import { z } from "zod";

// CORRECT - Node → Third-party → Local (with blank lines)
import { readFile } from "node:fs/promises";

import { z } from "zod";

import type { User } from "./types.js";
```

### 2.2 Type Imports

```typescript
// WRONG - Value import for types only
import { User, Config } from "./types";

// CORRECT - Type imports
import type { User, Config } from "./types.js";

// CORRECT - Mixed imports
import { createUser, type User } from "./user-service.js";
```

### 2.3 Project Structure

```
project/
├── src/
│   ├── index.ts           # Entry point
│   ├── cli/               # CLI commands
│   ├── core/              # Business logic
│   └── types.ts           # Shared types
├── test/
│   └── *.test.ts
├── package.json
├── tsconfig.json
└── biome.json
```

---

## 3. Type Safety Patterns

### 3.1 Use Zod for Runtime Validation

```typescript
import { z } from "zod";

const ConfigSchema = z.object({
  host: z.string().default("localhost"),
  port: z.number().int().min(1).max(65535),
  timeout: z.number().positive().optional(),
});

type Config = z.infer<typeof ConfigSchema>;

function loadConfig(raw: unknown): Config {
  return ConfigSchema.parse(raw);
}
```

### 3.2 Discriminated Unions

```typescript
// CORRECT - Discriminated union for results
type Result<T> = { success: true; data: T } | { success: false; error: string };

function process(input: string): Result<number> {
  const parsed = parseInt(input, 10);
  if (isNaN(parsed)) {
    return { success: false, error: "Invalid number" };
  }
  return { success: true, data: parsed };
}
```

### 3.3 Exhaustive Checks

```typescript
type Status = "pending" | "active" | "completed";

function handleStatus(status: Status): string {
  switch (status) {
    case "pending":
      return "Waiting...";
    case "active":
      return "In progress";
    case "completed":
      return "Done";
    default:
      // Compile error if new status added
      const _exhaustive: never = status;
      throw new Error(`Unknown status: ${_exhaustive}`);
  }
}
```

---

## 4. Error Handling

### 4.1 Custom Error Classes

```typescript
export class ApplicationError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly cause?: Error,
  ) {
    super(message);
    this.name = "ApplicationError";
  }
}

export class ValidationError extends ApplicationError {
  constructor(message: string, cause?: Error) {
    super(message, "VALIDATION_ERROR", cause);
    this.name = "ValidationError";
  }
}
```

### 4.2 Error Handling Pattern

```typescript
import { readFile } from "node:fs/promises";

import { z } from "zod";

// Assumes ConfigSchema, ValidationError, ApplicationError defined above

async function loadConfig(path: string): Promise<Config> {
  try {
    const content = await readFile(path, "utf-8");
    return ConfigSchema.parse(JSON.parse(content));
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new ValidationError(`Invalid config: ${error.message}`, error);
    }
    throw new ApplicationError(
      `Failed to load config from ${path}`,
      "CONFIG_ERROR",
      error instanceof Error ? error : undefined,
    );
  }
}
```

---

## 5. Testing Standards

### 5.1 Vitest Patterns

```typescript
import { describe, it, expect } from "vitest";

import { process } from "../src/core.js";
import { ValidationError } from "../src/errors.js";

describe("process", () => {
  it("handles valid input", () => {
    const result = process({ value: "test" });
    expect(result.success).toBe(true);
  });

  it("rejects invalid input", () => {
    expect(() => process(null)).toThrow(ValidationError);
  });
});
```

### 5.2 Parameterized Tests

```typescript
import { describe, it, expect } from "vitest";

import { validatePort } from "../src/validation.js";

describe("validation", () => {
  it.each([
    { port: 80, valid: true },
    { port: 0, valid: false },
    { port: 65536, valid: false },
  ])("validates port $port as $valid", ({ port, valid }) => {
    if (valid) {
      expect(() => validatePort(port)).not.toThrow();
    } else {
      expect(() => validatePort(port)).toThrow();
    }
  });
});
```

---

## 6. Async Patterns

### 6.1 Proper Promise Handling

```typescript
// WRONG - Floating promise
async function process() {
  fetchData(); // Not awaited
}

// CORRECT
async function process() {
  await fetchData();
}

// CORRECT - Fire and forget with explicit void
async function process() {
  void logAnalytics(); // Intentionally not awaited
}
```

### 6.2 Concurrent Operations

```typescript
// Sequential (slow)
const a = await fetchA();
const b = await fetchB();

// Concurrent (fast)
const [a, b] = await Promise.all([fetchA(), fetchB()]);

// With error handling
const results = await Promise.allSettled([fetchA(), fetchB()]);
for (const result of results) {
  if (result.status === "rejected") {
    logger.error("Operation failed", result.reason);
  }
}
```

---

## 7. Common Anti-Patterns

### 7.1 Type Assertions Abuse

```typescript
// WRONG - Unsafe assertion
const config = rawData as Config;

// CORRECT - Runtime validation
const config = ConfigSchema.parse(rawData);
```

### 7.2 Non-null Assertions

```typescript
// WRONG - May crash at runtime
const value = map.get("key")!;

// CORRECT - Handle undefined
const value = map.get("key");
if (value === undefined) {
  throw new Error("Key not found");
}
```

### 7.3 Ignoring Promise Rejections

```typescript
// WRONG
promise.catch(() => {}); // Silently ignores errors

// CORRECT
promise.catch((error) => {
  logger.error("Operation failed", error);
});
```

---

## 8. Code Review Checklist

Before submitting TypeScript code, verify:

- [ ] No `any` types (use `unknown` if needed)
- [ ] Type imports use `import type`
- [ ] Zod schemas for runtime validation
- [ ] Custom error classes with context
- [ ] All promises awaited or explicitly voided
- [ ] Tests with vitest
- [ ] `biome check` passes
- [ ] `tsc --noEmit` passes

---

## 9. Tools

### Required

- `bun` - Runtime and package manager
- `biome` - Linting and formatting
- `vitest` - Testing
- `typescript` - Type checking

### Configuration

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": true
  }
}
```

---

## Related

- [Coding Baseline](baseline.md) - Language-agnostic standards
- [Modern TypeScript Stack](../knowledge/toolchains/typescript/modern-typescript-stack.md) - bun, biome, vitest setup

## Attribution

Adapted from [FulmenHQ Crucible](https://github.com/fulmenhq/crucible) TypeScript coding standards.
