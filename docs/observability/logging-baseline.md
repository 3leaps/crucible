# Logging Baseline

**Canonical URL** (hosted site planned — v0.1.x): `https://crucible.3leaps.dev/observability/logging-baseline`

Fundamental logging standards for 3leaps tools.

## Core Rules

1. **Logs go to STDERR** - Never pollute STDOUT
2. **Use RFC3339 timestamps** - Always with timezone
3. **Include context** - What operation, what resource
4. **Structured when possible** - JSON for machine parsing

## Log Levels

| Level | Numeric | Usage                                    |
| ----- | ------- | ---------------------------------------- |
| DEBUG | 10      | Detailed diagnostics for troubleshooting |
| INFO  | 20      | General operational messages             |
| WARN  | 30      | Warning conditions, non-fatal issues     |
| ERROR | 40      | Error conditions, operation failures     |
| FATAL | 50      | Unrecoverable, application exit          |

**Guideline**:

- DEBUG: Developer troubleshooting
- INFO: Operator monitoring
- WARN: Potential problems
- ERROR: Failures needing attention
- FATAL: Immediate action required

## Output Format

### Human-Readable (Development)

```
2025-10-08T15:30:00Z INFO  Processing started file=config.yaml
2025-10-08T15:30:01Z ERROR Failed to parse config error="invalid syntax"
```

### Structured JSON (Production)

```json
{"timestamp":"2025-10-08T15:30:00Z","level":"INFO","message":"Processing started","file":"config.yaml"}
{"timestamp":"2025-10-08T15:30:01Z","level":"ERROR","message":"Failed to parse config","error":"invalid syntax"}
```

## Context Fields

Always include relevant context:

| Field        | When             |
| ------------ | ---------------- |
| `file`       | File operations  |
| `duration`   | Timed operations |
| `error`      | Error conditions |
| `count`      | Batch operations |
| `request_id` | Request tracing  |

```go
logger.Info("Processing completed",
    "file", filename,
    "duration", elapsed,
    "count", processed,
)
```

## Stream Discipline

```
┌─────────────┐     ┌─────────────┐
│   Logs      │────▶│   STDERR    │────▶ Terminal / Log aggregator
└─────────────┘     └─────────────┘

┌─────────────┐     ┌─────────────┐
│   Data      │────▶│   STDOUT    │────▶ Pipes / Files / Automation
└─────────────┘     └─────────────┘
```

**Test your discipline**:

```bash
# Should show only data
mytool process input.json 2>/dev/null

# Should show only logs
mytool process input.json >/dev/null
```

## Environment Control

Support log level via environment:

```bash
LOG_LEVEL=debug mytool process    # Verbose
LOG_LEVEL=error mytool process    # Quiet
```

Or via flag:

```bash
mytool --log-level=debug process
mytool -q process  # Quiet mode
```

## References

- [Stream Output Policy](../sop/stream-output.md) - Mandatory stdout/stderr discipline
- [FulmenHQ Crucible - Logging Standard](https://github.com/fulmenhq/crucible/blob/main/docs/standards/observability/logging.md)
