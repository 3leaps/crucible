---
title: "Multi-Org GitHub CLI Auth Guide"
description: "Recommended pattern for using GitHub CLI across multiple GitHub organizations from one workstation without repeated auth switching."
author: "GPT-5"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-03-11"
last_updated: "2026-03-27"
status: "active"
category: "guide"
tags: ["github", "gh", "auth", "direnv", "secrets", "multi-org", "workstation"]
---

# Multi-Org GitHub CLI Auth Guide

This guide recommends a practical pattern for working across multiple GitHub organizations from a single developer machine.

## Problem

`gh` is comfortable when one machine maps to one GitHub identity or one token context. That breaks down when one operator regularly moves between repositories owned by different organizations with different token scope requirements.

Common symptoms:

- repeated `gh auth login` or `gh auth switch`
- commands succeeding in one org and failing in another
- accidental use of the wrong token in the wrong repository
- friction during releases, automation debugging, and admin tasks

This is common in multi-org operating models such as a services firm, a foundation org, or a partner ecosystem that shares maintainers across several GitHub organizations.

## Recommendation

Use directory-scoped environment injection, not repeated interactive login, as the default workflow.

The recommended stack:

1. an org-root directory for each GitHub organization
2. `direnv` to load environment on directory entry
3. a secret manager to provide token material
4. `.envrc` at the org root that exports `GH_TOKEN` and `GITHUB_TOKEN`

## Why This Pattern

GitHub CLI honors `GH_TOKEN` and `GITHUB_TOKEN` as environment-provided credentials. This lets the active repository tree determine credential context without rewriting global auth state.

Benefits:

- automatic context switch when moving between org roots
- no repeated `gh auth login`
- lower risk of using the wrong token in the wrong org
- no token in shell history or process arguments when using a proper secret manager
- works well with a workspace layout organized by org

## Why Not Use `gh auth login` As The Primary Workflow

Interactive login is fine for initial bootstrap or recovery. It is weak as a daily operating pattern in a multi-org environment because:

- it relies on manual switching
- the active context is easy to forget
- scope mismatches surface late, when commands fail
- it increases cognitive load during release and maintenance work

## Why Not Use `GH_CONFIG_DIR` As The Primary Workflow

`GH_CONFIG_DIR` can isolate full GitHub CLI profiles, including config, aliases, and extensions. That is useful when you need separate `gh` personalities.

It is not the best first solution for this problem because:

- the core issue is token context, not full config isolation
- it creates more state to manage
- it adds another switching mechanism on top of repository navigation

Use `GH_CONFIG_DIR` only if you later decide you need org-specific CLI config in addition to org-specific credentials.

## Reference Layout

```text
~/dev/
  org-a/
    .envrc
    repo-1/
    repo-2/
  org-b/
    .envrc
    repo-3/
  org-c/
    .envrc
    repo-4/
```

Each `.envrc` sets credentials for that org root and all nested repositories.

## Example `.envrc` Shape

The exact secret-manager command will vary. The important property is that the token is read from protected storage at shell-entry time rather than copied into shell history.

```sh
# Generic — substitute your secret manager's retrieval command
export GH_TOKEN="$(secret-tool read org-a github token)"
export GITHUB_TOKEN="$GH_TOKEN"
```

```sh
# macOS Keychain example
export GH_TOKEN="$(security find-generic-password -a "$USER" -s "gh-org-a" -w)"
export GITHUB_TOKEN="$GH_TOKEN"
```

```sh
# age-encrypted secret manager example
export GH_TOKEN=$(your-secret-tool get --key GH_TOKEN_ORG_A --reveal)
export GITHUB_TOKEN="$GH_TOKEN"
```

If your secret manager supports process-scoped environment export, that is also acceptable.

## Token Guidance

Use one token per organization or trust boundary.

Guidance:

- prefer least-privilege tokens
- size scopes to the tasks performed in that org
- export both `GH_TOKEN` and `GITHUB_TOKEN`
- do not commit `.envrc`
- keep secret-manager storage outside the repository

## Security Notes

This pattern avoids common exposure paths such as:

- shell history
- command-line arguments visible in `ps`
- accidental copy-paste into notes or scripts

It does not eliminate all exposure risk. The token still exists in the process environment while commands run. That is normal for environment-based auth and should be part of the local workstation threat model.

## Non-Interactive Shell Limitation

direnv hooks only fire in interactive shells. This means `GH_TOKEN` is **not automatically set** in:

