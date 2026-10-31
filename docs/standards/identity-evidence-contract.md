---
title: "Identity Evidence Contract"
description: "Portable observations and scoped assurance assessments for hosts, workloads and keys"
category: "standards"
status: "draft"
version: "0.1.0"
lastUpdated: "2026-10-29"
maintainer: "3leaps-core"
reviewers: ["architecture", "security"]
approvers: ["lead-maintainer"]
tags: ["identity", "evidence", "contracts"]
content_license: "CC0"
audience: "implementers"
---

# Identity Evidence Contract

`identity-evidence/v0` is a proposed report format for identifying a subject and
describing the evidence available for its binding. It is independent of an issuer,
agent framework, cloud, operating system, implementation language, or policy
engine. It neither grants authority nor defines a new signing protocol.

## Objects and roles

| Object     | Purpose                                                                                                           |
| ---------- | ----------------------------------------------------------------------------------------------------------------- |
| Report     | Immutable observation/evaluation snapshot with producer provenance and evaluator identity when assessed           |
| Subject    | Report-local reference to a physical device, OS installation, VM, container, process, session or key holder       |
| Identifier | Names one subject within an explicit namespace and lifecycle; not a bearer credential                             |
| Key        | Identifies exact public-key bytes under a pinned representation profile, separately from an enrollment identifier |
| Claim      | A named property and typed scalar value under a pinned property profile, about one subject and optionally one key |
| Evidence   | Reference to bounded evidence, its method, collector, source subject and collection time                          |
| Assessment | One classifier value for one subject and scope, supported by named evidence and a versioned evaluation rule       |
| Capability | Result of an explicitly requested provider probe, independent of assessment success                               |

The [schema](../../schemas/identity-evidence/v0/report.schema.json) checks shape.
It cannot establish that a reporter is honest or a signature is valid. A receiver
must authenticate an accepted evaluator, or independently evaluate the evidence.
An untrusted report is a claim even if every JSON field says `current`.

All profile references have an `id` and a `sha256:` revision digest. The digest
pins the exact profile artifact bytes; a mutable name alone is insufficient.
Profiles specify their own machine-resolvable vocabulary and validation rules.
An unknown or unaccepted profile cannot establish a trusted assessment.

## Observation, evaluation and provenance

An observation-only report has an empty `assessments` array and no `evaluator`.
It means evaluation has not occurred. An assessment with value/state `unknown`
means evaluation occurred but did not establish the requested claim. Any nonempty
assessment array requires an evaluator, including unknown-only results. Neither
form requires a remote service; collection and evaluation may be local.

Later evaluation creates a new immutable report. `input_reports` names each input
by report ID and SHA-256 of its complete RFC 8785 canonical JSON bytes. A report ID
alone is not content identity. Carried-forward evidence and capability records
include `origin.input_ref` and `origin.record_ref`. Preserve their original IDs,
collection/observation times and descriptors, and their referenced subject,
identifier, key, claim and comparison-subject descriptors. The new origin points
to the immediate input; earlier origins remain available through that input.
This v0 rule deliberately forbids silently remapping imported local references.
Colliding, unequal imported descriptors require separate reports or a future
explicit remapping contract, not overwrite-on-merge.

Resolve input reports and require both their embedded `report_id` and canonical
digest to match the input reference before accepting that provenance. Compare
imported descriptors using JSON value semantics: booleans are distinct from
numbers, object member order is immaterial, array order is preserved, and equivalent
numeric values within the accepted property domain compare equally.
If unavailable, provenance verification is incomplete. Resolving evidence or
profiles is an explicit bounded consumer operation, not an automatic network
fetch by schema validation. New collection has a new record; it does not refresh
the timestamp of old evidence. Input provenance does not imply that any input
report or collector is trusted.

## Evaluator implementation and authority

`evaluator.software` identifies implementation name and revision.
`evaluator.principal` identifies a claimed authority by namespace and value.
`evaluator.verification_profile` pins the rules under which a receiver may accept
that authority. A name, code hash or principal string is not authentication.

An accepted verification profile must specify:

- How the evaluator principal is authenticated and which roots or local execution
  context the consumer accepts. Producer provenance is a separate question.
- How that principal is bound to the complete report, including input digests,
  all assessments, exact keys, property claims, boundaries and evidence digests
  and descriptors. Binding only the report ID or software revision is insufficient.
- Report canonicalization and any detached proof/envelope representation,
  algorithm/key encoding, audience/freshness/replay checks, authority lifetime,
  revocation and unavailable-verifier behavior.
- Which evidence the evaluator must independently verify and which authenticated
  collection sources it may accept, with exact subject/key/property binding.

