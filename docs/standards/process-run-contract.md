---
title: "Local Process Telemetry & Control Contract"
description: "Portable contract for observing and steering local long-running processes — append-only event streams, card rendezvous, and token-gated control channels, without collector or network complexity"
category: "standards"
status: "draft"
version: "0.0.0"
lastUpdated: "2026-07-06"
maintainer: "core-standards"
reviewers: ["architecture", "security", "operations"]
approvers: ["lead-maintainer"]
tags: ["telemetry", "process-control", "contract", "observability", "ipc", "interoperability"]
content_license: "CC0"
relatedDocs:
  - "docs/standards/data-artifact-contract.md"
  - "docs/observability/logging-baseline.md"
audience: "implementers"
---

# Local Process Telemetry & Control Contract

This draft defines the portable contract identified by
`contract: process-run/v0`.

The contract describes how a local long-running process — started from a CLI,
a service control plane, or a scheduler — exposes **what it is doing** (an
append-only event stream) and **how to reach it** (a token-gated local control
channel), so that any conforming consumer — a second CLI invocation, a
config-driven sidecar/forwarder, a supervisor, or an operator with `tail` and
`jq` — can observe and steer it without knowing which producer created it.

Most tools need a **flight recorder and a steering wheel, not a telescope**.
Distributed-tracing stacks (OpenTelemetry collectors, span batching, exporter
auth) answer "observe a distributed system from outside." This contract
answers the smaller, more common question — "let one operator see and steer
local long-running work" — at a deliberately minimal complexity floor: files
and a local socket, schema-versioned. Telemetry ecosystems remain reachable:
the event envelope is mappable to OTLP by a downstream forwarder (see
Relationship To Other Contracts), so ecosystem compatibility is a
_deployment config concern_, never a producer concern.

This is not an orchestrator, a durable-execution runner, a message bus, a
log-shipping pipeline, or a metrics database. Producers keep their native
payloads and producer-specific profiles. The portable contract governs the
metadata that travels between processes: the card, the event envelope, and the
control exchange.

## Design Stance

- **The artifact is the interface for state; a socket exists only where
  liveness is required.** Progress, history, and outcomes live in append-only
  files any tool can read. The socket exists solely for interactions that
  need a live process on the other end (inquiry of in-flight state, stop).
- **Fail-open emission.** Telemetry must never block, slow, or crash the work
  it describes. A full disk, a missing directory, or an absent consumer
  degrades telemetry, never the pipeline.
- **Sidecar-optional.** Nothing about a conforming producer knows or cares
  whether anything is tailing its events. Forwarding to chat, email, OTLP, or
  anywhere else is a consumer deployment concern.
- **Local-only transport.** Events go to local files; control goes over a
  local socket. There is no WAN listener, no TLS, no PKI, and no network
  attack surface in the producer. Remote reach, if any, is a consumer
  (bridge) concern with its own authentication.
- **Lock-and-key control.** Control is authorized by an invocation-time key
  plus filesystem permissions — two independent local layers. Deployments
  layer stronger boundaries by where they host the process, not by adding
  protocol complexity.
- **Payload-open, metadata-governed.** The `data` payload of events and the
  `result` of producer-specific verbs are producer-owned. The envelope,
  card, and exchange shapes that travel between tools have closed, versioned
  semantics.
- **Fail closed on control, fail open on telemetry.** A malformed or
  unauthorized control request is rejected. A telemetry problem is absorbed.

## Capability And Versioning

Process cards MUST carry the portable contract capability string:

```json
{
  "capabilities": ["contract: process-run/v0"]
}
```

The capability string is host-less. Instances MUST NOT embed a schema host or
URL as the contract identity. Consumers resolve the capability to a trusted
`contract.json` manifest, verify its `capability`, and load the relative
`entry_schema` (`process-card.schema.json`). Resolution MUST fail closed when
the manifest is missing, the capability does not match, or the entry schema is
missing. Direct `$id` lookup remains valid for schema-aware tooling, but it is
not the contract-entry mechanism.

Event lines and control exchanges do not repeat the capability token; the card
is the discovery root that binds a run's streams and channels to the contract
version.

### Evolution Rules

Additive changes are allowed within this `v0` draft when older consumers
either ignore the new field or fail closed safely.

Breaking changes include:

- changing the meaning of an existing field;
- weakening the default control posture (token required, owner-only
  permissions, unknown-verb rejection);
- making a previously optional field load-bearing without a capability or
  version boundary;
- changing terminal-event or staleness semantics;
- renaming fields without a profile mapping or alias.

