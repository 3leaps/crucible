# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file keeps the latest three releases. Earlier releases, back to
> v0.1.17 (the first public baseline), are in [CHANGELOG.md](CHANGELOG.md) and
> [docs/releases/](docs/releases/).

---

## v0.2.6 (2026-10-30)

**Durable-record bounds protocol integers at 2^53 - 1 and batches schema validation; role catalog adds draft devsecops, mediaeng and creative prompts and refines secops.**

- **Durable-record (`v0` and `v1`)**: bounds all 53 contract-defined integer
  fields across all 13 `durable-record/v0` and `durable-record/v1` schemas at
  `9007199254740991` ($2^{53} - 1$), leaving arbitrary `record.payload` numbers
  and `scripts/rfc8785-canonicalize.py` unchanged. Defines the four-stage wire
  evaluation order (`ingest` -> `numeric_domain` -> `shape` -> `logical
semantics`) with bounded raw-token safe-integer inspection before binary64
  rounding, counter-exhaustion refusal without wraparound, and typed-boundary
  range enforcement. Batches schema validation through `goneat validate suite
--format json` so parser, range or tool failures raise harness errors rather
  than satisfying negative schema cases.
- **Role catalog (`devsecops` 1.0.0, `mediaeng` 1.0.0, `creative` 1.0.0, `secops` 1.1.0)**:
  adds draft `devsecops` (repository-side security tooling, CI security gates,
  signing/verification automation and supply-chain pinning without live secrets
  or signing authority), `mediaeng` (deterministic audio, video, graphics,
  vector, DSP, codec and rendering pipelines) and `creative` (structured
  musical, video, vector and procedural media production under human artistic
  direction), and updates `secops` (`1.1.0`) to sharpen boundaries with
  `devsecops` and `watcher`.

See [docs/releases/v0.2.6.md](docs/releases/v0.2.6.md).

---

## v0.2.5 (2026-10-29)

**Role prompts add execution continuity; contract controls fix UTF-8 subprocess decoding and large integer body lengths.**

- **Role prompts (`devlead` 1.2.0, `devrev` 1.3.0, `uxdev` 1.2.0)**: add
  execution-continuity guidance and bounded implementation, review and
  interface loops while keeping existing authority and independent-review
  boundaries unchanged.
- **Fixed**: contract and permission controls decode captured subprocess output
  as UTF-8 with replacement rather than the host locale's default encoding, and
  durable-record/v1 logical controls handle nonnegative integer body lengths
  above the floating-point range without `OverflowError`.

See [docs/releases/v0.2.5.md](docs/releases/v0.2.5.md).

---

## v0.2.4 (2026-10-28)

**Durable-record/v1 records body lifecycle; release tag tooling closes four silent defaults.**

- **Body lifecycle (durable-record/v1, additive)**: a store that supports
  removing external bodies names a `body_removal_stream` and records
  `body_published`, `body_removal_started` and `body_removed` there, per body
  and incarnation. A removal is evidenced only by `body_removed`; a later
  publication abandons an open removal. Reader states are defined at a
  consistent cut. Lifecycle grants no removal eligibility, and physical
  removal stays fail-closed. Existing v1 records and journals are unchanged.
  The logical controls qualify no store.
- **Release tag tooling**: `make release-tag` refuses the default keyring and
  signs with a pinned OpenPGP `gpg` signer, reporting any configured signer it
  overrides; `make release-push-tag` uses the
  explicit HTTPS URL with only the org token, isolated from home credentials,
  proxy and TLS overrides. The read-only ruleset check no longer reports a
  hidden bypass list as a match.

See [docs/releases/v0.2.4.md](docs/releases/v0.2.4.md).
