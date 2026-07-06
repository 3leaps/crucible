---
title: "FFI Bindings Setup for Rust Projects"
description: "Adding Go and TypeScript bindings to Rust libraries via FFI"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-30"
last_updated: "2026-01-30"
status: "draft"
tags: ["rust", "ffi", "go", "typescript", "bindings", "napi-rs", "cgo"]
---

# FFI Bindings Setup for Rust Projects

How to add Go and TypeScript bindings to Rust libraries. Based on patterns from docprims and sysprims.

## Project Structure

```
myproject/
├── Cargo.toml              # Workspace root
├── package.json            # Root package.json (private, for tooling)
├── crates/
│   └── myproject-core/     # Core Rust library
├── ffi/
│   └── myproject-ffi/      # C-ABI exports (cdylib + staticlib)
└── bindings/
    ├── go/
    │   └── myproject/      # Go module with CGO
    └── typescript/
        └── myproject/      # npm package with napi-rs
```

## Root package.json

**Required** for code quality tools (biome, prettier, etc.) even if not publishing from root.

```json
{
  "name": "myproject-repo",
  "private": true,
  "description": "Workspace root for repo tooling (non-published)",
  "license": "MIT OR Apache-2.0",
  "engines": {
    "node": ">=18"
  }
}
```

Without this, tools like `npm publish --dry-run` from wrong directory give confusing errors, and some quality checkers expect a root package.json.

## Rust FFI Crate

The FFI crate exports C-ABI functions for bindings to consume.

### Cargo.toml

```toml
[package]
name = "myproject-ffi"
version.workspace = true

[lib]
crate-type = ["cdylib", "staticlib"]

[dependencies]
myproject-core = { path = "../../crates/myproject-core" }
```

### Key Points

- `cdylib` produces `.so`/`.dylib`/`.dll` for dynamic linking
- `staticlib` produces `.a` for static linking (Go default)
- Use `cbindgen` to generate C header from Rust

## Go Bindings

### Structure

```
bindings/go/myproject/
├── go.mod                  # github.com/org/myproject/bindings/go/myproject
├── myproject.go            # Public Go API
├── ffi.go                  # CGO bridge (calls C functions)
├── cgo_darwin_arm64.go     # Platform-specific CGO flags
├── cgo_linux_amd64.go
├── cgo_linux_amd64_musl.go # Build tag: musl
├── lib/                    # Prebuilt static libraries
│   ├── darwin-arm64/libmyproject_ffi.a
│   ├── linux-amd64/libmyproject_ffi.a
│   └── ...
├── lib-shared/             # Prebuilt shared libraries (optional)
│   ├── darwin-arm64/libmyproject_ffi.dylib
│   └── ...
└── include/
    └── myproject.h         # C header from cbindgen
```

### CGO Platform Files

Each platform needs a CGO file with build constraints:

```go
//go:build darwin && arm64

package myproject

/*
#cgo LDFLAGS: -L${SRCDIR}/lib/darwin-arm64 -lmyproject_ffi -lm -liconv
#cgo LDFLAGS: -framework Security -framework CoreFoundation
*/
import "C"
```

### Static vs Shared Libraries

**Static (default)**: Library linked into binary, no runtime dependency.

**Shared**: Smaller binary, but runtime library required.

```bash
# Static (default)
go build ./...

# Shared (build tag)
go build -tags myproject_shared ./...
```

### Shared Library Runtime (Darwin)

Darwin shared libraries need runtime path handling:

```bash
# Development
export DYLD_LIBRARY_PATH="path/to/lib-shared/darwin-arm64"
./myapp

# Distribution: embed rpath at build time
go build -ldflags='-extldflags "-Wl,-rpath,@executable_path"' ./...
# Then bundle dylib next to binary
```

### Darwin install_name

Shared libraries on Darwin must use `@rpath` in install_name, not hardcoded build paths:

```bash
# In CI after building dylib
install_name_tool -id "@rpath/libmyproject_ffi.dylib" libmyproject_ffi.dylib
```

Without this, consumers get errors about missing libraries at CI build paths.

### Go Module Tagging

Go modules in subdirectories need separate tags:

```bash
# Main version tag
git tag v0.1.0

# Go submodule tag (required for go get)
git tag bindings/go/myproject/v0.1.0

git push origin v0.1.0 bindings/go/myproject/v0.1.0
```

## TypeScript Bindings

### Structure

```
bindings/typescript/myproject/
├── package.json            # @org/myproject (publishable)
├── tsconfig.json
├── src/
│   ├── index.ts            # Public API
│   ├── ffi.ts              # Native binding loader
│   └── native.ts           # Platform detection
├── native/
│   └── Cargo.toml          # napi-rs native addon
├── dist/                   # Compiled JS + native addon
│   ├── index.js
│   └── native/
│       └── myproject.darwin-arm64.node
└── scripts/
    └── clean.js
```

### package.json

```json
{
  "name": "@org/myproject",
  "version": "0.1.0",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "files": ["dist/", "README.md", "LICENSE"],
  "napi": {
    "name": "myproject",
    "triples": {
      "defaults": false,
      "additional": ["x86_64-unknown-linux-gnu", "aarch64-apple-darwin"]
    }
  },
  "scripts": {
    "build": "tsc -p tsconfig.build.json",
    "build:native": "napi build --cargo-cwd native --release --platform --strip dist/native"
  }
}
```

### Runtime Support

napi-rs addons work with both Node.js and Bun:

```typescript
// No special handling needed - works in both runtimes
import { extractFile } from "@org/myproject";
const result = extractFile("./doc.md");
```

### npm Publishing

npm publishing requires cross-platform prebuilds. Options:

1. **Platform-specific packages**: `@org/myproject-linux-x64-gnu`, etc.
2. **CI prebuild workflow**: Build all platforms, upload as npm optionalDependencies
3. **Post-install build**: Requires Rust toolchain on consumer machine (not recommended)

## CI/CD Considerations

### Go Bindings Prep Workflow

Before wiring bindings into CI, read [Rust CI Parity and Generated-Tool Dependencies](ci-parity-and-generated-tools.md). The recurring failure mode is that CI exercises bindings or header-generation paths that local `prepush` does not, while required tools such as `cbindgen` are not installed or verified locally.

Separate workflow to build and commit prebuilt libraries:

1. Build FFI for all platforms (cargo-zigbuild for cross-compilation)
2. Run `install_name_tool` for Darwin dylibs
3. Commit libraries to `bindings/go/myproject/lib/`
4. Create PR for review

This keeps prebuilt binaries in the repo so `go get` works without Rust.

### TypeScript CI

1. Build native addon per-platform
2. Run tests with native addon
3. (Optional) Publish to npm with OIDC trusted publishing

### Release Workflow

1. Run Go bindings prep workflow
2. Merge generated PR
3. Tag with both main version and Go submodule version
4. TypeScript: trigger npm publish workflow

## Rust Static Library Symbol Collision

When a Go application links multiple Rust static libraries (e.g., docprims + go-libsql), duplicate symbols can occur:

```
duplicate symbol '_rust_eh_personality' in:
    libfoo.a
    libbar.a
```

**Solutions**:

1. Use shared library mode for one dependency
2. Build both Rust libraries into single staticlib
3. Use `-Wl,--allow-multiple-definition` (not recommended)

## Related

- [Go CGO documentation](https://pkg.go.dev/cmd/cgo)
- [napi-rs documentation](https://napi.rs/)
- [cbindgen](https://github.com/mozilla/cbindgen) - C header generation from Rust