For detached report authentication, the canonical report includes the evaluator
descriptor; the proof lives outside those bytes to avoid a self-reference. For
an in-process evaluation, the profile specifies the accepted call/execution
boundary. This contract defines neither signing protocol nor trust installation.
The draft examples use synthetic profile references and provide no authenticated
principal or proof. A receiver that independently evaluates evidence issues its
own report; it does not promote an untrusted evaluator label.

## Evidence format selection

Every evidence record, including in an observation-only report, requires a pinned
`format_profile` (ID and exact artifact revision digest). The profile identifies
the payload grammar/encoding, provider semantics, supported evidence methods and
verification prerequisites. This is distinct from the evaluation rule that uses
the evidence. A consumer selects handlers through accepted configuration and
verifies authenticated bindings of the evidence descriptor, profile and payload.
A source/collector string is descriptive provenance, not decoder selection or
permission to execute code or fetch a URL. An unknown profile is unsupported;
an unavailable payload is unavailable; a malformed payload or failed proof is
invalid. Preserve those outcomes separately.

Profile resolution is explicit and bounded. A profile reference in a report does
not cause automatic network retrieval or make that profile an accepted trust
policy. Evaluated reports cannot override these rules by naming a different
assessment rule. Profile authenticity, permitted algorithms and evidence freshness
must still be established under the consumer's accepted verification policy.

## Initial subject scope

This version covers host, installation, VM/container, process, session and key
holder evidence. Human and account identity are deferred. `key-holder` must not
silently mean a person or an account. An authority principal or native security
principal in a provider profile is an opaque scoped reference, not a report-level
claim about a human. Future account support should begin with an authority-scoped
opaque account reference, with any link to a person represented separately.
Account authentication, key possession, presence, user verification and action
approval remain distinct. Approval needs explicit action, audience and lifetime
binding; it cannot be inferred from a general identity classification.

## Identifier semantics

An identifier records `subject_ref`, `namespace`, `value`, `derivation`,
`stability`, and `clone_behavior`. Equality requires the same namespace,
derivation and value, not just the displayed bytes. It establishes identifier
equality, not exclusive physical-machine identity.

- `stability`: `unknown`, `process`, `boot`, `installation`, `enrollment`, or
  `device`. This is the intended lifecycle, subject to the provider's documented
  repair/reset/rotation behavior, not a promise of perpetual persistence.
- `clone_behavior`: `unknown`, `copyable`, `regenerated`, or `device-bound`.
  `regenerated` requires an established provisioning rule; detecting a VM does
  not establish that its images receive fresh identity on cloning.
- `derivation` identifies a versioned canonicalization/derivation profile.
  Algorithm changes never silently preserve the same profile identity.

A random enrollment ID and the fingerprint of an enrolled public key are distinct.
An approved rotation may preserve the former and changes the latter. Identifier
comparison cannot authorize recovery, rotation, merging or automatic reenrollment.

`keys` is a separate collection. Each descriptor has a subject, a pinned
`representation_profile`, and `public_key_digest` over that profile's canonical
public-key bytes. That profile must specify the algorithm, public parameters,
encoding and normalization; the digest alone cannot identify an unspecified key
encoding. No private key is carried. `key_ref` binds proof, enrollment, custody
evidence and key assessments to that exact descriptor. `identifier_ref` continues
to name the subject/enrollment identity. They are not interchangeable references.

An `enrolled-key` assessment needs enrollment evidence linking the exact identifier
and key, plus possession proof for that key. An `attested-key` assessment needs
the attested identifier/key binding and possession proof for that key. Custody
is assessed against `key_ref`, not against an enrollment ID. A `not-applicable`
custody assessment forbids `key_ref`: no key is involved in that assessment. If a
key exists but its custody is unestablished, use `unknown`, optionally naming that
key, rather than `not-applicable`. Rotation may retain
the enrollment identifier while adding a different key descriptor. Old proof and
custody evidence remain tied to the old key and cannot satisfy the new assessment.
The [rotation example](../../schemas/identity-evidence/v0/examples/software-key-rotation.json)
preserves old assessments as stale and supplies new evidence for the new key;
it does not define or authorize a rotation ceremony.

Do not use NIC lists, hostnames, IP addresses or changing hardware inventories as
the default stable identity input. Native OS IDs are observations with their own
scope: an installation ID is not a physical-device attestation. UUIDv5 is a name
derivation mechanism, not a proof or secret. A versioned identifier profile may
use it for naming; changing its inputs changes its result.

Raw serials and native machine IDs should remain local unless explicitly needed.
Use an application/tenant-scoped derivation profile or an independently random
enrollment identifier for exported records. A public namespace hash is not a
secrecy guarantee for low-entropy inputs. Keyed derivations must state who holds
the key, rotation semantics and the correlation boundary. Do not derive private
keys from fingerprints, timestamps, PIDs or comparison codes.

