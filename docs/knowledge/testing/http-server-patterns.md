---
title: "HTTP Server Testing Patterns"
description: "Practical patterns for HTTP server implementations and fixture development"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["testing", "http", "server", "patterns", "go", "typescript", "python"]
upstream_source: "fulmenhq/crucible docs/guides/testing/http-server-patterns.md"
---

# HTTP Server Testing Patterns

Practical patterns for implementing HTTP servers and test fixtures. These patterns were derived from real fixture development and apply across languages.

## Go HTTP Handler Anti-Patterns

These patterns were derived from 25+ lint fixes during fixture server development.

### Error Handling in Response Writers

**Problem**: `json.Encoder.Encode()` returns an error that linters catch when ignored.

**Anti-pattern**:

```go
w.Header().Set("Content-Type", "application/json")
w.WriteHeader(http.StatusOK)
json.NewEncoder(w).Encode(response)  // Error return value not checked
```

**Correct pattern** (explicit ignore after headers sent):

```go
w.Header().Set("Content-Type", "application/json")
w.WriteHeader(http.StatusOK)
_ = json.NewEncoder(w).Encode(response)  // Explicit ignore signals intent
```

**Why explicit ignore?** After `WriteHeader()` is called, HTTP status is committed. If `Encode()` fails (client disconnects), we can't change the response. The blank identifier signals intentional ignore to linters and maintainers.

**Alternative** (pre-header error handling):

```go
data, err := json.Marshal(response)
if err != nil {
    http.Error(w, "internal error", http.StatusInternalServerError)
    return
}
w.Header().Set("Content-Type", "application/json")
w.WriteHeader(http.StatusOK)
_, _ = w.Write(data)
```

### Response Body Close in Tests

**Problem**: `resp.Body.Close()` returns an error that linters catch.

**Anti-pattern**:

```go
resp := w.Result()
defer resp.Body.Close()  // Error return value not checked
```

**Correct pattern** (test helper):

```go
// closeBody is a test helper that closes a response body and fails on error
func closeBody(t *testing.T, body io.Closer) {
    t.Helper()
    if err := body.Close(); err != nil {
        t.Errorf("failed to close response body: %v", err)
    }
}

// Usage
func TestMyHandler(t *testing.T) {
    resp := w.Result()
    defer closeBody(t, resp.Body)
    // ... assertions ...
}
```

### Context Cancellation in Delay Handlers

**Problem**: Handlers that sleep must respect context cancellation for graceful shutdown.

**Anti-pattern**:

```go
func DelayHandler(w http.ResponseWriter, r *http.Request) {
    time.Sleep(time.Duration(ms) * time.Millisecond)  // Ignores cancellation
    // ... respond ...
}
```

**Correct pattern**:

```go
func DelayHandler(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    select {
    case <-time.After(time.Duration(ms) * time.Millisecond):
        // Timer completed, send response
    case <-ctx.Done():
        // Client disconnected or server shutting down
        return  // Don't send response to dead connection
    }
    // ... respond ...
}
```

**Helper function**:

```go
// sleepWithContext sleeps for duration, returns true if completed, false if cancelled.
func sleepWithContext(ctx context.Context, d time.Duration) bool {
    timer := time.NewTimer(d)
    defer timer.Stop()  // Critical: prevents timer goroutine leak

    select {
    case <-timer.C:
        return true
    case <-ctx.Done():
        return false
    }
}
```

**Note**: Prefer `time.NewTimer` + `defer timer.Stop()` over `time.After` in long-lived servers. `time.After` creates a timer that can't be stopped if the context cancels first, leading to goroutine accumulation under load.

### Body Limits and Safe Reads

**Problem**: Unbounded `io.ReadAll` on request body enables memory DoS.

**Anti-pattern**:

```go
body, err := io.ReadAll(r.Body)  // Unbounded - attacker sends 2GB
```

**Correct pattern** (bounded reads):

