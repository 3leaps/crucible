# Native process observation — provider profile

**Status:** proposed draft provider profile, not a qualified OS adapter or an
authorization credential. `profile.json` pins this specification and
`evidence.schema.json`; evidence descriptors pin `profile.json` by exact SHA-256
revision.

## Purpose and authority boundary

Record a read-only OS observation of one process incarnation and its selected
execution-context facts so local or downstream verifiers can distinguish live
continuity from process exit, zombie retention, PID reuse, namespace mismatch,
context drift or lost visibility.

Observation-only reports using this profile omit `evaluator`, keep `assessments`
empty, and cite the canonical payload digest from an `os-observation` evidence
descriptor. An observation payload does not authenticate the caller, prove
physical-machine uniqueness, separate processes sharing an account, or grant
signal or launch authority.

Live OS continuity handles (`pidfd` on Linux, `kqueue` `EVFILT_PROC` `NOTE_EXIT`
on macOS, or equivalent non-destructive OS synchronization handles) are private
in-memory adapter resources. They require no signal permission for acquisition,
expose no signal API under this profile, and are **never serialized** into
portable JSON payloads or treated as bearer proof across process boundaries.
Adapter probe outcomes for live handle mechanisms may be reported in the report
`capabilities` array.

## Fact status vocabulary and report capability mapping

Payload fact wrappers use a seven-state `status` vocabulary with a strict 1:1
bijection to `report.schema.json` `capabilities[].status`:

| Payload fact `status` | Report `capabilities[].status` | Value / digest field | `reason` field | Required meaning                                                                                     |
| --------------------- | ------------------------------ | -------------------- | -------------- | ---------------------------------------------------------------------------------------------------- |
| `observed`            | `available`                    | Required             | Optional       | Probe succeeded and passed pre/post incarnation bracketing                                           |
| `not-present`         | `not-present`                  | Forbidden            | Required       | Observation scope establishes that the optional facility or target object is absent                  |
| `inaccessible`        | `inaccessible`                 | Forbidden            | Required       | Kernel or OS access control denied visibility (`EPERM`, `EACCES`, `ptrace_may_access`, `hidepid`)    |
| `unsupported`         | `unsupported`                  | Forbidden            | Required       | Platform family or adapter cell does not implement the concept (for example PID namespaces on macOS) |
| `not-probed`          | `not-probed`                   | Forbidden            | Required       | Fact omitted by default opt-in disclosure policy or explicit caller probe budget                     |
| `error`               | `error`                        | Forbidden            | Required       | Unexpected OS error, malformed kernel surface, or bracketing race prevented a trustworthy read       |
| `unknown`             | `unknown`                      | Forbidden            | Required       | Visibility is indeterminate under the current mount, container or observer scope                     |

Adapters must preserve `error` and `unknown` distinctly and never collapse them
into `inaccessible`, `unsupported`, `zombie` or process exit. In particular, a
failed metadata read following a liveness probe must never be reported as
`process_state.value = "zombie"`; zombie state requires direct kernel state
observation (`SZOMB` on macOS, state `Z` on Linux) bracketed to the target
incarnation.

## Host scope, clone behavior and disclosure policy

`process.host_scope` carries `{namespace, value, derivation, stability,
clone_behavior}` and an optional report-local `identifier_ref`. It is a
**descriptor supplied across an explicit caller boundary, not authentication**.

- **Caller trust and stability:** Strict incarnation `match` requires consumer
  policy to establish that `host_scope` came from an accepted local caller or
  authenticated report source **and** that `stability` is one of `boot`,
  `installation`, `enrollment` or `device`. Untrusted caller scope or
  `stability` equal to `unknown` or `process` yields
  `insufficient:unestablished-host-scope`, never `match`. When both observations
  carry trusted, established host scopes whose `(namespace, value, derivation)`
  tuples differ, comparison yields `mismatch:host-scope-mismatch`.
- **Clone, snapshot restore and reinstall behavior:** `clone_behavior` equal to
  `copyable` or `unknown` discloses that VM cloning, golden-image copying or
  live snapshot restore can duplicate `host_scope` across distinct instances; a
  restored live snapshot can also duplicate `boot_id` and `start_identity` in
  both branches until reboot. Reinstall or provisioning reset under
  `installation` or `regenerated` produces a distinct `value` and compares as
  `mismatch:host-scope-mismatch`.
