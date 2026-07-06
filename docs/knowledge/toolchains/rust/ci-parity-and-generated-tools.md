---
title: "Rust CI Parity and Generated-Tool Dependencies"
description: "Keeping local checks, CI, and generated-tool dependencies aligned in Rust projects"
author: "GPT-5"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-03-12"
last_updated: "2026-03-12"
status: "draft"
tags: ["rust", "ci", "toolchains", "ffi", "bindings", "github-actions"]
---

# Rust CI Parity and Generated-Tool Dependencies

A recurring failure mode in Rust repos with bindings or generated artifacts is that local checks pass, but CI fails immediately because CI exercises a broader surface area or uses a different toolchain.

This is not usually a single-tool problem. The pattern is:

1. CI runs targets that local `prepush` does not run.
2. Those targets depend on non-default tools such as `cbindgen`, `bindgen`, `cargo-zigbuild`, or packaging CLIs.
3. Local formatting or linting uses a different Rust toolchain than CI.

The result is drift: contributors think they are green locally, but the first realistic validation happens in GitHub Actions.

## The Rule

For every CI-critical target:

1. `prepush` must execute the same target or a strict equivalent.
2. `bootstrap` must install every non-default tool that target needs.
3. `tools` or an equivalent verification target must assert those tools are present.
4. Local Rust toolchain and CI Rust toolchain must be pinned to the same version when formatter or lint output matters.

If any of those four conditions is missing, local green is not trustworthy.

## Common Failure Cases

### Formatter Drift

Local machine runs `cargo fmt` on one stable release, CI runs a newer floating `stable`, and formatting differs on edge cases.

Fix:

- Add `rust-toolchain.toml` for contributor toolchain pinning
- Pin the exact same version in CI
- Include `rustfmt` and `clippy` components in the pinned toolchain

Example:

```toml
[toolchain]
channel = "1.94.0"
components = ["rustfmt", "clippy"]
```

```yaml
- name: Setup Rust
  uses: dtolnay/rust-toolchain@1.94.0
```

Do not rely on floating `stable` if CI blocks on `cargo fmt --check`.

### Generated Header / Binding Tool Missing

Local Rust tests pass, but bindings tests fail in CI because `ffi-header` or equivalent requires `cbindgen` and local setup never installed it.

Fix:

- Treat `cbindgen` as part of the required toolchain, not an optional convenience
- Install it in `bootstrap`
- Verify it in `tools`
- Ensure `prepush` reaches the target that actually invokes it

Example pattern:

```make
bootstrap:
	cargo install cbindgen --locked

tools:
	@command -v cbindgen >/dev/null 2>&1 || \
	  (echo "[!!] cbindgen not found"; exit 1)

ffi-header:
	cbindgen --config cbindgen.toml --crate myproject-ffi --output crates/myproject-ffi/myproject.h

go-test: ffi-header
	cd bindings/go/myproject && go test ./...

prepush: check go-test ts-test
```

The important part is not `cbindgen` specifically. The important part is that the generated-tool dependency is part of the same path contributors run before pushing.

### CI Covers More Surfaces Than Local Checks

This is common in Rust workspaces that also ship:

- Go bindings
- TypeScript bindings
- generated headers
- release packaging or signing scripts

If CI runs `make go-test` or `make ts-test` but local `prepush` only runs `cargo test`, the local gate is incomplete.

Fix:

- Make `prepush` cover every CI-blocking surface
- Call the real targets (`go-test`, `ts-test`, `ffi-header`, etc.) rather than re-implementing pieces of them in shell scripts

## Recommended Structure

### 1. Pin Rust Toolchain Explicitly

Use `rust-toolchain.toml` for contributors and pin the same version in CI.

This is separate from MSRV. MSRV declares compatibility; toolchain pinning keeps development and formatting output stable.

### 2. Centralize Generated Targets in Make or Task Runner

Prefer a small number of canonical targets:

- `ffi-header`
- `go-test`
- `ts-test`
- `ci`
- `precommit`
- `prepush`

Then make higher-level targets depend on the lower-level ones.

This gives you one place to encode tool dependencies and build order.

### 3. Distinguish Fast Checks vs Real Push Gate

A good split is:

- `precommit`: fast, frequent, mostly Rust-local (`fmt-check`, `clippy`, unit tests)
- `prepush`: full CI-equivalent or close to it, including bindings and generated artifacts

Do not call a target `prepush` if it knowingly omits CI-blocking surfaces.

### 4. Verify Tools Explicitly

A `tools` target should fail loudly when required tools are absent.

Typical examples:

- `rustfmt`
- `clippy`
- `cargo-deny`
- `cargo-audit`
- `cbindgen`
- language-specific tools needed by bindings (`go`, `node`, `npm`, `bun`, etc.)

## Checklist

Before considering local checks equivalent to CI, verify:

- Is the Rust version pinned locally and in CI?
- Does `prepush` execute every CI-blocking job family?
- Do generated targets declare their dependencies transitively?
- Does `bootstrap` install all non-default tools needed by those targets?
- Does `tools` verify those tools explicitly?
- Are bindings or FFI tests run locally before push?

If any answer is no, expect CI-only failures.

## Where This Shows Up Most Often

This pattern is especially common in:

- Rust + Go FFI repos
- Rust + TypeScript napi-rs repos
- repos with generated headers or codegen
- release pipelines that add signing or packaging tools later than the original dev setup

See also [FFI Bindings Setup](ffi-bindings-setup.md) for the broader bindings layout and release patterns.
