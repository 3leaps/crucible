# Stream Output Policy

**Status**: Mandatory for all 3leaps CLI tools

Stdout purity is essential for Unix-style tool chaining, MCP stdio transport, and programmatic consumption. This policy defines what goes where.

## The Rule

| Stream   | Purpose            | Content                                          |
| -------- | ------------------ | ------------------------------------------------ |
| `stdout` | Data channel       | Schema-validated output OR explicit UX output    |
| `stderr` | Diagnostic channel | Everything else: logs, progress, warnings, debug |

**No exceptions for "just one little message."** A single debug line to stdout breaks `tool | jq`.

## stdout: Data Channel

stdout is for data that downstream tools or users will consume programmatically.

**Allowed**:

- JSON output conforming to a defined schema (JSON Schema 2020-12 preferred)
- Structured formats with documented schema (CSV, NDJSON, YAML)
- Explicit human UX when tool design requires it (e.g., `--human` flag, interactive prompts)
- Single-value output for simple queries (e.g., `tool version` → `1.2.3`)

**Never**:

- Log messages (even "Starting..." or "Done")
- Progress indicators or spinners
- Warnings or deprecation notices
- Debug or trace output
- Error messages (use stderr + exit code)

### Schema Discipline

When stdout is JSON:

```go
// Good: Output conforms to documented schema
type Output struct {
    Version string   `json:"version"`
    Items   []Item   `json:"items"`
}

// Write to stdout only
json.NewEncoder(os.Stdout).Encode(output)
```

Reference the schema in tool documentation or embed schema URL in output:

```json
{
  "$schema": "https://schemas.3leaps.dev/tool/v0/output.schema.json",
  "version": "1.2.3",
  "items": []
}
```

## stderr: Diagnostic Channel

stderr is for humans and log aggregators, not pipelines.

**Required**:

- All log output (DEBUG, INFO, WARN, ERROR, FATAL)
- Progress indicators and status updates
- Warnings and deprecation notices
- Error details (in addition to exit codes)

**Including structured logs**:

```go
// Structured JSON logging goes to stderr
logger := slog.New(slog.NewJSONHandler(os.Stderr, nil))
logger.Info("processing started", "file", filename)
```

This is the confusing part: **JSON-formatted logs go to stderr**, not stdout. Both are JSON. Different purposes. Different streams.

## Why This Matters

### Tool Chaining

```bash
# Works: stdout is pure data
tool list --format=json | jq '.items[] | .name' | sort

# Broken: log message corrupts JSON
tool list --format=json | jq '.items[] | .name'
# parse error: Invalid literal at line 1, column 1
# (because stdout started with "Loading config...")
```

### MCP Stdio Transport

MCP servers using stdio transport require stdout purity. Any non-protocol output breaks the JSON-RPC stream.

### Programmatic Consumption

```python
# Works: predictable stdout
result = json.loads(subprocess.check_output(["tool", "query"]))

# Broken: mixed output
result = json.loads(subprocess.check_output(["tool", "query"]))
# JSONDecodeError: Expecting value (got "Connecting to server...")
```

## Implementation Requirements

### 1. Logger Configuration

Verify your logging framework writes to stderr:

```go
// Go: slog
logger := slog.New(slog.NewJSONHandler(os.Stderr, nil))

// Go: zerolog
log.Logger = zerolog.New(os.Stderr).With().Timestamp().Logger()

// Go: zap
cfg := zap.NewProductionConfig()
cfg.OutputPaths = []string{"stderr"}
```

```python
# Python: standard logging
import sys
logging.basicConfig(stream=sys.stderr)

# Python: structlog
structlog.configure(
    logger_factory=structlog.WriteLoggerFactory(file=sys.stderr)
)
```

```typescript
// TypeScript: pino
const logger = pino({
  transport: { target: "pino/file", options: { destination: 2 } },
});
// Note: fd 2 = stderr
```

### 2. Progress and Status

Use stderr for progress indicators:

```go
fmt.Fprintf(os.Stderr, "Processing %d/%d...\r", current, total)
```

