---
title: "YAML Shell Script Gotchas"
description: "Common pitfalls when writing shell scripts in GitHub Actions YAML"
author: "Claude Opus 4.5"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-01-31"
last_updated: "2026-02-18"
status: "approved"
tags: ["github-actions", "yaml", "shell", "heredoc", "troubleshooting"]
---

# YAML Shell Script Gotchas

GitHub Actions workflows embed shell scripts in YAML files using the `run:` key. This creates opportunities for subtle bugs where YAML parsing interferes with shell script content.

## Heredocs in `run:` Blocks

### The Problem

YAML literal block scalars (`|`) preserve content but require consistent indentation:

```yaml
# THIS IS BROKEN
- name: Create config
  run: |
    cat > config.txt <<'EOF'
registry=https://example.com
auth=false
EOF
```

The heredoc content (`registry=...`, `auth=...`, `EOF`) starts at column 0, breaking the YAML structure. YAML interprets `registry=https://example.com` as a new mapping key.

### actionlint Error

```
.github/workflows/example.yml:10:0: could not parse as YAML: could not find expected ':'
```

### Solutions

#### Option 1: Use `printf` (Recommended)

```yaml
- name: Create config
  run: |
    printf '%s\n' 'registry=https://example.com' 'auth=false' > config.txt
```

Advantages:

- No indentation issues
- Clear and readable
- Works with any content

#### Option 2: Maintain YAML Indentation in Heredoc

```yaml
- name: Create config
  run: |
    cat > config.txt <<'EOF'
    registry=https://example.com
    auth=false
    EOF
```

**Warning**: This writes the file WITH leading spaces:

```
    registry=https://example.com
    auth=false
```

Many config parsers won't accept this.

#### Option 3: Use `<<-` with Tabs (Not Recommended)

```yaml
- name: Create config
  run: |
    cat > config.txt <<-'EOF'
    	registry=https://example.com
    	auth=false
    	EOF
```

The `<<-` operator strips leading **tabs** (not spaces). But:

- YAML editors often convert tabs to spaces
- GitHub's web editor uses spaces
- Mixing tabs/spaces is error-prone

#### Option 4: Use `sed` to Strip Indentation

```yaml
- name: Create config
  run: |
    cat > config.txt <<'EOF' | sed 's/^    //'
        registry=https://example.com
        auth=false
    EOF
```

Works but adds complexity.

## Multi-Line Strings with Special Characters

### Quotes in Shell Commands

```yaml
# BROKEN - YAML sees unbalanced quotes
- run: echo "Hello "World""

# FIXED - escape inner quotes
- run: echo "Hello \"World\""

# OR use single quotes for outer
- run: 'echo "Hello World"'

# OR use literal block
- run: |
    echo "Hello \"World\""
```

### Dollar Signs and Variable Expansion

```yaml
# YAML doesn't expand, but shell does
- run: echo $HOME # Shell expands $HOME

# To prevent shell expansion
- run: echo '$HOME' # Prints literal $HOME

# In double quotes, escape it
- run: echo "\$HOME" # Prints literal $HOME
```

### GitHub Expression Syntax

```yaml
# ${{ }} is evaluated by GitHub BEFORE shell runs
- run: echo "${{ secrets.TOKEN }}" # Token inserted, then shell runs

# To pass literal ${{ }} to shell (rare)
- run: echo '${{ literal }}' # Single quotes prevent GitHub expansion? NO!
# GitHub expressions are ALWAYS evaluated regardless of quotes
```

## Conditional Commands

### `set -e` and Pipelines

```yaml
- run: |
    set -euo pipefail
    # If any command fails, step fails
    some_command | grep pattern  # grep failure = step failure with pipefail
```

Without `pipefail`, only the last command's exit code matters:

```yaml
- run: |
    set -e
    failing_command | cat  # cat succeeds, so step succeeds despite failure!
```

### Conditional Execution

