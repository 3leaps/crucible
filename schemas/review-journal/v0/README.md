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
- **Cross-stream ceiling** — no event's classification exceeds the manifest
  ceiling on either dimension. This spans two files, so it is a **journal-set**
  check (`scripts/validate-review-journal-set.sh` in this repository), not a
  single-file schema property.
- **Anchor label integrity** — a labeled digest anchor must be what its label
  claims: `sha256:` carries 64 hex, `git-tree:sha1:` carries a 40-hex OID,
  `git-tree:sha256:` a 64-hex OID. A label that names an algorithm it does not
  use is a false provenance record at the one field this process treats as
  immutable.
- **Participant join** — every roster seat declares its `participant` (id, kind,
  and reasoner for agents), and events join back via `agent.participant_ref`, so
  seat/prompt/reasoner variance is machine-comparable. The `reasoner` field MUST
  admit non-exposure (`"not-exposed"`) — an invented reasoner is a false
  provenance record.
- **Prompt identity** — approving seats carry `role_prompt.digest` (required): a
  version pin is semantic identity, not byte identity, so the digest is what
  proves which framing a seat actually ran under.
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
  an accepted gate through any seat nor sets the ceiling).

Every enforcement above is **proven able to fail**: the [`rejects/`](rejects/)
fixtures are negative controls asserted in `make check`, each paired with a
single-field-corrected baseline twin so the rejection is pinned to its intended
gate (EPR-0002 obligation 3).

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
