---
id: "PDR-0010"
title: "Verify staged assets before immutable release publication"
status: "proposed"
date: "2026-10-23"
last_updated: "2026-10-23"
deciders:
  - "@3leapsdave"
  - "cxotech"
scope: "Crucible foundation / adopting repositories' release publication"
tags:
  - "process"
  - "release"
  - "verification"
  - "governance"
relates-to:
  - "PDR-0004 (publication authority and the existing CI publication posture)"
  - "PDR-0008 (committed release identity and explicit ceremony inputs)"
  - "EPR-0002 (verification of resolved state and discriminating negative controls)"
---

# PDR-0010: Verify Staged Assets Before Immutable Release Publication

## Status

**Proposed.** Acceptance establishes this publication profile; a repository
adopts it through a reviewed tooling and checklist change. Filing this record
does not change repository settings, authorize publication, or establish that
Crucible's current workflow conforms.

## Context

A signed tag binds a source revision. Release assets are assembled separately
and may include archives, binaries, checksum manifests, signatures, and public
verification material. Verifying the tag does not prove that the complete
intended asset set was uploaded or that its uploaded bytes verify.

Immutable publication fixes that assembled set. A draft therefore has a
specific purpose: verify the staged release before its assets become fixed.
The ceremony must also report whether publication completed; a successful
draft creation is not a successful release.

## Decision

### 1. Scope, authority, and relationship to existing records

An adopting GitHub repository enables immutable releases and records the first
release covered by this profile. Adoption may be per repository; this record
does not require an organization-wide setting. Other forges require a reviewed
profile stating their actual guarantees before claiming equivalent adoption.

**The maintainer's signed annotated tag authorizes the exact source revision.
Publication additionally requires verification of the staged asset set and an
explicit maintainer-controlled publication action.** The publication action
may be a local command that verifies and publishes. CI in this profile has
read-only verification authority; a green run does not publish the release.

On acceptance and adoption, this profile supersedes PDR-0004's requirements for
automatic CI publication, no normal draft stage, and no manual undraft, within
the adopting repository. It retains the obligations to verify against committed
key pins, bind the exact annotated tag object and commit, protect version-tag
refs, pin verification dependencies, and verify the published result. The
prerelease and latest-state checks also remain, with the intended values
explicit in the ceremony.

Read-only CI here governs release verification and publication authority. It is
not a blanket ban on separately reviewed automation that prepares a branch or
pull request. Such automation must have separate job permissions and credential
handling and must not perform release publication. Review its effective access
to release and tag mutation and record any residual capability in the adoption
review; calling a job "PR preparation" does not remove capabilities granted by a
broad token.

PDR-0004 remains the applicable publication profile for repositories that have
not adopted this successor. Existing CI write permissions do not themselves
authorize either profile. PDR-0008's identity controls apply where adopted;
its reference to a read-only verification job does not silently supersede
PDR-0004's publishing job. An adoption change must reconcile the workflow,
checklist, and verifier documentation together.

### 2. Verify the draft's resolved state before publishing

The ceremony uses an explicit repository and release tag. It refuses implicit
tag creation, a lightweight tag, an unexpected tag object or commit, and
publication against an unverified or changed ref. The published version tag is
not moved, deleted, or reused to repair a release.

The release definition is committed and machine-readable, and is read from the
verified tag's commit, not from an unverified working tree or environment
override. It declares the canonical release tag, companion version tags, and
attached assets. Each asset rule identifies its name or bounded naming rule,
role, required or optional disposition and allowed multiplicity, and applicable
manifest and signature coverage. Declared rules resolve to an exact asset set
before publication; optionality does not permit arbitrary additions. A tag-only
release explicitly resolves to zero attached assets; it does not manufacture
signatures for nonexistent assets. A shared declaration schema may follow
separately; adoption must supply a documented format and executable validation.

Forge-generated source archives are identified separately from attached assets
and are not silently claimed as maintainer-signed payloads. A tag-bound
declaration defines the expected shape; it need not contain digests of outputs
built after that tag. Those belong in the verification record below, which
avoids a circular requirement to commit output digests before the outputs exist.

The maintainer-controlled ceremony creates a draft for the verified tag, uploads
the declared set, and then checks the remote draft:

- Enumerate its attached assets and reconcile them against the declaration in
  both directions. Missing required assets, duplicates, and unexpected assets
  fail verification.