- **Default opt-in probe policy and low-entropy hashing:** Default collection
  probes incarnation facts (`boot_id`, `pid_numbering_namespace`,
  `target_pid_namespace`, `pid`, `process_state`, `start_identity`) and
  `execution_context.security_principal` when permitted by caller policy. The
  four digest facts (`namespace_context_digest`, `executable_digest`,
  `arguments_digest`, `security_context_digest`) default to `not-probed` unless
  explicitly requested by the caller. Raw `argv` vectors, `environ` entries,
  filesystem paths, working directories, hardware serials and unscoped native
  machine identifiers are excluded from portable payloads.
- **No confidentiality from unsalted digests:** Domain-separated SHA-256 context
  digests provide deterministic equality and integrity binding only. Low-entropy
  inputs (short command lines, predictable flags, common UIDs or standard binary
  images) remain guessable offline. Callers must not export `arguments_digest`
  across untrusted boundaries when command-line arguments could carry secrets,
  and applications must not pass secrets via `argv`.

When opted in, context digests use SHA-256 over exact length-delimited,
domain-separated byte preimages (`u32_be` denotes unsigned 32-bit big-endian
byte length or element count):

- `arguments_digest`:
  `SHA256("3leaps.native-process-observation.arguments.v0\0" || u32_be(argc) || for arg in argv { u32_be(len(arg)) || arg })`
- `executable_digest`:
  `SHA256("3leaps.native-process-observation.executable-image.v0\0" || image_bytes)`
  over verified readable executable file bytes (never a pathname hash; retains
  residual `no-running-memory-attestation` because an on-disk file read does not
  attest mapped pages after unlink or `memfd` execution).
- `namespace_context_digest`:
  `SHA256("3leaps.native-process-observation.namespaces.v0\0" || u32_be(count) || for (kind, ns_id) in sorted_ascii { u32_be(len(kind)) || kind || u32_be(len(ns_id)) || ns_id })`
- `security_context_digest`:
  `SHA256("3leaps.native-process-observation.security-context.v0\0" || u32_be(len(scheme)) || scheme || "\0" || canonical_context_bytes)`

## Numeric PID bounds, Linux namespace views and start-identity sub-profiles

`process.pid` is a canonical positive decimal string in `1..=2147483647`
(`i32::MAX`, no leading zeros). Signalling sentinels (`0`, negative values, and
values above `2147483647`) are rejected by schema and collector input checks.

### Linux PID numbering namespace vs target PID namespace

On Linux, numeric PIDs are relative to a PID namespace: `pidfd_open(pid, 0)`
resolves `pid` in the calling task's active PID namespace, whereas `/proc/<pid>`
resolves `<pid>` in the PID namespace bound to that `procfs` mount at mount time
(see Linux kernel `procfs` namespace documentation). Inspecting
`/proc/<pid>/ns/pid` identifies only `target_pid_namespace` (the innermost PID
namespace of the target process), **not** `pid_numbering_namespace` (the
namespace in which `process.pid` was resolved).

Before emitting a Linux observation or opening a `pidfd`, a collector must
establish a verified numbering view on its opened `/proc` root descriptor:

1. `fstatfs(proc_fd)` reports `PROC_SUPER_MAGIC` (`0x9fa0`).
2. `readlinkat(proc_fd, "self")` parses as a canonical positive integer equal to
   `getpid()`.
3. `/proc/self/status` `NSpid:` contains **exactly one** decimal PID token and
   that token equals `getpid()`, proving that the `procfs` superblock namespace
   and the caller's active PID namespace are the same namespace (eliminating
   both ancestor bind-mount coincidence where ancestor and child PIDs happen to
   share the same number and foreign descendant mounts).
4. `fstatat(proc_fd, "self/ns/pid")` yields `(st_dev, st_ino)` encoded as
   `pidns:<dev>:<ino>` for `pid_numbering_namespace`.