Unknown core event kinds, verbs, or state values MUST fail closed in
consumers that act on them (a forwarder MAY pass unknown events through; a
supervisor MUST NOT act on an unknown state).

## Governed Objects

### Process Card

The card is the discovery root for one running process: a small JSON file
written at startup that says _who I am, where my events are, and how to reach
me_. Schema: `process-card.schema.json`.

Required responsibilities:

- identify the run (`run_id`) and the portable contract capability;
- identify the process with the **(pid, started_at) pair** — pid alone is
  reusable by the OS and MUST NOT be trusted as identity;
- identify the producer (name, version, optional profile);
- point at the telemetry stream and/or the control channel (at least one).

Rules:

- The card and its directory are **owner-only** (`0700` directory, `0600`
  files). The card carries the _path_ of the key file, never the key.
- The card is **ephemeral**: the producer writes it at startup and removes it
  on clean exit. Consumers MUST treat a card whose `(pid, started_at)` no
  longer matches a live process as **stale** and MAY sweep it. A stale card
  is normal (crash, SIGKILL, power loss) — sweeping is housekeeping, not an
  error.
- Cards live in a per-deployment **runtime directory** under
  `<runtime>/proc/<run_id>/`. The runtime directory location is
  producer-configured (documented, e.g., flag > env var > platform runtime
  dir). Note: Unix socket paths have a low platform length limit
  (~104 bytes on macOS, ~108 on Linux) — runtime directories SHOULD be
  short-pathed.

### Process Event Stream

An append-only NDJSON file, one contract-shaped envelope per line. Schema:
`process-event.schema.json`.

Envelope: `ts`, `event`, `run_id`, `seq` (monotonic per run), `severity`
(`TRACE|DEBUG|INFO|WARN|ERROR|FATAL`), `pid`, optional correlation
(`context_id`, `trace_id`, `span_id`), optional `producer`, and the
producer-owned `data` payload.

Core event kinds and their contract semantics:

| Kind            | Semantics                                                                                                                                                     |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `started`       | First event of a run. SHOULD carry `producer` and the work envelope (e.g. totals) in `data`.                                                                  |
| `heartbeat`     | Liveness at a producer-chosen cadence. Consumers MAY treat missed heartbeats as suspicion, not death — the card's `(pid, started_at)` check is the authority. |
| `progress`      | Work advanced. SHOULD carry `data.done` / `data.total`.                                                                                                       |
| `completed`     | Terminal: finished successfully.                                                                                                                              |
| `canceled`      | Terminal: stopped by request or signal. SHOULD carry `data.reason`.                                                                                           |
| `failed`        | Terminal: died on error. SHOULD carry `data.reason` / error detail.                                                                                           |
| `control_audit` | A control-channel action occurred (accepted or denied). SHOULD carry `data.verb`, `data.outcome`.                                                             |

Producer-specific kinds use the `x-` prefix. Exactly one terminal event ends
a run's stream; nothing follows it.

Emission rules:

- **Append-only**; one JSON object per line; no rewrites.
- **Fail-open**: emission failure is absorbed (optionally counted), never
  propagated to the work.
