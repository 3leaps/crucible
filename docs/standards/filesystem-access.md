---
title: "Portable Filesystem Access Contract"
description: "Root-relative name admission, held-object access profiles and bounded qualification claims"
category: "standards"
status: "draft"
version: "0.0.0"
lastUpdated: "2026-11-13"
maintainer: "core-standards"
reviewers: ["architecture", "security", "development"]
approvers: ["lead-maintainer"]
tags: ["filesystem", "handles", "containment", "contract"]
content_license: "CC0"
---

# Portable Filesystem Access Contract

## Status and scope

`filesystem-access/v0` is a proposed, experimental vocabulary and conformance
corpus for access relative to a held directory object. The
[schema bundle](../../schemas/filesystem-access/v0/README.md) and
[ADR-0020](../decisions/ADR-0020-filesystem-access-contract.md) accompany this
standard. MUST, MUST NOT and MAY state requirements of the candidate contract.
Adopters pin an exact revision; v0 can change before stabilization.

The operations are root acquisition, bounded regular-file read, exclusive
regular-file creation, bounded non-recursive directory listing, and metadata or
identity inspection of held objects. Recursive walking, replacement, deletion,
publication, durability, storage transactions and authorization policy are outside
this contract. Acquiring a root requires caller authority; a conforming name or
capability report grants no authority.

Schema validation checks structure. The logical evaluator checks authored recipe
expectations. Neither proves native filesystem enforcement, race resistance or
production suitability. Native capability availability and adversarial operation
qualification are separate evidence. The standalone checks are verification tools,
not consumer-linked filesystem implementations, under
[PDR-0006](../decisions/PDR-0006-shipping-charter.md).

## F1 — Names and lexical admission

Caller names are Unicode scalar strings encoded as UTF-8. Implementations MUST
reject invalid UTF-8 and unpaired surrogates without replacement decoding. `/` is
the only separator on every platform. A dedicated admitted-name definition lives
in this family; the general foundation `relativePath` type is not a runtime
containment guarantee.

The following yield `invalid_name` before traversal:

- Empty names, NUL, backslash, leading or trailing `/`, and empty segments.
- Drive, UNC and device prefixes, including drive-relative `C:foo`.
- Reserved Windows device names in any segment, case-insensitively: `CON`,
  `PRN`, `AUX`, `NUL`, `COM1`–`COM9` and `LPT1`–`LPT9`, including extensions
  and trailing spaces or dots. Implementations also refuse the Windows
  superscript-digit device aliases.
- Colon in any segment (including alternate data stream syntax), and a segment
  ending in a space or dot, except the exact `.` and `..` tokens admitted below.
  These conservative portable restrictions prevent platform aliasing; refusal
  does not normalize the caller's name.

Under `no-links/v0`, both `.` and `..` segments yield `invalid_name`. Under
`containment/v0`, `.` denotes the current held directory and `..` is a physical
parent step subject to F3. For reserved-device recognition, strip trailing ASCII spaces and dots from a
segment, take the stem before its first dot, strip trailing ASCII spaces from
that stem, and compare ASCII case-insensitively to the reserved set. This check
also covers the superscript digits ¹, ² and ³ in COM/LPT aliases.
Neither Unicode normalization nor case folding may be
applied to accepted names. Filesystem case and normalization behavior belongs to
the OS directory object. Exact caller spelling remains available for interpretation;
case-insensitive device-name recognition is a refusal check only.

Implementations MUST NOT lexically collapse `..` or pre-canonicalize a request.
For example, `a/../file` must visit `a`; an escaping link there must be refused
before `file` can be opened. A name that is lexically admitted is still subject
to profile, capability, type and bound checks.

Raw request and recipe fields can carry invalid names so implementations can
report `invalid_name`. The admitted-name definition is for the result of lexical
admission, not a requirement to discard negative test cases before evaluation.

## F2 — Trusted root acquisition

`open_root` is a separate trusted admission step. The caller supplies a host
location through a local adapter; portable requests identify that admission by an
opaque reference, not an absolute host path. Data-path profiles start at the
resulting held root directory object. Ancestor components of the trusted host
location are outside the data-path guarantee. Callers needing stronger acquisition
policy must enforce it at admission.

Acquisition MUST refuse a root-leaf symlink by default (`policy_denied` /
`link_refused`); Windows reparse points are refused with `reparse_refused`.
A caller intentionally admitting a symlinked root must resolve and authorize it
explicitly before this operation. There is no implicit follow fallback.

Directory-only, no-follow admission MUST be applied by the open itself, before
post-open metadata checks. On Unix the baseline sequence is
`open(..., O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)`, followed by
`fstat` on the returned descriptor. Each intermediate directory uses the same
constraints relative to a held parent. A platform-specific search-only directory
handle is permitted only with equivalent directory and no-follow enforcement and
its own operation qualification.

