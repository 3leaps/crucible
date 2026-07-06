---
id: "ADR-0006"
title: "Local Process Telemetry & Control as a Companion Portable Contract"
status: "proposed"
date: "2026-07-06"
last_updated: "2026-07-06"
deciders:
  - "@3leapsdave"
  - "cxotech"
scope: "Crucible foundation / process contracts"
tags:
  - "schemas"
  - "process-control"
  - "telemetry"
  - "observability"
  - "interchange-contract"
relates-to:
  - "docs/standards/data-artifact-contract.md (data-artifact/v0 — the sibling contract)"
  - "crucible ADR-0004 (coverage-attestation — companion-contract precedent)"
  - "crucible ADR-0003 (decision-record taxonomy — vehicle selection)"
  - "crucible ADR-0001 (schema/config versioning — the promotion gate)"
---

# ADR-0006: Local Process Telemetry & Control as a Companion Portable Contract

## Status

**Current Status**: Proposed — a companion portable contract riding its own
ratification gate. It does **not** block any existing contract's freeze.
Graduation Proposed → Accepted is gated on a downstream conforming
implementation (the same discipline applied to `coverage-attestation/v0`).

## Context

`data-artifact/v0` governs **what was produced** — the artifact and its
descriptors. It says nothing about **the producing process**: how a local,
long-running run exposes what it is doing while it runs, and how an operator or
sibling tool reaches in to inquire or steer it.

That gap is filled today by per-tool dialects — ad-hoc status files, bespoke
control sockets, log-tailing conventions — none portable across producers.
Distributed-tracing stacks (OTel collectors, span batching, exporter auth)
answer a _different, larger_ question ("observe a distributed system from the
outside") at a complexity floor most local work neither needs nor can justify.
The common, unmet need is smaller: **a flight recorder and a steering wheel,
not a telescope** — let one operator see and steer local long-running work at a
deliberately minimal floor (append-only files + a local socket, schema-versioned),
with ecosystem compatibility deferred to a config-driven forwarder.

The shapes here are not speculative: a three-spike harness field-validated the
duo end-to-end (bindings under two runtimes; a control loop in a zero-dependency
substrate; a live worker steered over its control socket while a config-driven
sidecar forwarded its event file onward). The schemas and golden fixtures land
from that validation.

## Decision

Establish `contract: process-run/v0` as a **companion portable contract family**
in crucible, sibling to `data-artifact/v0`:

- `docs/standards/process-run-contract.md` — the normative standard (rides its
  review loop at doc-status `draft`, consistent with `data-artifact/v0`; this
  ADR carries the adoption lifecycle).
- `schemas/process-run/v0/` — `contract.json` entry manifest + `process-card`,
  `process-event`, `control-exchange` schemas + golden examples.
- Same L2 identity model as `data-artifact/v0`: a host-less capability token,
  resolved through a trusted `contract.json` entry manifest; instances must not
  embed a schema host as identity.

**Vehicle — Standard + ratifying ADR, not a DDR.** By the ADR-0003 taxonomy a
data-model/schema choice is nominally DDR territory, but the incumbent practice
for portable contracts is a standard ratified by an ADR (ADR-0002 key-material
fingerprint, ADR-0004 coverage-attestation). Consistency with that
contract-ratification lane — one grep wide, per ADR-0003 — outweighs minting the
first-ever DDR, and the contract carries genuinely architectural stance
(local-only transport, fail-open emission, lock-and-key control) beyond a pure
data-model choice.

**Name — `process-run/v0`.** Named for the governed object, like its siblings
(`data-artifact`, `coverage-attestation`): the unit governed is a **run**, and
`run_id` is already the data model's own identity key (card, event envelope, and
control snapshot all carry it), so the family name and the schema agree by
construction. It is neutral between the two co-equal halves — you _observe_ a run
and _steer_ a run — which a telemetry-flavored name would not be. "Plane"-style
names were considered and rejected: _plane_ is load-bearing infrastructure
vocabulary (control/data/management plane = network-exposed surfaces), the
inverse of this contract's no-listener/no-WAN thesis, and it collides with
consumer HTTP-exposure vocabulary. A long-lived serve-mode process instance is a
"run" for this contract's purposes.

**One family, one capability token** for card/events/control. The three objects
are designed against each other (the card points to the event stream and the
control socket; terminal events reconcile against outputs); they version
together, not as three independently-versioned tokens.

Core stance (normative intent, hardened in review):

- **The artifact is the interface for state; a socket exists only where liveness
  is required.** Progress, history, outcomes live in append-only files any tool
  can read; the socket is only for live-process interactions (in-flight inquiry, stop).
- **Fail-open emission.** Telemetry never blocks, slows, or crashes the work it
  describes.
- **Local-only transport.** Events to local files, control over a local socket.
  No WAN listener, no TLS, no PKI, no network attack surface in the producer.
- **Lock-and-key control.** Authorized by an invocation-time key plus filesystem
  permissions — two independent local layers; constant-time verification is
  consumer policy.
- **Payload-open, metadata-governed.** Producer payloads and producer-specific
  verbs stay producer-owned; the card, event envelope, and control exchange that
  travel _between_ tools have closed, versioned semantics.

**Bridge to `data-artifact/v0`.** Terminal events SHOULD carry
`data.artifacts[]` (`artifact_id` + the artifact's `lifecycle` claim) so a run's
outcome links to its outputs. The two claims stay independent: a run's own
states are the event kinds plus `running | stopping | done`; `lifecycle`
(`complete | partial`) remains the _artifact's_ vocabulary. The terminal-event
bridge maps between the two namespaces; it never conflates them. (This is why a
`process-lifecycle` family name was rejected — it would have collided with the
artifact's `lifecycle` field across the very bridge that links them.)

**Substrate-neutral.** The contract was field-validated over both a
framed-channel IPC substrate and a zero-dependency local-socket path, so
conformance does not depend on any specific library. Producer-tooling
enhancements that would make a first-class embedding path are tracked with the
substrate owners; they are not a gate on this contract.

## Consequences

- Consumers gain one portable shape for observing and steering local runs across
  producers — a second CLI invocation, a config-driven sidecar/forwarder, a
  supervisor, or an operator with `tail` and `jq` — instead of per-tool dialects.
- Telemetry ecosystems remain reachable: the event envelope maps to OTLP in a
  downstream forwarder, keeping producers OTLP-free (ecosystem compatibility is a
  deployment-config concern, never a producer concern).
- One more family to carry through ratification — mitigated by arriving with
  end-to-end field validation and a motivating need already in hand, and by
  riding a `proposed` gate that does not couple to any existing freeze.

## Open questions for the review loop

1. **One contract vs three** — card/event/control as one capability token
   (current stance) or three independently-versioned tokens. Current stance: one.
2. **`pause`/`resume` verbs** — deliberately absent from v0 (no demonstrated
   need); confirm or add.
3. **Rotation within a run** — v0 recommends against; large/long runs may force
   the question — decide the continuation convention if so.
4. **Named-pipe (Windows) profile** — UDS semantics are specified; the named-pipe
   mapping needs a platform reviewer.
5. **Heartbeat cadence guidance** — producer-chosen today; consider a card field
   declaring the cadence so consumers can calibrate staleness suspicion.
6. **Key rotation for serve-mode** — out of scope for finite per-run keys;
   confirm the re-key-on-config-reload convention for long-lived `serve`-mode runs.
