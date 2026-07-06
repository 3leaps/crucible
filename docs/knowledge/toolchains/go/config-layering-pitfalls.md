---
title: "Config Layering Pitfalls"
description: "Precedence bugs when multiple configuration layers contribute to the same field"
author: "Claude Opus 4.6"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-02-09"
last_updated: "2026-02-09"
status: "draft"
tags: ["go", "configuration", "layering", "precedence", "troubleshooting"]
---

# Config Layering Pitfalls

Most tools have multiple configuration layers: inference from context, config file defaults, environment variables, CLI flags, and explicit overrides. When multiple layers contribute to the **same field**, merge logic must respect precedence — or lower-priority defaults silently overwrite higher-quality values.

## The Problem

A tool infers a value from context (e.g., archive format from file extension), then a config default overwrites it:

```
Step 1: inferFormat("tool_windows_amd64.zip") → "zip"     (correct)
Step 2: applyConfig(cfg.ArchiveType="tar.gz") → "tar.gz"  (overwrites!)
Step 3: extract("tar.gz", file)               → exit status 2
```

The config default was intended as a fallback for unknown formats, but it unconditionally replaced a value that was already correctly determined.

## Why It's Subtle

- **Works in the common case**: Most assets match the default format, so the overwrite produces the same value
- **Fails for edge cases**: The bug only triggers when the inferred value differs from the default (e.g., `.zip` on Windows when the default is `.tar.gz`)
- **No error at merge time**: The overwrite is silent — the wrong value only causes a failure downstream during extraction or execution
- **Tests miss it**: Unit tests that use matching formats (inference == default) pass; only cross-format combinations fail

## The Pattern

### Wrong: Unconditional Apply

```go
// Config default always overwrites, even when inference already set the value
if cfg.ArchiveType != "" {
    result.ArchiveFormat = archiveFormatFromString(cfg.ArchiveType)
}
```

### Right: Guard with Empty Check

```go
// Config default only fills in when inference didn't determine a value
if cfg.ArchiveType != "" && result.ArchiveFormat == "" {
    result.ArchiveFormat = archiveFormatFromString(cfg.ArchiveType)
}
```

### Right: Explicit Priority Chain

For complex cases with many layers, make the priority chain explicit:

```go
func resolveFormat(inferred, configDefault, explicit string) string {
    // Explicit override wins (highest priority)
    if explicit != "" {
        return explicit
    }
    // Inference from file extension (high quality)
    if inferred != "" {
        return inferred
    }
    // Config default (fallback only)
    return configDefault
}
```

## Recognizing the Pattern

Watch for these code shapes:

```go
// Shape 1: Unconditional assignment after inference
cls := inferFromExtension(filename)  // sets cls.Format
if cfg.Format != "" {
    cls.Format = cfg.Format           // BUG: overwrites inference
}

// Shape 2: Condition checks type but not value
if cls.Type == TypeArchive {
    cls.Format = cfg.DefaultFormat    // BUG: doesn't check cls.Format
}

// Shape 3: Legacy compatibility guard without value check
if cfg.LegacyField != "" && cfg.NewField == "" {
    cls.Field = cfg.LegacyField       // BUG: doesn't check cls.Field
}
```

## Viper and Cobra

This pattern is related to but distinct from Viper's config hierarchy (flags > env > config > defaults). Viper handles precedence correctly within its own layers. The pitfall occurs when **your code** merges Viper's output with values from other sources (inference, API responses, file extension parsing) without respecting precedence.

```go
// Viper handles its own layers correctly
format := viper.GetString("archive-format") // flag > env > config > default

// But when combining with inference, YOU must handle precedence
inferred := inferFromExtension(filename)
if inferred != "" {
    format = inferred  // inference should beat config default
}
// Unless the user explicitly set the flag
if viper.IsSet("archive-format") {
    format = viper.GetString("archive-format")  // explicit flag wins
}
```

## Testing Strategy

### Always Test Cross-Layer Combinations

```go
func TestConfigDefaultDoesNotOverrideInference(t *testing.T) {
    tests := []struct {
        name      string
        filename  string
        cfgDefault string
        want      string
    }{
        {"inference matches default", "tool.tar.gz", "tar.gz", "tar.gz"},
        {"inference differs from default", "tool.zip", "tar.gz", "zip"},
        {"no inference, default applies", "tool.bin", "tar.gz", "tar.gz"},
        {"no inference, no default", "tool.bin", "", ""},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            cfg := &Config{ArchiveType: tt.cfgDefault}
            result := classify(tt.filename, cfg)
            assert.Equal(t, tt.want, result.Format)
        })
    }
}
```

The critical test case is row 2: inference differs from default. If this test doesn't exist, the bug hides indefinitely.

### Property: Inference Beats Default

Express the invariant as a property: "If inference produces a non-empty value, the final result must equal the inferred value (unless an explicit override is set)."

## Real-World Example

sfetch v0.4.2 had `archiveType: "tar.gz"` as a config default. When downloading `goneat_v0.5.3_windows_amd64.zip`, the file extension inference correctly determined `.zip` format, but the legacy compatibility guard applied `tar.gz` over it. The fix: adding `&& cls.ArchiveFormat == ""` to the guard condition.

This caused Windows CI failures across downstream projects — `tar` was invoked on `.zip` files, producing `exit status 2`.

## Related

- [Cobra CLI Patterns](cobra-cli-patterns.md) - Viper config hierarchy
- [Windows Runner Gotchas](../../cicd/github-actions/windows-runners.md) - Where this bug manifests in CI
- [Cross-Platform Asset Selection](../../cicd/github-actions/cross-platform-asset-selection.md) - Related classification logic