On Windows, the directory sequence uses `NtCreateFile` with
`FILE_DIRECTORY_FILE | FILE_OPEN_REPARSE_POINT`, a non-inheritable handle and
parent-relative names for intermediate steps. The opened handle's type and
reparse tag are inspected before use. `FILE_FLAG_BACKUP_SEMANTICS` on a Win32 open
alone does not impose this pre-open directory constraint. Backend evidence must
name the actual API and sequence.

Opening with plain `O_RDONLY` and testing `fstat` afterward is forbidden: a FIFO
substituted at the name can block before inspection. A FIFO, socket, device or
ordinary file at a root or intermediate directory position MUST be refused
promptly as `wrong_type` or `policy_denied` / `special_file`. A backend must distinguish a link from another non-directory using a qualified
non-follow sequence before reporting a link-specific reason. An ambiguous native
open failure, such as `ENOTDIR` from a directory-only no-follow open, may be
reported conservatively as `wrong_type`; it does not prove which guard fired.
Synthetic stable recipes with known link identity use `link_refused`. Resource
cleanup closes every acquired handle on refusal. Native qualification includes timed
FIFO-at-root and FIFO-at-intermediate-component controls; a schema or simulated
FIFO refusal is not that evidence.

If the caller provides an expected pre-open object identity, compare it to the
identity obtained from the opened handle, never to a second path lookup. A
mismatch closes the handle and refuses admission (`io_error`). A cached numeric identity by
itself cannot prove continuity across a period with no retained handle (F6).

## F3 — Resolution profiles

### `containment/v0`

Resolution starts at the held root. Every visited directory object and every
expanded link target MUST stay inside that root at the cell's declared membership
observation point. Relative symlinks are expanded component by component from the
held directory containing the link. A `..` step checks both the current directory
and its physical parent against the held root; stepping above the root fails
immediately with `policy_denied` / `escape`. Absolute targets are refused.
Leaving the root and later re-entering is always an escape.

For each recognized symlink, check and consume its expansion budget before
interpreting the target (an exhausted budget yields `hop_limit` even if the
unread target would be malformed). Decode target bytes without replacement;
malformed encoding or NUL yields `invalid_name`. A rooted POSIX, drive, UNC or
device target yields `policy_denied` / `escape`, before portable separator
checks. Otherwise require F1's relative component grammar, allowing exact `.`
and `..` for physical resolution. Empty targets/components, trailing `/`,
backslash, colon and portable alias violations yield `invalid_name`.
The same target interpretation applies to final links for reads and directory
listing. `stat` operates on a held handle and never follows a newly supplied name.

An upward-relative sibling link is valid: from `a/link -> ../b/file`, the walk
visits `a`, then the root, then `b/file`. For `a/link -> sub/dir`, the name
`a/link/..` visits `a/sub/dir` and its physical parent `a/sub`; it does not return
to `a` by lexical cancellation. Directory requirements apply before later
components: `file/..` cannot skip opening a non-directory.

Symlink expansion has a configurable positive hop budget, default and maximum 40. Attempting the next expansion after that budget yields `policy_denied` /
`hop_limit`. Resolution does not reset the budget for nested targets.

On Windows, relative `IO_REPARSE_TAG_SYMLINK` targets may be followed under these
rules on the admitted volume. Junctions (`IO_REPARSE_TAG_MOUNT_POINT`), absolute
symlinks and unqualified reparse tags are refused; an implementation must never
let an unrecognized tag silently select a different resolution mechanism.

### `no-links/v0`

Every intermediate component is opened as a directory relative to a held parent,
with true no-follow enforcement on that open. The final component is opened
without following links and checked against the requested type. Path-based
`lstat` followed by a normal open is insufficient. Linux kernel enforcement may
use `RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS`; manual backends use qualified
per-component directory-only no-follow opens. Optional `no_xdev` is separate.

On Windows every reparse point is refused (`policy_denied` / `reparse_refused`),
including cloud and virtualization tags. v0 defines no reparse-tag allowlist.
On Unix encountered links yield `policy_denied` / `link_refused`. Exclusive
create's existing-final-entry rule takes precedence as specified in F4.

Neither profile proves file-content provenance, confidentiality against another
writer, hardlink isolation, absence of mount aliases, or an authorization decision.
An in-root hardlink can refer to data also named elsewhere. Additional hardlink,
mode and filesystem policies require explicitly qualified extensions.

## F4 — Operations, bounds and result semantics

