---
title: "Cross-Platform Asset Selection"
description: "Pitfalls in OS-aware asset matching for multi-platform release downloads"
author: "Claude Opus 4.6"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-02-09"
last_updated: "2026-02-09"
status: "draft"
tags: ["cross-platform", "asset-selection", "regex", "release-engineering", "troubleshooting"]
---

# Cross-Platform Asset Selection

When downloading release assets for the current platform, tools must select the correct archive from a list like:

```
tool_v1.2.3_darwin_amd64.tar.gz
tool_v1.2.3_darwin_arm64.tar.gz
tool_v1.2.3_linux_amd64.tar.gz
tool_v1.2.3_linux_arm64.tar.gz
tool_v1.2.3_windows_amd64.zip
tool_v1.2.3_windows_arm64.zip
```

This is a language-agnostic problem affecting shell scripts, Go, Rust, Python, and any tool that maps `runtime.GOOS`/`os.name`/`$OSTYPE` to release asset filenames.

## The Substring False Positive Problem

### The Problem

OS aliases like `"win"` (short for `"windows"`) appear as substrings inside other platform names. A regex or string search for `win` matches `dar`**win**:

```
Pattern: (?:win|windows)
Asset:   tool_v1.2.3_darwin_arm64.tar.gz
Match:   tool_v1.2.3_da[rwin]_arm64.tar.gz  <-- FALSE POSITIVE
```

On a Windows/arm64 system, this causes the tool to download the **darwin/arm64** asset instead of the **windows/arm64** asset. The downloaded binary silently fails to execute (wrong OS), producing a confusing error.

### Why It Happens

Many tools maintain a mapping of OS names to aliases for matching flexibility:

```
windows -> ["win", "win32", "win64", "mingw"]
darwin  -> ["macos", "macosx", "osx"]
linux   -> ["linux"]
```

When these aliases are compiled into a regex alternation (`win|windows`), the short alias matches as a substring inside unrelated tokens. The regex engine finds a valid match and stops looking — it has no concept of "token boundaries."

### Common False Positives

| Alias  | False Match In | Explanation                     |
| ------ | -------------- | ------------------------------- |
| `win`  | `darwin`       | `dar` + `win`                   |
| `arm`  | `charm`        | `ch` + `arm`                    |
| `arm`  | `farmOS`       | `f` + `arm` + `OS`              |
| `x86`  | `x86_64`       | Overlapping architecture tokens |
| `i386` | `i3868`        | Numeric run-on in version tags  |
| `osx`  | `bosx`         | Hypothetical, same class        |

## Root Cause Analysis

The fundamental issue is **regex matching vs. token-boundary matching**. A regex finds character sequences. An asset name is a sequence of **tokens** separated by delimiters (`_`, `-`, `.`). The correct question is "does this asset contain the token `win`?" not "does this asset contain the substring `win`?"

```
"tool_v1.2.3_darwin_arm64.tar.gz"
 Tokens: [tool, v1, 2, 3, darwin, arm64, tar, gz]
 Substring "win": YES (inside "darwin")
 Token "win":     NO  (no token equals "win")
```

## Solution: Boundary-Aware Token Matching

### Pattern

Validate regex matches with a second pass that checks token boundaries. A token boundary exists when the character before and after the match is either a non-alphanumeric character or a string boundary.

```go
func isAlphaNum(b byte) bool {
    return (b >= 'a' && b <= 'z') ||
           (b >= 'A' && b <= 'Z') ||
           (b >= '0' && b <= '9')
}

func containsTokenBoundary(haystack, needle string) bool {
    hLen := len(haystack)
    nLen := len(needle)
    if nLen == 0 || nLen > hLen {
        return false
    }
    for i := 0; i <= hLen-nLen; i++ {
        if strings.EqualFold(haystack[i:i+nLen], needle) {
            before := i == 0 || !isAlphaNum(haystack[i-1])
            after := i+nLen == hLen || !isAlphaNum(haystack[i+nLen])
            if before && after {
                return true
            }
        }
    }
    return false
}
```

**Behavior**:

```
containsTokenBoundary("darwin_arm64", "win")    -> false  ("w" preceded by alphanumeric "r")
containsTokenBoundary("windows_amd64", "win")   -> true   ("w" at start, "d" preceded by non-alnum "_"... wait)
```

Wait — `"windows"` starts with `"win"` followed by `"d"` which is alphanumeric. So `containsTokenBoundary("windows_amd64", "win")` returns `false` because `"d"` follows `"win"`. This is correct behavior: the **full alias list** `["win", "win32", "win64", "windows"]` handles this. `"windows"` matches as a token because it's delimited by `_`.

### Multi-Stage Selection