- AI coding agents (e.g., Claude Code's Bash tool)
- CI/CD pipeline steps
- cron jobs and scheduled tasks
- MCP servers and agent subprocesses
- scripts invoked via `ssh host 'command'`

In these contexts, the token must be loaded explicitly. Options:

1. **`direnv export bash`**: Run `eval "$(direnv export bash)"` from the org root directory. This works in non-interactive shells but requires direnv to be installed and the `.envrc` to be allowed.
2. **Direct secret manager call**: Invoke the secret manager directly (e.g., `export GH_TOKEN=$(your-secret-tool get --key KEY --reveal)`). Bypasses direnv entirely.
3. **Dedicated resolver tool**: Use a purpose-built CLI that reads the org-to-token mapping from config and emits the correct export statements. This is the most robust option for agent and automation use cases.

For agentic contexts, the resolver approach is recommended — it does not depend on direnv hooks, does not require the agent to understand `.envrc` syntax, and can enforce path-containment checks to prevent token injection from untrusted directories.

## When To Standardize This Pattern

Adopt this as a shared team pattern when:

- one machine is used across several GitHub organizations
- maintainers regularly perform release or admin tasks in multiple orgs
- token scope differs across orgs
- manual auth switching has already caused friction or mistakes

## When Not To Use This Pattern

A simpler model may be enough when:

- the machine works in only one GitHub organization
- all work happens through browser UI and git over SSH
- `gh` is rarely used
- the workstation is ephemeral and fully re-provisioned per engagement

## Implementation Checklist

This is a general bootstrap sequence. Adapt the specific tools to your environment.

### 1. Install direnv

| Platform         | Command                                |
| ---------------- | -------------------------------------- |
| macOS (Homebrew) | `brew install direnv`                  |
| Linux (apt)      | `sudo apt install direnv`              |
| Linux (dnf)      | `sudo dnf install direnv`              |
| Windows (Scoop)  | `scoop install direnv`                 |
| Windows (Winget) | `winget install -e --id direnv.direnv` |

### 2. Hook direnv into your shell

Add the appropriate hook near the end of your shell config, after all other shell initialization but before any prompt setup (e.g., Starship, oh-my-posh).

| Shell      | Hook                                          |
| ---------- | --------------------------------------------- |
| zsh        | `eval "$(direnv hook zsh)"` in `~/.zshrc`     |
| bash       | `eval "$(direnv hook bash)"` in `~/.bashrc`   |
| PowerShell | See [direnv PowerShell setup](#windows-notes) |
| fish       | `direnv hook fish \| source` in `config.fish` |

### 3. Prepare secret storage

Choose one encrypted secret manager. Populate it with one PAT per org. The important properties are:

- tokens are stored encrypted at rest
- retrieval does not expose values in shell history or `ps` output
- the retrieval command can be used in a `$()` subshell within `.envrc`

### 4. Create `.envrc` per org root

Place one `.envrc` at each org root directory. Each file should export `GH_TOKEN` and `GITHUB_TOKEN` using a subshell call to your secret manager. See [Example .envrc Shape](#example-envrc-shape) above.

### 5. Allow each `.envrc`

```bash
direnv allow ~/dev/org-a
direnv allow ~/dev/org-b
```

direnv will not load an `.envrc` until explicitly allowed. Re-allow is required after any edit.

### 6. Verify

From within each org tree, confirm the token resolves:

```bash
cd ~/dev/org-a/any-repo
gh api user --jq .login
```

## SSH and Git Push/Pull

This pattern covers `gh` CLI auth only. For `git push` and `git pull` over SSH, use per-org SSH host aliases in `~/.ssh/config`. The two mechanisms are complementary — SSH aliases handle git transport, and direnv handles `gh` CLI context.

## Windows Notes

direnv supports Windows natively as of v2.33+ and is available through both Scoop and Winget.

**Recommended install path**: Scoop (`scoop install direnv`) is preferred for developer workstations because it manages PATH automatically and integrates well with other developer tools. Winget (`winget install -e --id direnv.direnv`) is a viable alternative if Scoop is not in use.

**Shell compatibility**:

- **PowerShell 7+**: Supported. Add the direnv hook to your `$PROFILE`:

  ```powershell
  Invoke-Expression "$(direnv hook pwsh)"
  ```

  Use PowerShell 7 (pwsh), not Windows PowerShell 5.1.

- **Git Bash / MSYS2**: Supported. Hook as for bash: `eval "$(direnv hook bash)"` in `~/.bashrc`.

- **WSL**: Use the Linux installation method within WSL. The WSL filesystem is separate from the Windows filesystem, so `.envrc` files and secret storage should live inside WSL.

- **cmd.exe**: Not supported. Use PowerShell 7 or Git Bash.

**Secret manager on Windows**: The pattern is the same — use any secret manager that can output a value to stdout for subshell capture. Examples include `1password-cli` (`op read`), `keepassxc-cli`, or PowerShell `SecretManagement` module. Avoid passing tokens as command-line arguments visible in Task Manager.

## Adoption Notes

For an org-specific implementation, create a local operational runbook that defines:

- directory roots
- secret-manager choice
- token naming convention
- bootstrap steps
- verification commands
- rollback path

This guide defines the pattern. Local runbooks should define the implementation.

## References

- GitHub CLI environment variables: https://cli.github.com/manual/gh_help_environment
- GitHub CLI auth login: https://cli.github.com/manual/gh_auth_login
- direnv installation: https://direnv.net/docs/installation.html
- direnv Windows setup: https://github.com/kbstar/direnv-windows-setup
