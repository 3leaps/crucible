---
id: "PDR-0008"
title: "Release public identity is committed, checked by one tool, and bound by explicit inputs"
status: "proposed"
date: "2026-10-22"
last_updated: "2026-10-23"
deciders:
  - "@3leapsdave"
  - "cxotech"
scope: "Crucible foundation / release process"
tags:
  - "process"
  - "release"
  - "signing"
  - "supply-chain"
  - "governance"
relates-to:
  - "crucible PDR-0004 (the signed tag authorizes publication; CI verifies against a committed key pin)"
  - "crucible EPR-0002 (a gate asserts on resolved state and is proven able to fail)"
  - "crucible ADR-0002 (key-material fingerprint contract; the scheme registry)"
  - "crucible ADR-0003 (the *DR taxonomy; PDR = a revisable ways-of-working choice)"
---

# PDR-0008: Release Public Identity Is Committed, Checked by One Tool, and Bound by Explicit Inputs

## Status

**Proposed.** Generalizes the key-pin posture that PDR-0004 established for this
repository into a rule that any adopting repository can follow. The layout in
§3 is a recommended default; the controls in §2 are the mandate.

## Context

A release carries three kinds of public identity material: the OpenPGP key
that signs the tag, the minisign key that signs the checksum manifests, and
the fingerprint anchors a verifier compares those keys against. A repository
that verifies other tools during its build or bootstrap also holds those
tools' public keys.

PDR-0004 fixed one piece of this for crucible: CI verifies the tag signature
in an isolated keyring built solely from a committed key export, so a stray
key on the tagger's account cannot publish. It did not say where the
minisign pin lives, who derives the fingerprint anchors, how the release
tooling finds its checker, or how it learns the tag name. Each adopting
repository answered those questions for itself. The answers diverged in ways
that matter:

- Some repositories supply the minisign public key only through an
  environment variable that names a file on the maintainer's machine. The
  release then trusts whatever that file holds at staging time. Nothing in
  the tagged commit records who was trusted, and nothing in review saw it.
- Some repositories carry a local script that decodes the minisign public
  blob and hashes it, beside the designated checker that does the same
  thing. Two parsers for one security-relevant value is the duplicated-enum
  hazard ADR-0002 was written to close.
- Some release targets resolve the checker from `PATH` or from a working-tree
  build when the pinned binary is absent. The ceremony then runs whichever
  checker happened to be first, which may be the very code under release.
- Some release targets derive the tag from `git describe` or from the
  version file when no tag was given. A ceremony step that fabricates its
  own tag name can sign the wrong commit without any input being wrong.
- Keys that verify third-party tools sit as Makefile literals, under
  CI-only directories, or inline in installer scripts, where a rotation is
  an edit nobody is asked to review as trust material.

Each of these is a control with a silent failure mode: the release looks
correct, the tag verifies, and the thing that was wrong leaves no trace.
That is the failure class PDR-0004 and EPR-0002 exist to remove.

## Decision

### 1. Scope

This record governs **public** identity material only: public key exports,
public key pins, fingerprint anchors, and the tagger string. Private keys,
passphrases, keyring homes, ceremony transcripts, and filesystem paths to
any of them are out of scope because they never enter a working tree in any
form. An ignore rule is not the boundary.

### 2. Controls (mandatory for an adopting repository)

1. **Public pins are committed blobs, read from the tagged commit.** Every
   public key the release signs with, and every anchor a verifier checks
   against, is a committed file. Release staging reads it from the tag's
   commit object, not from the working tree and not from an environment
   variable naming a file. An environment variable MAY feed the one-time
   step that first writes the committed file; after that the committed blob
   is the only input. A later edit on the default branch cannot change who
   was trusted for an already-tagged release. The same rule holds at
   verification time: a release verifier or installer does not accept an
   environment override of a committed pin. A test fixture that needs a
   different key goes through an explicit test-only flag or path, never the
   production variable, and a release verifier, an installer, and a
   ceremony build refuse that flag or path outright.

