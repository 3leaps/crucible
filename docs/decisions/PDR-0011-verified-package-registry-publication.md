---
id: "PDR-0011"
title: "Authorize package registry publication against the verified final archive"
status: "proposed"
date: "2026-10-23"
last_updated: "2026-11-23"
deciders:
  - "@3leapsdave"
  - "cxotech"
scope: "Crucible foundation / adopting repositories' package registry publication"
tags:
  - "process"
  - "release"
  - "verification"
  - "governance"
relates-to:
  - "PDR-0008 (committed identity and explicit ceremony inputs)"
  - "PDR-0010 (forge publication and separate distribution surfaces)"
  - "EPR-0002 (resolved-state evidence and discriminating negative controls)"
---

# PDR-0011: Authorize Package Registry Publication Against the Verified Final Archive

## Status

**Proposed.** This record defines a publication profile for repositories that
adopt it through reviewed tooling and a release checklist. It does not authorize
a registry upload or claim that an existing implementation conforms.

Graduation to **accepted** requires a first adopter to publish under this
profile with the EPR-0002 evidence below, followed by a recorded acceptance
decision. A draft implementation or successful isolated test is not that
publication evidence. Existing implementations may be evaluated as adoption
candidates. Their presence or a successful release alone does not establish
conformance with this profile or change this record's status.

## Context

Package verification can compile source and execute dependency build scripts or
compiler extensions. Publication uses a credential to upload an archive. These
operations need different authority, even when a package manager combines them
in one command. Clearing environment variables or choosing a new home directory
changes configuration discovery; it does not create a filesystem boundary.

A second distinction is the archive's identity. A publication command may
repackage source after a successful verification. Verifying one archive and
authorizing another does not establish that the published bytes were checked.

## Decision

**Compilation and publication authority are separated. Publication is authorized
for the final registry, package name, version, and archive digest, and completion
requires verification of what the registry actually serves.**

### 1. Separate verification from credentialed publication

Run verification that executes package or dependency code in disposable CI with
no access to the maintainer account's filesystem, signing or registry
credentials, or writable state later used by the publisher. Repository access
is read-only; checkout credentials are not persisted. Declare and restrict any
artifact-service capability required to return results.

The maintainer-side ceremony runs reviewed orchestration and a pinned package
toolchain. It does not compile or execute package/dependency code. Source,
manifest paths, configuration discovery, and archive handling are validated
before use. Build-produced configuration or executables are not imported into
the publishing environment. Use fresh publisher state that verification code
cannot modify; a new directory under the same account is not sufficient when
that account also executes untrusted verification code.

This profile assumes a trusted host, toolchain, and reviewed control code. It
does not claim to repair a compromised maintainer account or prove that a
dependency is benign. Ordinary development builds are outside this ceremony's
scope. A different execution boundary or accepted residual risk requires an
explicitly reviewed alternative profile; a green build is not that approval.

### 2. Retain the identity of the archive actually verified

The verification record binds the repository, verified source revision and tag
objects where used, verification workflow revision, run and attempt, artifact
identity, toolchain version, package name/version, and archive SHA-256 digest.
Retain the archive that the successful verification consumed, with its digest
captured before any subsequent repackaging. Where verification executes code,
protect the reference archive from that code's writes or compare it with a
protected pre-execution digest before accepting the result.

Retrieve artifacts from that selected run and verify their bytes against the
record. Do not select an artifact merely by a reusable name or the latest run.
The record is evidence with a declared execution boundary, not independent
release authorization. A digest beside an archive does not authenticate either
one; the ceremony also verifies the record's origin and source binding.

### 3. Bind authorization to the final upload

Before transmission, the publisher checks the actual final archive against the
approved digest and binds authorization to the intended registry, package name,
and version. Any request metadata outside the archive is derived by reviewed
tooling from the approved package and checked for consistent identity and
dependency declarations. Fix packaging inputs, lockfile, toolchain, registry
selection, and configuration across verification and publication.

If the publication tool repackages, comparing an earlier package output is not
the final upload check. Use a reviewed mechanism that checks the archive the
tool will transmit before releasing publication authority. It must refuse a
different destination, identity, or checksum and must not have a direct-token,
alternate-provider, or cached-authorization bypass. Do not fall back to an
ungated upload when the mechanism is unavailable. Post-publication detection
does not substitute for this check.

A direct uploader of an approved archive is another possible mechanism, but
its registry metadata, authentication, response handling, and archive identity
are part of the reviewed publisher. This record does not require building a
new uploader.

### 4. Declare transformations instead of claiming false byte equality

Prefer verification of the exact final archive. For dependent packages, this
may mean a second credential-free verification after a predecessor becomes
available in the registry.

If an adopter permits a packaging transformation, define and review it before
publication. Record the original verified digest, the rule, and the final
approved digest. Name the claim as equivalence under that rule, not byte
identity. The rule must compare the complete package inventory and all
unaffected content, rejecting missing or unexpected members, ambiguous entries,
and unsafe archive paths or member types.

For example, a lockfile rule may name a fixed set of predecessor packages
published and independently verified earlier in the same ceremony. For each
named predecessor entry, only its previously absent registry source and checksum
may become the declared registry source and verified published-archive digest.
The package name/version, dependency graph, all other entries and fields, and
every other archive member remain unchanged under the declared comparison. An
arbitrary lockfile exclusion or dependency re-resolution does not satisfy this rule.
The publisher still authorizes the exact final archive digest after the
transformation check.