If `/proc` is missing, not `procfs`, bind-mounted from an ancestor or foreign
PID namespace (`NSpid` depth != 1 or `self` link mismatch), or unreadable, the
collector must **refuse** to emit an unverified PID mapping rather than guessing.
`target_pid_namespace` is read separately from `fstatat(proc_fd, "<pid>/ns/pid")`
(`pidns:<dev>:<ino>`); when kernel `ptrace_may_access` denies `/proc/<pid>/ns/pid`,
`target_pid_namespace` records `status: "inaccessible"` while preserving
`pid_numbering_namespace`.

### Start-identity sub-profiles

| Sub-profile `id`                                                     | Platform | `boot_id` grammar & source                                              | PID namespace rule                                                                   | `start_identity.value` grammar & range                                       | Clock behavior & collision residual                                                                                   |
| -------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `urn:3leaps:identity-evidence:start-identity:linux-procfs-stat:v0`   | `linux`  | Lowercase UUID from `/proc/sys/kernel/random/boot_id`                   | Both `pid_numbering_namespace` and `target_pid_namespace` required `observed`        | Unsigned 64-bit decimal ticks (`0..=18446744073709551615`), `stat` field 22  | Monotonic boot ticks (`USER_HZ`, typically 10 ms); immune to wall-clock steps; residual `sub-tick-pid-reuse-window`   |
| `urn:3leaps:identity-evidence:start-identity:macos-kinfo-starttime:v0` | `macos`  | Lowercase UUID from `sysctl("kern.bootsessionuuid")`                    | Both `pid_numbering_namespace` and `target_pid_namespace` required `unsupported`     | `<sec>.<usec>` (`sec` in `0..=9223372036854775807`, 6-digit `000000..999999`) | XNU `p_starttime` (`microtime` wall clock at `fork`); residual `wall-clock-step-and-microsecond-reuse-window`         |
| `urn:3leaps:identity-evidence:start-identity:windows-filetime:v0`    | `windows`| Reserved (not qualified in initial draft)                               | Reserved `unsupported`                                                               | Reserved unsigned 64-bit 100 ns `FILETIME` decimal                           | Reserved; verifiers must return `insufficient:unsupported-start-identity-profile` until a Windows cell is qualified   |

On macOS, `status: "unsupported"` on `pid_numbering_namespace` and
`target_pid_namespace` is a profile-defined not-applicable dimension for
`macos-kinfo-starttime:v0` only. It is **never a wildcard** that matches a Linux
observation or excuses missing Linux namespace facts.

### Pre/post incarnation bracketing and non-atomicity

Reading multiple syscalls or `/proc` files is not atomic. Collectors must
bracket every observation snapshot and every continuity-handle registration:

1. Capture pre-snapshot $S_0 = (\text{numbering\_view}_0, \text{boot\_id}_0,
   \text{target\_pid\_ns}_0, \text{pid}, \text{start\_identity}_0,
   \text{state}_0)$.
2. Collect requested `execution_context` facts and, when requested, open the
   read-only continuity handle (`pidfd_open(pid, 0)` on Linux; `kqueue`
   `EVFILT_PROC` `NOTE_EXIT` registration on macOS — omit `NOTE_EXITSTATUS`
   unless separately qualified so status-collection restrictions never masquerade
   as process exit).
3. Capture post-snapshot $S_1$ over the same incarnation tuple (and re-read
   `security_principal` when collected from a separate syscall/file).
4. Emit `observer.bracketed = true` only when $S_0 = S_1$. If the target exited
   or changed incarnation between $S_0$ and $S_1$, discard the partial read
   rather than emitting a cross-incarnation composite.

Even when $S_0 = S_1$, residual windows remain: in-place context changes within
the same incarnation (`setuid`, `prctl`, `unshare`) between intermediate reads
and post-observation TOCTOU between $S_1$ and a consumer's downstream action
(`post-observation-toctou-window`).

## Deterministic comparison rules

Given `baseline` and `candidate` payloads under `native-process-observation:v0`
and consumer policy `{host_scope_trusted, require_live, required_context_facts,
detect_observed_context_drift}`, comparison evaluates in strict order without
wall-clock tolerance or prefix shortcuts:

1. **Profile and bracketing:** Both payloads must match the pinned
   `native-process-observation:v0` profile; if either has
   `observer.bracketed != true`, return `insufficient:unbracketed-observation`.
   If either `start_identity.profile` is unknown or reserved
   (`windows-filetime:v0`), return
   `insufficient:unsupported-start-identity-profile`.
