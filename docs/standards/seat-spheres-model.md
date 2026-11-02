---
title: "Seat Spheres Model"
description: "Semantics for a seat's function and per-subject spheres: relations, default decision rights, rollup rules, RACI mapping, and the relationship to project-work/v0"
category: "standards"
status: "draft"
version: "0.0.0"
lastUpdated: "2026-11-02"
maintainer: "core-standards"
reviewers: ["architecture", "project-management"]
approvers: ["lead-maintainer"]
tags: ["seat", "spheres", "delegation", "decision-rights", "raci", "project-work"]
content_license: "CC0"
relatedDocs:
  - "docs/standards/project-work-contract.md"
  - "schemas/project-work/v0/README.md"
  - "schemas/seat-spheres/v0/README.md"
audience: "implementers"
---

# Seat Spheres Model

This draft defines the semantics of a **seat**'s standing delegation: what kind
of seat it is (`function`), which subjects it has been delegated and in what
relation (`spheres`), and what each relation means for decision rights. It is
the standing counterpart to the per-work assignment carried by
[project-work/v0](project-work-contract.md).

The model does not define a seat registry, a capability registry, or a board.
It defines the meaning of the records an adopter keeps in them, so two
adopters read the same seat the same way.

> **Draft schema.** The field names used here match the
> [`contract: seat-spheres/v0`](../../schemas/seat-spheres/v0/README.md) draft
> schema (`seat-view.schema.json`): `seat`, optional `reports_to`, `function`,
> `spheres[]` with `subject {kind, id}`, `relation`, `exceptions`, and optional
> `since`, `cover`, `review_by`, `no_apply`, and `note`, and `measures[]` with
> `name`, `target`, `set_by`, `as_of`, and `expires`, plus an optional
> `almanac_locator`. Spelling and nesting are provisional while the contract is
> in `draft` status.

