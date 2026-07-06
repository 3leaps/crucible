---
title: "Windows Runner Gotchas"
description: "Platform differences that cause CI failures on Windows GitHub Actions runners"
author: "Claude Opus 4.6"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-02-09"
last_updated: "2026-02-18"
updated_in: "kitfly v0.2.3 - added shell-based .exe resolution pattern"
status: "draft"
tags: ["github-actions", "windows", "cross-platform", "cicd", "troubleshooting"]
---

# Windows Runner Gotchas

Windows GitHub Actions runners differ from Linux/macOS in ways that cause subtle CI failures. This document captures lessons learned from cross-platform release pipelines.

Scope note:

- This page covers runner/platform behavior in GitHub Actions.
- TypeScript package availability gaps on Windows ARM64 are tracked in [Windows ARM64 Gaps in the TypeScript Stack](../../toolchains/typescript/windows-arm64-gaps.md).
- Bun binary release assembly and packaging patterns are tracked in [Bun-Compiled TypeScript Binaries](../../toolchains/typescript/bun-compiled-binaries.md).

## Shell Defaults

Windows runners default to `pwsh` (PowerShell), not `bash`. Any step using bash syntax without an explicit `shell:` will fail silently or produce wrong results.

### The Problem

```yaml
# BROKEN on Windows - uses pwsh by default
- run: |
    set -euo pipefail
    echo "hello from bash"
```

PowerShell ignores `set -euo pipefail` and interprets the rest differently.

### Solution

Always specify `shell:` explicitly when your script targets a particular shell:

```yaml
# For bash scripts on Windows
- run: |
    set -euo pipefail
    echo "hello from bash"
  shell: bash

# For PowerShell scripts (explicit is still better)
- run: |
    Write-Host "hello from PowerShell"
  shell: pwsh
```

**Recommendation**: Use `pwsh` natively for Windows steps rather than forcing `bash`. PowerShell is the idiomatic shell on Windows runners and avoids path separator issues.

```yaml
# Idiomatic Windows CI
- name: Build
  shell: pwsh
  run: |
    go build -o bin/tool.exe .
    .\bin\tool.exe --version
```

## Cross-Device Rename Failures

### The Problem

On Windows runners, `os.TempDir()` may return a path on a different drive (e.g., `C:\Users\...`) than the workspace (e.g., `D:\a\...`). `os.Rename` fails across drive boundaries because it uses the `MoveFileEx` syscall, which cannot move files across volumes.

On Unix, this produces `EXDEV` (cross-device link). On Windows, the error is `ERROR_NOT_SAME_DEVICE` (error code 17). Critically, `errors.Is(err, syscall.EXDEV)` does **not** match the Windows error, so EXDEV-specific guards silently fall through.

### Root Cause

```go
// This guard ONLY catches Unix EXDEV, not Windows cross-device errors
if errors.Is(err, syscall.EXDEV) {
    return copyFallback(src, dst)
}
return err // Windows cross-device error reaches here!
```

### Solution

Fall back to copy on **any** rename failure, not just EXDEV:

```go
func moveOrCopy(src, dst string) error {
    if err := os.Rename(src, dst); err != nil {
        // Fallback covers cross-device errors on all platforms
        // (EXDEV on Unix, ERROR_NOT_SAME_DEVICE on Windows)
        if errCopy := copyFile(src, dst); errCopy != nil {
            return fmt.Errorf("rename: %w; copy fallback: %w", err, errCopy)
        }
        _ = os.Remove(src)
    }
    return nil
}
```

The copy fallback uses a temp file + rename within the destination directory to ensure atomicity:

```go
func copyFile(src, dst string) error {
    in, err := os.Open(src)
    if err != nil {
        return err
    }
    defer in.Close()

    srcInfo, err := in.Stat()
    if err != nil {
        return err
    }

    if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
        return err
    }

    tmp := dst + ".tmp"
    out, err := os.Create(tmp)
    if err != nil {
        return err
    }

    if _, err := io.Copy(out, in); err != nil {
        _ = out.Close()
        _ = os.Remove(tmp)
        return err
    }
    if err := out.Close(); err != nil {
        _ = os.Remove(tmp)
        return err
    }
    if err := os.Chmod(tmp, srcInfo.Mode().Perm()); err != nil {
        _ = os.Remove(tmp)
        return err
    }
    // Final rename is same-device (tmp is in dst's directory)
    if err := os.Rename(tmp, dst); err != nil {
        _ = os.Remove(tmp)
        return err
    }
    return nil
}
```

