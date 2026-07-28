# contract: review-journal/v0

The machine-readable companion to the
[Fierce-Collaboration Review standard](../../../docs/standards/fierce-collaboration-review.md).
An append-only NDJSON journal of a relied-upon review — one event per line —
parallel to the required human-readable markdown alignment log.

Emission is **optional-but-recommended best practice**: the markdown alignment log
is the required foundation, and the journal is the diffable form. It is **intended**
to cut review wall-time and to make panel variance (sub-agent vs live, model vs
model, framing vs framing) measurable — both are stated as design intent and
neither is yet evidenced; see the standard §9.2. When a journal **is** emitted, it
MUST conform to this contract.

**What conformance does and does not establish.** v0 checks the shape of each
event and manifest. It does **not** yet check that an event's classification stays
within the manifest ceiling (a cross-stream property), that `access_tier ≥
sensitivity` (a cross-enum property), or that an anchor's _content_ is a
well-formed digest rather than merely present. It also records, but cannot yet
join, participant identity to role-prompt and reasoner — so a conforming journal
is **not** evidence that model or framing variance is machine-measurable. These
gaps are owned with closure triggers in PDR-0005; conformance is bounded to what
the contract actually checks.

## Shape

| File                          | Role                                                                                        |
| ----------------------------- | ------------------------------------------------------------------------------------------- |
| `review-manifest.schema.json` | Entry manifest — declares the review, its panel, and its **classification ceiling**.        |
| `review-event.schema.json`    | One NDJSON line — a finding, verdict, remediation, or gate event, each **self-classified**. |
| `contract.json`               | Capability manifest; `entry_schema` points at the review manifest.                          |
| `examples/`                   | A synthetic manifest + event stream.                                                        |

## Classification & ROE

Both the manifest ceiling and every event use the ecosystem's own
[sensitivity](../../../docs/standards/data-sensitivity-classification.md) and
[access-tier](../../../docs/standards/access-tier-classification.md) tokens. The
org's cxotech agent or the maintainer sets the manifest `ceiling` — with the
non-author valve in the standard §10 where the ceiling-setter would otherwise be
the author; an event's `classification` must not exceed it. **That bound is a
rule, not yet a check** — see above. This gives every contributor a
partially-objective check — _"the evidence I want to add classifies at X; the
ceiling is Y; X ≤ Y is permitted"_ — before adding potentially non-public evidence.

`unknown` is a valid but temporary state: missing classification is a policy error,
set `unknown` and isolate until classified.

The event schema enforces the minimum evidence-bearing shape for each phase:
findings carry stable identity, target, severity, evidence, verdict, and anchor;
verdicts re-cite identity, evidence, verdict, and anchor; remediations carry
identity, evidence, and a remediation reference; gates carry evidence,
disposition, and anchor. Review seats in the manifest carry their named
role-prompt identity; author and maintainer seats are exempt.

These are **presence** requirements. The contract does not yet constrain an
anchor's content, nor does it prevent an `author` seat from recording an approving
gate — so v0 conformance is not evidence that the standard's author-≠-approver
non-negotiable was honoured. Both are owned with closure triggers in PDR-0005.

Append-only is an authoring rule, not tamper evidence. This v0 contract does not
define signatures or a hash chain; deployments that rely on record integrity must
supply that property at the storage or envelope layer.

## Status

**Draft (v0).** The manifest, event stream, and contract manifest are validated in
`make check` (mirroring `process-run/v0`) — the contract carries its own executable
gate per EPR-0002.
