# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file keeps the latest three releases. Earlier releases, back to
> v0.1.17 (the first public baseline), are in [CHANGELOG.md](CHANGELOG.md) and
> [docs/releases/](docs/releases/).

---

## v0.2.8 (2026-11-07)

**Defines `durable-record` (`v0` and `v1`) RFC 3339 instant validation profiles and finite JSON Schema subset admission, deprecates `durable-record/v0` for new producers, specifies the `durable-record/v1` writer-owned incomplete-append abort boundary and `runtime.incarnation_allocation`, adds the draft `opslead` role, and adds workflow supply-chain, key-expiry, and local-path hygiene gates.**

- **Durable-record (`v0` and `v1`) timestamp profiles, `v0` deprecation, and `v1` incomplete-append abort boundary**:
  enforces ASCII-only RFC 3339 instant validation with year bounds `0001`–`9999`
  (`0000` and UTC year underflow/overflow refused), proleptic Gregorian calendar
  validation, unconditional `:60` leap-second refusal, per-position Stage 3 vs.
  Stage 4 evaluation trace, and finite JSON Schema Draft 2020-12 keyword subset
  admission (forbidding sibling assertion keywords alongside `$ref`). Marks
  `schemas/durable-record/v0/contract.json` as `"status": "deprecated"`
  (`"superseded_by": "contract: durable-record/v1"`) for new stream production
  while keeping historical `v0` validation intact. Specifies the
  `durable-record/v1` writer-owned incomplete-append abort boundary (`0 <= k < L`
  under continuous reader and writer exclusion, `SameFile` descriptor identity
  on the truncate handle, `fsync` of file and directory, post-truncate `fstat`
  size match, prior-cut `1..cut_seq` re-validation, and fail-closed in-process
  handle poisoning on indeterminate commits or gate failures) and adds optional
  `runtime.incarnation_allocation` (`"effect_dependent"` |
  `"prewrite_durable_ledger"`) to `stratum-profile.schema.json`.
- **Agentic role catalog (`opslead` `1.0.0`, draft)**: adds supplemental
  `config/agentic/roles/opslead.yaml` (category `governance`, domains
  `governance`, `coordination`, and `automation`) and
  `docs/catalog/roles/opslead.md` for accountable stewardship of estate
  operating procedures, seat and identity lifecycle records, and operating
  baselines, with explicit boundary separation from `dispatch`, `secops`,
  `devsecops`, `projectmgr`, and `cxotech`.
- **Workflow supply-chain pinning, signing-key expiration horizon, and local-path hygiene**:
  adds `scripts/test-workflow-pins.sh` (enforcing 40-hex commit SHA pins with
  version comments on `uses:`, `@sha256:` digests on `container` images, and
  workflow permission boundaries), `check_release_key_expiry` in
  `scripts/release-env.sh` wired into `scripts/release-derive-anchors.sh` and
  `scripts/release-verify-anchors.sh` (failing closed on expired primary or
  signing subkeys and warning within 30 days of expiration), and
  `scripts/content-check.py` (scanning tracked files for generic local OS path
  shapes).

See [docs/releases/v0.2.8.md](docs/releases/v0.2.8.md).

---

## v0.2.7 (2026-11-02)

**Adds proposed `identity-evidence/v0` and draft `seat-spheres/v0` contracts, extends `project-work/v0` with commitment and `agent`/`run` provenance fields, adds the draft `advisor` role, splits SPDX `MIT`/`CC0-1.0` license files, and enforces pre-sign tagger identity.**

- **Identity evidence (`identity-evidence/v0`, proposed) and identity-assurance classifiers**:
  adds `docs/standards/identity-evidence-contract.md`,
  `docs/standards/identity-assurance-classification.md`, four categorical
  classifier dimensions (`identity-binding`, `key-custody`,
  `execution-isolation`, `platform-evidence`), and the
  `schemas/identity-evidence/v0/` schema, profile (`local-process-session` and
  `report-admission`), example and vector bundle with batched logical and wire
  controls.
- **Seat spheres (`seat-spheres/v0`, draft) and `project-work/v0` commitment/provenance**:
  adds `docs/standards/seat-spheres-model.md` and `schemas/seat-spheres/v0/` for
  seat `function`, `reports_to`, per-subject `spheres[]` (`lead`, `support`,
  `advise`, `assure`, `interested`), read-time rollup rules and packet-to-subject
  linking; extends `project-work/v0` with `requested_by`, `check_by`, `agent`
  (requiring `role`) and `run` (requiring `parent`, `expires` and packet
  `check_by`) party kinds, standardized `person-id` (`^[a-z][a-z0-9._-]{0,63}$`,
  excluding `agent-` and `run-`), and `schemas/project-work/v0/semantic-validation.md`.
- **Role catalog, licensing and release provenance**: adds supplemental draft
  `config/agentic/roles/advisor.yaml` (`1.0.0`, category `consulting`); splits
  root licensing into verbatim SPDX `LICENSE` (`MIT`), `LICENSE-CC0` (`CC0-1.0`)
  and `NOTICE` (`package.json` `"(MIT AND CC0-1.0)"`); requires verified
  `THREELEAPS_CRUCIBLE_TAGGER_NAME`, `THREELEAPS_CRUCIBLE_TAGGER_EMAIL` and
  `THREELEAPS_CRUCIBLE_PGP_KEY_ID` (`^[0-9A-F]{40}!$`) before `gpg` signing in
  `scripts/release-tag.sh`; and fixes `durable-record` (`v0` and `v1`) wire
  preflight to catch `OverflowError` on large non-protocol integers and order
  document-wide `ingest` checks ahead of `numeric_domain`.

See [docs/releases/v0.2.7.md](docs/releases/v0.2.7.md).

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