## Evidence and evaluation boundary

Evidence records require `format_profile` as specified in [Evidence format
selection](#evidence-format-selection), including when no assessment exists. The
pinned profile specifies the evidence byte format and digest preimage. Evidence
records contain a digest reference, not a raw credential or private key.
The digest identifies evidence bytes; it is not authentication of those bytes.
Evidence methods in this draft are declaration, OS observation, enrollment,
possession proof, device attestation, workload attestation, authority statement,
custody observation and isolation observation.

Each assessment binds a subject and an identifier where applicable. The evaluator
rule identifies the exact revision, and the assessment gives `assessed_at`,
`valid_until`, state, evidence references and residual assumptions. A scope string
is an identifier for a documented comparison/policy context, not free-text proof.
Different isolation scopes can coexist for one subject. The rule itself is a
pinned profile reference. A display `scope` string does not replace the typed
boundary or property selectors described below.

Each report permits at most one assessment per `(subject_ref, identifier_ref,
key_ref, dimension, scope, boundary_identity, sorted(claim_refs))`, with missing
optional references distinct from present ones and boundary identity normalizing
comparison-subject/threat arrays as sets; refreshing that tuple produces a new
immutable report with input provenance, not a second entry in the same array.

## Explicit isolation boundaries and platform properties

Every execution-isolation assessment includes a `boundary` with a pinned profile,
`comparison_subject_refs`, and profile-defined `threats`. At least one comparison
subject or an `external_boundary` selector is required. The profile defines what
each threat means and, for external selectors, which actors/population it covers.
The assessment subject is the protected side; comparison subjects/external actors
are the other side. The value describes whether and how the requested boundary
was established. `shared-account` is a valid result with no additional established
separation, not a claim that the listed threats are prevented.

Comparison-subject and threat arrays are sets: ordering has no semantic meaning.
Supporting isolation evidence must concern that same directed boundary, profile
revision and threat set. No symmetry, transitivity or inheritance is implied.
A guest assessment against neighboring guests cannot become an assessment of
same-account processes inside that guest. Reversing the subject/comparison sides,
adding an actor or threat, or composing two boundaries requires its own evaluation.

Every platform-evidence assessment names one or more `claim_refs`. Each claim
contains an exact subject, pinned `property_profile`, machine-resolvable
`property`, scalar `value`, and `key_ref` when the property concerns a key. The
property profile defines its type, units, meaning, applicable subject/key, and
verification requirements. Claim values remain assertions until evaluated.
Each cited claim must have applicable supporting evidence naming that exact
claim. A hardware-attested key-origin property cannot establish OS version,
runtime integrity or any other uncited property. References are necessary binding
checks; the verifier must still prove that evidence actually covers those values.

Before an assessment can be used as current evidence, an accepted evaluator must:

1. Resolve unique subject, identifier, key, claim, input and evidence references;
   ensure each cited evidence item concerns the assessed subject, key, property
   and comparison boundary. Reference matching alone does not prove the relationship.
2. Verify method-specific evidence under a pinned provider/evaluation profile.
   Check source authenticity, accepted roots, exact public-key/subject binding,
   algorithms, request/audience binding, challenge freshness and replay handling
   where required. Evidence from the issuer's key cannot establish client custody.
3. Check the assessment window and evidence freshness at use time, including the
   applicable revocation source and explicit outage behavior. An evaluator's
   local clock and an authenticated remote timestamp are different trust inputs.
4. Apply the selected consumer profile. A successful observation may still leave
   a particular operation's required predicates unsatisfied.

`enrolled-key` requires accepted enrollment plus fresh possession proof for the
same exact key and subject. `attested-key` requires accepted device/workload
attestation plus fresh possession proof for the same exact key and subject.
Hardware key custody requires evidence about that key's custody, not simply a
TPM capability result. Platform evidence covers only named properties certified
by the accepted authority. Human approval alone cannot establish hardware custody.

The logical controls in this proposal check references and necessary evidence
method combinations. They do not implement cryptographic verification, root
acceptance, revocation, policy authorization or replay persistence. Passing them
does not produce a trusted assessment.

## Collection and failure behavior

Collection is read-only by default and accepts an explicit probe budget and
provider selection. Provider probing, enrollment, proof generation, hardware
interaction and remote verification are separate operations. Optional provider
absence is a normal result. A malformed report or contradictory typed references
is a contract error; a correctly represented inaccessible device is not.

Capability output distinguishes unsupported implementation, device not present,
device inaccessible, not probed, transient/error and unknown. Only use
`not-present` when the selected scope permits an actual absence conclusion.
A guest unable to see its host's hardware reports its guest visibility, not a
claim about physical host inventory. Do not silently fall back under the same
enrolled identity when a required provider becomes inaccessible.

Report snapshots are immutable. New observations yield new reports; consumers
must not refresh old timestamps or promote cached labels merely because parsing
succeeds. Revocation or conflicting evidence affects the relevant assessment,
without erasing unrelated observations or historical provenance.

## Process and platform scope

Host, OS installation, VM, process and session are separate subject kinds. Process
identity requires an incarnation-aware observation profile: PID namespace/boot
context, PID and start identity or retained native process handle as available.
PID reuse, process exit, namespace changes and partial visibility are explicit
outcomes. Serialized handles are not portable proof; a live adapter owns their
lifetime and the consumer must revalidate at the relevant use boundary.

Ancestry and peer credentials can attribute local process activity without
separating hostile same-account workloads. VM isolation from other guests does
not imply isolation between processes sharing an account inside that VM. A
verified helper release proves origin of bytes, not which process ran them.
Local chip/OS detection remains observed unless accepted evidence covers it.

A [local process/session contract-fit profile](../../schemas/identity-evidence/v0/profiles/local-process-session/README.md)
works through incarnation, execution context, launch intent, session/key, audience,
challenge and lifetime binding. It is a proposed software-only slice. Its explicit
verifier inputs are synthetic test inputs, not authentication supplied by the
untrusted evidence itself. A launch receipt and key proof establish no appointment,
permission or same-account isolation. The consumer must reassess required predicates
at admission/use. Preserving a report in a checkpoint preserves historical evidence,
not a right to restore expired session authority. The verifier must bind the evidence
descriptors and the assessment's actually cited claims to the verified bundle's
method, subject, identifier and exact key as applicable. An unused matching claim
cannot justify a different selected claim. Assessment expiry is checked at verifier
time independently of receipt/challenge expiry; reevaluation creates new immutable
assessments rather than refreshing the old result.

## Portability and conformance

Rust and pure Go implementations consume the same versioned contract and vectors.
No C ABI is required by this format. The common corpus supplies synthetic
observations, evaluator inputs, expected normalized output and expected errors.
Expected answers are authored from the contract, never captured from one twin and
declared correct for the other. Normalize deterministic JSON using RFC 8785;
keep time, randomness and native evidence as explicit test inputs. Do not compare
random keys, live timestamps or provider-specific attestation bytes for equality.

Native provider qualification is a separate corpus: OS/architecture/version,
permissions, bare metal/VM/container, device access, reset/clone, reboot, PID reuse,
same-account neighbors and key lifecycle. A platform without a hardware provider
can pass its declared software-only profile. Qualification of one platform does
not qualify another, or a hardware provider hidden by a mock.

This draft includes vocabulary definitions, a closed report schema, synthetic
reports and structural/necessary-condition controls. Full proof profiles,
normalized evaluation vectors and native provider implementations remain to be
specified before a library release claims conformance.

The draft schema bounds each record/reference array to 256 items and ordinary
strings to 512 characters. The experimental [report admission profile](../../schemas/identity-evidence/v0/profiles/report-admission/README.md)
adds a 256 KiB received/canonical report cap, JSON nesting depth 16 and separate
provenance dependency depth 4. The profile defines the canonical input domain and
explicit resolver budgets; only the wire parsing limits have detecting controls
in the initial corpus. Limits remain revisable during v0 field iteration.

Optional `time_attribution` is available on the report, evidence, assessment and
capability objects, bound respectively to `created_at`, `collected_at`, `assessed_at`
and `observed_at`. Its `instant` must equal that scalar exactly. The object reuses
[durable-record v1's timestamp pattern](durable-record-v1-contract.md#production-time-instants-and-ordering):
`instant`, `source`, and `evidence` required for `trusted_time`; `producer_clock`
forbids evidence. Trusted-time evidence pins its format and digest, with an optional
opaque reference. Source assertions remain unverified until their authority and
exact target are authenticated. Original collection times and attribution remain
immutable through imports; policy deadlines carry no time attribution.

Identity instants retain whole-second UTC. Durable-record's fixed-microsecond type
is not interchangeable. The admission profile defines conservative projection and
uncertainty handling; provider verification and time-oracle qualification remain
separate. Ordinary local-clock operation remains valid, and absent optional time
evidence does not suppress unrelated observations. A consumer requiring verified
time must refuse an unmet predicate.

Use collision-resistant generated report and record IDs; report digests retain
content identity. Readable fixture IDs are not an allocation scheme. Native process
incarnation retains its own precision. Final ID generation, provider/proof suites,
resolver enforcement, time-boundary vectors and full twin conformance remain
review items before wire freeze or a library conformance claim.
