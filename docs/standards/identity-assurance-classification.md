---
title: "Identity Assurance Classification"
description: "Evidence-based descriptions of identity binding, key custody, execution boundaries and platform claims"
category: "standards"
status: "draft"
version: "0.1.0"
lastUpdated: "2026-10-29"
maintainer: "3leaps-core"
reviewers: ["architecture", "security"]
approvers: ["lead-maintainer"]
tags: ["identity", "classifiers", "assurance"]
content_license: "CC0"
audience: "implementers"
---

# Identity Assurance Classification

These proposed classifiers describe what evidence establishes about a particular
subject, in a particular scope, at a particular time. They support useful
software-only operation as well as optional hardware evidence. They are not
ratings of a user's competence, compliance certifications, or access grants.

An application can use an observed machine identifier for inventory while another
requires an enrolled key for an approval. Both use the same vocabulary. A missing
TPM does not invalidate an otherwise successful software identity observation.

## Canonical dimensions

Each dimension has a canonical machine definition under
`config/classifiers/dimensions/`. The companion
[contract](identity-evidence-contract.md) binds classifications to subjects and
evidence. Values are opaque strings; display order is not a numerical threshold.
Consumers adopt explicit dimensions and accepted values. Adopted dimensions must
be present, using `unknown` when unestablished. Unadopted dimensions may be omitted.

### Identity binding: `identity-binding`

| Value | Established claim | Boundary |
| --- | --- | --- |
| `unknown` | Evaluation could not establish the requested binding | Does not mean the subject does not exist |
| `declared` | A source supplied a label or identifier | No independent observation or proof |
| `observed` | A collector obtained an identifier from a specified local OS or execution interface | Copyable/spoofable under that interface's trust boundary; remotely it remains that collector's report |
| `enrolled-key` | An accepted enrollment binds the subject to a key, and a fresh proof establishes possession | Does not establish exclusive possession or hardware custody |
| `attested-key` | An accepted attestation binds the exact key to the stated device/workload subject, with a fresh possession proof | Only the attested subject and properties are established; not an arbitrary hostname, operator role or uncompromised runtime |

These names provide concise confidence classes without collapsing other
dimensions into them. `attested-key` does not implicitly include a human
enrollment. A consumer requiring both must check both evidence sets. An enrolled
software key is a useful class, not a failed attempt to obtain hardware identity.

### Key custody: `key-custody`

| Value | Meaning |
| --- | --- |
| `unknown` | Custody of the exact key is unestablished |
| `not-applicable` | The assessed subject has no key in this assessment |
| `software` | Key material is software-held within the stated account/process boundary |
| `os-managed` | A specified OS service manages key access; hardware non-exportability is not established |
| `hardware-backed` | Applicable evidence establishes that the exact key's private operations remain inside the stated hardware boundary |
| `virtual-hardware-backed` | Applicable evidence establishes a virtual security-device boundary; host/provider and migration assumptions remain explicit |

`not-applicable` forbids a key reference. An existing key with unestablished
custody uses `unknown`.

Custody assessments bind a separate exact-key descriptor, not an enrollment
identifier. Rotation can preserve enrollment identity while replacing the key;
old custody evidence does not establish custody of the new key.

A hardware device being present does not classify any key. A remote signer is a
separate subject: its hardware custody must not be copied onto the client key.
Provider location belongs in evidence scope, not in a global assurance rank.

### Execution isolation: `execution-isolation`

| Value | Meaning within the named comparison boundary |
| --- | --- |
| `unknown` | Evaluation could not establish the requested boundary |
| `shared-account` | Compared workloads share an OS security principal; no additional separation established |
| `separate-account` | Distinct principals and relevant access controls separate the compared workloads |
| `os-confined` | Applicable OS confinement policy enforces the stated separation |
| `virtual-machine` | Guest boundary separates the subject from the specified outside workloads |
| `confidential-workload` | Applicable attestation establishes the stated protected execution boundary against the specified outside actor |

Every isolation assessment has a directed boundary with comparison-subject
references or an external-boundary selector, a pinned profile, and named threats.
It states both what is separated from what and what it is protected against.
No symmetric, transitive or inherited isolation follows from these relationships. Multiple processes
can be `shared-account` relative to each other inside a `virtual-machine` relative
to other guests. UID equality is useful evidence; ancestry, process groups and
different PIDs alone do not establish security isolation. Do not infer separation
from UID inequality without checking namespaces, administrative paths and access.

### Platform claims: `platform-evidence`

| Value | Meaning |
| --- | --- |
| `unknown` | Platform claim cannot be assessed |
| `declared` | OS, architecture or device type is supplied by the subject |
| `locally-observed` | A named local interface reports the claimed properties |
| `authority-verified` | An accepted external authority vouches for the exact properties and subject |
| `hardware-attested` | Verified hardware-rooted evidence covers the exact properties and subject |

Platform assessments select exact claim records: subject, property profile,
property, value and key reference where applicable. Evidence must cover each
selected claim; a general platform label cannot widen that property set.

Architecture detection selects candidate adapters. It cannot upgrade confidence.
An attestation that covers key origin but not OS version cannot establish the OS
version. A portable hardware token can establish its own identity without
establishing the identity of the computer to which it is connected.

## Assessment state is separate

An empty assessment array means evaluation has not occurred. An `unknown`
assessment means evaluation occurred but could not establish the requested claim.
A later evaluation produces a new immutable report with input-report provenance;
collection times are preserved.

Each scoped classification has a state: `current`, `stale`, `revoked`,
`conflicting`, or `unknown`. A historical hardware-backed classification can be
retained with `stale` evidence; it must not satisfy a current-evidence requirement.
Missing observations are not proof of revocation or absence. Conflicting evidence
is surfaced for the affected claim, not resolved by selecting the strongest label.

Capability results separately use `available`, `not-present`, `inaccessible`,
`unsupported`, `not-probed`, `error`, or `unknown`. Failure to open a device is
usually `inaccessible` or `error`; it is not proof that hardware is absent.

## Composition and user experience

A profile is a versioned set of predicates over these dimensions, subject scopes,
evidence acceptance and freshness. It may require alternatives or combinations.
Do not calculate a global score by averaging, summing, or taking the maximum.
Profile names and required guarantees must be visible alongside any short label.

Ordinary collection returns available facts and explicit gaps. Examples:

- "Machine identifier available. Key proof not requested."
- "Enrolled session key verified. Device evidence unavailable to this guest."
- "This operation requires a device-bound key; the current enrollment uses a
  software key. Select an accepted enrollment or use the configured approval path."

The last message belongs to an operation-specific policy decision, not to every
invocation of an identity library. Discovery does not enroll, provision keys,
prompt for credentials, contact an attestation service, or change host settings
without an explicit caller request.

Data sensitivity and identity assurance remain independent dimensions. This
standard assigns no universal mapping from a sensitivity level or regulatory
regime to a deployment. Adopters own their operation requirements.

## Adoption and review

The values and evidence rules are proposed, not a released assurance scheme.
Before adoption, qualify each supported provider and define its accepted roots,
subject binding, proof algorithms, freshness, clone behavior, and refusal cases.
The shared logical corpus checks classification rules; it cannot qualify native
hardware or demonstrate a cryptographic verifier's correctness.