- Read back the staged bytes. Verify payload digests and manifest signatures
  against the committed trust material from the verified tag's commit. Check
  the complete declared signature and manifest coverage; a key uploaded beside
  an asset does not authenticate itself.
- Require applicable public-key assets to match their committed blobs, in
  addition to the fingerprint and signature checks.
- Confirm the release is still a draft for the same tag object and commit,
  with the intended prerelease setting and reviewed release notes. Carry the
  declared latest-state choice into publication and verify it afterward.

Retain a pre-publication verification record bound to the verified tag object
and commit, the declaration revision, the exact resolved asset names, sizes,
SHA-256 digests, and applicable signature-verification results. Recheck against
that record immediately before publication, and compare the post-publication
downloaded bytes against the same record. Do not rebuild the expected digest set
from the newly published assets. A mismatch is a failed verification, even if
the replacement set is internally self-consistent.

Local files, upload success, and a release object's existence are insufficient
evidence. Restrict draft write authority and concurrent publishers, then recheck
the tag and asset identities immediately before the publication action. The
record detects a swap within that window; it does not eliminate the window. Upload,
verification, and publication are separate operations; this profile claims no
atomic transaction across them and requires post-publication verification.

For GitHub CLI, explicitly retain the draft during verification. Supplying
assets to `gh release create` without `--draft` can upload and publish in the
same command, using separate requests; it does not provide this intervening
verification gate. See the [CLI publication behavior][gh-create].

### 3. Verify publication and report an honest outcome

After publishing, independently read the published state and require:

- The release exists, is not a draft, and is immutable, as reported by the
  release object's own immutability field. That field is readable with the
  ceremony's ordinary release-read access; the repository setting is not
  evidence that a given release is immutable.
- Its tag resolves to the verified annotated tag object and commit. Companion
  version tags, including module-prefixed tags, are separately protected and
  verified; a release's tag lock does not establish their protection.

  One release may have several version tags but is associated with one declared
  canonical tag. The immutable-release lock applies only to that associated tag.
  Companion tags require separate protection evidence and verification of their
  declared source-revision relationship; creating extra forge releases is not
  implied.
- The attached asset set and downloaded bytes match the pre-publication
  verification record, with the required digests and signatures valid.
- The latest/prerelease state matches the declared release intent.
- The forge release attestation verifies and binds the expected release,
  commit, and assets. GitHub's attestation supplements, rather than replaces,
  the maintainer's OpenPGP and minisign trust chains.

Registry publications and module-proxy observations are separate distribution
surfaces outside the forge release's immutable boundary. Each adopter declares
the surfaces, their order, exact versions and source bindings, and the
verification required for overall release completion. Explicit registry publish
commands normally follow verified immutable forge publication; any different
order needs a reviewed reason. Public version tags may already make a module
discoverable to consumers and proxies before that point, so the ceremony does
not claim that delaying a proxy check prevents distribution. Record and verify
each surface separately, including partial publication; no surface's success
implies another's. See [module proxy behavior][go-proxy].

`gh release verify` verifies the release attestation; it does not by itself
verify a downloaded local file. Use the required digest/signature checks and,
where applicable, `gh release verify-asset`, with explicit repository and tag.
See [release verification][gh-verify] and [asset verification][gh-verify-asset].

The ceremony reports a distinct outcome for staged-but-unpublished,
publication-failed, and published-but-verification-failed states. None is
reported as complete.

A missing, unavailable, or invalid required forge attestation blocks
"complete"; it is never downgraded to a warning. If publication already
occurred, report published-but-verification-failed, with the specific cause and
retained evidence. An unavailable service may be retried by re-reading and
verifying the same release; a failed attestation is investigated. Neither
permits deleting and recreating the release or asserting that it is still
staged. A named maintainer owns unresolved publication, and an
interruption or unknown response triggers a read of actual release state before
any retry. Retrying must not create a different release or replace assets after
publication. This preserves PDR-0004's requirement that an unfinished release
cannot silently pass the completion checklist.

### 4. Correction preserves history

Normal correction retains the published release and tag, adds a clear
withdrawal or correction notice, and publishes a corrected release under a new
appropriate version. Correct latest/prerelease metadata explicitly as needed.
A notice is mutable metadata, not a replacement signature or a revocation of
copies already downloaded.

