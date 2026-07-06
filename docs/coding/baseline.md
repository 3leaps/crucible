# Coding Baseline

**Canonical URL** (hosted site planned — v0.1.x): `https://crucible.3leaps.dev/coding/baseline`

Core coding conventions for all 3leaps tools. Language-agnostic principles that ensure consistency and interoperability.

## Output Hygiene

**Rule**: STDERR for logs, STDOUT for data. Zero tolerance.

| Stream | Purpose                | Examples                                            |
| ------ | ---------------------- | --------------------------------------------------- |
| STDOUT | Structured data output | JSON results, YAML configs, machine-readable output |
| STDERR | Diagnostic output      | Logs, debug info, progress, errors, warnings        |

**Why**: Pipelines, CI/CD, and automation parse STDOUT. Contamination breaks downstream tools.

```go
// Go
logger.Info("Processing completed")  // -> stderr
fmt.Println(jsonOutput)              // -> stdout (data only)

// WRONG - breaks pipelines
fmt.Printf("DEBUG: processing %s\n", file)
```

```python
# Python
logger.info("Processing completed")  # -> stderr
print(json.dumps(result))            # -> stdout (data only)

# WRONG - breaks pipelines
print(f"DEBUG: processing {file}")
```

```typescript
// TypeScript
logger.info("Processing completed"); // -> stderr
console.log(JSON.stringify(result)); // -> stdout (data only)

// WRONG - breaks pipelines
console.log(`DEBUG: processing ${file}`);
```

## Exit Codes

Use conventional Unix exit codes:

| Code | Meaning             | Usage                            |
| ---- | ------------------- | -------------------------------- |
| 0    | Success             | Operation completed successfully |
| 1    | General error       | Catch-all for unspecified errors |
| 2    | Misuse              | Invalid command-line arguments   |
| 3    | Configuration error | Invalid or missing config        |
| 4    | Input error         | Invalid input data or file       |
| 5    | Output error        | Cannot write output              |
| 126  | Cannot execute      | Permission or binary issues      |
| 127  | Not found           | Missing dependency               |
| 130  | SIGINT              | User interrupted (Ctrl+C)        |

**Rule**: Exit 0 ONLY on complete success. Log error details to STDERR before exiting.

## Timestamps

**Rule**: RFC3339 format with timezone. Always.

```
2025-10-08T15:30:00Z           # UTC
2025-10-08T15:30:00-04:00      # With offset
2025-10-08T15:30:00.123Z       # With milliseconds
```

**Do NOT use**:

- Unix timestamps (ambiguous timezone)
- Locale formats (`MM/DD/YYYY`, `DD/MM/YYYY`)
- Formats without timezone (`2025-10-08 15:30:00`)

## Error Handling

**Rule**: Errors must include context about what failed and why.

```go
// Go - wrap with context
return fmt.Errorf("failed to load config from %s: %w", path, err)
```

```python
# Python - chain exceptions
raise ConfigError(f"Failed to load config from {path}") from err
```

```typescript
// TypeScript - include context
throw new ConfigError(`Failed to load config from ${path}: ${err.message}`);
```

**Error messages should**:

- Describe the operation that failed
- Include relevant context (file path, resource ID)
- Preserve the original error
- Be actionable (user can fix it)

## Input Validation

**Rule**: Validate all external input. Trust nothing.

**Always validate**:

- CLI arguments
- File paths (prevent traversal)
- Environment variables
- API inputs
- File contents

```go
// Path traversal prevention - verify resolved path stays within allowed directory
// (ensure allowedBaseDir is an absolute path)
absPath, err := filepath.Abs(userPath)
if err != nil {
	return err
}
rel, err := filepath.Rel(allowedBaseDir, absPath)
if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
	return errors.New("path outside allowed directory")
}
```

## Secrets

**Rule**: Never hardcode secrets. Never log secrets.

**Do**:

- Use environment variables
- Use `.env` files (gitignored)
- Redact in logs

**Do NOT**:

- Hardcode API keys, passwords, tokens
- Commit `.env` files
- Include secrets in error messages

## References

Language-specific standards:

- [Go Coding Standards](go.md)
- [Python Coding Standards](python.md)
- [TypeScript Coding Standards](typescript.md)
- [Rust Coding Standards](rust.md)

For comprehensive specifications and extended patterns:

- [FulmenHQ Crucible - Cross-Language Coding Standards](https://github.com/fulmenhq/crucible/blob/main/docs/standards/coding/README.md)
- [FulmenHQ Crucible - Error Handling Patterns](https://github.com/fulmenhq/crucible/blob/main/docs/standards/error-handling-patterns.md)
