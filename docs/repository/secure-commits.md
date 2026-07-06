---
title: "Secure Commit Policy"
description: "Commit message standards for security-sensitive repositories"
author: "Claude Opus 4.5"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2024-12-25"
status: "draft"
tags: ["security", "commits", "policy"]
---

# Secure Commit Policy

**Canonical URL** (hosted site planned — v0.1.x): `https://crucible.3leaps.dev/repository/secure-commits`

Commit message standards for security-sensitive repositories that prevent inadvertent disclosure of vulnerability details.

## Overview

This policy extends [commit-style.md](commit-style.md) for repositories designated as **security-sensitive**. It balances transparency (clear commit history) with responsible disclosure (no exploit roadmaps).

**Core principle**: Describe the **functional improvement**, not the **vulnerability context**.

## When This Policy Applies

This policy is **mandatory** for repositories that:

1. Handle authentication, authorization, or cryptography
2. Process untrusted input (parsers, network handlers, file processors)
3. Are explicitly designated security-sensitive in their `AGENTS.md`

### Designating a Repository

Add to `AGENTS.md`:

```markdown
## Security Policy

This repository is designated **security-sensitive**.

All commits MUST follow the [Secure Commit Policy](https://crucible.3leaps.dev/repository/secure-commits).

Reviewers: Verify commit messages before merge.
```

This designation:

- Signals to developers and AI agents that heightened care is required
- Enables tooling enforcement
- Creates review accountability

## The Functional vs Contextual Rule

Focus on the **technical state** of the code, not the **attack scenario**.

| Aspect       | Functional (Do This)             | Contextual (Avoid This)                      |
| ------------ | -------------------------------- | -------------------------------------------- |
| **Focus**    | New constraint or logic          | The failure or attack                        |
| **Language** | Neutral, engineering-centric     | Alarming security terminology                |
| **Example**  | "Ensure input is validated"      | "Stop attackers from injecting code"         |
| **Refs**     | Public issue references (`#402`) | CVE numbers in commit title (pre-disclosure) |

### Good Examples

```
fix(parser): add bounds checking to input handling

Ensures processing terminates on malformed data.

Ref: #101
```

```
fix(auth): implement output encoding for error messages

Ensures all user-provided strings are escaped before rendering.
Updates error handler to use standard sanitization.

Ref: #882
```

```
fix(net): limit concurrent connections per host

Adds configurable ceiling to prevent resource exhaustion.
```

### Bad Examples (Attacker-Friendly)

```
fix: prevent remote code execution via buffer overflow in parser
```

```
fix(auth): fix XSS vulnerability that allows cookie theft

Fixes CVE-2024-1234. An attacker could use a crafted URL to steal session tokens.
```

```
fix(auth): patch SQL injection in login query (was vulnerable to ' OR 1=1 --)
```

## Restricted Keywords

Avoid these terms in commit messages for security fixes. Use neutral alternatives.

| Restricted Term             | Neutral Alternative                       |
| --------------------------- | ----------------------------------------- |
| vulnerability, exploit, bug | issue, logic, behavior, case              |
| SQL injection               | parameterized query, input sanitization   |
| XSS, cross-site scripting   | output encoding, HTML escaping            |
| buffer overflow             | bounds checking, memory safety            |
| RCE, remote code execution  | input validation, instruction filtering   |
| bypass, hole, leak          | edge case, state management, consistency  |
| attack, attacker, malicious | unexpected input, edge case, invalid data |

**Note**: These terms are appropriate in security advisories, CVE descriptions, and internal documentation—just not in public commit messages before disclosure.

## The Pointer Method

We do not use "security through obscurity." We ensure transparency by linking to restricted-access systems for full context.

1. **Commit header**: Neutral technical description
2. **Commit body**: Technical logic of the fix
3. **Commit footer**: Pointer to internal advisory

```
fix(parser): add length validation to header processing

Implements maximum length check before parsing.
Moves allocation to fixed buffer size.

Ref: SEC-NNN
Security-Advisory: ACME-YYYY-NNN
```

After public disclosure, commits may be updated (via squash or amend during PR) to include CVE references.

## Prohibited Content

The following must **never** appear in commit messages:

| Category         | Examples                                            |
| ---------------- | --------------------------------------------------- |
| PoC payloads     | `<script>alert(1)</script>`, SQL strings            |
| Secrets          | API keys, tokens, passwords (even test ones)        |
| PII / user data  | Real user data, log snippets with identifiable info |
| Exploit analysis | Detailed attack vectors, reproduction steps         |

## Enforcement

### Layer 1: Visibility

**AGENTS.md callout** ensures AI agents and developers see the policy:

```markdown
## Security Policy

⚠️ This repository is **security-sensitive**.

Before committing, review the [Secure Commit Policy](https://crucible.3leaps.dev/repository/secure-commits).

Checklist:

- [ ] Commit message uses functional language (not vulnerability context)
- [ ] No restricted keywords in commit header
- [ ] No PoC payloads, secrets, or exploit details
- [ ] Internal reference included (Ref: SEC-XXX)
```

### Layer 2: Pre-commit Hooks

Use `commitlint` with custom rules to block restricted keywords:

```javascript
// commitlint.config.js
module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "subject-restricted-keywords": [2, "never"],
  },
  plugins: [
    {
      rules: {
        "subject-restricted-keywords": ({ subject }) => {
          const restricted = [
            /vulnerab/i,
            /exploit/i,
            /injection/i,
            /xss/i,
            /overflow/i,
            /rce/i,
            /bypass/i,
            /attack/i,
          ];
          const found = restricted.filter((r) => r.test(subject));
          return [
            found.length === 0,
            `Commit subject contains restricted security term(s). Use neutral language per secure-commits policy.`,
          ];
        },
      },
    },
  ],
};
```

### Layer 3: CI Gate

Add to GitHub Actions workflow:

```yaml
- name: Check commit messages
  run: |
    RESTRICTED="vulnerability|exploit|injection|xss|overflow|rce|bypass|attack"
    if git log --format=%s origin/main..HEAD | grep -iE "$RESTRICTED"; then
      echo "::error::Commit message contains restricted security terms"
      echo "See: https://crucible.3leaps.dev/repository/secure-commits"
      exit 1
    fi
```

### Layer 4: PR Review

PR templates for security-sensitive repos should include:

```markdown
## Security Review

- [ ] Commit messages follow [Secure Commit Policy](https://crucible.3leaps.dev/repository/secure-commits)
- [ ] No vulnerability details in commit messages or PR description
- [ ] Internal security reference included if applicable
```

Reviewers are responsible for auditing commit message language as strictly as the code itself.

### Layer 5: Squash on Merge

Squash development commits when merging to main/release branches. This:

- Consolidates messy development history into clean functional commits
- Provides a final opportunity to craft appropriate commit messages
- Ensures only reviewed messages reach protected branches

## CVE and Disclosure Timeline

| Phase               | Commit Message Guidance                              |
| ------------------- | ---------------------------------------------------- |
| **Pre-disclosure**  | Neutral language only. No CVE, no vulnerability type |
| **Embargo period**  | Same as pre-disclosure                               |
| **Post-disclosure** | May add CVE reference in footer                      |
| **Advisory**        | Full details go in security advisory, not git log    |

For embargoed fixes:

- Use neutral messages initially
- After disclosure, update via squash or add follow-up commit with CVE reference

## Industry References

This policy aligns with:

- **SECOM Convention** (Security Commit Message Convention) - Structured security commit format
- **CERT Coordinated Vulnerability Disclosure** - Responsible disclosure practices
- **OpenSSF Best Practices** - Open Source Security Foundation guidelines
- **Conventional Commits** - Base commit format specification

## Integration with Other Standards

| Standard                                  | Relationship                                      |
| ----------------------------------------- | ------------------------------------------------- |
| [commit-style.md](commit-style.md)        | This policy extends commit-style for secure repos |
| [secrev role](../catalog/roles/secrev.md) | secrev agents should enforce this policy          |
| [agents.md](agents.md)                    | AGENTS.md carries the security designation        |

## References

- [SECOM: A Convention for Security Commit Messages](https://doi.org/10.1145/3524842.3528459)
- [CERT Guide to Coordinated Vulnerability Disclosure](https://vuls.cert.org/confluence/display/CVD)
- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [OpenSSF Security Scorecards](https://securityscorecards.dev/)