Release deletion is an explicit maintainer-authorized takedown decision, with
the original identity and verification evidence retained through the applicable
incident or withdrawal process. It is not the routine repair path. Deletion
does not authorize moving, re-signing, or reusing the version tag, and cannot
recall artifacts from downstream caches or package registries.

### 5. GitHub guarantee boundary

GitHub locks a published immutable release's attached assets and associated
tag. Drafts remain mutable. Titles, notes, and latest/prerelease flags remain
editable and must not serve as immutable trust anchors.

This profile binds the published asset set to what the maintainer verified and
signed. It does not establish how those bytes were built. Build provenance,
such as reproducible builds or build attestations for assets, is a separate
concern; the forge release attestation is not build provenance. Deleting the release
permits tag deletion, but the tag name cannot be reused, including after
repository recreation. The project's no-delete/no-reuse version policy remains
stricter than that provider capability. GitHub automatically creates a release
attestation. See [GitHub immutable releases][gh-immutable].

Enablement applies to future releases, not retroactively to existing releases;
record the adoption boundary. See [enabling immutability][gh-enable]. The cited
documentation does not establish that disabling the setting unlocks previously
immutable releases. This profile makes no such assumption and does not use
disablement as a recovery procedure.

## Adoption and evidence

Each adopting repository records its effective publication profile, expected
asset definition, publisher authority, verification commands, first covered
release, and any explicitly approved deviation. The tooling change is reviewed
separately from product changes and release version bumps. The first published
release supplies adoption evidence; a setting alone does not prove conformance.

Immutable publication locks the attached asset set. Before enabling the setting
for a repository, verify that its active ceremony completes all required asset
additions, replacements, and removals while the release is a draft and does not
depend on changing the associated tag after publication. A ceremony that still
requires those operations after publication must be changed first. A repository
already satisfying this condition may enable immutability before formally
adopting this profile. The same readiness check applies to every repository
covered by an organization-wide policy, whether explicitly selected or included
by default. Early enablement is not conformance: adoption evidence comes from a
release under the reviewed profile that passes all required checks.

The verification gates carry executable positive and negative controls under
EPR-0002. At minimum, demonstrate rejection of a missing required asset, an
unexpected asset, altered staged bytes, an internally consistent replacement
asset set after pre-verification, an invalid required signature, a changed tag
binding, and absent publication or immutability evidence. Controls must
reach the assertion they test, rather than pass on an unrelated earlier error;
removing that assertion must make its control fail. Tests use isolated fixtures
or test repositories, not destructive mutations of production releases. A
tag-only adopter declares the inapplicable asset/signature controls and still
tests rejection of an unexpected attached asset.

Crucible retains PDR-0004's publication behavior until its own reviewed adoption
change lands. This proposal does not change that workflow or create a new
attached-asset surface. A cross-repository rollout ledger and machine-specific
ceremony instructions belong outside this shared record.

## Consequences

The draft gate now judges the assembled release, and publication is complete
only after the immutable result is verified. Uploaded-byte verification adds
work and a deliberate maintainer-controlled step. The cost is accepted in
exchange for checking the actual asset set before it becomes fixed. Corrections
require new versions rather than replacing published bytes.

## References

- [PDR-0004: Release publication gate](PDR-0004-release-publication-gate.md)
- [PDR-0008: Release public identity](PDR-0008-release-public-identity-in-tree.md)
- [EPR-0002: Verification gate integrity](EPR-0002-verification-gate-integrity.md)
- [Decision-record taxonomy](../repository/decision-records.md)

[gh-create]: https://cli.github.com/manual/gh_release_create
[gh-verify]: https://cli.github.com/manual/gh_release_verify
[gh-verify-asset]: https://cli.github.com/manual/gh_release_verify-asset
[gh-immutable]: https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases
[gh-enable]: https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/establish-provenance-and-integrity/prevent-release-changes
[go-proxy]: https://go.dev/ref/mod#module-proxy

## Revision History

| Date       | Status Change | Summary                                                   | Updated By |
| ---------- | ------------- | --------------------------------------------------------- | ---------- |
| 2026-10-23 | → proposed    | Verify staged assets before immutable release publication | entarch    |
| 2026-10-23 | proposed      | Declaration, record, surfaces, attestation and CI scope    | entarch    |
| 2026-10-23 | proposed      | State that the profile is not build provenance             | cxotech    |
| 2026-10-23 | proposed      | Order enablement before adoption; immutability evidence source | devlead    |
