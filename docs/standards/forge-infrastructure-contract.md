---
title: "Portable Forge Infrastructure Contract"
description: "Seven-lane model for resolving forge requirements, authority, native features, automation, events, and assurance"
category: "standards"
status: "draft"
version: "0.0.0"
lastUpdated: "2026-08-27"
maintainer: "core-standards"
reviewers: ["architecture", "security", "information-architecture"]
approvers: ["lead-maintainer"]
tags: ["forge", "git", "capability", "authorization", "interoperability"]
content_license: "CC0"
relatedDocs:
  - "docs/guides/using-the-forge-infrastructure-contract.md"
  - "docs/standards/agent-wait-contract.md"
  - "docs/standards/auth-session-artifact.md"
  - "docs/standards/data-artifact-contract.md"
  - "docs/standards/process-run-contract.md"
  - "docs/standards/project-work-contract.md"
  - "docs/standards/review-journal-contract.md"
  - "docs/standards/service-job-contract.md"
audience: "implementers"
---

# Portable Forge Infrastructure Contract

This draft defines `contract: forge-infra/v0`: a portable way to resolve what
a forge can do, which provider-native feature does it, which authority may
exercise it, and whether a live binding still conforms.

The contract is a capability-resolution and control model. It is not a common
provider SDK, a `gh` proxy, or a credential envelope.

## Seven-lane model

The model separates facts and actions that have different authorities and
lifecycles:

| Lane | Concern               | Contract representation                                                     |
| ---- | --------------------- | --------------------------------------------------------------------------- |
| L1   | Intent and resolution | Requirement profile and digest-bound binding plan                           |
| L2   | Authority control     | Authority profile, policy-input facts, transition receipt                   |
| L3   | Native git data       | Hosted-container and content CRUD capability; native git execution boundary |
| L4   | Forge resources       | Issues, snippets, packages, releases, wikis, and governance objects         |
| L5   | Automation            | Workflow definitions, workflow runs, jobs, and runners                      |
| L6   | Events and telemetry  | Subscription, status, and check capabilities; delivery boundary             |
| L7   | Assurance             | Evidence, time-bounded verification, drift, reconciliation, and revocation  |

L3 through L6 form the neutral capability catalog. L1, L2, and L7 govern how a
consumer selects, authorizes, executes, and verifies those capabilities.

Earlier F0–F5 labels are non-normative aliases and are not contract fields.

## Design stance

- **Neutral vocabulary, curated mappings.** Portable meanings and
  provider-native facts remain separate.
- **Provider context is explicit.** A provider id is combined with an instance
  or offering context; hosted and self-managed deployments are not assumed to
  behave alike.
- **Operation-level honesty.** Support is asserted for an operation under a
  named authority profile, not for a feature name in the abstract.
- **Mint is not authority.** Registration, installation, consent, token
  issuance, binding, and verification are separate transitions.
- **Receipts are not credentials.** Contract artifacts carry identifiers,
  facts, and evidence references, never secret values.
- **Binding is not current authority.** A binding receipt records a completed
  transition; a time-bounded verification receipt reports live conformance.
- **Evidence expires.** Provider and acquisition claims carry source
  references and observation timestamps.
- **Consumer policy stays downstream.** Adopters state requirements without
  rewriting provider facts.

## Contract discovery and catalog identity

Contract documents carry:

```json
{
  "capabilities": ["contract: forge-infra/v0"]
}
```

The schema-registry entry point is
`schemas/forge-infra/v0/contract.json`. It exposes:

- the entry schema;
- the canonical neutral catalog; and
- every public object schema in this contract family.

Consumers resolve the capability token through a trusted registry or vendored
schema set, verify the manifest capability, and load the relative targets.

Every provider, requirement, plan, and object-reference document pins a
`catalog_ref` containing the catalog id and revision. A publisher MAY add a
SHA-256 digest. All document digests in this contract use RFC 8785 JSON
Canonicalization Scheme bytes. A resolver MUST reject documents whose catalog
reference does not match the selected catalog.

Path versioning follows ADR-0001. The `v0/` family is unstable; consumers
should pin a reviewed repository revision.

## L1: intent and resolution

### Requirement profile

A requirement profile expresses provider-neutral needs. Each row names:

- a neutral capability;
- one or more operations;
- a disposition (`required`, `preferred`, `allowed`, or `forbidden`); and
- optional allowed authority classes.

The profile does not select a provider or prescribe a provider grant.

### Binding plan

A resolver evaluates a requirement profile against a catalog, provider
profile, authority profiles, provider context, and target structure. Its
output is a binding plan containing:

- satisfied, partial, unresolved, and unknown operation resolutions;
- exact provider-native grants and interaction modes;
- ordered acquisition, install, consent, provision, bind, verify, rotate,
  revoke, or teardown actions;
- closed policy-input facts; and
- explicit gaps.