Or use a library that respects stderr:

```go
bar := progressbar.NewOptions(total,
    progressbar.OptionSetWriter(os.Stderr),
)
```

### 3. Error Output

Errors go to stderr with appropriate exit code:

```go
if err != nil {
    fmt.Fprintf(os.Stderr, "error: %v\n", err)
    os.Exit(1)
}
```

## Testing Requirements

Every repository with CLI tools MUST include stdout purity tests.

### Basic Stream Separation Test

```bash
#!/bin/bash
# test-stdout-purity.sh

# Capture streams separately
stdout_output=$(tool command 2>/dev/null)
stderr_output=$(tool command 2>&1 >/dev/null)

# stdout should be valid JSON (if JSON output expected)
echo "$stdout_output" | jq . > /dev/null || {
    echo "FAIL: stdout is not valid JSON"
    exit 1
}

# stdout should not contain log patterns
if echo "$stdout_output" | grep -qiE '(INFO|WARN|ERROR|DEBUG|loading|starting|processing)'; then
    echo "FAIL: stdout contains log-like content"
    exit 1
fi

echo "PASS: stdout purity verified"
```

### Go Test Example

```go
func TestStdoutPurity(t *testing.T) {
    cmd := exec.Command("./tool", "list", "--format=json")

    var stdout, stderr bytes.Buffer
    cmd.Stdout = &stdout
    cmd.Stderr = &stderr

    err := cmd.Run()
    require.NoError(t, err)

    // stdout must be valid JSON
    var result interface{}
    err = json.Unmarshal(stdout.Bytes(), &result)
    require.NoError(t, err, "stdout should be valid JSON")

    // stdout must not contain log patterns
    stdoutStr := stdout.String()
    assert.NotContains(t, strings.ToLower(stdoutStr), "info")
    assert.NotContains(t, strings.ToLower(stdoutStr), "error")
    assert.NotContains(t, strings.ToLower(stdoutStr), "loading")
}
```

### CI Integration

Add to your CI pipeline:

```yaml
- name: Verify stdout purity
  run: |
    ./tool list --format=json 2>/dev/null | jq . > /dev/null
    echo "stdout purity: OK"
```

## The Strict Rule

Based on implementation experience (sfetch, shellsentry):

| Content Type | Stream   | Always                                    |
| ------------ | -------- | ----------------------------------------- |
| Human text   | `stderr` | Status, errors, help, tables, diagnostics |
| Machine data | `stdout` | JSON, CSV, NDJSON, binary                 |

**Stream destination is constant.** Don't vary it based on flags or TTY. This is simpler to reason about, simpler to test, and eliminates ambiguity.

### --json Flag

Controls _whether_ to emit machine output, not _where_:

```bash
tool status           # Human-friendly to stderr, nothing to stdout
tool status --json    # Human-friendly to stderr, JSON to stdout
```

### --quiet Flag

Suppress stderr diagnostics:

```bash
tool process --quiet  # No progress/info to stderr, data still to stdout
```

### TTY Detection

Use TTY detection for _formatting_, not stream routing:

```go
if isatty.IsTerminal(os.Stderr.Fd()) {
    // Interactive: colors, tables, progress bars
    printColoredTable(os.Stderr, results)
} else {
    // Piped/redirected: plain text, no ANSI codes
    printPlainTable(os.Stderr, results)
}

// stdout is always machine data (when emitting)
json.NewEncoder(os.Stdout).Encode(results)
```

## Verification Checklist

For each CLI tool in your repository:

- [ ] Logger configured to write to stderr
- [ ] Progress indicators write to stderr
- [ ] JSON output conforms to documented schema
- [ ] stdout purity test exists and passes
- [ ] `tool cmd 2>/dev/null | jq .` works for JSON commands
- [ ] No "info", "loading", "processing" messages in stdout

## Related

- [Logging Baseline](../observability/logging-baseline.md) - Log levels and format
- [CI/CD Baseline](../operations/ci-baseline.md) - Testing in CI
