---
title: "HTTP Client Testing Patterns"
description: "Patterns for testing HTTP clients, middleware, and proxies"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["testing", "http", "client", "patterns", "go", "typescript", "python", "rust"]
upstream_source: "fulmenhq/crucible docs/guides/testing/http-client-patterns.md"
---

# HTTP Client Testing Patterns

Patterns for testing HTTP clients, middleware, and proxies using test fixtures. These patterns help implement robust test suites that cover edge cases most developers miss.

## Timeout Testing

### The Three Timeout Tiers

Most HTTP clients conflate different timeout types. Testing each tier separately reveals edge cases:

| Tier                | What It Measures          | Failure Mode                      |
| ------------------- | ------------------------- | --------------------------------- |
| **Connect timeout** | TCP handshake completion  | Server unreachable, firewall drop |
| **Header timeout**  | Time to first byte (TTFB) | Slow backend processing           |
| **Body timeout**    | Full response completion  | Large payloads, slow streaming    |

### Testing with Fixtures

| Scenario                   | Endpoint                        | Behavior                               |
| -------------------------- | ------------------------------- | -------------------------------------- |
| Header/read timeout (TTFB) | `/timeout`                      | TCP accepts, but never sends data      |
| Header timeout             | `/delay/{ms}/headers`           | Delays before sending headers          |
| Body timeout               | `/delay/{ms}/body`              | Sends headers immediately, delays body |
| Combined                   | `/drip?duration={ms}&bytes={n}` | Slow body streaming                    |

**Note on connect timeout testing**: True connect timeouts require the TCP handshake to never complete. Fixture endpoints cannot simulate this.

- Use an unroutable IP: `203.0.113.1:81` (TEST-NET-3). This is often a timeout, but some networks fail fast.
- `localhost:1` typically gives connection refused (not a timeout).
- For deterministic connect timeouts in CI, use an environment-level DROP/blackhole rule.

The `/timeout` endpoint tests **read/header timeout** (connection succeeds, no response), which is the more common failure mode.

### Go Example: Testing Header vs Body Timeout

```go
func TestClient_TimeoutTiers(t *testing.T) {
    t.Run("header_timeout_triggers", func(t *testing.T) {
        client := &http.Client{
            Transport: &http.Transport{
                ResponseHeaderTimeout: 100 * time.Millisecond,
            },
        }

        req, _ := http.NewRequest("GET", fixtureURL+"/delay/500/headers", nil)
        _, err := client.Do(req)
        require.Error(t, err)
    })

    t.Run("body_timeout_triggers", func(t *testing.T) {
        client := &http.Client{
            Timeout: 100 * time.Millisecond, // overall request deadline
        }

        req, _ := http.NewRequest("GET", fixtureURL+"/delay/500/body", nil)
        _, err := client.Do(req)
        require.Error(t, err)
    })
}
```

### Python Example: Timeout with httpx

```python
import httpx
import pytest

@pytest.mark.parametrize("endpoint,timeout,should_fail", [
    ("/delay/500/headers", 0.1, True),   # Header delay > timeout
    ("/delay/100/headers", 1.0, False),  # Header delay < timeout
])
async def test_header_timeout(fixture_url, endpoint, timeout, should_fail):
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        if should_fail:
            with pytest.raises(httpx.TimeoutException):
                await client.get(f"{fixture_url}{endpoint}")
        else:
            resp = await client.get(f"{fixture_url}{endpoint}")
            assert resp.status_code == 200
```

### Common Pitfalls

- **Confusing connect vs read timeout**: Many clients have separate settings
- **Not testing slow body scenarios**: Headers arrive, body doesn't
- **Ignoring Keep-Alive timeout**: Connection reuse can mask issues

## Redirect Handling

### Redirect Types and Semantics

| Status | Meaning   | Method Change?      | Body Forwarded? |
| ------ | --------- | ------------------- | --------------- |
| 301    | Permanent | GET only            | No              |
| 302    | Found     | GET only (browsers) | No              |
| 303    | See Other | Always GET          | No              |
| 307    | Temporary | Never               | Yes             |
| 308    | Permanent | Never               | Yes             |

### Testing with Fixtures

| Scenario           | Endpoint                 | Behavior               |
| ------------------ | ------------------------ | ---------------------- |
| Redirect chain     | `/redirect/{n}`          | N redirects before 200 |
| Absolute redirects | `/redirect/{n}/absolute` | Absolute URL redirects |
| Relative redirects | `/redirect/{n}/relative` | Relative URL redirects |
| Infinite loop      | `/redirect/loop`         | Redirects to self      |

### TypeScript Example: Redirect Handling

```typescript
import { describe, it, expect } from "vitest";

describe("redirect handling", () => {
  it("follows redirect chain up to limit", async () => {
    const response = await fetch(`${FIXTURE_URL}/redirect/3`, {
      redirect: "follow",
    });

    expect(response.ok).toBe(true);
    expect(response.redirected).toBe(true);
  });

  it("detects redirect loop", async () => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);

    try {
      await fetch(`${FIXTURE_URL}/redirect/loop`, {
        redirect: "follow",
        signal: controller.signal,
      });
      expect.fail("Should have thrown on redirect loop");
    } catch (error) {
      expect(error).toBeDefined();
    } finally {
      clearTimeout(timeout);
    }
  });
});
```