2. **Host scope:** If caller scope trust is not established or either
   `host_scope.stability` is `unknown` or `process`, return
   `insufficient:unestablished-host-scope`. If `(namespace, value, derivation)`
   differs, return `mismatch:host-scope-mismatch`.
3. **Boot identity:** If either `boot_id.status != "observed"`, return
   `insufficient:missing-boot-id`. If `boot_id.value` differs (or violates the
   sub-profile UUID grammar), return `mismatch:boot-id-mismatch` (or
   `insufficient:invalid-boot-id`).
4. **Start-identity sub-profile compatibility:** If either
   `start_identity.status != "observed"`, return
   `insufficient:missing-start-identity`. If `baseline.start_identity.profile !=
   candidate.start_identity.profile`, return
   `insufficient:incompatible-start-identity-profile`.
5. **PID namespaces:**
   - Under `linux-procfs-stat:v0`, if either `pid_numbering_namespace` is not
     `observed`, return `insufficient:missing-pid-numbering-namespace`; if either
     `target_pid_namespace` is not `observed`, return
     `insufficient:missing-target-pid-namespace`. If `target_pid_namespace.value`
     differs, return `mismatch:target-pid-namespace-mismatch`. If
     `pid_numbering_namespace.value` differs, return
     `insufficient:pid-numbering-namespace-mismatch` (numeric `pid` values from
     different numbering namespaces are never compared directly).
   - Under `macos-kinfo-starttime:v0`, both namespace facts on both observations
     must have `status == "unsupported"`; any other status returns
     `insufficient:invalid-macos-pid-namespace-status`.
6. **PID and start identity:** If `baseline.pid != candidate.pid`, return
   `mismatch:pid-mismatch`. Validate `start_identity.value` against the
   sub-profile integer/decimal range; if `baseline.start_identity.value !=
   candidate.start_identity.value`, return `mismatch:start-identity-mismatch`.
7. **Process state:** If either `process_state.status != "observed"`, return
   `insufficient:missing-process-state`. When `require_live` is true and
   `candidate.process_state.value != "live"`, return `mismatch:process-not-live`.
8. **Execution context:** For each fact in `required_context_facts`, if either
   observation has `status != "observed"`, return
   `insufficient:missing-context-<fact>`; if the observed values/digests differ,
   return `mismatch:context-changed-<fact>`. When `detect_observed_context_drift`
   is true, any `execution_context` fact that is `observed` in both observations
   with unequal value/digest returns `mismatch:context-changed-<fact>`.
9. Otherwise return `match`.

## Composition with `local-process-session:v0`

`local-process-session:v0` requires an observed `pid_namespace` string and all
five `execution_context` fields unconditionally. Consumers must **not**
substitute this profile's narrower `process` object directly or invent sentinel
strings, empty hashes or null values for unavailable native fields.

Instead, an evaluator building a `local-process-session:v0` report imports the
observation report through `input_reports` (preserving collection time and
provenance) and runs a fail-closed projection adapter that produces the
`local-process-session:v0` `process` sub-object **only** when:

- `observer.bracketed` is `true` and `process_state` is `observed` as `"live"`;
- `host_scope` is trusted by consumer policy and has `stability` in `{boot,
  installation, enrollment, device}`, projecting `<namespace>/<value>`;
- `boot_id` and `start_identity` are both `observed` under an accepted
  sub-profile;
- `pid_numbering_namespace` and `target_pid_namespace` are both `observed` and
  equal (establishing a single unambiguous `pid_namespace` string for `pid`);
  and
- all five `execution_context` facts (`security_principal`,
  `namespace_context_digest`, `executable_digest`, `arguments_digest`,
  `security_context_digest`) have `status == "observed"`.

When any predicate above is unmet (including macOS observations where PID
namespaces are `unsupported`, or default-policy observations where
`arguments_digest` is `not-probed`), projection into `local-process-session:v0`
refuses cleanly while the standalone `native-process-observation:v0` report
remains valid for consumers whose policy accepts software-only process
reobservation without those unavailable dimensions.
