# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file keeps the latest three releases. Earlier releases, back to
> v0.1.17 (the first public baseline), are in [CHANGELOG.md](CHANGELOG.md) and
> [docs/releases/](docs/releases/).

---

## v0.1.33 (2026-10-12)

**Experimental durable queue and durable record contracts, verified release
keys, and faster contract checks.**

- **Durable queue (proposed)**: `durable-queue/v0` defines an at-least-once
  queue as a logical contract: envelope, fenced leases, ledger with atomic groups
  and fold rules, capability profile and a typed control exchange, with
  behavioral vectors. Portable restore and `replay` are deferred.
- **Durable record (proposed)**: `durable-record/v0` defines engine-neutral
  record storage: digest-pinned revisions, an append-only journal sharing the
  queue's consistent-cut rule, keyed idempotent writes with typed receipts, and
  a stratum profile declaring durability and supported deletion scope.
- **Decisions and review**: EPR-0005 (proposed) on test evidence independence;
  EPR-0002 states its evidence boundary per obligation; the fierce-collaboration
  standard 0.7.0 adds an evidence-residual taxonomy and a one-page review card.
- **Release verification**: signed tags are verified against estate-wide
  release-key anchors read from the tagged commit; `make release-push-tag`
  verifies, pushes and confirms the tag.
- **CI and toolchain**: Linux quality plus Windows amd64 contract checks; the
  release workflow no longer re-runs Check. Goneat advances to v0.6.3 and the
  glibc tools runner to v0.5.9.

See [docs/releases/v0.1.33.md](docs/releases/v0.1.33.md).

---

## v0.1.32 (2026-10-01)

**Experimental immutable snapshots, enforced attribution footers, and native
contract validation.**

- **Segmented snapshots (proposed)** — `segmented-snapshot/v0` adds publication,
  manifest, profile and verification schemas, semantic controls and conformance
  cases for a flat immutable snapshot. Exact stored-byte identity does not prove
  authentication, runtime custody or crash durability; adopter evidence remains
  separate.
- **Data-artifact clarification** — lifecycle, publication, source coverage and
  representation guarantees remain distinct.
- **Attribution checks** — commit messages and PR bodies use the enforced
  three-line footer, with a checker, hook and reusable workflow. Current
  documentation and all seven role-example files use the same cross-org format.
- **Native checks and toolchain** — full repository quality runs on Linux;
  contract validation runs on Linux amd64/arm64, Darwin arm64 and Windows
  amd64/arm64. Goneat advances to v0.6.1 and the glibc tools runner to v0.5.7.
  Windows arm64 builds the pinned Goneat source with verified module checksums.
- **Project management prompt** — the draft role emphasizes inspectable delivery
  state, review gates and explicit authority for irreversible actions.

See [docs/releases/v0.1.32.md](docs/releases/v0.1.32.md).

---

## v0.1.31 (2026-09-17)

**Portable identities for inference paths, a deny-by-default application
control contract, and a verified development toolchain.**

- **Inference path taxonomy (proposed)** — `inference-path-taxonomy/v0`
  separates parties, model families, exact source-native model pins, and
  declared routes without claiming observed execution, health, or billing
  identity.
- **Application control and observation (proposed)** —
  `application-control/v0` defines transport-neutral discovery, catalogs,
  replay-safe requests, observations, and decision/effect evidence while
  keeping hosted content sessions outside the control boundary. ADR-0010,
  DDR-0001, and SecDR-0001 record its architecture, data, and authority model.
- **Release-signing key rotation** — the committed OpenPGP public-key pin now
  matches the current signing key. The release workflow verifies annotated tags
  against this pin before publication.
- **Verified development bootstrap** — sfetch is pinned to v0.4.12 and installed
  through an immutable, digest-checked verification engine; Goneat is pinned to
  v0.6.0. Check and release jobs use the v0.5.6 glibc runner carrying the same
  Goneat release.

See [docs/releases/v0.1.31.md](docs/releases/v0.1.31.md).