### 5. Verify the registry result and preserve partial outcomes

After upload, verify the registry's exact package/version, checksum, and
downloaded archive bytes against the approved final digest, together with the
declared identity and dependency metadata. Index presence or a successful
upload response alone is insufficient.

If a response is lost or indexing is delayed, report an unresolved publication
and inspect the actual registry state before retrying. Distinguish
not-published, outcome-unknown, and published-but-verification-failed from
complete. Publishing several packages is not atomic: retain each package's
state, and do not republish an already published predecessor merely because a
dependent package remains unfinished. A conflicting existing version or digest
requires maintainer investigation; never silently accept it as this attempt's
success. Corrections follow the registry's reviewed withdrawal and new-version
process, not an assumption that published bytes can be replaced.

## Scope of bindings

This record supplies a Cargo binding for maintainer-side publication. npm/PyPI
trusted-publisher workflows and other OIDC publication mechanisms require a
separately reviewed execution and authorization binding before claiming
conformance. An OIDC token is publication authority even when short-lived. Such
a binding must preserve separation from package-code execution, authorization of
the approved final artifact and destination, and independent registry-result
verification. Filing this profile neither authorizes CI publication nor revokes
authority granted by a separate reviewed profile.

## Cargo binding

Cargo's [`package`][cargo-package] command normally builds the assembled archive
to verify it. [`publish --no-verify`][cargo-publish] skips that build but still
packages the source before uploading. The flag is not an upload-existing-file
interface and does not disable configuration or credential-provider handling.

Cargo's [credential-provider publish request][cargo-provider] includes `name`,
`vers`, and `cksum`. The [Cargo 1.88.0 publication implementation][cargo-source]
computes that checksum from the final archive before requesting publication
credentials. A single trusted provider can therefore implement the final
authorization gate. An adopting implementation must pin and test this behavior,
including the initial read request, provider selection, failure handling, and
credential caching. No read handshake or cached credential may authorize a
publication that has not passed the package-specific check. Do not configure a
fallback that bypasses the provider.

This is a candidate binding, not a claim that the protocol alone supplies a
conforming implementation. Exercise the pinned Cargo binary against a local
test registry using dummy credentials and inspect the captured archive and
authorization behavior. Source inspection or a fake Cargo command alone does
not discharge that integration check.

## Adoption and evidence

Each adopter records its execution boundary, trusted tools and workflow,
verification record, publication authorization mechanism, any transformation,
registry completion checks, and first covered release. PDR-0008 identity
controls and PDR-0010 forge-publication controls remain separately applicable
where adopted; neither substitutes for the registry checks here. This record
does not grant CI publication authority or claim build provenance.

Apply EPR-0002 with executable controls that demonstrate:

- Verification code cannot read publisher secrets or alter publisher state.
- Missing or mismatched source/run/artifact identity is refused.
- A different final archive, registry, package name, or version receives no
  publication authorization, including through read-request, provider-fallback,
  credential-cache, or package-manager token flag/environment-variable paths.
  A provider-gated Cargo ceremony refuses direct `--token`,
  `CARGO_REGISTRY_TOKEN`, and `CARGO_REGISTRIES_<NAME>_TOKEN` inputs rather than
  allowing them to bypass its authorization check.
- Permitted transformations accept their positive case and reject unrelated
  lockfile changes, wrong predecessor digests, and missing or extra members.
- A registry checksum/download mismatch, delayed index, and interrupted upload
  cannot be reported as complete or trigger an unsafe blind retry.

Controls must reach the intended assertion and fail when it is removed. Use
dummy secrets and isolated test services; do not exercise negative controls by
publishing incorrect packages to a production registry. Policy acceptance and
implementation conformance are separate review decisions. No conforming
reference implementation is claimed by this proposed record.

## Consequences

Verification can execute build code without granting it publication authority.
The publisher has a specific package identity to authorize, and unresolved
multi-package publication remains visible. The cost is a separate verification
environment, retained evidence, and a tested package-manager binding. Some
dependent packages require another verification pass or an explicitly bounded
transformation.

This is a PDR because it chooses a revisable release ceremony and tool binding.
EPR-0002 already provides the durable principle; it does not need a new addendum
for this instance. Acceptance of a particular security risk remains a separate
review decision.

## References

- [PDR-0008: Release public identity](PDR-0008-release-public-identity-in-tree.md)
- [PDR-0010: Verified immutable release publication](PDR-0010-verified-immutable-release-publication.md)
- [EPR-0002: Verification gate integrity](EPR-0002-verification-gate-integrity.md)
- [Decision-record taxonomy](../repository/decision-records.md)

[cargo-package]: https://doc.rust-lang.org/cargo/commands/cargo-package.html
[cargo-publish]: https://doc.rust-lang.org/cargo/commands/cargo-publish.html
[cargo-provider]: https://doc.rust-lang.org/cargo/reference/credential-provider-protocol.html#publish-request
[cargo-source]: https://github.com/rust-lang/cargo/blob/rust-1.88.0/src/cargo/ops/registry/publish.rs

## Revision History

| Date       | Status Change | Summary                                                          | Updated By |
| ---------- | ------------- | ---------------------------------------------------------------- | ---------- |
| 2026-10-23 | → proposed    | Bind registry publication to a verified final archive            | entarch    |
| 2026-10-23 | proposed      | Explicit token controls, predecessor set and graduation evidence | entarch    |
| 2026-11-23 | proposed      | File as proposed; clarify adoption candidates and OIDC scope     | devlead    |
