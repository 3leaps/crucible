---
title: "Go CLI Patterns with Cobra"
description: "Patterns for building CLI applications with Cobra, Viper, and slog"
author: "Claude"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-29"
last_updated: "2026-01-29"
status: "draft"
tags: ["go", "cobra", "cli", "viper", "slog", "toolchains"]
upstream_source: "fulmenhq/crucible docs/standards/repository-structure/go/cli-cobra.md"
---

# Go CLI Patterns with Cobra

Patterns for building CLI applications with Cobra (commands), Viper (configuration), and slog (logging).

## Project Structure

### Microtool Pattern (Single Focused Tool)

```
cli-tool/
├── cmd/
│   └── tool-name/
│       └── main.go          # Minimal main (delegates to internal/cmd)
├── internal/
│   ├── cmd/                 # Cobra command definitions
│   │   ├── root.go          # Root command + global flags
│   │   ├── version.go       # version subcommand
│   │   └── process.go       # Business commands
│   ├── core/                # Business logic (CLI-agnostic)
│   └── config/              # Configuration handling
├── VERSION
└── Makefile
```

**Key principle**: Separate CLI interface from business logic. Core logic should be usable without Cobra.

## Entry Point Pattern

### main.go (Minimal)

```go
package main

import (
    "os"
    "github.com/example/tool-name/internal/cmd"
)

// Set via ldflags
var (
    version   = "dev"
    commit    = "unknown"
    buildDate = "unknown"
)

func main() {
    cmd.SetVersionInfo(version, commit, buildDate)

    if err := cmd.Execute(); err != nil {
        os.Exit(1)
    }
}
```

### Build with Version Info

```bash
go build -ldflags="-X main.version=1.0.0 \
  -X main.commit=$(git rev-parse --short HEAD) \
  -X main.buildDate=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -o bin/tool-name ./cmd/tool-name
```

## Root Command Pattern

```go
package cmd

import (
    "fmt"
    "os"

    "github.com/spf13/cobra"
    "github.com/spf13/viper"
)

var (
    cfgFile string
    verbose bool

    versionInfo struct {
        Version   string
        Commit    string
        BuildDate string
    }
)

func SetVersionInfo(version, commit, buildDate string) {
    versionInfo.Version = version
    versionInfo.Commit = commit
    versionInfo.BuildDate = buildDate
}

var rootCmd = &cobra.Command{
    Use:   "tool-name",
    Short: "Brief description",
    Long:  `Longer description of the tool.`,
    SilenceUsage:  true,  // Don't show usage on errors
    SilenceErrors: true,  // Handle errors ourselves
}

func Execute() error {
    return rootCmd.Execute()
}

func init() {
    cobra.OnInitialize(initConfig)

    rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file")
    rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "verbose output")

    viper.BindPFlag("verbose", rootCmd.PersistentFlags().Lookup("verbose"))
}

func initConfig() {
    if cfgFile != "" {
        viper.SetConfigFile(cfgFile)
    } else {
        home, err := os.UserHomeDir()
        if err != nil {
            fmt.Fprintf(os.Stderr, "Error: %v\n", err)
            os.Exit(1)
        }

        viper.AddConfigPath(home)
        viper.SetConfigType("yaml")
        viper.SetConfigName(".tool-name")
    }

    viper.SetEnvPrefix("TOOLNAME")
    viper.AutomaticEnv()

    _ = viper.ReadInConfig()  // Ignore if not found
}
```

## Configuration Hierarchy

**Priority** (highest to lowest):

1. Command-line flags
2. Environment variables
3. Config file
4. Defaults

```go
func init() {
    // Flag (highest priority)
    rootCmd.PersistentFlags().IntP("workers", "w", 0, "number of workers")

    // Bind to viper (enables env var and config file)
    viper.BindPFlag("workers", rootCmd.PersistentFlags().Lookup("workers"))

    // Environment variable (TOOLNAME_WORKERS)
    viper.SetEnvPrefix("TOOLNAME")
    viper.AutomaticEnv()

    // Config file loaded in initConfig()
    // Default set in config.Default()
}
```

## Logging with slog

### Setup (internal/utils/logger.go)

