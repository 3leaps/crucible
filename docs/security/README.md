# Verifying a release

This directory is the public identity for 3leaps/crucible releases: the keys
and fingerprints a verifier checks. Nothing here is secret. The layout
follows [PDR-0008](../decisions/PDR-0008-release-public-identity-in-tree.md).

Words used on this page:

- A **release** is a GPG-signed annotated Git tag (`vX.Y.Z`). It is not a
  download, and it is not a checksum file.
- A **pin** is a public key file committed in this repository. A check uses
  the committed copy, never a key fetched from somewhere else.
- An **anchor** is the committed fingerprint of a pin. The checker
  recomputes the fingerprint from the pin and requires the same value.
- The **checker** is decernor 0.1.8 or newer. It computes and compares
  fingerprints. It does not sign the tag.

## What a release carries

A crucible release is a **GPG-signed annotated Git tag** (`vX.Y.Z`). Crucible
publishes no release assets. There are no `SHA256SUMS` or `SHA512SUMS`
files, minisign-signed or otherwise. Do not look for them: their absence is
expected, not a failed download.

The tag signature is the only release signature. The sections below say
what to trust, then how to check the tag.

## Files

| File | What it is |
| --- | --- |
| `release-signing-keys.asc` | Public OpenPGP export: the approved primary key and exactly one signing subkey. This is the key that signs the tag. |
| `crucible-minisign.pub` | Minisign public pin for this repository. It signs no crucible release file. |
| `fulmenhq-goneat-minisign.pub` | Third-party pin. Bootstrap uses it to verify goneat release manifests. |
| `../../keys/expected-fingerprints.txt` | Two anchors, in order: the OpenPGP primary fingerprint, then the minisign public-blob SHA-256. |
| `../../keys/expected-fingerprints.ndjson` | The checker's fingerprint records for the same two keys. |

## A key that signs nothing

`crucible-minisign.pub` signs no file in a crucible release. The tag is
signed by the OpenPGP subkey in `release-signing-keys.asc`, not by minisign.
The file is still committed. The checker requires both keys as a pair: it
recomputes both anchors and fails if either file does not match. This
minisign public key is the same key other 3leaps repositories commit when
they sign downloadable files. The pin records that key for this repository.

## What to trust

Before you accept the files in this directory, obtain these three values
from a maintainer channel you already trust:

- the OpenPGP primary fingerprint
- the exact signing subkey
- the minisign public-blob fingerprint

A key that arrives beside the signature it is supposed to check is not an
independent check.

## How a tag is checked

Verification reads the pins and anchors from the **tagged commit**, as the
blobs stored in that commit. It does not read a working tree you have
edited, and it does not read the environment. It imports
`release-signing-keys.asc` into an empty keyring. It requires one good,
unexpired signature by the pinned signing subkey. The tagger name and email
must match `config/release/tagger-identity.txt`. GitHub's "verified" flag
is an additional check, not a substitute.

## Checker

The anchors are derived and verified by **decernor 0.1.8 or newer**. The
minisign fingerprint covers the decoded public blob, not its comment line
or the whole file. Anchors are derived twice and compared; they are never
typed by hand.

- Creating or verifying a release tag takes the checker from
  `THREELEAPS_CRUCIBLE_DECERNOR_BIN`: an absolute path to a regular,
  executable, non-symlink file. There is no fallback to `PATH`.
- CI downloads the checker archive pinned by digest in
  `config/release/decernor-ci-sha256.txt`.

To verify a tag locally:

```bash
export THREELEAPS_CRUCIBLE_DECERNOR_BIN=/absolute/path/to/decernor
./scripts/verify-pinned-tag.sh vX.Y.Z
```

Tags up to and including `v0.2.0` predate this layout (`release-minisign.pub`,
text anchors only). Verify one of those with the `scripts/verify-pinned-tag.sh`
from that tag's own commit, as its release workflow did; historical tags are
not re-signed.

To check that the committed anchors match the committed exports:

```bash
make release-check-anchors
```

## Third-party keys

`fulmenhq-goneat-minisign.pub` is passed to sfetch with `--minisign-key` when
bootstrap installs goneat. The goneat manifests are checked against this
committed file, never against a key fetched from the goneat release itself.

This file matches the copy committed in the sfetch repository
(`.github/keys/fulmenhq-goneat-minisign.pub`) and goneat's own committed
release key, byte for byte. SHA-256
`8d6f8404b2a48bdbca9bbc755e0b54e83c6e58dd3be2fe7219fc2c9d4c68913d`. Replacing
this file replaces the trusted key and is reviewed as a key change.

## Authorization

The release workflow has read-only permissions until the final publication
step. A passing tag workflow shows that the checks agreed. It does not
authorize the release. The signed tag authorizes publication
([PDR-0004](../decisions/PDR-0004-release-publication-gate.md)).