2. **One designated checker derives and verifies fingerprint anchors.** The
   repository names the checker and its minimum version. Anchor values are
   produced by that checker from the committed exports, written without
   overwrite, derived twice and compared. Hex is never typed by hand. The
   repository carries no second parser for the same value, in any language,
   including inline in a shell or Python verify step. The minisign anchor is
   the SHA-256 of the decoded public blob, per the scheme registry of
   ADR-0002, not of the comment line or the whole file.

3. **The ceremony binds its checker by explicit absolute path, with no
   fallback.** Ceremony steps (insert anchors, export pins, verify keys
   before tagging, tag preflight) take the checker from one
   repository-prefixed variable. The value is an absolute path to a regular,
   executable, non-symlink file whose reported identity is the expected tool
   and whose version meets the pinned minimum. A missing or malformed value
   fails before any side effect. There is no
   fallback to an unprefixed variable, to a working-tree build, or to
   `PATH`. The repository that ships the checker is not exempt: its own
   ceremony uses a previously published, digest-pinned release, because a
   checker verifying its own uncommitted build proves nothing. Checks that
   are not part of the ceremony MAY fall back, provided they do not derive
   an anchor, verify a pin, or select a signing key; the tag workflow, an
   installer, and a binary self-check are never in that class.

4. **The release tag is an explicit input, never derived.** Tag-consuming
   targets take the tag from one repository-prefixed variable. A bare,
   unprefixed tag variable from any origin fails before side effects. There
   is no default from `git describe`, from the version file, or from the
   current branch. The refusal lives at the outermost layer the maintainer
   invokes: a Makefile `?=` that lets an inherited bare variable win is a
   derived input even when the script underneath would refuse it.

5. **CI verification is present whenever anchors are.** Once a repository
   commits fingerprint anchors, its tag workflow runs the checker against
   the committed exports on every tag. The check runs inside the existing
   read-only tag workflow and needs no write authority; it is not a reason
   to keep or add a write-scoped job. The checker binary CI downloads is
   pinned by digest in a committed file. A green run is a consistency
   signal, not release authorization (PDR-0004 §1 still governs what
   authorizes publication).

6. **Third-party verification keys are files, named by origin.** A key that
   verifies another tool during build, bootstrap, or install lives as a
   committed file beside the repository's own pins, named for the producing
   organization and tool, so `fulmenhq-goneat-minisign.pub` rather than
   `goneat-minisign.pub`, and the same shape for a tool from the
   repository's own organization. Scripts and workflows read the file. No
   Makefile literal, no CI-only directory, no inline copy.

   A standalone installer that must run without the repository (fetched by
   URL and executed with nothing beside it) MAY carry a literal for any key
   it verifies, including the repository's own current and retired pins,
   only if a committed test asserts each literal equals the corresponding
   committed file, so a rotation that updates one and not the other fails.

7. **Binaries embed the committed file.** A binary that embeds its own
   public key for self-verification reads the committed pin file at build
   time (`go:embed`, `include_bytes!`, or the equivalent). There is no
   second copy kept in sync by a drift test; the installer allowance in
   §2.6 does not extend to binaries.

8. **Retired keys stay committed and labelled.** When a signing key rotates,
   the previous public pin remains in the tree under a name that marks it
   as retired, with the tag range it signed recorded beside it. The last
   tag the retired key signed is part of that record; an installer that
   selects a key by tag takes its cutoff from it and its retired literal
   falls under the §2.6 equality test against the retired file. Historical
   tags are never re-signed (PDR-0004). A verifier never tries both keys for
   one tag. For a retired OpenPGP key the recorded fingerprint is
   sufficient; the fingerprint is the pin, and the public export is
   available from the releases that key signed. No committed retired
   `.asc` is required.

9. **A verifier-facing README states what is checked.** The directory that
   holds the pins carries a short document naming the signature set, the
   anchors, the checker, and the statement that a passing tag workflow is
   not release authorization. A reference wording is in the appendix.