> **Proposed defaults.** The five relations (`lead`, `support`, `advise`,
> `assure`, `interested`) are settled. The wording of each relation's default decision
> right in [Decision Rights By Relation](#decision-rights-by-relation) is a
> **proposal pending maintainer confirmation**. Adopters SHOULD NOT treat that
> wording as normative until it is confirmed.

## Design Stance

- **One primary function.** A seat has one function, stable for the seat's
  life. A different function is a different seat. Other work the seat does is
  expressed through its spheres, not through a second function.
- **Spheres are per-subject.** Each entry relates the seat to exactly one
  subject. There is no seat-wide "scope" string.
- **Delegated subjects only.** Spheres list what was delegated. A subject that
  is not listed is **open**, which is not the same as owned. The exception is
  the [closed-by-default subjects](#closed-by-default-subjects).
- **Defaults by relation, exceptions only.** Decision rights follow from the
  relation. An entry records only where it departs from the default.
- **A standing handoff moves the lead.** When a supervisor hands a subject
  to a delegate for good, the delegate leads and the supervisor holds
  `advise`; accountability flows up through `reports_to`. Assigning one
  packet inside a sphere does not move the lead
  ([Delegation Convention](#delegation-convention)).
- **Capabilities are separate.** What a seat can verifiably do is recorded in
  a separate registry (the almanac). The seat view carries at most one
  optional locator for it, and no sphere carries capabilities.
- **Measures are optional and expire.** A measure attaches to exactly one
  sphere entry, is dated, has a required expiry, and drops out of the view
  when it expires.
- **Identity outlives assignment.** A long-lived seat keeps its id and
  function while its spheres change.

## The Four Parts

| Part         | Where it lives                                            | Stability                       |
| ------------ | --------------------------------------------------------- | ------------------------------- |
| function     | The seat view                                             | Fixed for the seat's life       |
| spheres      | The seat view, one entry per subject                      | Changes as delegation changes   |
| capabilities | The almanac; the seat view holds only an optional locator | Changes as abilities are proven |
| measures     | Inside exactly one sphere entry                           | Dated; expires                  |

### Function

`function` is a closed set:

`builder` | `operator` | `steward` | `consultant` | `analyst`

| Value        | The seat's standing orientation                     |
| ------------ | --------------------------------------------------- |
| `builder`    | Produces and changes the thing                      |
| `operator`   | Runs the thing and keeps it supplied and working    |
| `steward`    | Keeps the thing healthy and consistent over time    |
| `consultant` | Gives judgment when asked; does not own the outcome |
| `analyst`    | Observes, measures, and reports                     |

A seat has exactly one primary function, carried as `function` on the seat
view. Work outside that function is expressed through spheres: a `builder`
seat that also runs a process holds a sphere on that process rather than a
second function. Function is not a role: a role is the hat a seat wears for a particular piece
of work (see
[Relationship To project-work/v0](#relationship-to-project-workv0)), while a
function is a property of the seat itself. Function grants no decision rights;
only spheres do.

### The seat view

A seat view is one record per seat:

```json
{
  "capabilities": ["contract: seat-spheres/v0"],
  "seat": { "kind": "agent" | "person", "id": "…" },
  "reports_to": "…",
  "function": "…",
  "spheres": [ … ],
  "almanac_locator": "…",
  "updated": "RFC 3339 date-time"
}
```

- `capabilities` is the host-less contract token, as in `project-work/v0`. It
  names the contract and has nothing to do with a seat's capabilities, which
  are described under [Capabilities](#capabilities).
- `seat` is the **holder**: an `agent` (id matching
  `^agent-[a-z0-9]+(-[a-z0-9]+)*$`, 3-64 characters) or a `person` (an id
  matching `^[a-z][a-z0-9._-]{0,63}$` that does not start with `agent-` or
  `run-`). A `run` is never a holder.
- `reports_to` is optional: the agent or person id this seat reports to, never
  a run. It is a seat-level property, not a sphere. It is the **escalation
  path**: under the [Delegation Convention](#delegation-convention) a lead
  decides within its sphere and escalates to `reports_to`. On a
  [`decision` control record](#relationship-to-project-workv0) it maps to the
  `decider`.
- `almanac_locator` is optional.

### Spheres

`spheres` is a list of entries. Each entry names one subject and one relation:

```json
{
  "subject": { "kind": "…", "id": "…" },
  "relation": "lead" | "support" | "advise" | "assure" | "interested",
  "exceptions": [ … ],
  "since": "YYYY-MM-DD",
  "cover": "…",
  "review_by": "YYYY-MM-DD",
  "no_apply": true | false,
  "note": "…",
  "measures": [ … ]
}
```

- `subject` is a typed reference. `kind` is a lowercase slug naming the sort
  of thing delegated (for example `product`, `repo`, `surface`, or
  `process`); `id` is an adopter-defined identifier, lowercase only: segments
  of `a-z` and `0-9` joined by single `.`, `_`, `/`, or `-`, matching
  `^[a-z0-9]+([._/-][a-z0-9]+)*$`, at most 128 characters. Uppercase,
  whitespace, and doubled or trailing separators are invalid, so the exact
  `(kind, id)` comparison used for uniqueness and lead conflicts cannot split
  on spelling. `/` is allowed in an `id` so that the
  `<subject.kind>/<subject.id>` path-prefix match for packet scopes stays
  well-formed when `subject.id` uses the `project-work/v0` `scope` segment
  subset (see [Linking a packet to a subject](#relationship-to-project-workv0)
  for subjects that use `.`, `_`, or longer segments). `kind` is an **open
  slug**, not a closed enum: the four examples above are documented examples,
  and an adopter may use other slugs that match the slug pattern. Neither
  field is a catalog.
- `relation` is a closed set: `lead`, `support`, `advise`, `assure`,
  `interested`. `lead` is the responsibility relation. `support` and `advise`
  are the influence relations. `assure` is the gate relation: it runs the
  documented assurance checks and can block on a documented assurance
  criterion, check, or policy failure.
  `interested` is awareness only.
- `since` is the optional full date the delegation took effect. `note` is an
  optional free-text remark on the entry. Neither changes decision rights.
- `cover` is optional and names **one** agent or person id, never a run and
  never a list. It is a **substitute** for the holder: it acts within the
  entry when the holder is unavailable, and is never a second `lead`. It does
  not change the relation and is not an escalation path; escalation is
  `reports_to`.
- `review_by` is an optional full date by which the entry is reviewed. Passing
  it does not end the delegation or change any right; a consumer flags an
  entry whose `review_by` is in the past so it gets reviewed.
- `no_apply` is an optional boolean. When `true`, the seat authors changes for
  the subject but does not apply them, which separates the author from the
  applier (separation of duties). It limits who applies a change, not who
  decides it. Absent or `false` means no such limit. Only `lead` and
  `support` carry apply rights by default (see
  [Decision Rights By Relation](#decision-rights-by-relation)), so on
  `advise`, `assure`, or `interested` the flag is redundant and serves only as
  an explicit guard.
- A seat holds **at most one entry per subject**: `(subject.kind, subject.id)`
  is unique within a seat, so a seat does not hold two relations to the same
  subject. The schema cannot express this; consumers MUST enforce it.
- `exceptions` and `measures` are optional. When present they are non-empty.

**Unlisted means open.** A subject with no entry for a seat is open to that
seat: ordinary rules apply, and the seat has neither responsibility for the
subject nor any standing right to be consulted about it. Open is not
ownership. Consumers MUST NOT infer that a seat leads, supports, advises,
assures, or is informed about a subject because the subject is absent from its
list. The one exception is the closed-by-default subjects below.

#### Closed-by-default subjects

Subjects in **production, secrets, DNS, and identity** are **closed by
default**. The closed `kind` slugs are exactly `production`, `secrets`, `dns`,
and `identity`. For a subject of one of these kinds, unlisted means closed, not
open: a seat with no entry for it has no standing right to act on it, and
consumers MUST treat it as closed unless a sphere entry delegates it. For every
other kind, unlisted stays open. The schema does not encode this rule; it is a
consumer rule.

### Capabilities

Capabilities are **not** part of spheres or of the seat view's data model.
They are recorded in the almanac, a registry kept apart from the seat record,
and are verifiable: each is backed by evidence the registry can point to.

The only trace in the seat view is the optional `almanac_locator`, an opaque
string that tells a consumer where to look the seat up. It carries no
capability content and no meaning of its own.

- A sphere does not confer a capability. A seat that leads a subject may lack
  a capability the subject needs.
- A capability does not confer a sphere. A seat that can do something has not
  thereby been delegated the subject it applies to.
- A sphere entry MUST NOT carry a capability list. Consumers that need both
  join the seat view to the almanac through `almanac_locator`.
- **Privileged read access lives in capabilities, not spheres.** The ability
  to read production data, secrets, DNS records, or identity material is a
  verifiable capability recorded in the almanac. A sphere governs who may
  decide or act on a subject; it neither grants nor stands for read access.
  Holding a sphere on a closed subject does not imply read access, and read
  access does not imply a sphere.

### Measures

A measure is an optional, dated target attached to one sphere entry:

```json
{
  "name": "…",
  "target": "…",
  "set_by": "…",
  "as_of": "YYYY-MM-DD",
  "expires": "YYYY-MM-DD"
}
```

| Field     | Meaning                                                         |
| --------- | --------------------------------------------------------------- |
| `name`    | Short label for what is measured                                |
| `target`  | The intended level or condition, as text                        |
| `set_by`  | Who set the target: an agent id or a person id, never a run id  |
| `as_of`   | The full date the target was set or last confirmed              |
| `expires` | The full date the measure lapses; required, on or after `as_of` |

All five fields are required, so a measure always carries a date, an end, and
an accountable setter. There are no permanent measures. A measure belongs to
exactly one sphere entry. It is never shared across entries and never attached
to the seat as a whole. If two subjects need the same target, each entry
carries its own measure.

A measure is **current** through its `expires` date inclusive, and lapsed on
any later evaluation date. `expires` earlier than `as_of` is invalid; the
schema cannot express the ordering, so consumers MUST enforce it.

Measures describe an expectation of the entry; they do not change decision
rights.

## Decision Rights By Relation

The relations are settled; the default wording below is **proposed, pending
maintainer confirmation**.

The relation sets the default. Nothing else about a seat widens or narrows
these rights unless an exception is recorded on the entry.

| Relation     | Default decision right                                                                                                                                                                          | Obligation on others                                                                           |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `lead`       | Decides within the subject and is accountable for the outcome                                                                                                                                   | None to consult, beyond the advise relation below                                              |
| `support`    | Executes and contributes; may decide within tasks delegated to it                                                                                                                               | Delegating party states the task and its bounds                                                |
| `advise`     | No decision right; must be consulted when a change materially affects its view; holds no veto                                                                                                   | Decider consults before the change takes effect; the decision stays with it                    |
| `assure`     | Always consulted; runs the documented assurance checks and coverage; may block only on a documented assurance criterion, check, or policy failure. Decides nothing else and has no general veto | Decider consults before the change takes effect and does not proceed past a documented failure |
| `interested` | None; informed only                                                                                                                                                                             | Decider informs; no response is required                                                       |

**Apply rights.** Only `lead` and `support` carry apply rights by default:
they may apply changes to the subject. `advise`, `assure`, and `interested`
do not apply changes. `no_apply: true` removes the apply right from a `lead`
or `support` entry, leaving the seat to author and coordinate.

**What `assure` can block on.** The gate covers any documented assurance
criterion, check, or policy for the subject, such as security and
classification tests, four-eyes review, release provenance, and schema
conformance. The criterion must be written down before the block; a
preference is not a failure. An `assure` seat has no general veto and decides
nothing else about the subject. A block does not reassign the lead's
accountability. An **override** of a block is a decision by the subject's
`lead` or by `reports_to`, never by a run
([Relationship To project-work/v0](#relationship-to-project-workv0)).

**Exceptions.** An exception is recorded explicitly on the sphere entry,
never implied. It names the right it adjusts, whether it allows or denies that
right, and a reason:

```json
{ "effect": "allow" | "deny", "right": "…", "reason": "…" }
```

`reason` is required when `effect` is `allow`, because an allow widens the
default and the widening must be reviewable. It is optional when `effect` is
`deny`, which narrows the default.

`right` is a lowercase slug naming the right being adjusted (for example
`schema-change`); the slugs are adopter-defined. `allow` grants a right the
relation's default does not include. `deny` removes a right the default does
include. `reason` is free text recording why the default is being departed
from. An entry carries a short list of exceptions, not a policy document.

Within a single sphere entry, `right` **MUST be unique** across `exceptions[]`:
at most one exception per `right` may appear on an entry. A sphere entry that
lists duplicate `right` slugs—whether repeating the same `effect` or pairing
opposing `"effect": "allow"` and `"effect": "deny"` for the same `right`—is
semantically invalid. Because JSON Schema cannot express uniqueness of a single
property across objects whose other fields differ, consumers **MUST** enforce
per-entry `exceptions[].right` uniqueness as a semantic rule and **MUST reject**
any entry with duplicate or opposing exceptions for the same `right` (never
resolving the ambiguity by first-wins, last-wins, or implicit `deny`
precedence).

The rule that matters is: **a right that departs from the table above exists
only if an entry records it.** A consumer that finds a departure with no
exception treats the table as authoritative.

An exception cannot make an `advise`, `assure`, or `interested` entry
accountable for the subject. Accountability belongs to the `lead` relation.

### Delegation convention

Delegation happens at two levels. They differ in lifetime and in what they
change, and assigning work at the second level never requires editing spheres
at the first.

1. **Standing sphere handoff.** A supervisor hands ongoing stewardship of a
   subject to a delegate. **The lead moves to the delegate.** The supervisor
   does not keep it; it holds `advise` on the same subject. Accountability
   flows through `reports_to`: the lead is accountable for the subject,
   decides within the sphere, and escalates to the seat named in its
   `reports_to`.
2. **Per-packet execution.** Inside a sphere, the lead assigns one packet. A
   `support` seat, or a `run` acting for a parent, owns the packet in
   [project-work](#relationship-to-project-workv0). **The steward keeps the
   lead** on the subject, and accountability stays with it; only the packet's
   responsible party changes. No entry in any seat view is edited.

Level 1 is expressed in seat views:

- The worker's seat view carries `reports_to` naming the supervisor and a
  `lead` entry for the subject.
- The supervisor's seat view carries an `advise` entry for the same subject, so
  it must be consulted on material changes but does not decide them and has
  no veto.
- Two `lead` entries for one subject are still a conflict. A standing handoff
  moves the lead to the worker; it does not duplicate it.

A supervisor `agent-seat-supervisor` delegates `service-alpha` to
`agent-seat-builder`:

```yaml
# worker
seat: { kind: agent, id: agent-seat-builder }
reports_to: agent-seat-supervisor
function: builder
spheres:
  - subject: { kind: product, id: service-alpha }
    relation: lead
---
# supervisor
seat: { kind: agent, id: agent-seat-supervisor }
function: steward
spheres:
  - subject: { kind: product, id: service-alpha }
    relation: advise
```

(Each document also carries `capabilities` and `updated`; they are omitted
here for brevity.) A decision on `service-alpha` that the builder cannot
settle within its sphere goes to `agent-seat-supervisor`.

### Cross-sphere rights

A right that spans spheres, such as a release gate, is modeled as its own
**process sphere**: a subject with `kind` `process` whose entries say who
leads it, who assures it, and who advises. The gate does not live in a
product sphere or as a free-standing flag on a seat. A release gate for
several products is one `process` subject, and each product's lead consults it
through the relations on that subject.

## Seat-View Rollup

Spheres are per-subject records. `seat-view.schema.json` is the **single
storage schema**: one document per seat with a flat `spheres[]` list. There is
no second, grouped schema. The rules below are applied **at read time**: a
tool that renders a seat's grouped view, or checks one or more seat-view
documents for conflicts, projects and validates the stored documents without
rewriting them or introducing another record shape.

1. **Group by relation.** The view lists the seat's entries grouped under
   `lead`, `support`, `advise`, `assure`, and `interested`, in that order.
2. **One lead per subject.** Across all seats, two `lead` entries for the
   identical `(subject.kind, subject.id)` are a **conflict**. The consumer
   flags it and does not pick a winner. Entries that name different subjects,
   such as a narrower subject (`repo/alpha/api`) carved out of a broader one
   (`repo/alpha`), are split by scope and are not a storage conflict; when
   evaluating a packet whose `scope` matches both prefixes, the longest
   whole-segment prefix selects the effective subject (see
   [Overlapping subject matches](#relationship-to-project-workv0)).
3. **Expired measures drop out.** A measure whose `expires` date is before
   the evaluation date is omitted from the view. The entry and its
   other measures remain. Dropping is a view rule: the stored record is not
   rewritten.
4. **Unlisted subjects are open, except closed ones.** The view never
   synthesizes entries for subjects the seat does not list. Open subjects have
   no lead. An unlisted subject in a [closed-by-default
   class](#closed-by-default-subjects) is not open: the seat has no standing
   right to act on it.
5. **Function and identity are carried through unchanged.** The view shows
   the `seat` holder, `reports_to`, and `function` beside the grouped
   entries.
6. **Overdue reviews are flagged.** An entry whose `review_by` date is before
   the evaluation date is flagged, not dropped.

The date-order (`expires >= as_of`), per-seat `(subject.kind, subject.id)`
uniqueness, and per-entry `exceptions[].right` uniqueness checks described
above apply to the view as well; a violation is rejected or flagged, not
silently repaired.

## RACI Mapping

The relations map to RACI letters for readers who think in that matrix:

| Relation     | RACI                      | Caveat                                                                                                                                                                                |
| ------------ | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `lead`       | A, and R unless delegated | Accountability is not delegable to `support`; execution is. A lead that delegates a packet keeps A and gives R to a `support` seat or run; a standing handoff moves A to the delegate |
| `support`    | R                         | Unlike a plain R, may also decide within delegated tasks. Several seats may hold `support` on one subject                                                                             |
| `advise`     | C                         | The duty to consult is conditional on a material effect on its view, and carries no veto. RACI's C does not say either                                                                |
| `assure`     | C plus a gate             | Always consulted, and may block only on a documented assurance criterion, check, or policy failure. RACI has no gate; this is not a general veto                                      |
| `interested` | I                         | Informed, with no response owed                                                                                                                                                       |

Where this model differs from RACI:

- **Standing, not per task.** RACI assigns letters to a task. A sphere is a
  standing delegation over a subject; individual tasks inside it get their
  responsible party from [project-work](#relationship-to-project-workv0).
- **Open subjects have no row.** RACI expects an A for every row. An open
  subject has no lead and therefore no A until one is delegated.
- **One lead, many supports.** A has one holder per subject (rollup rule 2);
  R may have many.
- **Escalation is seat-level.** RACI has no escalation path. Here a lead
  escalates to its seat's `reports_to`, which is a property of the seat rather
  than of any one sphere.
- **Decision rights are explicit.** RACI leaves decision rights implicit in A.
  Here they are the table above, with exceptions recorded.

## Relationship To project-work/v0

[project-work/v0](project-work-contract.md) records work. This model records
standing delegation. They answer different questions and meet at the packet's
subject.

**Different lifetimes.** A packet `owner` is a per-work assignment: it starts
with the packet and ends with it. A sphere is a standing delegation that
outlives any one packet. Neither is derived from the other, and neither
replaces the other.

**Linking a packet to a subject.** `project-work/v0` carries no `subject`
field. In `ready-packet.schema.json` (`$defs.scope-path`), a packet's `scope`
is a slash-delimited path matching
`^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(/[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$`
with `maxLength: 253` (lowercase alphanumeric segments with internal hyphens,
at most 63 characters per segment and 253 characters total), and a sphere
subject renders as `<subject.kind>/<subject.id>`.

- **When default path-prefix linking applies.** The default
  `<subject.kind>/<subject.id>` path-prefix link is usable **only when the
  rendered `<subject.kind>/<subject.id>` string conforms to the
  `project-work/v0` `scope` grammar** (slash-delimited segments of lowercase
  alphanumeric characters and internal hyphens, no `.` or `_`, each segment at
  most 63 characters, and the full `<subject.kind>/<subject.id>` path at most
  253 characters). Under default linking, a packet belongs to a subject when
  its `scope` equals `<subject.kind>/<subject.id>` exactly or has it as a
  whole-segment path prefix (`scope` starts with
  `<subject.kind>/<subject.id>/`). Comparing `scope` with `subject.id` alone
  drops the kind and can collide across kinds, so the kind is always part of
  the match.
- **Subjects outside the `project-work/v0` `scope` grammar.** Because
  `seat-spheres/v0` `subject.id` (`^[a-z0-9]+([._/-][a-z0-9]+)*$`, `maxLength: 128`)
  also permits `.`, `_`, and segments longer than 63 characters (for example
  `repo/alpha.api`, `repo/alpha_api`, or a 64-character single segment), such a
  subject cannot be written directly as a `project-work/v0` `scope`. Linking a
  subject whose rendered `<subject.kind>/<subject.id>` falls outside the
  `project-work/v0` `scope` grammar requires an **explicit profile mapping
  table**. When no profile mapping entry is configured for such a subject, a
  consumer **MUST** treat the subject as unmapped for `project-work/v0` packet
  linking (flagging any requested link as unmapped) and **MUST NOT** silently
  normalize punctuation (such as rewriting `.` or `_` to `-`) or truncate
  segments or ids.

**Overlapping subject matches.** When a narrower subject is carved out of a
broader subject (for example `repo/alpha/api` led by `agent-narrow` alongside
`repo/alpha` led by `agent-broad`), both rendered paths are whole-segment
prefixes of a packet `scope` such as `repo/alpha/api/change`. Consumers MUST
resolve overlapping prefix matches deterministically before deriving packet
authority:

1. **Longest whole-segment prefix selects the effective subject.** Among all
   subjects matching the packet's `scope` by whole-segment prefix (or explicit
   profile mapping), the subject with the greatest number of matched path
   segments (`repo/alpha/api`, 3 segments, over `repo/alpha`, 2 segments) is
   the packet's **effective subject**.
2. **Single-holder authority comes from the effective subject.** The packet's
   `lead`, default `decider`, `cover`, expected `owner` (`lead` or `support`),
   and entry-level restrictions (`no_apply` and `exceptions[]`) are evaluated
   from the entries on the **effective subject** (`repo/alpha/api`). A `lead`
   or `support` entry on a broader ancestor subject (`repo/alpha`) does not
   make that ancestor holder a co-lead or default `decider` on the carved-out
   sub-scope.
3. **Ancestor consultation, gates, and notifications remain in force.**
   `advise`, `assure`, and `interested` entries on broader matching ancestor
   subjects (`repo/alpha`) continue to apply to the packet alongside those on
   the effective subject unless an explicit profile mapping specifies otherwise.
4. **Tie at the same longest prefix is a conflict.** If two seats both hold
   `lead` on the identical effective subject `(subject.kind, subject.id)` (or
   two profile mappings resolve to the same specificity with different leads),
   rollup rule 2 applies: the consumer flags a lead conflict and MUST refuse to
   derive a single `lead` or default `decider`.

**`owner`.** The `owner` of a packet is one of `person`, `role`,
`unassigned`, `agent`, or `run`. An `agent` owner is a seat id and requires a
`role`, the hat the seat wears for this work. Consistent with the standing
delegation:

- A packet owner normally holds `lead` or `support` on the packet's subject.
  A `lead` that hands a packet to a `support` seat or a `run` keeps `lead`
  on the subject ([Delegation Convention](#delegation-convention)). The
  `seat` holder of a seat view is an agent or a person, which are the
  owner kinds that can hold spheres.
- A consumer SHOULD flag, without rejecting, an owner that holds only
  `advise` or `interested` on the subject, or whose subject is open: such work
  is allowed, but the seat is acting outside any delegation.
- A seat with `no_apply` set to `true` on the subject may own a packet to
  author the change, but does not apply it; application falls to another party.
- `role` and `unassigned` are outside this model; neither names a holder.

**`decider`.** A `decision` control record names a `decider`. The default
decider for a subject is that subject's `lead`. When a decision goes beyond the
lead's sphere, is contested, or concerns the lead's own entry, it escalates and
the decider is the lead's `reports_to`. A record that names someone else is
valid, and SHOULD be traceable to an exception on the lead's entry or to an
explicit delegation recorded on the packet. A `decider` is never a `run`.

**`cover` and `reports_to`.** `cover` is a substitute: when the holder of an
entry is unavailable to accept a packet, answer a `check_by`, or take back a
packet returned from an expired run, work routes to the entry's `cover`, which
acts within the holder's entry and bounds. `reports_to` is the escalation
path and maps to the `decider` on `decision` control records, as above. The
two are not interchangeable: `cover` stands in, `reports_to` decides above.

**`assure` blocks.** When an `assure` seat blocks a packet on a documented
failure, project-work records it as a `blocked` progress event plus a
`blocker` control record: the `actor` is the `assure` seat and `waiting_on`
names the failing criterion, check, or policy. An override is a `decision`
control record whose `decider` is the subject's `lead` or `reports_to`, never
a `run`. Without an override, the block stands until the check passes.

**`requested_by` and `check_by`.** `requested_by` names who is owed the work;
it carries no accountability and implies no sphere. A requester may hold any
relation to the subject, or none. `check_by` is the instant by which the owner
is next expected to report; it is a property of the packet and does not read
from or write to spheres.

**`run`.** A `run` is one bounded execution acting for a `parent`. A run is
never a sphere holder (`seat.kind` is `agent` or `person`) and is never a
measure `set_by`. A run **inherits its parent's spheres and never holds its
own.** Specifically:

- The run acts under the parent's entries as they stand at evaluation time.
  It adds no entry, changes no relation, and carries no measures of its own.
- The run does not appear in any seat view and is never a `lead`.
- Inheritance ends when the run's `expires` passes. It does not outlast it.
- A parent that holds no seat view gives the run nothing to inherit, and the
  run is then treated as acting in open subjects only.

**Function versus role.** `function` is fixed per seat. `owner.role` is chosen
per piece of work and may differ between packets for the same seat. One does
not constrain the other.

**Three layers.** Three concerns stay separate:

- **Standing responsibility** is `seat-spheres/v0`, shown when a seat wakes.
- **Capabilities** are in the almanac, reached through `almanac_locator`.
- **Active commitments** are in `project-work/v0`.

None of the three is derived from another.

## Worked Examples

These examples use placeholder seat ids that fit the `agent-` holder-id shape,
placeholder person ids, and placeholder subjects. They are illustrations, not
a catalog. Dates are chosen to show a measure that is current and one that has
lapsed; the views below are evaluated on 2026-11-02.

### A builder seat

`agent-seat-builder` has function `builder` and reports to
`agent-seat-supervisor`. It leads delivery of two products, advises on
infrastructure, and is informed about platform operations.

```json
{
  "capabilities": ["contract: seat-spheres/v0"],
  "seat": { "kind": "agent", "id": "agent-seat-builder" },
  "reports_to": "agent-seat-supervisor",
  "function": "builder",
  "spheres": [
    {
      "subject": { "kind": "product", "id": "service-alpha" },
      "relation": "lead",
      "since": "2026-06-01",
      "measures": [
        {
          "name": "release-cadence",
          "target": "one tagged release every two weeks",
          "set_by": "maintainer-1",
          "as_of": "2026-11-01",
          "expires": "2027-01-31"
        }
      ]
    },
    {
      "subject": { "kind": "product", "id": "service-beta" },
      "relation": "lead",
      "exceptions": [
        {
          "effect": "deny",
          "right": "schema-change",
          "reason": "Schema changes are decided by the data steward"
        }
      ],
      "measures": [
        {
          "name": "open-defects",
          "target": "no more than five open defects older than 30 days",
          "set_by": "maintainer-1",
          "as_of": "2026-08-01",
          "expires": "2026-10-31"
        }
      ]
    },
    {
      "subject": { "kind": "surface", "id": "infrastructure" },
      "relation": "advise"
    },
    {
      "subject": { "kind": "process", "id": "platform-operations" },
      "relation": "interested"
    }
  ],
  "updated": "2026-11-02T09:00:00Z"
}
```

Seat view (reports to `agent-seat-supervisor`):

- **lead:** `product/service-alpha` (measure `release-cadence`, expires
  2027-01-31); `product/service-beta` (one exception denying `schema-change`;
  measure `open-defects` lapsed 2026-10-31 and is omitted).
- **support:** none.
- **advise:** `surface/infrastructure`.
- **assure:** none.
- **interested:** `process/platform-operations`.

The builder may decide within `service-alpha` and is accountable for it. It
must be consulted on infrastructure changes that materially affect its view,
but cannot veto them, and it is only told about platform operations. Every
other subject is open to it.

### An operator seat

`agent-seat-operator` has function `operator`. It leads environment supply and
tooling, supports CI runners, and advises on developer experience. It also
carries an almanac locator.

```yaml
capabilities:
  - "contract: seat-spheres/v0"
seat:
  kind: agent
  id: agent-seat-operator
function: operator
spheres:
  - subject: { kind: process, id: environment-supply }
    relation: lead
    measures:
      - name: provisioning-lead-time
        target: new environment available within one business day
        set_by: maintainer-2
        as_of: 2026-11-01
        expires: 2027-01-31
  - subject: { kind: surface, id: environment-tooling }
    relation: lead
  - subject: { kind: surface, id: ci-runners }
    relation: support
    exceptions:
      - effect: allow
        right: capacity-change
        reason: Runner pool sizing is delegated to this seat
  - subject: { kind: process, id: developer-experience }
    relation: advise
almanac_locator: almanac:example/agent-seat-operator
updated: 2026-11-02T09:00:00Z
```

Seat view:

- **lead:** `process/environment-supply` (measure `provisioning-lead-time`,
  expires 2027-01-31); `surface/environment-tooling`.
- **support:** `surface/ci-runners` (one exception allowing
  `capacity-change`).
- **advise:** `process/developer-experience`.
- **assure:** none.
- **interested:** none.

On `ci-runners` the operator executes and may decide within delegated tasks;
the `allow` exception additionally lets it decide runner capacity changes,
which the `support` default would not. Whoever leads `ci-runners` remains
accountable for the subject. If another seat also listed a `lead` entry for
the identical subject `process/environment-supply`, the rollup would flag a
conflict instead of choosing between them.

### A release gate and an assure seat

`agent-seat-assurer` has function `consultant` and reports to
`agent-seat-supervisor`. A release gate is a `process` subject. The assurer
assures it, authors but does not apply gate changes, and has its entry
covered by the builder and reviewed by a set date.

```json
{
  "capabilities": ["contract: seat-spheres/v0"],
  "seat": { "kind": "agent", "id": "agent-seat-assurer" },
  "reports_to": "agent-seat-supervisor",
  "function": "consultant",
  "spheres": [
    {
      "subject": { "kind": "process", "id": "release-gate" },
      "relation": "assure",
      "since": "2026-09-01",
      "cover": "agent-seat-builder",
      "review_by": "2026-12-15",
      "no_apply": true,
      "note": "Runs the documented assurance checks and coverage; blocks only on a documented failure."
    }
  ],
  "updated": "2026-11-02T09:00:00Z"
}
```

The assurer is always consulted on the release gate and can block a release
only on a documented assurance criterion, check, or policy failure, such as a
security or classification test, a four-eyes review, release provenance, or
schema conformance. It decides nothing else about the gate, has no general
veto, and does not apply changes to it (`no_apply` is redundant on `assure`
and is shown here as an explicit guard). If it blocks a packet on the gate,
the block is recorded as a `blocked` event plus a `blocker` control record,
and only the gate's `lead` or `reports_to` can override it. Reading
production or secrets material for those tests is a capability in the
almanac, not part of this entry.

### A packet and a run

A packet whose `scope` is `process/environment-supply`, or a path under it
such as `process/environment-supply/runbooks`, matches the subject
`process/environment-supply` and is owned by the operator seat:

```json
{
  "kind": "agent",
  "id": "agent-seat-operator",
  "role": "devlead"
}
```

The owner holds `lead` on that subject, so the owner is expected. A decision
on the packet defaults to that same seat as `decider`. If the seat starts a
`run` for part of the work, the run owner is
`{ "kind": "run", "id": "run-01K8P7Q2R4S6T8V0W2X4Y6Z8A0", "parent": "agent-seat-operator", "expires": "2026-11-02T12:00:00Z" }`.
That run acts under the operator's `environment-supply` entry while it lasts,
holds no sphere of its own, and cannot be the `decider`. Handing the packet to
the run, or to a `support` seat, leaves the operator as `lead`: per-packet
execution changes the packet's owner, not the operator's entry.

### Semantic resolution cases

The following logical cases summarize the required consumer behavior where
JSON Schema structural validation passes (`make check`) and consumer semantic
rules decide the outcome:

| Case         | Input summary                                                                                                                                                                             | Required consumer outcome                                                                                                                                                                                                  |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SS-CASE-01` | `agent-broad` holds `lead` on `repo/alpha` (plus `agent-sec` holds `assure` on `repo/alpha`); `agent-narrow` holds `lead` on `repo/alpha/api`; packet has `scope: repo/alpha/api/change`  | Longest whole-segment prefix selects `repo/alpha/api` as the **effective subject**: `agent-narrow` is `lead` and default `decider` (not `agent-broad`); `agent-sec`'s ancestor `assure` gate on `repo/alpha` still applies |
| `SS-CASE-02` | Two seats both hold `lead` on the identical subject `{ "kind": "repo", "id": "alpha/api" }`                                                                                               | Rollup rule 2 flags a lead conflict; consumer refuses to pick a winner or derive a default `decider`                                                                                                                       |
| `SS-CASE-03` | Sphere entry has `subject` `{ "kind": "repo", "id": "alpha.api" }`, `{ "kind": "repo", "id": "alpha_api" }`, or a 64-character single segment, and no profile mapping table is configured | Valid `seat-spheres/v0` subject, but outside `project-work/v0` `scope` grammar; consumer treats it as **unmapped** for default packet `scope` linking and never rewrites `.`/`_` to `-` or truncates segments              |
| `SS-CASE-04` | One sphere entry's `exceptions[]` contains both `{ "effect": "allow", "right": "schema-change", "reason": "…" }` and `{ "effect": "deny", "right": "schema-change" }`                     | Rejected as semantically invalid: `exceptions[].right` must be unique within a sphere entry (never resolved by first-wins, last-wins, or implicit `deny`)                                                                  |

## Out Of Scope

Seat registries and hosting, the almanac's own format and verification
method (beyond the opaque locator), subject catalogs and naming,
profile-defined packet-to-subject mapping tables, scheduling of measure reviews, and any enforcement
engine. A consumer that wants conflicts, overdue reviews, or expired measures
surfaced runs the rollup rules above; this document does not define a
validator.
