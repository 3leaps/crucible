# Application control v0 semantic validation

**Layer id:** `application-control/v0-semantics`
**Layer version:** `0.2.0`

JSON Schema validates individual artifacts. Implementations also enforce the
following cross-artifact rules and run the shared fixtures.

| Rule      | Requirement                                                                                                                                                                                                                           |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SEM-C01` | Operation identifiers, information-source identifiers, rule identifiers, and non-controllable surface references are unique within their respective catalog or policy.                                                                |
| `SEM-C02` | Each user-visible control surface appears exactly once: as a `surface_ref` on one operation, or as one `non_controllable_surfaces` entry. A programmatic-only operation may omit `surface_refs`.                                    |
| `SEM-C03` | Each application surface that emits or displays information appears exactly once in the information-source catalog. A programmatic-only source may omit `surface_refs`.                                                              |
| `SEM-C04` | Every request operation and target kind exists in the descriptor-pinned operation catalog.                                                                                                                                            |
| `SEM-C05` | Request and result payload schema URI and digest equal the operation's pinned request or result payload contract.                                                                                                                     |
| `SEM-C06` | A `mutate` or `destructive` operation requires `idempotency_key` and `request_fingerprint`; it also requires `expected_generation` when its catalog precondition is `generation_required`.                                            |
| `SEM-C07` | One idempotency key identifies exactly one canonical request projection. Reuse with a different projection or fingerprint is rejected. A valid replay returns the original result and sets `original_result_hash`.                    |
| `SEM-C08` | Every result is server-bound to the request target, replay fields, authenticated principal, evaluated policy artifact, and before/after generation. `denied` and `confirmation_required` decisions have `effect: not_applied`.          |
| `SEM-C09` | Every observation matches its descriptor-pinned source entry, including eligible consumer, mode, payload, provenance, and delivery semantics. `scrape` and `client_derived` sources never emit observation messages.                   |
| `SEM-C10` | `recorded_at` is not earlier than `occurred_at`. A source advertising replay supplies a cursor; detected stream gaps are explicit.                                                                                                    |
| `SEM-C11` | Each operation's `emitted_sources` exists in the information-source catalog.                                                                                                                                                          |
| `SEM-C12` | A policy rule references only cataloged applications and, according to its kind, operations and target kinds or information sources. An observe rule carries every referenced source's exact read capability. Deny precedes allow.  |
| `SEM-C13` | The receiver derives principal identity from its authenticated connection or local peer credentials. Payload values that attempt to assert identity have no authority.                                                                |
| `SEM-C14` | Evidence source is valid for its stage and its fact contract is operation-catalog-pinned. Request, decision, and effect evidence is server-bound to principal, target, replay, policy, and generation correlation as applicable.      |
| `SEM-C15` | A non-null control endpoint requires a non-null policy reference. A null endpoint means no control listener is available.                                                                                                             |
| `SEM-C16` | Descriptor catalog and policy digests match the exact artifacts used for validation and execution.                                                                                                                                    |
| `SEM-C17` | Before authorization or replay lookup, the receiver computes the canonical request fingerprint and constant-time compares it with the caller's claim. A mismatch is rejected; the claim is never authoritative.                    |

## Canonical request fingerprint

Canonical JSON v0 admits only JSON null, booleans, strings, integers in the
inclusive range `[-9007199254740991, 9007199254740991]`, arrays, and objects.
Fractional numbers are rejected. Object member names are sorted by ascending
Unicode scalar value. Arrays retain their order. There is no Unicode
normalization. Inputs containing duplicate object member names or invalid
Unicode are rejected before canonicalization.

Serialization uses the JSON literals `null`, `true`, and `false`; integers use
minimal base-10 form; and no insignificant whitespace is present. Strings are
UTF-8. Quotation mark and reverse solidus are escaped. Backspace, tab, line
feed, form feed, and carriage return use `\b`, `\t`, `\n`, `\f`, and `\r`;
other U+0000 through U+001F characters use lowercase `\u00xx`. All other
Unicode scalar values are emitted without escaping.

The canonical request projection is the complete request object with only the
top-level `request_id` and `request_fingerprint` members removed. Its
fingerprint is lowercase hexadecimal:

```text
SHA-256(
  UTF-8("application-control/v0/request-fingerprint") ||
  0x00 ||
  canonical-json-v0(request-projection)
)
```

The receiver computes this value itself. The caller-supplied fingerprint is
only a claim. The conforming request and replay fixtures are test vectors for
the algorithm; the mutation and mismatch fixtures prove fail-closed behavior.

The reference validator implements the rules exercised by
`fixtures/semantic/manifest.json`. Product profiles add fixtures that prove
their complete control-surface and information-source inventories against
`SEM-C02` and `SEM-C03`.