| Operation          | Required semantics                                                                                                                               |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `open_root`        | Trusted acquisition under F2; return a held directory reference.                                                                                 |
| `open_read`        | Resolve under the requested profile; open a regular file, enforce `max_bytes` on bytes actually read, and refuse overflow with `bound_exceeded`. |
| `create_exclusive` | Resolve an existing parent under the profile; create a regular file only if the final entry is absent. No automatic parent creation.             |
| `read_dir`         | Resolve one directory; observe its immediate entries, bounded by `max_entries`; no recursion.                                                    |
| `stat`             | Inspect a currently held handle, with its lifetime generation; never re-lookup a name.                                                           |
| `same_object`      | Compare raw object identities of currently held handles under F6.                                                                                |

The JSON request/result vocabulary describes operation metadata and outcomes.
It is not an RPC transport or a file-content encoding. Adapters deliver read
bytes through their local API and bind the reported byte length to those bytes.
Opaque root and handle references are meaningful only in the implementation's
live local reference table; accepting their string shape does not authorize
access or make them transferable capabilities.

`open_read` MUST refuse directories (`wrong_type`) and special objects
(`policy_denied` / `special_file`, or `wrong_type`) before a blocking read.
A Unix leaf-open sequence includes `O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC`, then
`fstat` verifies regular-file type before non-blocking mode is cleared. Failure to clear that mode closes the
handle and refuses the read with `io_error`. Relative
links permitted by containment are resolved first. Windows uses a qualified
handle-relative non-directory no-follow sequence plus reparse and device/type
checks. A pre-read size stat alone cannot enforce `max_bytes` if the file grows;
read at most the permitted bytes plus a bounded overflow observation. Refusal
MUST NOT be returned as a successful truncated read.

For `create_exclusive`, acquire the parent under the profile and perform the final
open with `O_CREAT | O_EXCL | O_NOFOLLOW` or the platform equivalent
(`NtCreateFile` with `FILE_CREATE | FILE_OPEN_REPARSE_POINT` on Windows).
Under **both** profiles any existing final entry, including a dangling link,
yields `already_exists`. Do not follow it, create its target, truncate it, or
mutate another existing entry. Bounds and unsupported requested guarantees are
checked before mutation. A failure that cannot establish whether a mutation
occurred yields `unknown_mutation_outcome`; automatic blind retry is forbidden. Native qualification injects a failure
after a create may have happened and checks this outcome.
Exclusive creation promises neither durability nor transactional rollback.

`read_dir` reports link/reparse entries as observations (`symlink` /
`reparse_point`) even under `no-links/v0`; observing an entry is not traversal.
Observed kind never authorizes reopening that entry without fresh checks. Entry
names are raw representable scalar names, not necessarily admitted traversal
names: do not silently omit a reserved name. Non-UTF-8 Unix names fail closed as
`invalid_name` or `io_error`, without lossy conversion. `.` and `..` directory
bookkeeping entries are excluded. The limit counts actual reported entries;
overflow yields `bound_exceeded`, never an apparently complete partial listing.
Order is unspecified and listings need not be snapshots under concurrent change.
If invalid encoding and overflow coexist, the first observed fault may determine
the error; native mixed-fault directories have no single portable error priority.
Reference cases isolate these faults.

## F5 — Capability selection and claim boundaries

Each qualified cell identifies OS, architecture, filesystem scope, backend,
operation, profile, adversary, membership observation point, mechanism and
evidence references. A report is a claim requiring independent verification;
well-formed evidence references alone prove nothing. Availability probes show
that an API or flag can be invoked. Qualification requires negative controls that
exercise its claimed behavior, including deterministic temporal controls for a
concurrent claim.

- `stable_tree`: directory ancestry, links and mount topology do not change
  during the qualified resolution and operation interval. Manual Unix and
  Windows walkers are restricted to this adversary in v0.
- `concurrent_rename_resistant`: requires a qualified atomic kernel-enforced
  operation. In v0, a Linux `openat2` cell is eligible only for the specific
  operation and observation point actually enforced and tested. A backend name
  or successful syscall probe does not confer this guarantee.

The observation point MUST distinguish parent resolution from the full operation.
A parent safely resolved by one syscall can be moved before a subsequent create
through its handle. Such a cell may claim creation in that admitted parent
object; it MUST NOT claim atomic containment of the later create. Post-operation
ancestry checks cannot undo a mutation. Held results do not promise descendants
remain under the root after later renames. Renaming the held root itself preserves
that object's identity and does not bind it to its old host path.

If the requested profile, adversary, operation or capability is unavailable, return
`unsupported_capability` before acting. No silent downgrade is allowed. In
particular, failed `openat2` availability, seccomp restrictions or an unqualified
network filesystem cannot silently select a weaker walker. `EPERM` alone does
not prove a seccomp denial; `E2BIG` is not authority to drop constraints. Retries
of transient failures such as `EAGAIN` are bounded and preserve all constraints.