### 3. Layout (recommended default, not mandated)

As with ADR-0003's position on record storage, the mandate is the controls
above; the layout below is the default an adopting repository takes unless it
has a reason not to. Crucible adopts it under §4.

| Path | Contents |
| --- | --- |
| `config/release/tagger-identity.txt` | One line: the exact git tagger string |
| `docs/security/release-signing-keys.asc` | Public OpenPGP export: the approved primary plus the exact signing subkey, nothing else |
| `docs/security/<repo>-minisign.pub` | The repository's own minisign public pin (comment line, then key line) |
| `docs/security/<repo>-minisign-retired-<n>.pub` | A retired own pin, with its tag range and last signed tag in the README |
| `docs/security/<org>-<tool>-minisign.pub` | A third-party verification key, named by the producing org and tool, including tools from the same org |
| `docs/security/README.md` | The verifier-facing statement (§2.9) |
| `keys/expected-fingerprints.txt` | Two lines: the OpenPGP primary fingerprint, then the minisign public-blob SHA-256 |
| `keys/expected-fingerprints.ndjson` | The checker's fingerprint records for the same two keys |
| `config/release/<checker>-ci-sha256.txt` | Digest and filename of the checker archive CI downloads |

The two-line anchor file is deliberately closed: it holds the repository's
own two signing keys and nothing else. Third-party keys are not anchors in
this file; they are verified by use (§2.6), and any fingerprint record for
them is a scheme-registry question under ADR-0002, not an extension of this
file.

Variable names follow one shape, `<REPO>_<PURPOSE>`, uppercased: the
repository's own short name as prefix, so two repositories' ceremonies run
in one shell without colliding. Each adopting repository records its exact
variable names, its checker's identity and pinned minimum version, and its
adoption state in its own tooling or decision lane; this repository's values
are recorded here with its §4 adoption change. The cross-repository
adoption ledger is operating detail kept outside this repository.

### 4. Adoption

A repository adopts this record at its next release-tooling change. It makes
one tooling change, separate from version bumps and product work, that
commits the pins, removes any second parser, binds the checker and tag as
explicit inputs, and adds the CI verification. Review is against the local
branch; the first tag after adoption is the proof. A repository that cannot
meet a control records the deviation in its own decision lane rather than
silently weakening it (EPR-0002).

This repository is conformant as of its adoption change. That change renamed
`docs/security/release-minisign.pub` to
`docs/security/crucible-minisign.pub`, added the verifier-facing README and
the NDJSON anchor file, pinned the checker CI downloads, and replaced the
inline anchor check with the designated checker. Its checker is decernor 0.1.8
or newer, bound through `THREELEAPS_CRUCIBLE_DECERNOR_BIN`, and its tag input is
`THREELEAPS_CRUCIBLE_RELEASE_TAG`. Crucible publishes signed tags only, so the
minisign pin is committed and anchored but signs no release file; manifest
controls apply if it ever publishes assets. Tags up to v0.2.0 predate the
adoption and verify with the script from their own commit. Its first release
under the adopted ceremony records the proof.

## Rationale

- **A pin that is not in the tagged commit is not a pin.** The whole value
  of committed trust material is that the tag object fixes it. An
  environment-supplied file defeats that while looking the same in the
  release assets.
- **One checker, or none.** ADR-0002 moved the fingerprint scheme into a
  registry so producer and consumer could not drift. A local re-derivation
  beside the checker reintroduces exactly that drift, with the added hazard
  that the two can disagree and the ceremony passes on whichever one ran.
- **Fallbacks are where silent failures live.** PATH lookup, working-tree
  builds, and derived tag names each turn a missing input into a plausible
  wrong answer. Failing before side effects turns the same condition into a
  red step, which is the channel every other release defect already uses
  (PDR-0004, EPR-0002).
- **Trust material should be reviewed as trust material.** A key as a file
  under a security directory is diffed, named, and noticed. The same bytes
  as a Makefile literal are an edit.

## Consequences

