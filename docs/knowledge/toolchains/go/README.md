---
title: "Go Toolchain Knowledge"
description: "Go ecosystem knowledge, CGO patterns, CLI patterns, and workarounds"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-02-09"
status: "draft"
tags: ["go", "cgo", "cobra", "slog", "toolchains", "configuration"]
---

# Go Toolchain Knowledge

Knowledge and workarounds for the Go ecosystem.

## Contents

| Document                                                | Description                            |
| ------------------------------------------------------- | -------------------------------------- |
| [Cobra CLI Patterns](cobra-cli-patterns.md)             | CLI with Cobra, Viper, slog            |
| [Config Layering Pitfalls](config-layering-pitfalls.md) | Precedence bugs in multi-layer configs |

## Planned

| Document                              | Description                                         |
| ------------------------------------- | --------------------------------------------------- |
| cgo-static-linking.md                 | Static linking with CGO                             |
| module-versioning.md                  | Go module version tagging                           |
| cross-platform-binary-distribution.md | Cross-platform binary packaging and `.exe` handling |

## Common Patterns

### CGO Static Linking

For Go bindings to Rust FFI libraries:

```go
// #cgo LDFLAGS: -L${SRCDIR}/lib/${GOOS}-${GOARCH} -lsysprims_ffi
// #include "sysprims.h"
import "C"
```

Platform-specific considerations:

- Linux: glibc vs musl
- macOS: Universal binaries or arch-specific
- Windows: MSVC vs MinGW (MinGW CGO has limitations)

### Module Versioning

For bindings in subdirectories:

```
# Tag format for bindings/go/pkg
git tag bindings/go/pkg/v1.2.3
```

Go resolves the tag by path prefix.

## Related

- [CI/CD](../../cicd/) - Build automation
- [Coding Baseline](../../../coding/baseline.md) - Language-agnostic coding standard
- [Go Coding Standards](../../../coding/go.md) - Normative Go standard
