---
title: "Rust Coding Standards"
description: "Rust-specific coding standards including ownership patterns, error handling, async patterns, and testing"
author: "devlead"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["standards", "coding", "rust", "async", "error-handling", "testing"]
upstream_source: "fulmenhq/crucible docs/standards/coding/rust.md"
---

# Rust Coding Standards

## Overview

Rust-specific coding standards ensuring consistency, quality, and safety. These standards apply to 3leaps Rust projects.

**Core Principle**: Write idiomatic Rust code that is safe, performant, and maintainable, with strict output hygiene and proper error handling.

**Foundation**: This guide builds upon [Coding Baseline](baseline.md) which establishes:

- Output hygiene (STDERR for logs, STDOUT for data)
- RFC3339 timestamps
- CLI exit codes
- Error handling patterns
- Security practices

Read the baseline first, then apply Rust-specific patterns below.

---

## 1. Critical Rules (Zero-Tolerance)

### 1.1 Output Hygiene

**Rule**: Output streams must remain clean for structured output.

**DO**: Use `tracing` for all diagnostic output

```rust
use tracing::{debug, info, warn, error};

// Correct logging - goes to STDERR via tracing subscriber
debug!("Processing {} files", file_count);
info!(duration_ms = elapsed.as_millis(), "Operation completed");
warn!("Config not found, using defaults");
error!(error = ?err, "Failed to process file");
```

**DO NOT**: Pollute output streams with print macros in library code

```rust
// CRITICAL ERROR: Breaks structured output
println!("DEBUG: Processing {}", filename);  // Never in library code
print!("Status: {}", status);                 // Never in library code
eprintln!("Error: {}", error);                // Use tracing::error! instead

// Exception: Binary entrypoints may use println! for final structured output
fn main() {
    // ... processing ...
    println!("{}", serde_json::to_string(&result).unwrap()); // OK for final output
}
```

### 1.2 No `unwrap()` or `expect()` in Library Code

```rust
// WRONG - Panics on error
let config = load_config(path).unwrap();
let value = map.get("key").expect("key should exist");

// CORRECT - Propagate errors
let config = load_config(path)?;
let value = map.get("key").ok_or_else(|| Error::MissingKey("key"))?;

// Exception: Tests may use unwrap/expect with clear context
#[test]
fn test_config_loading() {
    let config = load_config(test_path()).expect("test config should load");
    assert_eq!(config.port, 8080);
}
```

### 1.3 No `unsafe` Without Documentation

```rust
// WRONG - Undocumented unsafe
unsafe {
    ptr::write(dest, value);
}

// CORRECT - Documented safety invariants
// SAFETY: `dest` is a valid, aligned pointer obtained from Box::into_raw()
// and has not been deallocated. We have exclusive access via &mut self.
unsafe {
    ptr::write(dest, value);
}
```

**Rule**: Every `unsafe` block must have a `// SAFETY:` comment explaining why the operation is sound.

---

## 2. Code Organization

### 2.1 Project Structure

```
project/
├── src/
│   ├── lib.rs              # Library root
│   ├── error.rs            # Error types (thiserror)
│   ├── config.rs           # Configuration
│   └── modules/
│       ├── mod.rs
│       └── feature.rs
├── tests/
│   ├── integration/
│   └── fixtures/
├── benches/                # Benchmarks (criterion)
├── examples/
├── Cargo.toml
└── rust-toolchain.toml
```

### 2.2 Naming Conventions

- **Crates/Modules**: `snake_case` (`config_loader`, `file_processor`)
- **Types/Traits**: `PascalCase` (`ConfigLoader`, `FileProcessor`)
- **Functions/Methods**: `snake_case` (`load_config`, `process_file`)
- **Constants**: `SCREAMING_SNAKE_CASE` (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Lifetimes**: Short lowercase (`'a`, `'de` for deserialize)

### 2.3 Module Organization

```rust
// lib.rs - Public API surface

// Re-exports for convenient access
pub use config::Config;
pub use error::{Error, Result};

// Public modules
pub mod config;
pub mod error;

// Internal modules (not part of public API)
mod internal;
```

---

## 3. Error Handling

### 3.1 Use thiserror for Libraries

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum Error {
    #[error("configuration error: {0}")]
    Config(String),

    #[error("missing key: {0}")]
    MissingKey(String),

    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("parse error at line {line}: {message}")]
    Parse { line: usize, message: String },
}

pub type Result<T> = std::result::Result<T, Error>;
```

### 3.2 Use anyhow for Applications

```rust
use anyhow::{Context, Result};

fn load_config(path: &Path) -> Result<Config> {
    let content = std::fs::read_to_string(path)
        .with_context(|| format!("failed to read config from {}", path.display()))?;

    let config: Config = toml::from_str(&content)
        .with_context(|| format!("failed to parse config from {}", path.display()))?;

    Ok(config)
}
```

### 3.3 Error Context Pattern

```rust
// Add context when propagating errors
let data = fetch_data(&url)
    .await
    .with_context(|| format!("failed to fetch from {url}"))?;

// Chain errors for debugging
process_data(data)
    .with_context(|| "failed to process fetched data")?;
```

---

## 4. Async Patterns

### 4.1 Prefer tokio

```rust
use tokio::fs;
use tokio::io::AsyncWriteExt;