The plan pins the requirement digest and provider-profile revision. Its
`plan_spec_digest` is the RFC 8785 SHA-256 digest of `plan_spec`.
Side-effecting execution MUST bind its idempotency key and policy decision to
that digest.

Authority-action sequence numbers MUST be contiguous from one. Every action
other than `verify` declares the binding transition it produces. Verification
produces its own receipt and therefore declares no binding transition.

The portable contract defines policy input, not the policy engine. OPA/Rego or
another PDP may evaluate the facts. The resulting decision remains an opaque
`policy_decision_ref`; it is not embedded as provider data.

The policy-input target MUST match the execution target. Its requested
capability-operation, authority-profile, and provider-native grant tuples MUST
exactly match the plan's satisfiable resolutions. Its ordered authority-action
summaries MUST exactly match the plan's executable authority actions. These
facts are part of the same digest-bound plan; re-digesting internally
inconsistent facts does not authorize them.

## L2: authority control

### Authority profiles

An authority profile describes one provider-native principal or credential
class without credential material. The vocabulary distinguishes:

- anonymous access;
- application assertions and installations;
- application and OAuth user grants;
- personal, project, and group access tokens;
- deploy, job, workflow, and runner registration tokens; and
- service accounts.

`native_name` preserves the provider term. `authority_class` supplies the
portable category. Provider context, principal scope, resource selection,
grant model, acquisition mechanism, and lifecycle operations remain distinct.

Acquisition modes are:

| Mode               | Meaning                                                    |
| ------------------ | ---------------------------------------------------------- |
| `api`              | A documented API creates or exchanges the authority object |
| `operator_handoff` | A human completes a documented provider workflow           |
| `automatic`        | The provider issues authority during another lifecycle     |
| `unsupported`      | The authority cannot be acquired in this context           |

An operator handoff MUST include an operator URI template. Implementations
MUST NOT scrape provider user interfaces.

Every acquisition path cites evidence from the authority profile. A resolver
MUST verify those references and the provider context before using the
profile.

### Binding transitions and receipts

Authority changes are immutable transitions:

`registered → installed → consented/provisioned → bound → rotated/reconciled →
revoked → torn_down`

Not every provider uses every transition. A binding receipt records exactly
one attempted transition and its outcome. It carries:

- provider context, authority profile, subject, and optional target;
- binding-plan id, plan-spec digest, action sequence, and idempotency key;
- an opaque policy-decision reference;
- public provider identifiers and provider-native grants;
- an optional non-secret reference to an auth session; and
- transition time and outcome.

A receipt MUST NOT contain access or refresh tokens, client secrets, passwords,
private keys, PEM material, webhook secrets, signing tokens, or runner
registration tokens. Secret storage, delivery, and expiry are outside this
contract.

`contract: auth-session-artifact/v0` may provide value-stripped provenance and
expiry for a session. It is not a binding receipt and carries no forge binding
identifiers.

Side-effecting acquisition, bind, rotation, revocation, and teardown SHOULD
run through `contract: service-job/v0` or an equivalent boundary that enforces
digest binding and idempotency.

A planned receipt at action sequence two or later MUST reference the receipt
for the immediately preceding receipt-producing action in the same plan,
provider context, authority, and target. Actions such as `verify` that declare
no binding transition are skipped when identifying that predecessor. The
predecessor MUST have succeeded. Sequence one may begin from a newly planned
action or declare `history_basis: imported` when the provider object predates
the portable receipt chain. A failed, partial, or unknown transition MUST NOT
be bypassed or advance the chain.

## L3–L6: neutral catalog and provider profiles

### Neutral capability catalog

The canonical catalog defines stable capability ids, one lane, allowed
operations, and a portability class. It contains no provider products,
permission strings, token prefixes, or commercial offerings.

The v0 operation vocabulary is:

`discover | read | create | update | delete | execute | cancel | observe |
subscribe | receive | administer`

Portability classes are:

| Class                | Meaning                                                            |
| -------------------- | ------------------------------------------------------------------ |
| `portable`           | Providers expose substantially equivalent semantics                |
| `convergent`         | Providers share the job, but lifecycle or shape differs materially |
| `provider_extension` | Useful provider-native capability with no honest shared floor      |

Portability is not availability. Provider profiles make availability claims.

### Curated provider profiles

A provider profile maps native features to neutral capability operations.
Every operation cell names:

- the neutral operation and authority profile;
- availability (`supported`, `partial`, `emulated`, `unsupported`, or
  `unknown`);
- interaction modes;
- exact required provider grants, including an explicit empty set;
- evidence references and limitations; and
- an optional neutral fallback.

Profiles carry a provider context and revision. Provider ids are extensible,
not a closed vendor enum. Context distinguishes instance, deployment kind,
base URI, offering, and version where relevant.

A producer MUST NOT publish `supported`, `partial`, or `emulated` without
dated evidence. `unknown` means the mapping has not been established.

