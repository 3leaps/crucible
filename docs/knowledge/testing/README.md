---
title: "Testing Knowledge"
description: "Testing patterns, strategies, and platform-specific knowledge for reliable test suites"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["testing", "knowledge", "patterns", "http", "integration"]
---

# Testing Knowledge

This directory contains testing patterns, strategies, and platform-specific knowledge that supports reliable test suites across 3leaps projects.

## Contents

| Document                                        | Description                                                |
| ----------------------------------------------- | ---------------------------------------------------------- |
| [HTTP Server Patterns](http-server-patterns.md) | Patterns for implementing and testing HTTP servers         |
| [HTTP Client Patterns](http-client-patterns.md) | Patterns for testing HTTP clients, middleware, and proxies |

## Philosophy

Testing knowledge in this directory focuses on:

1. **Practical patterns** - Battle-tested approaches from real projects
2. **Anti-patterns** - Common mistakes and how to avoid them
3. **Platform specifics** - Language and framework-specific guidance
4. **Integration testing** - Testing against real services and fixtures

## Testing Fixtures

Many patterns reference "test fixtures" - lightweight servers that simulate specific behaviors (timeouts, redirects, auth failures). These are invaluable for integration testing HTTP clients.

Common fixture capabilities:

- `/timeout` - Never responds (tests read timeout)
- `/delay/{ms}/headers` - Delayed header response
- `/delay/{ms}/body` - Delayed body response
- `/redirect/{n}` - Redirect chains
- `/status/{code}` - Any HTTP status code
- `/echo` - Echo request details back

## Related

- [CI Baseline](../../operations/ci-baseline.md) - CI/CD testing patterns
- [Toolchains](../toolchains/) - Language-specific testing tools

## Attribution

HTTP testing patterns adapted from [FulmenHQ Crucible](https://github.com/fulmenhq/crucible) with permission.
