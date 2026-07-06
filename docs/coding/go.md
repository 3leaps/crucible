---
title: "Go Coding Standards"
description: "Go-specific coding standards including output hygiene, error handling, concurrency patterns, and testing"
author: "devlead"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["standards", "coding", "go", "concurrency", "testing"]
upstream_source: "fulmenhq/crucible docs/standards/coding/go.md"
---

# Go Coding Standards

## Overview

Go-specific coding standards ensuring consistency, quality, and reliability. These standards apply to 3leaps Go projects.

**Core Principle**: Write idiomatic Go code that is simple, readable, and maintainable, with strict output hygiene for structured data integrity.

**Foundation**: This guide builds upon [Coding Baseline](baseline.md) which establishes:

- Output hygiene (STDERR for logs, STDOUT for data)
- RFC3339 timestamps
- CLI exit codes
- Error handling patterns
- Security practices

Read the baseline first, then apply Go-specific patterns below.

---

## 1. Critical Rules (Zero-Tolerance)

### 1.1 Output Hygiene

**Rule**: Output streams must remain clean for structured output (JSON, YAML) consumed by tools and automation.

**DO**: Use logging packages for all diagnostic output

```go
import "log/slog"

// Correct logging (to stderr)
slog.Debug("processing files", "count", fileCount)
slog.Info("operation completed", "duration_ms", elapsed.Milliseconds(), "issues", len(issues))
slog.Error("failed to process", "error", err)
slog.Warn("config not found, using defaults")
```

**DO NOT**: Pollute output streams with direct writes

```go
// CRITICAL ERROR: Breaks structured output
fmt.Printf("DEBUG: Processing %s\n", filename)
fmt.Println("Processing files...")
println("Debug info")

// These break structured output consumed by CI/CD tools
os.Stdout.WriteString("Status message\n")

// Prefer slog over log.Printf for diagnostics
```

**Enforcement**: Any direct output writes in library code will fail code review.

### 1.2 Error Handling

**DO**: Always handle errors explicitly

```go
// Proper error handling
result, err := process(ctx, target, config)
if err != nil {
    return fmt.Errorf("processing failed for %s: %w", category, err)
}
```

**DO NOT**: Ignore errors or use blank identifiers unnecessarily

```go
// Never ignore errors
result, _ := process(ctx, target, config)

// Don't ignore critical errors
_, _ = os.ReadFile(configFile)
```

---

## 2. Code Organization

### 2.1 Project Structure

```
project/
├── cmd/                    # CLI entry points
│   └── tool-name/
│       └── main.go
├── internal/
│   ├── core/              # Core business logic
│   ├── config/            # Configuration
│   └── utils/             # Internal utilities
├── pkg/                   # Public packages (if any)
├── testdata/              # Test fixtures
└── Makefile
```

### 2.2 Naming Conventions

- **Types**: PascalCase (`Processor`, `CategoryResult`)
- **Functions**: camelCase for unexported, PascalCase for exported
- **Constants**: PascalCase for exported, camelCase for unexported
- **Files**: snake_case (`repo_status_processor.go`)

---

## 3. Logging Standards

### 3.1 Use slog (Go 1.21+)

```go
import "log/slog"

// Setup (typically in main or init)
logger := slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{
    Level: slog.LevelInfo,
}))
slog.SetDefault(logger)

// Usage
slog.Debug("processing", "file", filename)
slog.Info("completed", "duration", elapsed, "issues", count)
slog.Warn("config missing", "path", configPath)
slog.Error("operation failed", "error", err)
```

### 3.2 Structured Logging Context

Include relevant context in log messages:

```go
// Good: Contextual information
slog.Info("operation completed",
    "category", "status",
    "duration_ms", elapsed.Milliseconds(),
    "issues_found", len(issues),
)

// Bad: Missing context
slog.Info("operation completed")
```

---

## 4. Concurrency

### 4.1 Goroutine Management

Use proper synchronization:

```go
func runConcurrentOperations(items []Item) []Result {
    var wg sync.WaitGroup
    results := make(chan Result, len(items))

    for _, item := range items {
        wg.Add(1)
        go func(it Item) {
            defer wg.Done()
            results <- process(it)
        }(item)
    }

    wg.Wait()
    close(results)

    var out []Result
    for r := range results {
        out = append(out, r)
    }
    return out
}
```