**Key insight**: The final `os.Rename(tmp, dst)` always succeeds because `tmp` and `dst` are in the same directory, guaranteeing same-device operation.

## `.exe` Extension Propagation

### The Problem

Archives for Windows contain binaries with `.exe` extensions (e.g., `tool.exe`), but install logic may construct the destination path without it:

```
Expected: C:\Users\me\bin\tool.exe
Actual:   C:\Users\me\bin\tool        (not executable on Windows)
```

This happens when the install name is derived from the repository name or a config value that doesn't include the extension, and the code doesn't check whether the resolved binary inside the archive has `.exe`.

### Solution

After resolving the binary path inside an archive, propagate the `.exe` suffix to the install name:

```go
if runtime.GOOS == "windows" &&
    strings.HasSuffix(strings.ToLower(filepath.Base(binaryPath)), ".exe") &&
    !strings.HasSuffix(strings.ToLower(installName), ".exe") {
    installName += ".exe"
}
```

Also add a fallback when searching for binaries inside extracted archives:

```go
if goos == "windows" && !strings.HasSuffix(strings.ToLower(binaryName), ".exe") {
    exePath := filepath.Join(extractDir, binaryName+".exe")
    if _, err := os.Stat(exePath); err == nil {
        return exePath, nil
    }
}
```

**Apply this at every code path** that resolves a binary from an archive. In practice, there are often multiple call sites (extraction, preflight checks, cache lookups) that each need the same guard.

## Shell-Based `.exe` Resolution

### The Problem

The Go-level `.exe` propagation pattern (above) addresses binary extraction. But shell scripts and Makefiles that bootstrap tools on Windows face a related but distinct issue: `[ -x "$BINDIR/tool" ]` and `command -v tool` intermittently fail to resolve `.exe` binaries on Git Bash, particularly on ARM64 runners.

Git Bash sometimes transparently resolves `tool` to `tool.exe` and sometimes does not. The behavior varies between runner images and sessions. A bootstrap script that works on Windows x64 may fail on Windows ARM64 — or pass one run and fail the next.

### Symptoms

- Bootstrap installs `tool.exe` successfully but the next step reports "tool not found"
- `[ -x "$HOME/.local/bin/tool" ]` returns false even though `tool.exe` exists there
- `command -v tool` fails despite the binary being in `$PATH`
- Intermittent: same workflow passes on x64 but fails on arm64 (or passes one run, fails the next)

### Solution

Check both bare name and `.exe` at every resolution point:

```bash
# Existence checks — always test both forms
if [ -x "$BINDIR/tool" ] || [ -x "$BINDIR/tool.exe" ]; then
    echo "tool already installed"
fi

# Resolution — cascade through both forms
BIN="$(command -v tool 2>/dev/null || true)"
if [ -z "$BIN" ] && [ -x "$BINDIR/tool" ]; then BIN="$BINDIR/tool"; fi
if [ -z "$BIN" ] && [ -x "$BINDIR/tool.exe" ]; then BIN="$BINDIR/tool.exe"; fi
if [ -z "$BIN" ]; then echo "tool not found" >&2; exit 1; fi
```

Also add a post-install verification check — don't assume the install succeeded just because the install command exited zero:

```bash
# After installing
curl -sSfL "$URL" -o /tmp/install.sh && bash /tmp/install.sh --dir "$BINDIR"

# Verify it actually landed
if ! command -v tool >/dev/null 2>&1 \
    && [ ! -x "$BINDIR/tool" ] \
    && [ ! -x "$BINDIR/tool.exe" ]; then
    echo "error: tool installation failed" >&2
    exit 1
fi
```

**Key insight**: Apply the `.exe` fallback at **every** resolution point in the script. A typical bootstrap has 3-6 places that resolve a binary — missing any one of them creates an intermittent failure.

### Makefile-Specific Pattern

For Make variables that resolve tools, use `elif` chains:

```makefile
TOOL_RESOLVE = \
	TOOL=""; \
	if [ -x "$(BINDIR)/tool" ]; then TOOL="$(BINDIR)/tool"; \
	elif [ -x "$(BINDIR)/tool.exe" ]; then TOOL="$(BINDIR)/tool.exe"; fi; \
	if [ -z "$$TOOL" ]; then TOOL="$$(command -v tool 2>/dev/null || true)"; fi; \
	if [ -z "$$TOOL" ]; then echo "tool not found" >&2; exit 1; fi
```