- The stream is the durable record and outlives the card. Retention/rotation
  is producer-configured; if a stream rotates, the producer MUST emit a
  `started`-anchored continuation convention in its profile (v0 recommends:
  don't rotate within a run).

### Control Exchange

Line-delimited JSON request/response over a **local socket** (Unix domain
socket; platform named pipe where UDS is unavailable). Schema:
`control-exchange.schema.json`.

Request: `{token, verb, args?, request_id?}`. Response:
`{ok, result? | error, request_id?}`.

Core verbs and their contract semantics:

| Verb       | Semantics                                                                                                                                                    |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `describe` | Returns the card (static identity + capabilities).                                                                                                           |
| `status`   | Returns a live snapshot: `{run_id, state: running\|stopping\|done, progress?, ...}`.                                                                         |
| `stop`     | Requests termination. `args.mode`: `graceful` (default — finish the current unit, emit `canceled`, clean up) or `force` (immediate terminal event and exit). |

Producer-specific verbs use the `x-` prefix and MUST be listed in the card's
`control.verbs`.

## Protection Model

Two independent local layers, both mandatory:

1. **Filesystem**: runtime directory `0700`; card, key file, and socket
   owner-only (`0600`/default-restrictive socket). On platforms with peer
   credentials, producers MAY additionally check the connecting UID.
2. **Lock-and-key token**: a per-invocation key, generated by the producer or
   supplied by the invoker, stored only in the owner-only key file (and the
   invoker's hand). Every request presents it; the producer compares in
   constant time. Failure returns exactly `"unauthorized"` (no
   wrong-vs-unknown distinction) and SHOULD emit a `control_audit` event.

Explicit non-goals of the protection model: no network authentication, no
TLS/PKI, no user management, no rate limiting beyond what the producer
chooses. The threat model is same-host hygiene (accidental cross-talk,
other-user access, log-scraping of secrets), not a hostile network. Anything
stronger belongs to the deployment boundary (who may log into the host, or
what a remote bridge in front of the socket requires).

Signals remain the out-of-band fallback: a conforming producer also handles
SIGINT/SIGTERM gracefully (platform conventions such as the Ctrl-C double-tap
apply), and a supervisor whose control channel is dead MAY escalate
terminate→kill on the process group. The in-band `stop` verb is preferred
because it is authorized, auditable, and answers back.

## Attach Semantics (Consumers / Forwarders)

A consumer attaching to an event stream MUST choose an explicit attach mode:

| Mode              | Meaning                                                                                             |
| ----------------- | --------------------------------------------------------------------------------------------------- |
| `beginning`       | Replay the whole stream, then follow. Correct for durable collection; noisy for notification sinks. |
| `end`             | Follow new events only. Correct default for chat/notification bridges.                              |
| `since <ts\|seq>` | Replay from a point, then follow.                                                                   |

Forwarders SHOULD checkpoint read positions so restarts neither lose nor
replay events. Forwarders with unreliable sinks (e.g., a chat webhook
returning a non-retriable error) SHOULD route rejected events to a local
dead-letter file rather than dropping silently.

## Relationship To Other Contracts

- **`contract: data-artifact/v0`** — the sibling that governs _what was
  produced_. This contract governs _the producing process_. The bridge:
  terminal events SHOULD carry `data.artifacts[]` (`artifact_id` + the
  artifact's `lifecycle` claim, per the artifact contract's vocabulary) so a
  run's outcome links to its outputs' descriptors. A process `completed`
  claim and an artifact `complete` claim remain independent statements.
- **OpenTelemetry** — the envelope maps to OTLP logs (and `trace_id`/
  `span_id` pass through) so a forwarder can export to any OTel pipeline.
  The mapping lives in the forwarder, keeping producers OTLP-free:
  `ts`→`timeUnixNano`, `severity`→`severityText/Number`, `event` + `data`→
  `body/attributes`, `run_id`/`context_id`→resource attributes.
- **Logging baselines** — the envelope's severity enum and correlation-id
  conventions follow the common structured-logging practice so events and
  logs join cleanly downstream.

## Validation Requirements

- Producers MUST validate their own cards against the entry schema at
  startup (a producer that cannot describe itself correctly must not start
  serving control).
- Consumers MUST validate the card before using either pointer, and SHOULD
  validate event lines and control exchanges when acting on them (a
  pass-through forwarder MAY skip line validation).
- Reference fixtures live in `schemas/process-run/v0/examples/`; conforming
  implementations SHOULD test against them as goldens.

## Naming (decided 2026-07-06)

**`process-run`** — named for the governed object, like its siblings
(`data-artifact`, `coverage-attestation`): the unit this contract governs is a
**run**, and `run_id` is already the data model's own identity key (card,
event envelope, and control snapshot all carry it), so the name and the schema
agree by construction. It is also neutral between the two co-equal halves —
you observe a run and steer a run — which a telemetry-flavored name would not
be. "Plane"-style names were considered and rejected: plane is load-bearing
infrastructure vocabulary (control/data/management plane = network-exposed
surfaces), and this contract's thesis is the inverse.

**A long-lived serve-mode process instance is a "run"** for this contract's
purposes: it has a `run_id`, a card, a stream, and a channel exactly like a
bounded job; only its terminal event is further away.

## Review-Loop Items Before Freeze

- **One contract vs three**: card/event/control as one capability token
  (current draft) or three independently-versioned tokens. Current stance:
  one — the three objects are designed against each other.
- **`pause`/`resume` verbs**: deliberately absent from v0 (no demonstrated
  need); confirm or add.
- **Rotation within a run**: v0 recommends against; large/long runs may force
  the question — decide the continuation convention if so.
- **Named-pipe (Windows) profile**: UDS semantics are specified; the named
  pipe mapping needs a platform reviewer.
- **Heartbeat cadence guidance**: producer-chosen today; consider a card
  field declaring the cadence so consumers can calibrate suspicion.
- **Key rotation**: out of scope for per-run keys (runs are finite); confirm
  that long-lived `serve`-mode processes re-key on config reload.