```go
const maxBodySize = 1 << 20  // 1MB

limited := io.LimitReader(r.Body, maxBodySize+1)
body, err := io.ReadAll(limited)
if err != nil {
    http.Error(w, "read error", http.StatusInternalServerError)
    return
}
if len(body) > maxBodySize {
    http.Error(w, "request too large", http.StatusRequestEntityTooLarge)
    return
}
```

## Correlation ID Propagation

Correlation IDs enable request tracing across logs, responses, and downstream services.

### Requirements

1. **Accept** `X-Correlation-ID` or `X-Request-ID` from client
2. **Generate** if missing (recommend UUIDv7)
3. **Return** `X-Correlation-ID` in response headers
4. **Log** `correlation_id` field in all structured request logs

### Implementation Pattern (Go)

```go
type contextKey struct{ name string }
var correlationKey = contextKey{"correlation_id"}

func correlationMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        correlationID := r.Header.Get("X-Correlation-ID")
        if correlationID == "" {
            correlationID = r.Header.Get("X-Request-ID")
        }
        if correlationID == "" {
            correlationID = generateUUIDv7()
        }

        w.Header().Set("X-Correlation-ID", correlationID)
        ctx := context.WithValue(r.Context(), correlationKey, correlationID)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}
```

### Common Failure Mode

Enabling correlation in logging middleware config does NOT automatically propagate via HTTP headers. Both are required:

- Logging middleware: Include `correlation_id` in structured logs
- HTTP middleware: Accept/generate/return correlation ID headers

## Streaming Correctness

For endpoints that stream data:

### Byte-Count Invariants

- Endpoints defined as "streams {n} bytes" MUST return exactly {n} bytes
- Do NOT append debug footers, newlines, or JSON summaries
- Use HTTP trailers or separate metadata endpoints for end-of-stream stats

### Flush Behavior

```go
func StreamHandler(w http.ResponseWriter, r *http.Request) {
    flusher, ok := w.(http.Flusher)
    if !ok {
        http.Error(w, "streaming not supported", http.StatusInternalServerError)
        return
    }

    for i := 0; i < n; i++ {
        w.Write([]byte{byte(i % 256)})
        flusher.Flush()
    }
}
```

### Client Disconnect Handling

Treat write errors as disconnect - return without attempting error responses:

```go
_, err := w.Write(chunk)
if err != nil {
    return  // Client disconnected, don't try to write error JSON
}
```

## Determinism for Testability

### Range Endpoints

For `/range/{n}` endpoints that support HTTP Range requests:

- Full content and partial ranges MUST align
- Use deterministic pattern: `byte(i) = i % 256`
- Document this explicitly for consumers

**Why?** Clients need to compare full vs partial responses and verify offsets exactly.

### When Randomness is OK

- `/bytes/{n}` may return random data (bulk transfer testing)
- `/range/{n}` should NOT be random (correctness testing)

## Quick Reference: Endpoints and Patterns

| Testing Scenario | Endpoint Example                | Pattern Notes     |
| ---------------- | ------------------------------- | ----------------- |
| Connect timeout  | `/timeout`                      | Never responds    |
| Header timeout   | `/delay/{ms}/headers`           | Delayed headers   |
| Body timeout     | `/delay/{ms}/body`              | Delayed body      |
| Redirect chain   | `/redirect/{n}`                 | N redirects       |
| Redirect loop    | `/redirect/loop`                | Infinite loop     |
| Status codes     | `/status/{code}`                | Any HTTP status   |
| Auth failure     | `/api/protected`                | 401 response      |
| Forbidden        | `/api/admin/config`             | 403 response      |
| Streaming        | `/stream/{n}`                   | Chunked encoding  |
| Slow drip        | `/drip?duration={ms}&bytes={n}` | Timed byte stream |

## Attribution

Adapted from [FulmenHQ Crucible](https://github.com/fulmenhq/crucible) HTTP server patterns, originally developed during fixture server implementation.
