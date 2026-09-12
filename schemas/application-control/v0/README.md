# Application control schema family v0

Machine-readable schemas and conformance fixtures for the
[Portable Application Control and Observation Contract](../../../docs/standards/application-control-contract.md).

The hostless capability token is `contract: application-control/v0`.
Consumers resolve that token through a trusted registry or a vendored,
digest-pinned copy. Retrieval URLs do not replace the logical schema
identifiers under `contract:application-control/v0/`.

## Artifacts

| Artifact                                 | Purpose                                                              |
| ---------------------------------------- | -------------------------------------------------------------------- |
| `contract.json`                          | Capability and entry-schema manifest                                 |
| `application-descriptor.schema.json`     | Instance discovery plus immutable catalog and policy references      |
| `operation-catalog.schema.json`          | Exhaustive inventory of application controls                         |
| `information-source-catalog.schema.json` | Exhaustive inventory of information sources and their delivery modes |
| `control-message.schema.json`            | Transport-neutral operation request and result                       |
| `observation-message.schema.json`        | Emitted event, snapshot, or sample                                   |
| `control-evidence.schema.json`           | Evidence across interaction, request, decision, and effect stages    |
| `control-policy.schema.json`             | Thin authorization inputs evaluated at the application boundary      |
| `semantic-validation.md`                 | Cross-artifact invariants that JSON Schema cannot express            |

Run `sh scripts/test-application-control-controls.sh` from the repository root.

## Boundary

The contract controls the application, not content sessions hosted by the
application. Product profiles define their own application objects, operation
identifiers, payload schemas, information sources, policy lifecycle, transport,
and enforcement. The shared family standardizes discovery, catalog shapes,
request/result correlation, replay-safe mutation inputs, observation
provenance, and decision/effect evidence.

The receiver recomputes every mutation fingerprint using the exact canonical
JSON v0 algorithm in `semantic-validation.md` before authorization or replay
lookup. A caller-provided fingerprint is only a claim.

An application may adapt these messages to an existing command transport. The
adapter does not change the contract's semantics and must not turn an open
transport argument bag into an unversioned operation API.

## Complete instrumentation

Each product profile maintains two reviewed inventories:

1. Every user-visible control surface—buttons, menu items, shortcuts, command
   palette entries, gestures, and equivalent affordances—maps to exactly one
   cataloged operation, or appears in `non_controllable_surfaces` with a reason.
2. Every information source—state changes, samples, status values, counters,
   notifications, and other parallel telemetry—maps to exactly one cataloged
   source.

Multiple surfaces may intentionally map to the same operation. The stable
`surface_refs` make those aliases explicit and testable.

An operation exposed only through a CLI, SDK, agent tool, or another
programmatic adapter may omit `surface_refs`. This does not weaken the
inventory rule: every user-visible control that does exist must still appear
exactly once. Information sources may likewise omit `surface_refs` when they
have no application display or emitter surface.

Product implementations should generate UI actions and remote dispatch from the
same operation registry where practical. When generation is impractical,
contract tests must compare the runtime UI inventory against the catalog.
Direct UI activation emits interaction evidence with the same operation and
request identifiers plus the exact `surface_ref`; protocol receipt,
authorization decision, and application effect remain separate evidence stages.
Other parallel state or measurement emitters belong in the information-source
catalog.

Each operation also pins the payload contract for every evidence stage it can
produce. Evidence facts are validated against those catalog entries rather
than accepted as open, self-declared types.

## Information delivery

The catalog separates information semantics from delivery:

- `event`: emitted for a meaningful state transition;
- `snapshot`: emitted state suitable for initial synchronization or recovery;
- `scrape`: read on demand; never emitted merely because time passed;
- `sample`: emitted on a bounded cadence for measurements where streaming adds
  value;
- `client_derived`: calculated by the consumer from cataloged inputs.

Only `event`, `snapshot`, and `sample` appear in
`observation-message.schema.json`. A clock or similarly cheap, continuously
changing display normally belongs to `scrape` or `client_derived`, not an event
stream. Streaming is therefore explicit and selective rather than an automatic
consequence of instrumenting a source.

Each source additionally declares its exact read capability, eligible consumer
or adapter kinds, projection and redaction rule, units, bounded dimensions and
cardinality, explicit stale/unknown/unavailable representations, and ordering,
coalescing, and gap behavior. Consumer eligibility does not grant the read
capability.

Stream producers expose sequence or cursor information when replay is
advertised. Consumers treat gaps as first-class state and use a cataloged
snapshot or scrape path to recover.

## Authorization

A request never supplies its own principal. The receiver binds authenticated
identity at the trust boundary, resolves the active policy, evaluates denials
before allows, applies confirmation and rate bounds, and records decision and
effect separately. Results and post-interaction evidence carry the
server-authored principal reference plus target, policy, replay, and
before/after-generation correlation. Policy covers both control operations and
access to information sources, including subscriptions, snapshots, scrapes,
and samples.

The startup circuit breaker belongs to the product profile. A disabled product
advertises a null control endpoint and does not listen. Enabling a listener
without an active policy still grants no operation.

The shared policy schema is deliberately thin. Enterprise issuance, signature,
enrollment, expiration, revocation, and offline behavior remain
deployment-specific until multiple independent adopters establish a common
lifecycle.

## Open payloads

The `value` member of payload and evidence objects is intentionally open because
its shape is governed by the adjacent schema URI and schema-artifact digest.
Consumers must resolve the exact digest, validate `value` against that schema,
and fail closed if the artifact is missing or mismatched. This is the only open
object-shaped surface in the family.

## Versioning

The `v0` family is experimental. Consumers pin the exact repository commit (or
a content-addressed bundle derived from it), schema identifiers, schema
artifact digests, and semantic layer version. Adding a semantic rule is a
contract change. Changing or removing a rule requires a new family version.