The recommended architecture layers multiple selection strategies:

1. **Pattern match** - User-defined or default regex patterns find candidates
2. **Boundary validation** - Token-boundary checks filter out false positives
3. **Inference rules** - Architecture and OS inference disambiguates remaining candidates
4. **Heuristic fallback** - Alias tables with boundary-aware matching as a last resort

```go
func matchWithPatterns(assets []Asset, goos, goarch string) *Asset {
    osTokens := aliasList(goos) // e.g., ["windows", "win", "win32", "win64"]

    for _, pattern := range patterns {
        re := regexp.MustCompile(renderPattern(pattern, goos, goarch))
        var matches []Asset
        for _, a := range assets {
            if re.MatchString(a.Name) {
                matches = append(matches, a)
            }
        }
        // Stage 2: Validate with boundary-aware token check
        var validated []Asset
        for _, m := range matches {
            if containsTokenCI(m.Name, osTokens) {
                validated = append(validated, m)
            }
        }
        if len(validated) > 0 {
            return pickBest(validated, goos, goarch)
        }
    }
    return nil
}
```

The key insight: **the regex finds candidates; the boundary check confirms them**. Neither alone is sufficient.

## Asset Naming Conventions

To make token-boundary detection reliable, use consistent delimiters in asset names:

### Recommended Format

```
{name}_{version}_{os}_{arch}.{ext}
```

or with hyphens:

```
{name}-{version}-{os}-{arch}.{ext}
```

### Examples

```
# GOOD - tokens clearly delimited
tool_v1.2.3_darwin_amd64.tar.gz
tool_v1.2.3_windows_amd64.zip

# BAD - ambiguous token boundaries
tool-v1.2.3-darwinamd64.tar.gz    (no delimiter between os and arch)
toolv1.2.3_win_amd64.zip          (no delimiter between name and version)
```

### Full OS Names Preferred

Using full OS names (`windows` not `win`, `darwin` not `dar`) in asset filenames eliminates the substring problem at the source. Short aliases should only be used in the **matching logic**, not in asset names.

## Testing Strategy

### Always Test Cross-Platform

The critical mistake is testing asset selection only against the target platform's assets. The bug only manifests when the full asset list is present:

```go
// INSUFFICIENT - only tests the happy path
assets := []Asset{{Name: "tool_windows_amd64.zip"}}
result := selectAsset(assets, "windows", "amd64")

// CORRECT - tests with the full real asset list
assets := []Asset{
    {Name: "tool_darwin_amd64.tar.gz"},
    {Name: "tool_darwin_arm64.tar.gz"},
    {Name: "tool_linux_amd64.tar.gz"},
    {Name: "tool_windows_amd64.zip"},
    {Name: "tool_windows_arm64.zip"},
}
result := selectAsset(assets, "windows", "arm64")
// Verify it did NOT select darwin_arm64
assert.Equal(t, "tool_windows_arm64.zip", result.Name)
```

### Include Negative Cases

```go
// Test that "win" does not match "darwin"
result := selectAsset(fullAssetList, "windows", "arm64")
assert.NotContains(t, result.Name, "darwin")

// Test that "arm" does not match "charm"
assets := []Asset{
    {Name: "charm_linux_amd64.tar.gz"},
    {Name: "tool_linux_arm64.tar.gz"},
}
result := selectAsset(assets, "linux", "arm64")
assert.Equal(t, "tool_linux_arm64.tar.gz", result.Name)
```

### End-to-End Regression Tests

For each OS/arch combination, run the full selection pipeline against a representative asset list and verify both positive selection (correct asset chosen) and negative exclusion (wrong-platform assets rejected).

## Beyond Selection: Format Classification

Asset selection is only half the problem. After selecting the correct asset, the tool must also correctly classify its **format** (`.tar.gz` vs `.zip` vs raw binary). A common bug: config defaults like `archiveType: "tar.gz"` override format inference from the file extension, causing `.zip` assets to be extracted with `tar`.

This is a layered configuration precedence issue — see [Config Layering Pitfalls](../../toolchains/go/config-layering-pitfalls.md) and the "Archive Format Override" section in [Windows Runner Gotchas](windows-runners.md) for details.

## Upstream Status

This is not a bug in any upstream tool — it's a pattern-level pitfall in any code that maps platform identifiers to release asset names. There is no single upstream fix; each tool must implement boundary-aware matching.

## Related

- [Windows Runner Gotchas](windows-runners.md) - Windows CI runner differences
- [YAML Shell Gotchas](yaml-shell-gotchas.md) - Shell scripting pitfalls in CI
- [Config Layering Pitfalls](../../toolchains/go/config-layering-pitfalls.md) - Format classification precedence bugs
