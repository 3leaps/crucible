# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file keeps the latest three releases. Earlier releases, back to
> v0.1.17 (the first public baseline), are in [CHANGELOG.md](CHANGELOG.md) and
> [docs/releases/](docs/releases/).

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