### Common Pitfalls

- **No max redirect limit**: Infinite loops hang forever
- **Method change on 302/303**: POST becomes GET
- **Cookie/header propagation**: Security implications across origins

## Retry and Backoff

### When to Retry

| Condition                           | Retry? | Notes                        |
| ----------------------------------- | ------ | ---------------------------- |
| 429 Too Many Requests               | Yes    | Respect `Retry-After` header |
| 503 Service Unavailable             | Yes    | Temporary overload           |
| 5xx with idempotent method          | Yes    | GET, HEAD, PUT, DELETE       |
| Network error (connect timeout)     | Yes    | Transient failure            |
| 4xx (except 429)                    | No     | Client error, won't change   |
| Non-idempotent without confirmation | No     | May cause duplicates         |

### Exponential Backoff Pattern (Go)

```go
func retryWithBackoff(ctx context.Context, fn func() error) error {
    backoff := 100 * time.Millisecond
    maxBackoff := 10 * time.Second
    maxRetries := 5

    for attempt := 0; attempt < maxRetries; attempt++ {
        err := fn()
        if err == nil {
            return nil
        }

        if !isRetryable(err) {
            return err
        }

        select {
        case <-ctx.Done():
            return ctx.Err()
        case <-time.After(backoff):
            backoff = min(backoff*2, maxBackoff)
        }
    }

    return fmt.Errorf("max retries exceeded")
}
```

## Auth Failure Handling

### 401 vs 403 Semantics

| Status           | Meaning              | Client Action                       |
| ---------------- | -------------------- | ----------------------------------- |
| 401 Unauthorized | "Who are you?"       | Authenticate (login, refresh token) |
| 403 Forbidden    | "I know you, but no" | Don't retry, permission denied      |

### Go Example: Auth Testing

```go
func TestAuthFailures(t *testing.T) {
    t.Run("401_includes_www_authenticate", func(t *testing.T) {
        resp, err := http.Get(fixtureURL + "/api/protected")
        require.NoError(t, err)
        defer resp.Body.Close()

        assert.Equal(t, 401, resp.StatusCode)
        assert.Contains(t, resp.Header.Get("WWW-Authenticate"), "Bearer")
    })

    t.Run("403_no_retry", func(t *testing.T) {
        resp, err := authenticatedClient.Get(fixtureURL + "/api/admin/config")
        require.NoError(t, err)
        defer resp.Body.Close()

        assert.Equal(t, 403, resp.StatusCode)
        // Client should NOT retry 403
    })
}
```

## Streaming and Chunked Responses

### Rust Example: Streaming with reqwest

```rust
use futures_util::StreamExt;

#[tokio::test]
async fn test_streaming_response() {
    let client = reqwest::Client::new();
    let mut stream = client
        .get(format!("{}/stream/10", FIXTURE_URL))
        .send()
        .await
        .unwrap()
        .bytes_stream();

    let mut total_bytes = 0;
    while let Some(chunk) = stream.next().await {
        let chunk = chunk.unwrap();
        total_bytes += chunk.len();
    }

    assert!(total_bytes > 0);
}
```

## Correlation ID Round-Trip

Use correlation IDs to connect client requests to server logs:

```python
import uuid
import requests

def test_correlation_id_propagation(fixture_url):
    correlation_id = str(uuid.uuid4())

    response = requests.get(
        f"{fixture_url}/echo",
        headers={"X-Correlation-ID": correlation_id}
    )

    # Verify round-trip
    assert response.headers.get("X-Correlation-ID") == correlation_id
```

## CI/CD Integration

### Health Check Before Tests

```yaml
- name: Wait for fixture
  run: |
    until curl -sf http://localhost:8080/health/ready; do
      sleep 1
    done
```

### Parallel Test Isolation

- Use unique correlation IDs per test for log filtering
- Consider separate fixture instances per test suite
- Use dynamic port allocation:

```go
listener, _ := net.Listen("tcp", "127.0.0.1:0")
port := listener.Addr().(*net.TCPAddr).Port
```

## Quick Reference: Test Scenarios

| Testing Scenario    | Endpoint              | Key Assertion                         |
| ------------------- | --------------------- | ------------------------------------- |
| Read/header timeout | `/timeout`            | Error after connect, no data received |
| Header timeout      | `/delay/{ms}/headers` | Error before body                     |
| Body timeout        | `/delay/{ms}/body`    | Headers received, body timeout        |
| Redirect chain      | `/redirect/{n}`       | Final status 200                      |
| Redirect loop       | `/redirect/loop`      | Error or max redirects                |
| Status codes        | `/status/{code}`      | Correct status handling               |
| Retry-After         | `/status/429`         | Respects header delay                 |
| Auth required       | `/api/protected`      | 401 + WWW-Authenticate                |
| Permission denied   | `/api/admin/config`   | 403, no retry                         |
| Streaming           | `/stream/{n}`         | Complete stream received              |
| Correlation ID      | `/echo`               | ID round-trips                        |

## Attribution

Adapted from [FulmenHQ Crucible](https://github.com/fulmenhq/crucible) HTTP client patterns.
