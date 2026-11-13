---
id: "SecDR-0002"
title: "Secret surface non-disclosure and input isolation"
status: "proposed"
date: "2026-11-13"
author: "devlead"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
deciders: ["@3leapsdave", "cxotech", "entarch", "secrev"]
scope: "Crucible foundation / secret input and observation boundaries"
tags: ["security", "secrets", "application-control", "mcp", "input-isolation"]
relatedDocs:
  - "docs/standards/secret-surface-boundaries.md"
  - "docs/decisions/SecDR-0001-application-controller-authority.md"
---

# SecDR-0002: Secret Surface Non-Disclosure and Input Isolation

## Status

Proposed. Publication and adoption require security review. The companion
[Secret Surface Boundaries](../standards/secret-surface-boundaries.md)
standard remains draft; publishing it does not qualify an implementation.

## Context

Secret-handling libraries and local tools also expose metadata, verification
and ceremony operations. These surfaces require an explicit separation
between value-free control or observation and custody of secret input.

## Decision

Control-plane endpoints, `application-control/v0` results, information sources
and evidence facts, and all MCP messages in both directions (including
elicitation and sampling) MUST remain
value-free. They MUST NOT accept or emit plaintext secret values, decrypted
payloads, private identities, signing keys or seeds, passphrases, PINs,
recovery codes or threshold unseal shares. Only non-secret metadata, policy,
public recipient material and verification facts may cross these surfaces.
Errors, progress and diagnostic output obey the same boundary.

Secret input MUST use a documented `SecretInputPort`: an echo-disabled
controlling TTY, an explicit caller-owned stdin/FD pipe, an owner-only file
outside detected VCS roots with ownership and ACL verification, isolated
hardware/native OS input, or an in-process library/FFI buffer under host
custody. CLI argument values, convenience unlock environment variables,
control/MCP payloads and WebView DOM input MUST NOT carry that material.
An unavailable TTY fails deterministically without blocking.

Graphical surfaces MUST display only value-free state and delegate secret
entry to isolated input ports. Local TUI inspection MAY reveal a single entry
explicitly, strictly in-process on an interactive TTY, with zeroized buffers,
default masking, idle auto-lock, and explicit time-bounded clipboard copy if
offered, with conditional clearing of its own item only (disabled without
safe platform support),
and no network, IPC or MCP listeners.

Local child-execution wrappers MUST exclude unlock material from the child
environment, including fail-closed value-equality checks under aliases, and
SHOULD offer clean-environment allowlisting. Their explicit inherited
file-descriptor/OS-handle allowlist MUST exclude unlock-bearing ports,
including standard input when applicable; descriptor hygiene alone is not
isolation from arbitrary same-user code. External cryptographic helpers
MUST use an explicit executable/path allowlist and a minimal declared
environment excluding unrelated credentials and loader/runtime injection settings,
never input-supplied command strings. Helper streams MUST be explicitly routed and bounded within the same
custody boundary, not inherited ordinary terminal streams or logs by default;
only an allowlisted value-free projection may leave it. Explicit local
inspection follows the companion standard's TUI boundary.

Generated private keys, seeds and unencrypted secret outputs MUST stay
outside detected VCS roots, including ignored paths. Output and temporary/staging files MUST have
verified owner-only access (including ACLs) before secret bytes are written;
existing targets are checked before truncation or writing. This is consistent with the
[3 Leaps OSS Sensitive Local Data Policy](https://github.com/3leaps/oss-policies/blob/main/SENSITIVE-LOCAL-DATA.md).
Encryption or recipient options against an unencrypted target MUST fail
closed unless an explicit conversion verb is selected.

Ordinary CLI reporting and diagnostics remain value-free. Human plaintext
display follows the TUI rule; separately authorized local data-plane exports
require an explicit owner-only file or dedicated caller-owned output port,
never an implicit stdout/stderr dump or an adapter secret-return path.

The companion standard defines the observable rules. Adopters MUST include
automated synthetic-canary controls for non-disclosure across metadata,
errors and logs, plus controls for each input and execution boundary they
expose.

## Consequences

- Secret custody and metadata/verification interfaces have separate contracts.
- Application-control authorization does not waive non-disclosure or input
  isolation, and this record grants no secret-transfer capability.
- Graphical ceremony status and isolated native input can compose without
  placing secret material in a renderer.
- Implementations document host custody and cleanup limits and demonstrate
  conformance rather than infer it from a schema or adapter name.

## References

- [Secret Surface Boundaries](../standards/secret-surface-boundaries.md)
- [SecDR-0001: Application Controller Authority](SecDR-0001-application-controller-authority.md)
- [Portable Application Control and Observation Contract](../standards/application-control-contract.md)