**Positive**

- Who was trusted for a given release is answerable from the tag alone.
- Key rotation is a reviewed change to named files, and a forgotten pin
  update fails closed before the first post-rotation tag (as PDR-0004
  already requires for the OpenPGP pin).
- Reviewers find every repository's trust material in the same place and
  check it with the same tool.

**Negative / costs (accepted)**

- Repositories that today take the minisign pin from the environment gain
  a committed file and a one-time migration.
- The repository that ships the checker loses the convenience of verifying
  with its own fresh build; it must release behind itself by one version.
- Standalone installers that must embed a literal gain a coupling test.
- Retired pins accumulate in the tree. This is the record, not clutter.

## Alternatives considered

- **Carve out environment delivery for repositories that do not embed the
  key.** Rejected. It creates a second profile, and the exposure it accepts
  (trusting a file by path at staging time) is the same regardless of
  whether a binary also embeds the key.
- **Widen the anchor file to hold third-party keys.** Rejected. The
  designated checker's verification contract requires exactly two records,
  and a third-party key is verified by using it, not by anchoring it. A
  record format that can name whose key a record is belongs in the ADR-0002
  registry when a consumer needs it.
- **Allow a self-build fallback for the checker's own repository.** Rejected.
  The circularity is the point: the thing being released is the thing
  doing the checking.
- **Grandfather existing file names.** Rejected for this repository, which
  publishes the default and should not be its first exception; its own pin
  is renamed in its adoption change (§4). Other repositories may keep a
  historical name if they record the deviation.

## Appendix: verifier-facing README (reference wording)

> Official releases use a GPG-signed annotated Git tag and minisign-signed
> SHA256SUMS and SHA512SUMS manifests. These are separate signatures.
>
> Establish the expected GPG primary and exact signing subkey, and the
> minisign public-blob fingerprint, through an independently trusted
> maintainer channel before accepting downloaded public keys. A key
> distributed beside a signature is not independent authentication.
>
> The public pins are `release-signing-keys.asc` and `<repo>-minisign.pub`.
> Release staging extracts both from the verified tagged commit as inert
> blobs, not from the current checkout or an external public-key locator.
> The published `<repo>-minisign.pub` asset must match the committed file
> byte-for-byte; fingerprint verification remains required.
>
> The text and NDJSON anchors in each tagged commit are derived by
> `<checker> <min version>` or newer. The minisign fingerprint covers the
> decoded public blob, not its comment or whole file. Verify exported
> public material against both anchors with that tool, then use the
> approved minisign public key to verify both manifests and check every
> listed digest. Require the complete expected asset set.
>
> Tag verification reads committed public data in an isolated keyring and
> requires the exact signing subkey. The forge's own "verified" flag is an
> additional check. Historical tags are not retroactively signed.
>
> The tag workflow has read-only permissions. A passing tag workflow is a
> consistency signal; it is not release authorization.

## References

- [PDR-0004: The signed tag authorizes publication](PDR-0004-release-publication-gate.md) — the committed-key-pin posture this record generalizes
- [EPR-0002: Gates assert on resolved state](EPR-0002-verification-gate-integrity.md) — why fallbacks and derived inputs are rejected
- [ADR-0002: Key-material fingerprint contract](ADR-0002-keymaterial-fingerprint-portable-contract.md) — the scheme registry; where a third-party record format would go
- [ADR-0003: Decision & Governance Record Taxonomy](ADR-0003-decision-record-taxonomy.md) — defines PDR; precedent for mandating controls and recommending layout

## Revision History

| Date       | Status Change | Summary                                                       | Updated By |
| ---------- | ------------- | ------------------------------------------------------------- | ---------- |
| 2026-10-22 | → proposed    | Committed pins, one checker, explicit checker and tag inputs | cxotech    |
| 2026-10-22 | proposed      | Installer literals, retired-key selection, no env override at verify | cxotech    |
| 2026-10-23 | proposed      | Record this repository's adoption (§4)                       | devlead    |
