# review-journal/v0 — reject fixtures (negative controls)

These fixtures prove the contract's gates can **fail** — [EPR-0002](../../../docs/decisions/EPR-0002-verification-gate-integrity.md)
obligation 3. A schema whose examples all validate is configured, not proven;
each `reject-*` here must **fail** validation, and the repository's `make check`
asserts that it does.

**Every reject has a baseline twin, and the pair differs in exactly one field —
an invariant the battery asserts mechanically**, via a structural JSON diff
(added/removed/changed scalars count one each; an added or removed subtree
counts one at its root), not by prose. The `baseline-*` fixture is identical
except that the defective field is corrected, and it must **pass**. This is the
control-of-the-control: it proves the reject fails _for the intended reason_ —
the mutated field — and not for some unrelated malformation, pinning each
rejection to its own failure identity by construction rather than by matching
error text. Set-level fixtures are additionally asserted **schema-valid**, so a
set reject is proven to fail only at the set gate.

| Directory   | Validated by                             | Reject must fail because                                                                                                                                                                                                                                                                                                                                       |
| ----------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `manifest/` | `review-manifest.schema.json`            | ceiling below the sensitivity floor · author-only roster · approving seat without a prompt digest · ceiling set by the author seat · agent participant without a reasoner · half-unknown ceiling · maintainer seat occupied by a non-human participant · execution record claiming a terminal-scrape capture form · execution record without its harness token |
| `event/`    | `review-event.schema.json`               | mislabeled tree anchor (SHA-1 OID under a sha256 label) · malformed sha256 digest · author seat recording an accepted gate · finding without a defect class · deferred without owner/trigger · classification below the tier floor · half-classified entry · event without a participant_ref                                                                   |
| `set/`      | `scripts/validate-review-journal-set.sh` | an event classified above the manifest ceiling (sensitivity-only mutation) · an accepted gate recorded by the author's participant through a non-author seat (gate-only mutation) · a roster with a duplicated seat (ambiguous join) · a ceiling set_by that resolves to no roster seat                                                                        |

The `set/` pairs exercise properties that span the manifest and event stream
together — the cross-stream ceiling and the person-level
author-does-not-approve join — which no single-file schema check can express.

Fixture data is synthetic by construction. Reasoners are placeholder family
names; digests are illustrative values.