### Lane boundaries

- **L3 native git.** The catalog distinguishes the hosted repository container
  from repository content. It can state that a principal may administer the
  remote and read, create, update, or delete content through native git or a
  mapped provider contents API. Repository and content execution stays in git
  or repository tooling; this contract defines no blob/tree/commit schema,
  command model, or generic forge proxy.
- **L4 forge resources.** Provider-native objects use `forge-object-ref`.
  Published byte bags remain governed by `contract: data-artifact/v0`.
- **L5 automation.** A workflow definition and a workflow run are different
  capabilities. Runs are observed or cancelled; execution is requested through
  the definition or a provider-native dispatch. Forge automation may implement
  service jobs, but does not replace their admission and result contract.
- **L6 events and telemetry.** Subscription management is a forge capability.
  Event delivery is a separate integration. An agent may wait for a payload
  reference through `contract: agent-wait/v0`; `contract: process-run/v0`
  governs only a local receiver process; `contract: data-artifact/v0` governs
  payload or log bags. This contract does not normalize delivery envelopes,
  retries, acknowledgement, or signature verification.

## L7: verification, drift, and evidence

A binding receipt alone does not prove current authority. A verification
receipt observes one binding and reports:

- verification and expiry times;
- methods used;
- expected, observed, missing, and unexpected grants;
- operation-level capability checks; and
- an outcome such as conformant, drift, denied, revoked, expired, or unknown.

Verification MUST be time-bounded. Consumers MUST NOT treat an expired
verification as current authority. Drift SHOULD trigger an explicit reconcile,
rotate, revoke, or teardown plan; it MUST NOT silently escalate grants.
`verified_at` and `valid_until` are RFC 3339 instants and MUST be compared
chronologically after offset normalization, never lexically.

A `conformant` outcome requires observed grants to match the resolved plan and
binding receipt, no missing or unexpected grants, and allowed results for every
reported capability check. It also requires a successful `bound`, `rotated`, or
`reconciled` receipt; registration, installation, consent, or provisioning is
not usable authority. A `drift` outcome requires a grant delta or a
denied/unknown capability check. Every satisfiable required operation in the
linked plan MUST have a capability check.

Relied-upon human or automated review evidence remains governed by
`contract: review-journal/v0`. Provider checks and statuses may project an
outcome but are not the journal.

## Forge object references

`forge-object-ref` locates one provider-native object. Identity consists of:

- catalog reference and provider context;
- neutral capability id;
- provider-native id; and
- optional repository path.

Credentials, authority-profile ids, binding-receipt ids, and consumer record
ids are access context, not object identity.

## Required operational sequence

Implementations follow this sequence:

1. requirement;
2. resolution plan;
3. opaque policy decision;
4. digest- and idempotency-bound execution;
5. non-secret binding receipt;
6. time-bounded verification;
7. use and observation; and
8. drift reconciliation, revocation, or teardown.

Registration or token issuance MUST NOT be reported as usable authority before
the applicable bind and verification steps succeed.

## Cross-document invariants

JSON Schema validates individual documents. Producers and consumers MUST also
enforce:

1. Catalog ids are unique; parent ids resolve within the same revision.
2. All `catalog_ref` values match the selected catalog id and revision.
3. Provider mappings, operations, and fallbacks resolve to the catalog.
4. Provider operation cells are unique and all evidence references resolve.
5. Authority-profile references exist in the same provider context.
6. Authority acquisition evidence references resolve.
7. Requirement operations exist on the neutral capability.
8. Binding-plan refs, revisions, digests, contexts, policy facts, resolutions,
   contiguous action sequences, and action-to-transition mappings resolve.
9. Binding receipts match a specific plan action, target, authority, and
   provider context; successor links cite the immediate receipt-producing
   predecessor and never bypass or advance a non-successful receipt.
10. Verification receipts match their binding and plan action, have a finite
    chronologically ordered validity interval, require a successful usable
    binding for conformance, and substantiate conformant or drift outcomes.
11. Object references resolve to the selected catalog.

The fixture and control battery is
`scripts/test-forge-infra-controls.sh`. Implementations publishing arbitrary
document sets MUST enforce equivalent invariants for their own registry.

## Out of scope for v0

- A universal provider SDK or common endpoint set
- Credential storage, exchange, signing, or secret verification
- Provider UI automation or automatic permission escalation
- A complete vendor grant catalog frozen into Crucible
- Webhook payload normalization, retry queues, or poison-message handling
- Provider billing, quota, or commercial entitlement negotiation
- Treating hosted issues, automation, or callbacks as revision authority by
  default

## Schema identity and publication

Schema `$id` values are hostless:
`contract:forge-infra/v0/<file>`.

Publication URLs are retrieval conveniences, not provider-instance identity.
Consumers resolve sibling schema ids through the selected trusted registry or
vendored schema set.
