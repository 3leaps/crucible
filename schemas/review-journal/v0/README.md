# contract: review-journal/v0

The machine-readable companion to the
[Fierce-Collaboration Review standard](../../../docs/standards/fierce-collaboration-review.md).
An append-only NDJSON journal of a relied-upon review — one event per line —
parallel to the required human-readable markdown alignment log.

Emission is **optional-but-recommended best practice**: the markdown alignment log
is the required foundation, and the journal is the diffable form. It is **intended**
to cut review wall-time — stated as design intent and not yet evidenced; see the
standard §9.2. When a journal **is** emitted, it MUST conform to this contract.

**What conformance establishes.** v0 checks the shape of each event and manifest,
and additionally enforces:

- **Cross-enum floor** — `access_tier ≥ sensitivity` per the
  [minimum-access-tier-per-sensitivity table](../../../docs/standards/access-tier-classification.md#relationship-to-sensitivity),
  in-schema, on every entry classification and on the manifest ceiling. `unknown`
  is valid only as a pair: a half-classified value fails closed.
- **Cross-stream ceiling and roster closure** — no event's classification
  exceeds the manifest ceiling on either dimension; roster seat names are
  unique (a duplicated seat makes the join ambiguous and fails); every event's
  seat is declared and its mandatory `participant_ref` resolves to that seat's
  participant; `ceiling.set_by` resolves to exactly one roster seat. These
  span two files, so they are **journal-set** checks
  (`scripts/validate-review-journal-set.sh` in this repository), not
  single-file schema properties.
- **Anchor label integrity** — a labeled digest anchor must be what its label
  claims: `sha256:` carries 64 hex, `git-tree:sha1:` carries a 40-hex OID,
  `git-tree:sha256:` a 64-hex OID. A label that names an algorithm it does not
  use is a false provenance record at the one field this process treats as
  immutable.
- **Participant join** — every roster seat declares its `participant` (id, kind,
  and reasoner for agents), and every event carries a **mandatory**
  `agent.participant_ref` joining back to it, so seat/prompt/reasoner variance
  is machine-comparable and the person-level checks below have a participant to
  check. The `reasoner` field MUST admit non-exposure (`"not-exposed"`) — an
  invented reasoner is a false provenance record. The maintainer seat's
  participant MUST be human — merge authority is a human, and the roster says
  so checkably.
- **Prompt identity** — approving **agent review seats** (every seat required to
  carry `role_prompt`) carry `role_prompt.digest` (required): a version pin is
  semantic identity, not byte identity, so the digest is what proves which
  framing a seat actually ran under. The author and the human maintainer are
  outside this requirement by design — neither is a prompted review seat.
- **Execution record (optional, shape-enforced)** — a seat may record how it was
  actually run: a symbolic `harness` token, an optional symbolic `profile_ref`,
  a `mode` (`interactive` | `headless` | `subagent`), and a `capture` form. All
  references are symbolic — tokens resolved against an operator-maintained
  launch matrix, never command lines, flags, or filesystem paths — and the
  capture enum deliberately admits no terminal-scrape form. Optional in v0
  (reserve-don't-force); the standard §9.2 requires it for every compared seat
  when a **framing-comparison claim** is made from the journal — a bound the
  schema cannot see, so it stays normative in the standard, checked by the
  panel, not the file gate. When present, its shape is enforced and proven able
  to fail.
- **Finding lifecycle** — findings and verdicts carry a machine-readable
  `lifecycle`; `deferred` requires an owner and closure trigger, because
  unlabeled deferral is not closure. Findings carry a `defect_class`, which is
  what makes convergence checkable across rounds.
- **Claim-scoped gates** — gate events carry `gate_scope` (scope, non-goals,
  bounds), so `accepted` names what it covers rather than implying a general
  guarantee.
- **Author-does-not-approve** — at the seat level in-schema (an `author` seat
  cannot record an `accepted` gate; the ceiling's `set_by` cannot be the author
  seat; a roster of only author seats is invalid), and at the **person** level in
  the journal-set check (the participant occupying an author seat neither records
  an accepted gate through any seat nor sets the ceiling). The join this rests on
  is mandatory and unambiguous: events must carry `participant_ref`, duplicate
  roster seats fail, and a `set_by` that resolves to no participant fails —
  never passes by absence.

Every enforcement above is **proven able to fail**: the [`rejects/`](rejects/)
fixtures are negative controls asserted in `make check`, each paired with a
baseline twin, and the battery **mechanically asserts** that every pair differs
in exactly one field and that set-level fixtures are schema-valid — so each
rejection is pinned to its intended gate by construction, not by prose
(EPR-0002 obligation 3).

**What conformance still does not establish.** `human-merge-authority` remains
stated at principle altitude and enforced by no mechanism in this contract — a
journal cannot prove who held merge authority. Append-only remains an authoring
rule, not tamper evidence: v0 defines no signatures or hash chain; deployments
relying on record integrity supply that property at the storage or envelope
layer. The wall-time claim (§9.2) remains design intent. The journal-set check
runs in this repository's gate; a downstream adopter proves its own tooling
against the shipped reject fixtures, which are contract data.

## Shape

| File                          | Role                                                                                                                |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `review-manifest.schema.json` | Entry manifest — declares the review, its panel + participants, and its **classification ceiling** (with `set_by`). |
| `review-event.schema.json`    | One NDJSON line — a finding, verdict, remediation, or gate event, each **self-classified**.                         |
| `contract.json`               | Capability manifest; `entry_schema` points at the review manifest.                                                  |
| `examples/`                   | A redacted, fictionalized journal of a real panel — the contract dogfooding its own format.                         |
| `rejects/`                    | Negative-control fixtures with baseline twins; see [`rejects/README.md`](rejects/README.md).                        |

## Classification & ROE

Both the manifest ceiling and every event use the ecosystem's own
[sensitivity](../../../docs/standards/data-sensitivity-classification.md) and
[access-tier](../../../docs/standards/access-tier-classification.md) tokens. The
org's cxotech agent or the maintainer sets the manifest `ceiling` — recorded
first-class in `ceiling.set_by`, never the author, with the non-author valve in
the standard §10 — and an event's `classification` must not exceed it. Both
bounds are now checks, not only rules. This gives every contributor a
partially-objective check — _"the evidence I want to add classifies at X; the
ceiling is Y; X ≤ Y is permitted"_ — before adding potentially non-public
evidence.

`unknown` is a valid but temporary state: missing classification is a policy
error, set `unknown` (both dimensions) and isolate until classified. A
half-classified pair fails validation.

## Status

**Draft (v0).** The manifest, event stream, contract manifest, journal-set
properties, and the full negative-control battery are validated in `make check` —
the contract carries its own executable gate per EPR-0002, and that gate is
demonstrated able to fail.