`capabilities.no_xdev: true` requests mount-boundary enforcement, including
same-device bind mounts. It is optional, not an implicit profile invariant.
Linux may enforce it with `RESOLVE_NO_XDEV` or a separately qualified mount-ID
sequence (`statx` / `STATX_MNT_ID`). Device or volume equality alone is
insufficient. An unqualified cell returns `unsupported_capability`; a verified
crossing yields `policy_denied` / `cross_device`. Mount-ID availability alone
does not upgrade a manual resolver's adversary qualification.

## F6 — Held-handle identity and lifetimes

Unix identity is the raw `(st_dev, st_ino)` pair. Windows identity is the raw
`(volume_serial, file_id_128)` pair, without hashing or random fallbacks. Wire
encodings preserve the full native width without floating-point rounding.
`stat` inspects a held handle. `same_object` compares compatible raw identities
from held handles; it does not compare path spellings or file contents.

At least one handle must remain open throughout an asserted object's continuity
interval. After all handles close, an inode or file ID may be reused.
Implementation-issued generations are bound to live local handle references;
callers may carry them but cannot manufacture or revive them. They prevent
comparison of stale handle references and are a boundary on valid comparison, **never evidence** that a newly opened object is
the previously closed one. A stale or mismatched handle generation is refused;
matching cached numeric IDs does not rehabilitate it. Identity namespaces must
also match: IDs from different hosts, volumes or incompatible identity schemes
cannot be equated by dropping fields.

## F7 — Errors and validation layers

The closed category vocabulary is `invalid_name`, `policy_denied`,
`unsupported_capability`, `not_found`, `already_exists`, `wrong_type`,
`bound_exceeded`, `io_error`, and `unknown_mutation_outcome`. `policy_denied`
has a reason from `escape`, `link_refused`, `reparse_refused`, `special_file`,
`cross_device`, `hop_limit`; other categories do not borrow policy reasons.
Adapters return each result in association with exactly one live request;
this family does not define a detached response-correlation protocol. A result
without that association must not be used to infer held-handle continuity.
Results are bound to their request operation and identify success or failure
unambiguously. Success must carry only that operation's result payload. A schema
reject is not a successfully executed policy refusal. `unknown_mutation_outcome`
is confined to `create_exclusive`. Held-handle `stat` and `same_object` have no
name-admission or byte/entry-bound stage: stale references yield `io_error`, and
an unsupported identity mechanism yields `unsupported_capability`.

Perform shape validation, lexical/handle-reference validation, capability
selection, resolution and operation checks in that order. Within an operation,
refuse on the first visited violation; do not explore beyond an escape to find a
later success. The existing final-entry rule for exclusive create is evaluated
only after a valid parent is admitted, without inspecting the final entry's type
or link payload. For no-links reads/listing, link refusal precedes target type
checks; for containment reads/listing, link-target admission and escape checks
precede checks on the resolved object's type. Where the standard allows alternative
native error mappings (for example a special-file type refusal), an adapter
states its mapping and its recipe expectations; it must not treat arbitrary I/O
failure as proof that the intended security guard fired.

Diagnostics MUST NOT contain file contents or host paths outside the admitted
root. Portable error records use closed vocabulary and opaque references; native
debugging details require a separately authorized local channel.

## F8 — Corpus and qualification

The versioned `cases.json` uses declarative fixture recipes for directories,
regular files, links and outside-root sentinels. No filesystem symlinks are
checked into this repository. A native adapter materializes only synthetic
fixtures in a fresh private workspace and cleans them up afterward. Recipe
locations and link-target text have separate grammars; test materialization must
never interpret hostile target text as authority to create a host object.

Path-operation cases use the flat `name`, `profile`, bounds and `request`
capability fields as their sole request source; an embedded `access_request` is
forbidden. Root-admission and held-handle cases instead require an
operation-matched `access_request` and forbid duplicate flat request/bound fields.
For these cases, `name` and `profile` are descriptive fixture labels only;
neither drives a path re-lookup. A root `root_ref` resolves through the case's
explicit `runtime.root_bindings` table to a synthetic recipe location and its
optional observed identity. An unmapped root reference yields `io_error`;
duplicate bindings are invalid test data. Capability requirements come only
from the embedded request.

The Python controls exercise lexical admission, physical link resolution,
exclusive-create non-mutation, bounded reads/listings, capability refusals and
held-reference lifetimes. Expectations are authored data; the evaluator must not
read an expected verdict to decide an outcome. Mutation controls establish that
broken behavior and malformed claims are detected. Native FIFO probes, where
available, exercise directory-opening refusal and non-blocking leaf type checks
on the current platform.
They do not qualify a full resolver or any concurrent adversary.

Promotion beyond proposed/experimental requires independent agreement with the
corpus and consumer operation qualification. Adopters additionally test native
Windows reparse behavior, same-device bind mounts, unsupported fallback,
root/ancestor moves, moved-parent create, handle lifetime and deterministic
concurrent replacement under each claimed cell. This repository's model results
must never be relabeled as that platform evidence.