```yaml
# Run command only if file exists
- run: |
    if [ -f config.txt ]; then
      process config.txt
    fi

# Alternative with || true (command can fail without failing step)
- run: |
    rm -f optional_file.txt || true
```

## Shell Selection

Default shell varies by runner:

- Linux/macOS: `bash`
- Windows: `pwsh` (PowerShell)

Explicitly set shell for consistency:

```yaml
- run: |
    echo "bash script"
  shell: bash

- run: |
    Write-Host "PowerShell script"
  shell: pwsh
```

### POSIX sh vs Bash

```yaml
# This uses bash features that don't work in sh
- run: |
    [[ $VAR == "value" ]]  # [[ ]] is bash-only
    echo ${VAR:-default}    # Works in both
  shell: bash # Explicitly require bash

# For maximum portability
- run: |
    [ "$VAR" = "value" ]   # POSIX test
  shell: sh
```

## `curl | bash` Pipe Masking Install Failures

### The Problem

The common `curl URL | bash` pattern for install scripts masks failures because `curl` and `bash` are separate pipeline stages. If the install script downloads successfully but fails during extraction or file placement, `curl`'s exit code is 0 (it delivered the script). With `set -e` alone (no `pipefail`), only the last command's exit code matters. Even with `pipefail`, if the script fails _internally_ without a non-zero exit (e.g., a silent extraction failure), the pipe reports success.

```yaml
# FRAGILE: curl succeeds even if install script fails internally
- run: |
    curl -sSfL "$INSTALL_URL" | bash -s -- --dir "$BINDIR" --yes
    # Next step assumes tool was installed...
    $BINDIR/tool --version  # fails: tool not found
```

### Root Cause

Three things conspire:

1. **Pipeline exit masking** — `curl` exits 0 because the HTTP request succeeded. With `pipefail`, bash's exit code propagates, but only if bash itself exits non-zero.
2. **Silent script failures** — Install scripts may fail during archive extraction or file placement without setting a non-zero exit code (e.g., `tar` extraction failure caught by an internal `|| true`).
3. **No post-install verification** — The pipeline trusts the exit code rather than verifying the binary actually exists.

### Solution

Separate download from execution so each step's exit code is independently checked, and add post-install verification:

```yaml
- run: |
    set -euo pipefail
    # Download the script (curl failure = step failure)
    curl -sSfL "$INSTALL_URL" -o /tmp/install.sh
    # Execute separately (script failure = step failure)
    bash /tmp/install.sh --dir "$BINDIR" --yes
    # Verify the binary actually landed
    if ! command -v tool >/dev/null 2>&1 && [ ! -x "$BINDIR/tool" ]; then
      echo "error: tool installation failed" >&2
      exit 1
    fi
```

**Key principle**: Never trust a piped install script's exit code. Always verify the expected binary exists after installation.

### Discovered In

kitfly v0.2.3 CI — `curl | bash` for sfetch installation silently failed extraction on a Windows ARM64 runner. The install script downloaded and started but extraction produced no binary. The pipeline reported success, and the next bootstrap step failed with "sfetch not found".

## Best Practices

1. **Use `run: |` for multi-line scripts** - clearer than escaped newlines
2. **Avoid heredocs** - use `printf` or `echo` instead
3. **Always `set -euo pipefail`** at script start for early failure
4. **Explicitly set `shell:`** when using bash-specific features
5. **Test with actionlint** before pushing workflow changes
6. **Use `${{ env.VAR }}` for GitHub env vars** in complex expressions

## Validation

Always validate workflows locally before push:

```bash
# Install actionlint
brew install actionlint  # macOS
# or
go install github.com/rhysd/actionlint/cmd/actionlint@latest

# Validate
actionlint .github/workflows/*.yml
```

## Related

- [actionlint](https://github.com/rhysd/actionlint) - Static checker for GitHub Actions
- [shellcheck](https://www.shellcheck.net/) - Shell script linter
- [YAML Specification](https://yaml.org/spec/1.2.2/) - Block scalar rules
