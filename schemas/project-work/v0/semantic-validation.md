# Project work v0 semantic validation

These rules apply after structural validation against the project-work v0
schemas. JSON Schema checks shape only; the rules below span documents or compare
against the clock, so `make check` does **not** prove them and consumers MUST
run them.

**No executable check exists in this repo.** SEM-P01 through SEM-P07 are
specified here only. `scripts/test-project-work-controls.sh` covers structural
examples and rejects; nothing in this repository resolves a seat, reads a clock,
or compares `check_by` with `expires`.

The party model is described in
[`docs/standards/project-work-contract.md`](../../../docs/standards/project-work-contract.md#agent-and-run-parties).

## Rules

| Rule    | Required check                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SEM-P01 | An `agent` id on any party (packet `owner` or `requested_by`, project-state `owner`, ledger `actor`, `decider`) MUST resolve to a seat in the adopter's seat registry. An id with no matching seat is refused, not treated as an opaque name. `role` is not checked against the registry: it is the hat for this work.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| SEM-P02 | A `run` owner MUST NOT own a packet at or after its authoritative `expires` (see SEM-P07). On lapse, apply the order below.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| SEM-P03 | A `run` `parent` that is an agent seat id (`agent-…`) MUST resolve under SEM-P01. A `parent` that is a person id resolves only if the adopter's identity source knows it; this contract defines no such source. Parent existence alone does not prove delegation; see SEM-P07.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| SEM-P04 | A `run` is never a `requested_by`, a `decider`, or a project-state `owner`, and never chains: no `parent` is a run id. The schema enforces these structurally; a consumer that builds party records by another route MUST apply the same refusal.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| SEM-P05 | `check_by` and `expires` are compared as instants, not strings. A packet whose owner is a `run` MUST have `check_by` strictly before the run's authoritative `expires`. The schema enforces only that `check_by` is present (not in `done` or `cancelled`); the ordering is this rule. Producers and validators MUST enforce this at write. A consumer reading older data SHOULD flag a violation rather than refuse it. Exempt: packets in `done` or `cancelled`. See SEM-P02 for what lapse does.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| SEM-P06 | A ledger line whose `actor` is a `run` MUST have `ts` strictly before that run's authoritative `expires` (SEM-P07), not merely the `expires` string carried on that line in isolation. A consumer MUST refuse lines at or after the authoritative `expires`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| SEM-P07 | Each `run` `id` (`run-<ULID>`) names one bounded execution with an immutable `(parent, expires, role)` binding (`expires` compared as an instant; `role` includes whether `role` is set or omitted). The authoritative binding comes from the adopter's run/session record if present, or otherwise from the first admitted record (packet `owner` or ledger `actor`) for that `run` `id` in the consumer's authoritative admitted packet/journal set (never an untrusted or partial replica encountered out of order; if the authoritative binding is unavailable or unresolved when evaluating a partial slice, treat the binding as unknown and refuse until resolved). Every occurrence of that `run` `id` MUST match its authoritative `(parent, expires, role)` binding; any packet or ledger line that rebinds `parent`, extends or alters `expires`, or changes `role` for an existing `run` `id` MUST be refused. Renewing or extending work beyond `expires` requires issuing a **new** `run` `id`. |

## SEM-P02: run expiry order

At or after the run's authoritative `expires` (SEM-P07), the packet is no longer
the run's. The consumer MUST NOT dispatch the packet to the run or accept status
for it from the run, and then:

1. **Return to the parent if it resolves and its owner record is complete.**
   - **Person parent:** If `parent` is a person id and resolves in the adopter's
     identity source (SEM-P03), the new owner is `{kind: "person", id: parent}`.
   - **Agent parent:** If `parent` is an agent seat id (`agent-…`) that resolves
     under SEM-P01, constructing `{kind: "agent", id: parent, role}` requires a
     deterministic work `role`:
     1. Use the run's explicit `role` if set on the run owner;
     2. Otherwise, use the unambiguous work `role` bound to `parent` for this
        packet in the consumer's prior accepted packet/journal history (for
        example, the `role` worn by `parent` when it delegated or previously
        owned the packet, or in the adopter's run-delegation record).
     3. If the run omitted `role` and the consumer holds no unambiguous
        work-role binding for `parent` on this packet, the consumer MUST NOT
        guess a seat default or emit an invalid role-less `agent` owner; step 1
        does not apply and the consumer MUST fall through to step 2.
2. **Else escalate** to the packet's `escalation.default` (a role slug): the new
   owner is `{kind: "role", id: <escalation.default>}`.
3. **Else** (the parent cannot take ownership under step 1 and the packet has no
   `escalation.default`), no owner can be assigned. The packet stays lapsed and
   is surfaced to the consumer's operator.

**Recording the change.** Record the owner change as a control record of kind
`decision`: `decider` is the party reassigning, `affects` is `[<packet id>]`,
and `summary` names the expired run and the new owner. No structured field
carries the new owner, so prose in `summary` is the only link. That is a **v1
gap**: a future version should give an owner change a structured home.

**Lifecycle at expiry.**

- `active`: the packet MUST NOT stay `active` under a lapsed owner. The
  consumer appends a `blocked` progress event (`active` to `blocked`) and an open
  `blocker` control record (`waiting_on` names the expired run and "owner
  reassignment"). That is the owner-lapsed state. It lasts until the steps
  above assign a new owner, after which the blocker is resolved and an
  `unblocked` event restores the class (journal-set rule 1 in the standard
  applies).
- `draft`, `ready`, `review`, `blocked`: the class is unchanged; reassign the
  owner as above.
- `done`, `cancelled`: exempt. Nothing is reassigned.

## Logical semantic cases (consumer conformance)

Because JSON Schema validates single documents without a clock, seat registry, or
cross-record state, the cases below are structurally valid against the schema
and MUST be enforced by consumer semantic validation:

| Case        | Rule(s)          | Input / scenario                                                                                                                                                                                                    | Required consumer outcome                                                                                                                                               |
| ----------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SEM-CASE-01 | SEM-P06, SEM-P07 | Packet owner and subsequent ledger `actor` both use `run-01JC8Z3K5M7Q4W9XBTN2VYE6RD` with identical `(parent: "agent-seat-builder", expires: "2026-11-01T23:00:00Z", role: "devlead")` and `ts < expires`.          | **Accept** — provenance matches the authoritative binding for that `run` `id` and `ts` precedes `expires`.                                                              |
| SEM-CASE-02 | SEM-P07          | Ledger event or packet reuses `run-01JC8Z3K5M7Q4W9XBTN2VYE6RD` (bound to `parent: "agent-seat-builder"`) but sets `parent: "maintainer-2"`.                                                                         | **Refuse** — structurally valid, but rebinding `parent` on an existing `run` `id` violates SEM-P07 even if `maintainer-2` exists.                                       |
| SEM-CASE-03 | SEM-P06, SEM-P07 | Ledger event reuses `run-01JC8Z3K5M7Q4W9XBTN2VYE6RD` (authoritative `expires: "2026-11-01T23:00:00Z"`) with `actor.expires: "2026-11-02T23:00:00Z"` and `ts: "2026-11-02T12:00:00Z"`.                               | **Refuse** — structurally valid and `ts < actor.expires` on the line in isolation, but silently extending `expires` on the same `run` `id` violates SEM-P07.            |
| SEM-CASE-04 | SEM-P02          | Role-less `run` owner lapses at `expires`; `parent` (`agent-seat-builder`) resolves under SEM-P01 and the consumer holds an unambiguous prior work-role binding (`role: "devlead"`) for that parent on this packet. | **Reassign to parent (step 1)** — new owner is `{kind: "agent", id: "agent-seat-builder", role: "devlead"}`.                                                            |
| SEM-CASE-05 | SEM-P02          | Role-less `run` owner lapses at `expires`; `parent` (`agent-seat-builder`) resolves under SEM-P01, but the consumer holds no recorded or unambiguous work-role binding for `agent-seat-builder` on this packet.     | **Fall through to step 2 / step 3** — consumer MUST NOT guess a role or emit a role-less `agent` owner; escalate to `escalation.default` (step 2) or operator (step 3). |

## Notes

- Seat registries and authorization policies are not part of this contract.
  `seat_kind` and what a seat or run is authorized to do live in the adopter's
  policy and registry. Structural schema validity, a resolving seat or parent,
  or a claimed `role` records provenance shape only and does **not** grant
  execution or delegation authorization.
- Resolution or binding failures are refusals. Do not fall back to treating an
  unresolved `agent-…` id as a person or role, or accepting a mutated `run`
  binding.
- A `run` `role` is optional on the wire because a run inherits its parent's hat
  when an unambiguous work-role binding exists for that parent on the packet;
  when no such binding exists, SEM-P02 step 1 falls through to escalation.
