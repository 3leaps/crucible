# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file keeps the latest three releases. Earlier releases, back to
> v0.1.17 (the first public baseline), are in [CHANGELOG.md](CHANGELOG.md) and
> [docs/releases/](docs/releases/).

---

## v0.2.10 (2026-11-11)

**Adds a physical Parquet fixture corpus and complete independent logical reader for `durable-index/v0`, and tightens durable-record framing and schema validation controls.**

- **Durable-index physical and logical evidence:** binds 26 Parquet fixtures and
  six NDJSON twins with byte pins, signed and absent size annotations, both
  codecs and page versions, row-group and ordered member boundaries. Baseline
  controls check inventory, hashes, raw row schemas and logical parity; physical
  decoding and R2/W1/W2/W3 qualification remain separate. Extends the
  independent reader to all authored logical scenario categories and clarifies
  literal-prefix plan discovery.
- **Durable-record and validator controls:** refuses blank or whitespace-only
  journal lines at ingest, adds ancestor-seal refusals, and preserves
  schema-stage leap-second refusal alongside semantic timestamp checks. Updates
  exact-number, format, Unicode and validator-report controls; pins Goneat
  `v0.6.8` and the `v0.5.15` glibc runner.

`durable-index/v0` remains experimental. These fixtures do not qualify a
physical reader, writer, or storage runtime.

See [docs/releases/v0.2.10.md](docs/releases/v0.2.10.md).

---

## v0.2.9 (2026-11-08)

**Specifies the `durable-record/v1` retention policy for retired-record body reclamation, designated `body-removal` stream recovery, and detached canonical `stream-seal` artifacts; adds the draft `identity-evidence/v0` `native-process-observation:v0` provider profile; and hardens the RFC 8785 JCS and RFC 3339 instant helper scripts.**

- **Durable-record `v1` retention policy, designated `body-removal` recovery, and detached stream seals**:
  specifies deterministic Precedence `1 -> 2 -> 2b -> 3 -> 4 -> 5` eligibility
  evaluation for removing external body bytes referenced only by retired records
  under a store-wide exclusion fence (designated-stream placement and target
  `incarnation` `body_removal_stream` / `body_lifecycle` state, store-wide stream
  and continuation coverage `protection_unavailable`, same-store
  `decision_time >= e["at"]` `journal_time` ordering, conservative
  continuation/sealed-ancestor `protected_use` hold blocking, `still_referenced`
  on unretired referencing records, and `{id, version}` policy-bound
  `removal_authorization` verification), paired with
  `schemas/durable-record/v1/removal-eligibility-request.schema.json`. Adds
  designated `body-removal` stream recovery via `stream_opened.recovery` and
  `runtime.quarantined_designated_streams` under
  `runtime.incarnation_allocation: "prewrite_durable_ledger"`, the 19-row
  per-`(digest, length)` reconciliation table (`R1`–`R19`, `recovery_incomplete`),
  and sticky `publishing` / `integrity_loss` carry-forward across clean cuts and
  multi-hop predecessor replay. Adds `schemas/durable-record/v1/stream-seal.schema.json`
  for detached canonical RFC 8785 JCS stream seals with canonical
  `effective_restriction_manifest_digest` preimages, transitive `ancestor_seals`
  finality verification, zero trailing bytes at `cut_seq`, and conservative
  sealed-ancestor hold dominance, backed by 183 new conformance vectors (395
  total), 17 new schema reject fixtures (66 total), and 107 new AST mutation
  witnesses (187 total).
- **Identity evidence (`native-process-observation:v0`, draft)**: adds
  `schemas/identity-evidence/v0/profiles/native-process-observation/`
  (`profile.json`, `evidence.schema.json`, `README.md`, and platform examples)
  plus `schemas/identity-evidence/v0/examples/native-process-observation.json`
  for standalone native process incarnation and context observation without
  requiring launch or possession evidence, defining the seven-state fact
  visibility vocabulary mapped 1:1 to report capability status, host-scope and
  clock/user/PID-namespace descriptor semantics, three-class Linux `/proc`
  `openat2` and magic-link resolution rules, `u32`/`u64` integer bounds,
  incarnation bracketing, and fail-closed projection into
  `local-process-session:v0`.
- **RFC 8785 canonicalization and RFC 3339 instant helper hardening**: replaces
  recursive JSON parsing and serialization in `scripts/rfc8785-canonicalize.py`
  with an iterative implementation enforcing explicit input bounds, rejecting all
  66 RFC 7493 §2.1 Unicode noncharacters across planes `0..16` and out-of-domain
  integer tokens before arbitrary-precision expansion, and adding `--check`,
  `--digest`, `--vector`, `--ndjson-array` (`--head N`), and `--sort-set` CLI
  modes (`scripts/test-rfc8785-controls.py`); extends `scripts/rfc3339-instant.py`
  with `max_fraction_digits`, `reject_submicrosecond_nonzero`, and exact
  arbitrary-precision fractional ordering in `compare`.

See [docs/releases/v0.2.9.md](docs/releases/v0.2.9.md).

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
