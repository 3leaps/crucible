# Release Public Identity

This directory holds the public identity material for 3leaps/crucible releases,
following [PDR-0008](../decisions/PDR-0008-release-public-identity-in-tree.md).
Nothing here is secret.

## What a release carries

A crucible release is a **GPG-signed annotated Git tag** (`vX.Y.Z`). Crucible
publishes no release assets, so there are no minisign-signed `SHA256SUMS` or
`SHA512SUMS` manifests to verify. Do not look for them: their absence is
expected, not a failed download.

The tag signature is the only release signature. Verify it as described below.

## Files

| File                           | Contents                                                                                       |
| ------------------------------ | ---------------------------------------------------------------------------------------------- |
| `release-signing-keys.asc`     | Public OpenPGP export: the approved primary key and exactly one signing subkey                 |
| `crucible-minisign.pub`        | The minisign public pin for this repository                                                    |
| `fulmenhq-goneat-minisign.pub` | Third-party key: verifies goneat release manifests during bootstrap                            |
| `../../keys/expected-fingerprints.txt`    | Two anchors: the OpenPGP primary fingerprint, then the minisign public-blob SHA-256 |
| `../../keys/expected-fingerprints.ndjson` | The checker's fingerprint records for the same two keys                             |

`crucible-minisign.pub` signs nothing today. It is committed and anchored
because the checker's verification contract covers both keys as a pair, and
because the same minisign key is shared across 3leaps repositories, so the pin
records the key this repository would sign with. If crucible ever publishes a
release asset, its manifests are signed with this key and checked against this
pin.

## Trust

Establish the expected GPG primary key, the exact signing subkey, and the
minisign public-blob fingerprint through an independently trusted maintainer
channel before accepting these files. A key distributed beside a signature is
not independent authentication.

Tag verification reads the pins and anchors from the **tagged commit** as inert
Git objects, not from the current checkout or the environment. It imports the
pin into an isolated keyring and requires one good, unexpired signature by the
pinned signing subkey, with the committed tagger identity
(`config/release/tagger-identity.txt`). GitHub's "verified" flag is an
additional check, not a substitute.

## Checker

The anchors are derived and verified by **decernor 0.1.8 or newer**. The
minisign fingerprint covers the decoded public blob, not its comment line or
the whole file. Anchors are derived twice and compared; they are never typed
by hand.

- The release ceremony takes the checker from `THREELEAPS_CRUCIBLE_DECERNOR_BIN`:
  an absolute path to a regular, executable, non-symlink file. There is no
  fallback to `PATH`.
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
bootstrap installs goneat, so the goneat manifests are verified against this
committed file and never against a key fetched from the goneat release itself.

Provenance at adoption: the file is byte-identical to the copy committed in the
sfetch repository (`.github/keys/fulmenhq-goneat-minisign.pub`) and to goneat's
own committed release key, SHA-256
`8d6f8404b2a48bdbca9bbc755e0b54e83c6e58dd3be2fe7219fc2c9d4c68913d`. A change to
this file is a key rotation and is reviewed as one.

## Authorization

The release workflow has read-only permissions until the final publication
step. A passing tag workflow is a consistency signal; it is not release
authorization. The signed tag authorizes publication
([PDR-0004](../decisions/PDR-0004-release-publication-gate.md)).
