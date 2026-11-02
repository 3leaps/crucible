# Seat Spheres Schemas v0

> **Status:** draft.

Machine-readable draft schema for a seat's responsibility model: a thin set of
per-subject records (spheres) that roll up into one seat view. Normative
semantics, default decision rights, rollup rules, and the relationship to
`project-work/v0` are specified in
[`docs/standards/seat-spheres-model.md`](../../../docs/standards/seat-spheres-model.md).

The contract identity is the opaque capability token
`contract: seat-spheres/v0`. Consumers resolve that token through local
configuration, a vendored copy, or another trusted registry. Instances must not
embed a schema host as their identity.

The contract entry point is `contract.json`. Consumers resolve the capability to
that manifest, verify its `capability`, and load the relative `entry_schema`
(`seat-view.schema.json`). Resolution fails closed when the manifest is missing,
the capability does not match, or the entry schema is missing.

| Schema                  | Governs                                               |
| ----------------------- | ----------------------------------------------------- |
| `seat-view.schema.json` | One seat: its holder, function, and delegated spheres |

`seat-view.schema.json` is the only storage schema. Rollups across seats or
subjects are computed at read time and are not stored.

## Model

- **Function** is a closed enum (`builder`, `operator`, `steward`, `consultant`,
  `analyst`) and is stable for the life of the seat.
- **Seat** is the holder, with an optional `reports_to` (an agent or person id).
- **Spheres** list delegated subjects only. A subject is a typed reference
  (`kind` slug such as `product`, `repo`, `surface`, or `process`, plus `id`).
  A subject that is not listed is open, not owned, except for the closed-by-default
  kinds described below.
- **Relation** is a closed enum: `lead`, `support`, `advise`, `assure`,
  `interested`.
- **Sphere options** are an optional `cover`, an optional `review_by` date, and
  an optional boolean `no_apply`: the seat authors changes for the subject but
  does not apply them. `cover` is one agent or person id that acts for the holder
  when the holder is unavailable; never a second lead.
- **Exceptions** are an optional short list of overrides, each a `right`, an
  `effect` (`allow` or `deny`), and a `reason`, to the default decision rights for
  the relation. A `reason` is required when the effect is `allow` (widening) and
  optional when it is `deny`. The defaults are documented below, not encoded in
  the schema.
- **Measures** attach to one sphere entry. Each has a `name`, `target`, `set_by`,
  `as_of`, and a required `expires` date, so there are no permanent measures.
- **Capabilities** are not part of this schema. A seat view may carry one opaque
  `almanac_locator` string and nothing more.
- **Holders** (`seat`) are an agent or a person. An agent id matches
  `^agent-[a-z0-9]+(-[a-z0-9]+)*$` (3-64 characters). A person id matches
  `^[a-z][a-z0-9._-]{0,63}$` and does not start with `agent-` or `run-`. A run
  is never a holder, and a run id is never a measure `set_by`, `reports_to`, or
  `cover`.

## Default decision rights by relation (documentation only)

These defaults are proposed. They are documented, not encoded in the schema.

| Relation     | Default                                                                                                                                                                           |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `lead`       | Accountable; decides within the sphere.                                                                                                                                           |
| `support`    | Executes and contributes; may decide within delegated tasks.                                                                                                                      |
| `advise`     | Is consulted when materially affected; no veto.                                                                                                                                   |
| `assure`     | Always consulted; runs the documented assurance checks and coverage; may block only on a documented assurance criterion, check, or policy failure; decides nothing else; no veto. |
| `interested` | Is informed.                                                                                                                                                                      |

Documented assurance criteria for `assure` include security and classification
tests, four-eyes review, release provenance, and schema conformance. An override
of an `assure` block requires a `decision` control record whose `decider` is the
subject's `lead` or `reports_to`, never a `run`.

An entry's `exceptions` (`{effect, right, reason}`; `reason` is required for
`allow`) override these defaults for that subject. Within a single sphere
entry, `exceptions[].right` MUST be unique.

A measure is current through its `expires` date, inclusive.

## Closed by default

The closed-by-default kind slugs are exactly `production`, `secrets`, `dns`, and
`identity`. For every other subject kind, unlisted means open, not owned. For a
subject of one of these four kinds, unlisted means closed: it is not open.
Consumers **MUST** treat an unlisted subject of these kinds as closed unless a
sphere entry delegates it. This is a documented consumer rule, not encoded in the
schema.

## Modeling notes

These are documented conventions and consumer rules, not encoded in the schema.

- **One primary function per seat.** Other work is expressed as spheres, not as
  additional functions.
- **Standing handoff moves the lead; per-packet execution does not.** When a
  supervisor hands ongoing stewardship of a subject to a delegate, the delegate
  holds `lead` and the supervisor holds `advise` (with escalation through
  `reports_to`). When a `lead` assigns a single packet in `project-work/v0` to a
  `support` seat or a `run`, the steward keeps `lead` on the subject.
- **Release gates are process spheres.** Model a gate as a subject of kind
  `process`.
- **Privileged read access lives in capabilities, not spheres.** A sphere says
  who decides about a subject; it never grants access.

## Consumer-enforced rules

The schema is a **structural** validation surface. The following semantic rules
cannot be expressed in JSON Schema and **MUST** be enforced by consumers (see
[`docs/standards/seat-spheres-model.md`](../../../docs/standards/seat-spheres-model.md)):

- **Per-seat subject uniqueness:** `(subject.kind, subject.id)` is unique across
  a seat's `spheres[]`.
- **Per-entry exception uniqueness:** `right` is unique across a single sphere
  entry's `exceptions[]`; duplicate or opposing (`allow` and `deny`) entries for
  the same `right` MUST be rejected.
- **Measure date order:** `expires` is on or after `as_of` for each measure.
- **One lead per subject across seats:** two `lead` entries for the identical
  `(subject.kind, subject.id)` across seats are a conflict.
- **Overlapping subject prefixes on a packet:** when multiple subjects match a
  `project-work/v0` packet `scope` by whole-segment prefix, the **longest
  whole-segment prefix** selects the effective subject for `lead`, default
  `decider`, `cover`, and entry-level restrictions (`no_apply`, `exceptions[]`),
  while `advise`, `assure`, and `interested` entries on matching ancestor
  subjects remain in force.
- **Default `project-work/v0` `scope` linking:** direct `<subject.kind>/<subject.id>`
  path-prefix linking applies only when the rendered path conforms to the
  `project-work/v0` `scope` grammar (`^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(/[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$`,
  `maxLength: 253`: slash-delimited lowercase alphanumeric/hyphen segments, no
  `.` or `_`, at most 63 characters per segment and 253 characters total);
  subjects outside that grammar require an explicit profile mapping table and
  MUST be treated as unmapped (never silently normalized or truncated) when
  unmapped.

These checks are consumer-side; `make check` does not prove them.

Worked examples in [`examples/`](examples/). Negative fixtures in [`rejects/`](rejects/).