### Discovered In

kitfly v0.2.3 CI — sfetch extraction completed on Windows ARM64 but `[ -x "$BINDIR/sfetch" ]` returned false. The bare name check passed on x64 runners but failed intermittently on ARM64. Fixed by adding `.exe` fallbacks at all six resolution points plus post-install verification.

## Path Separators

### The Problem

`filepath.Join` produces `\` separators on Windows. Tests or assertions that hardcode `/` will fail:

```go
// Fails on Windows: got "bin\tool.exe", want "bin/tool.exe"
assert.Equal(t, "bin/tool.exe", filepath.Join("bin", "tool.exe"))
```

### Solution

Use `filepath.Join` consistently for construction and comparison, or normalize with `filepath.ToSlash` when comparing against known `/`-separated strings:

```go
expected := filepath.Join("bin", "tool.exe")
assert.Equal(t, expected, result)
```

## ARM64 Runners

### Custom Runner Labels

Windows ARM64 runners are not part of the standard GitHub-hosted runner pool. Self-hosted or custom labels are required:

```yaml
windows-dogfood-arm64:
  name: Windows dogfood (arm64)
  runs-on: windows-latest-arm64-s # Custom self-hosted label
```

### actionlint Configuration

Custom runner labels cause `actionlint` to report errors. Add them to `.github/actionlint.yaml`:

```yaml
self-hosted-runner:
  labels:
    - windows-latest-arm64-s
