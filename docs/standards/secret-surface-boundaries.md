---
title: "Secret Surface Boundaries"
description: "Value-free control, observation and graphical surfaces; isolated secret input, local inspection, child execution and key custody"
category: "standards"
status: "draft"
version: "0.1.0"
date: "2026-11-13"
lastUpdated: "2026-11-13"
author: "devlead"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
maintainer: "core-standards"
reviewers: ["secrev", "entarch", "cxotech", "devrev"]
approvers: ["lead-maintainer"]
tags: ["security", "secrets", "application-control", "mcp", "input-isolation"]
content_license: "CC0"
supervised_by: "@3leapsdave"
relatedDocs:
  - "docs/decisions/SecDR-0002-secret-surface-non-disclosure-and-input-isolation.md"
  - "docs/standards/application-control-contract.md"
  - "https://github.com/3leaps/oss-policies/blob/main/SENSITIVE-LOCAL-DATA.md"
audience: "maintainers"
---

# Secret Surface Boundaries

MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119. This draft defines
boundaries for products handling secrets through libraries, CLIs, control
planes, Model Context Protocol (MCP) adapters and user interfaces. It adds no
secret-transfer operation to `application-control/v0` and grants no authority
to read or deliver a secret.

## 1. Value-free control and observation

Control-plane endpoints, `application-control/v0` operation results,
information sources and evidence facts, and all MCP messages in both directions (including tools, resources,
prompts, elicitation requests/responses and sampling requests/responses)
MUST NOT return, echo, stream or serialize:

- plaintext secret values or decrypted secret payload bytes;
- private encryption identities, signing private keys or seeds; or
- passphrases, PINs, recovery codes or threshold unseal shares.

This applies to success and failure paths, progress events, subscriptions,
diagnostics and logs. Wrapping a secret in JSON, an encoding or an error object
does not make it metadata. These surfaces MUST NOT carry secret-bearing
requests either (§2).

Permitted outputs are value-free metadata, policy and verification facts:
project or entry identifiers, logical folder paths, credential types,
non-secret descriptions, schema or codec validation results, public recipient
keys and fingerprints, recipient-set drift status and signature verification
outcomes. A field's name does not establish that its contents are non-secret;
implementations MUST construct an allowlisted projection rather than return
raw secret documents or unconstrained user-supplied descriptions. Public keys
and identifiers remain subject to the product's authorization and privacy
policy.

These boundaries keep secret material out of model context, transcripts,
prompt caches, MCP host telemetry, IPC peer logs and crash reports.
Redaction after such a surface receives the material does not satisfy input
isolation.

## 2. SecretInputPort: explicit input custody

`SecretInputPort` names a trust boundary, not a prescribed wire schema or API.
Plaintext secret input and unlock material MUST NOT be accepted through CLI
flags or positional arguments, dedicated convenience environment variables
for unlock material, control-plane payloads, any MCP message (including elicitation responses), or browser/WebView
DOM input and keystroke event streams. Examples of prohibited environment
channels are `<APP>_PASSPHRASE` and `<APP>_IDENTITY` carrying unlock bytes.
An explicit non-secret descriptor or file path may select an input port; it
MUST NOT itself contain the secret or be treated as proof of access authority.

An implementation MAY accept the following ports, with custody documented for
each supported port:

| Port | Required boundary |
|---|---|
| Controlling terminal | Interactive TTY, echo disabled while entering secrets and restored on exit; absent controlling TTY fails fast with a deterministic non-zero exit, never an unattended prompt or hang |
| Standard input or file descriptor | Explicit caller-supplied pipe; the caller controls both ends and prevents logging or forwarding into a control/MCP adapter |
| Owner-only file | Outside every detected VCS repository root; POSIX mode `0600`, correct owner and no extended ACL grants; use equivalent owner-only access controls on other platforms |
| Hardware or native OS input | Physical token gesture, token PIN entry or native credential dialog isolated from WebView DOM and model context |
| Library or FFI buffer | Embedding host owns in-process custody, bounded lifetime and cleanup; the buffer is never marshalled through a control-plane or MCP request |