async fn write_result(path: &Path, data: &[u8]) -> Result<()> {
    let mut file = fs::File::create(path).await?;
    file.write_all(data).await?;
    file.flush().await?;
    Ok(())
}
```

### 4.2 Cancellation Safety

```rust
use tokio::select;
use tokio_util::sync::CancellationToken;

async fn process_with_cancellation(
    token: CancellationToken,
) -> Result<()> {
    loop {
        select! {
            _ = token.cancelled() => {
                tracing::info!("Processing cancelled");
                return Ok(());
            }
            result = process_next() => {
                result?;
            }
        }
    }
}
```

---

## 5. Testing Standards

### 5.1 Unit Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_valid_input() {
        let result = parse("valid input");
        assert!(result.is_ok());
        assert_eq!(result.unwrap().value, "expected");
    }

    #[test]
    fn test_parse_invalid_input() {
        let result = parse("");
        assert!(matches!(result, Err(Error::Parse { .. })));
    }
}
```

### 5.2 Async Tests

```rust
#[tokio::test]
async fn test_async_operation() {
    let result = fetch_data("http://example.com").await;
    assert!(result.is_ok());
}
```

### 5.3 Test Fixtures

```rust
use std::path::PathBuf;

fn fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join(name)
}

#[test]
fn test_with_fixture() {
    let config = load_config(&fixture_path("valid_config.toml"))
        .expect("fixture should load");
    assert_eq!(config.port, 8080);
}
```

---

## 6. Performance Patterns

### 6.1 Avoid Unnecessary Allocations

```rust
// WRONG - Unnecessary allocation
fn process(items: Vec<Item>) -> Vec<Result> {
    items.into_iter().map(transform).collect()
}

// CORRECT - Accept iterator
fn process(items: impl IntoIterator<Item = Item>) -> Vec<Result> {
    items.into_iter().map(transform).collect()
}

// CORRECT - Return iterator when possible
fn process(items: impl IntoIterator<Item = Item>) -> impl Iterator<Item = Result> {
    items.into_iter().map(transform)
}
```

### 6.2 Use Cow for Flexibility

```rust
use std::borrow::Cow;

fn process_name(name: Cow<'_, str>) -> String {
    if name.contains('-') {
        name.replace('-', "_")  // Allocates only when needed
    } else {
        name.into_owned()
    }
}

// Caller can pass &str or String
process_name(Cow::Borrowed("hello-world"));
process_name(Cow::Owned(String::from("hello")));
```

---

## 7. Common Anti-Patterns

### 7.1 Panic in Library Code

```rust
// WRONG
fn get_value(map: &HashMap<String, Value>, key: &str) -> &Value {
    &map[key]  // Panics if key missing
}

// CORRECT
fn get_value(map: &HashMap<String, Value>, key: &str) -> Option<&Value> {
    map.get(key)
}

// Or with error
fn get_value(map: &HashMap<String, Value>, key: &str) -> Result<&Value> {
    map.get(key).ok_or_else(|| Error::MissingKey(key.to_string()))
}
```

### 7.2 Clone Abuse

```rust
// WRONG - Unnecessary clone
fn process(data: &Data) {
    let owned = data.clone();  // Why clone if not needed?
    work_with_reference(&owned);
}

// CORRECT - Use references
fn process(data: &Data) {
    work_with_reference(data);
}
```

### 7.3 String Building

```rust
// WRONG - Repeated allocation
let mut s = String::new();
for item in items {
    s = s + &item.to_string();
}

// CORRECT - Use push_str
let mut s = String::new();
for item in items {
    s.push_str(&item.to_string());
}

// BETTER - Pre-allocate
let mut s = String::with_capacity(items.len() * 10);
for item in items {
    s.push_str(&item.to_string());
}
```

---

## 8. Code Review Checklist

Before submitting Rust code, verify:

- [ ] No `println!`/`print!` in library code
- [ ] No `unwrap()`/`expect()` in library code
- [ ] All `unsafe` blocks have `// SAFETY:` comments
- [ ] Errors propagated with `?` and context
- [ ] Tests cover happy path and error conditions
- [ ] `cargo fmt` passes
- [ ] `cargo clippy` passes with no warnings
- [ ] `cargo test` passes

---

## 9. Tools

### Required

- `rustfmt` - Code formatting
- `clippy` - Linting
- `cargo-deny` - License and advisory checking

### Configuration

```toml
# Cargo.toml
[package]
rust-version = "1.75"  # MSRV
edition = "2021"

[lints.rust]
unsafe_code = "warn"

[lints.clippy]
all = "warn"
pedantic = "warn"
```

### CI Integration

```bash
cargo fmt --check
cargo clippy -- -D warnings
cargo test
cargo deny check

# If cargo-deny advisories are blocked by RustSec parsing issues,
# use the workaround and run cargo-audit for vulnerability scanning.
cargo deny check bans licenses sources
cargo audit
```

---

## Related

- [Coding Baseline](baseline.md) - Language-agnostic standards
- [MSRV Policy](../knowledge/toolchains/rust/msrv-policy.md) - Version guidance
- [cargo-audit vs cargo-deny](../knowledge/toolchains/rust/cargo-audit-vs-deny.md) - Security tools

## Attribution

Adapted from [FulmenHQ Crucible](https://github.com/fulmenhq/crucible) Rust coding standards.