```

### Package Manager Availability

ARM64 Windows runners may not have `chocolatey`. Fall back to `winget`:

```yaml
- name: Install dependency
  shell: pwsh
  run: |
    if (Get-Command choco -ErrorAction SilentlyContinue) {
      choco install minisign -y --no-progress
    } else {
      winget install -e --id FrankDenis.Minisign --silent `
        --accept-source-agreements --accept-package-agreements
    }
```

## Dogfood CI Pattern

Use your own tool to install a known dependency on every target platform. This validates the full download-verify-extract-install pipeline:

```yaml
windows-dogfood-x64:
  name: Windows dogfood (x64)
  runs-on: windows-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-go@v5
      with:
        go-version: "1.24"

    - name: Build tool
      shell: pwsh
      run: |
        go build -o bin/tool.exe .
        .\bin\tool.exe --version

    - name: Install dependency via tool
      shell: pwsh
      run: |
        .\bin\tool.exe `
          --repo org/dependency `
          --tag v1.0.0 `
          --dest-dir bin
        .\bin\dependency.exe version
```

**Key properties**:

- Build from the current commit (not a released version)
- Install a real dependency with signature verification
- Run the installed dependency to prove it works
- Test on both x64 and arm64 runners

## Archive Format Override on Windows

### The Problem

Windows release assets are typically `.zip` files, while Linux/macOS assets use `.tar.gz`. When a tool has a default config like `archiveType: "tar.gz"`, that default can override a correctly-inferred `.zip` format, routing Windows archives through the wrong extraction codepath.

Symptoms:

- `exit status 2` from `tar` when extracting a `.zip` file
- Extraction succeeds on Linux/macOS but fails on Windows
- The error appears only when the tool uses a config file or embedded defaults

### Root Cause

Multi-layer format classification creates a precedence conflict:

```
Layer 1: File extension inference  → .zip detected from "tool_windows_amd64.zip"
Layer 2: Config default            → archiveType: "tar.gz" (global default)
Layer 3: Explicit override         → (none set by user)
```

Without a guard, Layer 2 overwrites Layer 1's correct inference. The extraction logic sees `tar.gz` and invokes `tar` on a `.zip` file.

### Solution

When applying config defaults, check whether a higher-quality inference already determined the format:

```go
// WRONG: config default unconditionally overwrites inference
if cfg.ArchiveType != "" && cls.Type == AssetTypeArchive {
    cls.ArchiveFormat = archiveFormatFromString(cfg.ArchiveType)
}

// RIGHT: only apply default when inference didn't already set a format
if cfg.ArchiveType != "" && cls.Type == AssetTypeArchive && cls.ArchiveFormat == "" {
    cls.ArchiveFormat = archiveFormatFromString(cfg.ArchiveType)
}
```

The key guard is `cls.ArchiveFormat == ""` — it preserves formats inferred from file extensions while still allowing the config default to fill in unknown cases.

### General Principle

This is a broader pattern in layered configuration: **lower-priority defaults must not overwrite higher-quality inferences**. When multiple layers contribute to the same field, the merge logic needs explicit precedence guards. See [Config Layering Pitfalls](../../toolchains/go/config-layering-pitfalls.md) for the general pattern.

### Testing

Add a regression test that combines a Windows `.zip` asset with a `tar.gz` config default:

```go
func TestConfigDefaultDoesNotOverrideZipFormat(t *testing.T) {
    cfg := &Config{ArchiveType: "tar.gz"}
    result := classifyAsset("tool_v1.0_windows_amd64.zip", cfg)
    assert.Equal(t, ArchiveFormatZip, result.ArchiveFormat)
}
```

## CRLF Line Endings

### The Problem

Git on Windows converts LF to CRLF on checkout by default. Format checkers (Biome, Prettier, etc.) then flag every file in the repository as having incorrect line endings, even though the files are correct in the repository.

### Solution

Add `.gitattributes` to the repository root:

```
# Force LF line endings on all platforms
* text=auto eol=lf
```

This must be committed **before** format checks run in CI. Existing Windows clones need a fresh checkout after the file is added.

## TypeScript Native Binary Gaps on ARM64

### The Problem

Several Rust/C++ tools in the TypeScript stack do not publish `win32-arm64` native binaries:

| Tool   | Missing Package                   | Impact                                     |
| ------ | --------------------------------- | ------------------------------------------ |
| Biome  | `@biomejs/cli-win32-arm64`        | Lint step fails                            |
| Rollup | `@rollup/rollup-win32-arm64-msvc` | Test step fails (Vitest depends on Rollup) |

Bun itself runs via x64 emulation on ARM64 Windows, but npm/bun package resolution uses `process.arch` (which reports `arm64`) at **install time** to select optional dependency variants. The package manager tries to install the arm64 package even though x64 packages would work at runtime.

### Solution

Split monolithic quality checks into individual CI steps and use matrix flags to skip unavailable tools:

```yaml
matrix:
  include:
    - os: windows-latest-arm64-s
      name: windows-arm64
      skip-lint: true # Biome: no arm64 binary
      skip-test: true # Rollup/Vitest: no arm64 binary

steps:
  - name: Lint
    if: matrix.skip-lint != true
    run: make lint

  - name: Typecheck
    run: make typecheck # tsc is pure JS, works natively

  - name: Test
    if: matrix.skip-test != true
    run: make test

  - name: Build
    run: make build # File I/O and path handling validated
```

Windows x64 provides full lint + test coverage for all Windows-specific behavior. The ARM64 target validates the bootstrap chain, TypeScript compilation, and build pipeline.

See [Windows ARM64 Gaps in TypeScript](../../toolchains/typescript/windows-arm64-gaps.md) for the full analysis including path handling patterns.

## Node.js Path Separators

### The Problem

`path.join()` and `path.resolve()` produce `\` separators on Windows. Code that compares paths using hardcoded `/` breaks:

```typescript
// FAILS on Windows: resolved is "C:\project\docs\file.md"
if (!resolved.startsWith(`${root}/`)) { ... }
```

### Solution

Use `path.sep` for separator and `path.resolve()` to normalize roots:

```typescript
import { resolve, sep } from "node:path";

const normalizedRoot = resolve(root);
if (!resolved.startsWith(`${normalizedRoot}${sep}`)) { ... }
```

For URL paths (which always use `/`), normalize after stripping the root prefix:

```typescript
return resolvedPath.slice(root.length + 1).replaceAll("\\", "/");
```

In tests, use `resolve()`, `join()`, `isAbsolute()`, `dirname()`, and `sep` instead of hardcoded path strings.

## Testing Strategy

1. **Always test on Windows** - cross-platform matrix builds catch the majority of these issues
2. **Test cross-device scenarios** - mock `os.Rename` to return errors and verify fallback paths
3. **Test `.exe` propagation** - verify install names include `.exe` when the archive binary has it
4. **Test with real asset lists** - asset selection bugs only manifest when the full asset list includes multiple platforms

## Related

- [YAML Shell Gotchas](yaml-shell-gotchas.md) - Shell scripting in YAML `run:` blocks
- [Cross-Platform Asset Selection](cross-platform-asset-selection.md) - OS token matching pitfalls
- [Config Layering Pitfalls](../../toolchains/go/config-layering-pitfalls.md) - Config default vs inference precedence
- [Windows ARM64 Gaps in TypeScript](../../toolchains/typescript/windows-arm64-gaps.md) - Biome, Rollup, Vitest binary availability