File input MUST validate the object actually opened, refuse links or ambiguous
ownership/access checks, and fail closed if it cannot establish the required
custody. On systems where mode `0600` can coexist with extended ACL grants,
checking mode bits alone is insufficient. A native dialog that hands secret
bytes back to a WebView does not meet the hardware/native port boundary.

## 3. Graphical interfaces and local terminal inspection

Graphical inspection and ceremony interfaces ("glass"), including browser and
WebView views, MUST remain value-free. They MAY display inventories, logical
paths, public recipients and fingerprints, signature status, drift posture,
and ceremony or quorum progress. Unlock and secret-entry gestures MUST use
an isolated port from §2. Decrypted secret values MUST NOT enter the DOM or
renderer heap, including hidden controls, accessibility state or developer
diagnostics.

A local terminal UI MAY offer human inspection of decrypted entries only
strictly in-process on an interactive TTY. It MUST use buffers that are
zeroized on release, mask values by default, require explicit single-entry
reveal, auto-lock after idle time, and expose no network, IPC or MCP listener.
If clipboard copying is offered, it MUST be explicit and time-bounded and
use platform-supported ownership or item-identity checks to clear only the
item it placed at expiry. It MUST NOT overwrite later clipboard content.
Without a safe conditional-clear mechanism, clipboard copy MUST be disabled;
losing ownership ends the operation without a claim that retained copies
were cleared. Documentation MUST identify the clipboard's OS trust boundary.
It MUST NOT promise erasure of copies already retained by terminal capture,
clipboard history or another process. Secrets MUST NOT be placed in debug
formatters or ordinary logs. Managed-runtime or FFI copies MUST have an
explicit lifetime and cleanup policy; unsupported erasure guarantees MUST NOT
be advertised.

The TUI exception does not authorize graphical reveal or machine-readable
secret inspection. Non-interactive invocation MUST fail rather than silently
switch to a plaintext dump.

## 4. Child execution and helpers

A locally authorized wrapper MAY inject scoped application secrets into a
child environment as a separate data-plane operation. This is not an
application-control or MCP secret-returning operation, nor permission to
invoke arbitrary executables through those surfaces.

Before spawning, such a wrapper MUST remove all unlock credential variables
from the child environment. It MUST also compare candidate child environment
values with unlock material and fail closed on equality, including an alias
under another variable name. It MUST NOT echo rejected values. Wrappers
SHOULD offer an explicit `--clean-env` mode with allowlisted pass-through so
unrelated ambient secrets are not inherited. Documentation MUST identify
which scoped application values are injected and distinguish them from
unlock material, which is never injected.

Wrappers MUST use an explicit inherited file-descriptor/OS-handle allowlist
and exclude every unlock-bearing input port from the scoped application
child, including inherited standard input when it carried unlock material.
Unused descriptors MUST be closed or non-inheritable before spawn; standard
streams MUST be rebound to a declared non-unlock channel as needed. These
rules prevent implicit transfer, not access by arbitrary same-user code to
other readable files or process memory. Products requiring isolation from an
untrusted child MUST establish a separate OS access boundary and state its
limits. Cryptographic helpers receive only the ports explicitly required by
their separately defined custody contract below.

External cryptographic and hardware helpers MUST be resolved through an
explicit executable/path allowlist, with an optional pinned digest check.
Implementations MUST construct a minimal helper-environment allowlist and
MUST NOT execute untrusted command strings embedded in inputs. Only declared
helper settings and explicitly selected custody-port descriptors may remain;
unrelated ambient credentials and dynamic-loader/runtime injection settings
MUST be excluded. A helper that requires secret material receives it only
through its documented §2 port, never a convenience unlock environment
variable. Ambient `PATH` lookup alone does not establish helper trust. Helper stdin, stdout, stderr and failure
diagnostics MUST be explicitly routed and bounded within the same
secret-custody boundary, never inherited ordinary terminal streams or logs
by default. Only an allowlisted value-free projection may leave that
boundary. Any human secret-entry gesture uses an isolated §2 port; any raw
secret inspection requires the explicit local inspection boundary in §3.
Raw helper output MUST NOT be forwarded to control, MCP or graphical surfaces.