### 4.2 Context Handling

Always respect context cancellation:

```go
func Process(ctx context.Context, target string) (*Result, error) {
    // Check context early
    select {
    case <-ctx.Done():
        return nil, ctx.Err()
    default:
    }

    // Long-running operations should check context periodically
    for _, file := range files {
        select {
        case <-ctx.Done():
            return nil, ctx.Err()
        default:
            // Process file
        }
    }

    return result, nil
}
```

---

## 5. Testing Standards

### 5.1 Table-Driven Tests

```go
func TestProcessor_Process(t *testing.T) {
    tests := []struct {
        name            string
        input           string
        expectedIssues  int
        expectedSuccess bool
    }{
        {"valid_input", "testdata/clean", 0, true},
        {"invalid_input", "testdata/invalid", 1, false},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            processor := NewProcessor()
            result, err := processor.Process(context.Background(), tt.input)

            require.NoError(t, err)
            assert.Equal(t, tt.expectedSuccess, result.Success)
            assert.Len(t, result.Issues, tt.expectedIssues)
        })
    }
}
```

### 5.2 Test Helpers

```go
func setupTestData(t *testing.T, state string) string {
    t.Helper()
    testDir := filepath.Join("testdata", "fixtures", state)
    return testDir
}

func closeBody(t *testing.T, body io.Closer) {
    t.Helper()
    if err := body.Close(); err != nil {
        t.Errorf("failed to close body: %v", err)
    }
}
```

---

## 6. Security and Validation

### 6.1 Input Validation

Validate all inputs, especially file paths:

```go
func validateTarget(target string, allowedBase string) error {
    absTarget, err := filepath.Abs(target)
    if err != nil {
        return fmt.Errorf("invalid target path: %w", err)
    }

    // Check path stays within allowed directory
    rel, err := filepath.Rel(allowedBase, absTarget)
    if err != nil || strings.HasPrefix(rel, "..") {
        return errors.New("path outside allowed directory")
    }

    return nil
}
```

### 6.2 File Operations

Use restrictive permissions:

```go
func writeConfigFile(filename string, data []byte) error {
    return os.WriteFile(filename, data, 0640)
}
```

---

## 7. Common Anti-Patterns

### 7.1 Output Contamination

```go
// NEVER: Contaminates structured output
fmt.Printf("DEBUG: Processing %s\n", filename)

// ALWAYS: Use structured logging
slog.Debug("processing file", "filename", filename)
```

### 7.2 Hardcoded Values

```go
// Bad: Hardcoded paths
configPath := "/home/user/.config/app.yaml"

// Good: Dynamic paths
configPath := filepath.Join(homeDir, ".config", "app.yaml")
```

### 7.3 Ignored Errors

```go
// Bad: Ignored error
file, _ := os.Open(filename)

// Good: Proper error handling
file, err := os.Open(filename)
if err != nil {
    return fmt.Errorf("failed to open %s: %w", filename, err)
}
defer file.Close()
```

---

## 8. Code Review Checklist

Before submitting Go code, verify:

- [ ] No direct output writes (`fmt.Print*`) in library code
- [ ] All errors are handled and wrapped with context
- [ ] Structured logging used for diagnostics
- [ ] Tests cover happy path and error conditions
- [ ] Context cancellation is respected
- [ ] File operations use proper permissions
- [ ] No hardcoded paths or values
- [ ] `go fmt` and `go vet` pass
- [ ] `golangci-lint` passes

---

## 9. Tools

### Required

- `go fmt` - Code formatting
- `go vet` - Static analysis
- `golangci-lint` - Comprehensive linting

### CI Integration

```bash
# Check for forbidden patterns
if grep -r "fmt\.Print" internal/; then
    echo "ERROR: fmt.Print* found in library code"
    exit 1
fi
```

---

## Related

- [Coding Baseline](baseline.md) - Language-agnostic standards
- [HTTP Server Patterns](../knowledge/testing/http-server-patterns.md) - Go HTTP anti-patterns
- [Cobra CLI Patterns](../knowledge/toolchains/go/cobra-cli-patterns.md) - CLI with Cobra

## Attribution

Adapted from [FulmenHQ Crucible](https://github.com/fulmenhq/crucible) Go coding standards.