```go
package utils

import (
    "log/slog"
    "os"
)

var Logger *slog.Logger

func init() {
    Logger = slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    }))
}

func SetupLogger(verbose bool, level string) {
    var slogLevel slog.Level

    if verbose {
        slogLevel = slog.LevelDebug
    } else {
        switch level {
        case "debug":
            slogLevel = slog.LevelDebug
        case "warn":
            slogLevel = slog.LevelWarn
        case "error":
            slogLevel = slog.LevelError
        default:
            slogLevel = slog.LevelInfo
        }
    }

    Logger = slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{
        Level: slogLevel,
    }))
}
```

### Usage

```go
utils.Logger.Info("Processing target", "target", target, "dry-run", dryRun)
utils.Logger.Warn("Processing completed with issues", "count", len(result.Issues))
utils.Logger.Error("Failed to process", "error", err)
```

**Note**: Logs go to STDERR. Structured data goes to STDOUT.

## Use RunE for Error Handling

```go
// GOOD - Return errors, let Cobra handle them
var myCmd = &cobra.Command{
    RunE: func(cmd *cobra.Command, args []string) error {
        if err := doSomething(); err != nil {
            return fmt.Errorf("operation failed: %w", err)
        }
        return nil
    },
}

// BAD - Manual error handling
var myCmd = &cobra.Command{
    Run: func(cmd *cobra.Command, args []string) {
        if err := doSomething(); err != nil {
            fmt.Fprintf(os.Stderr, "Error: %v\n", err)
            os.Exit(1)
        }
    },
}
```

## Output Formatting

### Support Multiple Formats

```go
func OutputResult(result *Result, format string, outputFile string) error {
    var output []byte
    var err error

    switch format {
    case "json":
        output, err = json.MarshalIndent(result, "", "  ")
    case "yaml":
        output, err = yaml.Marshal(result)
    case "text":
        output = []byte(formatText(result))
    default:
        return fmt.Errorf("unsupported format: %s", format)
    }

    if err != nil {
        return fmt.Errorf("failed to format: %w", err)
    }

    if outputFile != "" {
        return os.WriteFile(outputFile, output, 0644)
    }

    fmt.Println(string(output))
    return nil
}
```

## Makefile Targets

```makefile
BINARY_NAME := tool-name
VERSION := $(shell cat VERSION 2>/dev/null || echo "dev")
COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_DATE := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
LDFLAGS := -X main.version=$(VERSION) -X main.commit=$(COMMIT) -X main.buildDate=$(BUILD_DATE)

build:
	go build -ldflags="$(LDFLAGS)" -o bin/$(BINARY_NAME) ./cmd/$(BINARY_NAME)

build-all:
	GOOS=linux GOARCH=amd64 go build -ldflags="$(LDFLAGS)" -o bin/$(BINARY_NAME)-linux-amd64 ./cmd/$(BINARY_NAME)
	GOOS=darwin GOARCH=amd64 go build -ldflags="$(LDFLAGS)" -o bin/$(BINARY_NAME)-darwin-amd64 ./cmd/$(BINARY_NAME)
	GOOS=darwin GOARCH=arm64 go build -ldflags="$(LDFLAGS)" -o bin/$(BINARY_NAME)-darwin-arm64 ./cmd/$(BINARY_NAME)

test:
	go test -v -race ./...

lint:
	golangci-lint run
```

## Testing Commands

```go
func TestProcessCommand(t *testing.T) {
    tests := []struct {
        name        string
        args        []string
        expectError bool
    }{
        {
            name:        "valid_target",
            args:        []string{"process", "testdata/valid.yaml"},
            expectError: false,
        },
        {
            name:        "missing_target",
            args:        []string{"process"},
            expectError: true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            cmd := rootCmd
            cmd.SetArgs(tt.args)

            err := cmd.Execute()

            if tt.expectError {
                assert.Error(t, err)
            } else {
                assert.NoError(t, err)
            }
        })
    }
}
```

## Checklist for New CLI Projects

- [ ] Cobra for CLI framework
- [ ] Viper for configuration
- [ ] slog for structured logging (to STDERR)
- [ ] Separate cmd/ from internal/cmd/
- [ ] Core business logic in internal/core/
- [ ] Version command with ldflags injection
- [ ] Config file support with validation
- [ ] Output formatting (JSON/YAML/text)
- [ ] Proper exit codes
- [ ] Command tests

## Attribution

Adapted from [FulmenHQ Crucible](https://github.com/fulmenhq/crucible) Go CLI patterns.