## 5. Non-repository custody and explicit conversion

Tools MUST refuse to write generated private keys, signing seeds or
unencrypted secret outputs inside any detected VCS repository root, including
ignored and untracked paths. Implementations MUST evaluate the resolved
destination, including linked parents, rather than rely on `.gitignore` or
the process working directory. Uncertain repository or destination checks
MUST fail closed. This applies the
[3 Leaps OSS Sensitive Local Data Policy](https://github.com/3leaps/oss-policies/blob/main/SENSITIVE-LOCAL-DATA.md)
to secret custody: sensitive material stays outside working trees entirely.

Before writing any secret bytes, tools MUST establish and verify owner-only
access to output and temporary/staging files: POSIX mode `0600`, correct
owner and no extended ACL grants, or equivalent owner-only controls on other
platforms. New files MUST be created exclusively with those protections in
place; existing targets require verification of the opened object before
truncation or writing. Link, ownership, permission or ACL uncertainty MUST
refuse the write. Atomic replacement MUST preserve these protections across
staging and final destination; repairing permissions after writing secret
bytes is insufficient.

When encryption or recipient options are supplied against an unencrypted
target, the operation MUST fail closed unless the caller selects an explicit
conversion verb. An ordinary write MUST NOT silently retain plaintext or
change storage protection.

### Explicit local data-plane output

Ordinary CLI reporting, text/JSON metadata, stderr and diagnostics MUST remain
value-free, including redirected or captured output. Local human plaintext
display is limited to the explicit interactive TUI reveal boundary in §3.
A separately authorized local data-plane export MAY write plaintext to a
caller-selected owner-only file under this section or an explicit dedicated
caller-owned output FD/pipe whose trust and capture boundary is documented.
It MUST NOT silently use ordinary stdout/stderr, or switch to a dump when a
TTY or output port is unavailable. It MUST fail closed unless the destination
and authority are explicit. This export path is separate from metadata and
TUI inspection and grants no new operation authority. Control-plane, MCP and
graphical adapters MUST NOT use it to receive or forward secret bytes.

## 6. Observable conformance

Implementations exposing CLI metadata (`--format json`), control-plane, TUI
or MCP adapters MUST include automated canary-secret non-disclosure controls.
Known synthetic canaries MUST be absent from metadata stdout, JSON/MCP
responses, ordinary text stdout, stderr, progress, errors and diagnostic
logs, including redirected output, malformed-input and helper-failure paths.
Every supported MCP method, including elicitation and sampling when present,
MUST obey and exercise the same input/output refusal boundary. Authorized
local TUI single-entry reveal is tested separately; it does not exempt the TUI's metadata, errors or logs.

Controls MUST also exercise rejected input channels, absent-TTY failure,
owner/ACL and repository-file refusal for input, output and staging,
unlock-variable alias equality, excluded inherited unlock descriptors/handles
(including stdin), helper allowlist refusal and plaintext-conversion refusal
where applicable. A synthetic-canary child control MUST demonstrate that an
unlock port is not inherited even when the environment is empty. A helper
environment sentinel MUST prove that undeclared ambient credentials and
loader settings are excluded. Explicit data-plane export tests MUST verify
authorized destination custody and refusal of implicit stdout/stderr dumps.
Tests use synthetic material and MUST NOT collect real credentials. An
adapter's schema validation alone does not establish this behavioral
conformance. This document specifies controls for adopters; it does not claim
that an existing product has passed them.
