# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **durable-record/v1 body lifecycle.** A store that declares
  `deletion.external_bodies: supported` names a `body_removal_stream` in its
  profile and records `body_published`, `body_removal_started` and
  `body_removed` there, per `{digest, length}` and strictly increasing
  `incarnation`. A removal is evidenced only by `body_removed`, written after
  absence is observed; a start alone proves nothing, and a later publication
  abandons it. Reader states (`available`, `integrity_loss`, `removal_pending`,
  `removed`, `publishing`, `unpublished`) are defined at a consistent cut. The
  section states fencing by incarnation and that lifecycle entries grant no
  removal eligibility. New refusals `body_removal_stream` and `body_lifecycle`;
  vectors, schema rejects and mutation witnesses cover them.

### Changed

- **Release tag tooling closes four silent defaults.** `release-tag` refuses a
  signing keyring that is the default keyring by either `gpgconf`'s homedir or
  the account home from the user database, and stops if either cannot be
  resolved. Signing requires OpenPGP through `gpg`: a configured `gpg.format`,
  `gpg.program` or `gpg.openpgp.program` naming anything else is refused, and
  the signing command pins all three. `release-push-tag` fetches, checks,
  pushes and confirms over `https://github.com/3leaps/crucible.git` instead of
  `origin`, with only the org token direnv loads and gh's credential helper, and
  with git isolated from the home directory, global configuration and proxy or
  TLS environment; a missing token, a URL rewrite, proxy, TLS, extra header,
  cookie file or username setting, or a failed remote read stops it. The release workflow's read-only ruleset check
  no longer reports a hidden bypass list as a match; it says the list was not
  checked. The one-time v0.2.3 tag ceremony section is removed from
  `RELEASE_CHECKLIST.md`.

## [0.2.3] - 2026-10-27

### Added

- **durable-record/v1 continuation streams and restriction review.** A stream
  that re-records another stream's content declares `continues` (source
  capability, stream and complete-group cut digest) on `stream_opened`, and
  marks each re-recorded entry with `imported_from`. A `restrictions_reviewed`
  entry binds the reviewed source cut, the effective source restriction
  manifest (including inherited reviews) and the destination's applied
  manifest, with an authorization reference. Serve, export and reuse of a
  continuation fail closed as `restrictions_pending` until a current review
  exists; a later import, a destination restriction change, or a
  restriction change in the source or any ancestor reopens it. New
  refusals `restrictions_pending` and `continuation`; vectors, schema rejects
  and mutation witnesses cover each rule. An empty or malformed observed
  source journal is refused as `continuation`.

### Changed

- **Repository classes clarifications (draft 0.1.1).** C5 requires a `version`
  subcommand (a `--version` flag alone does not satisfy it), accepts a
  JSON-only reporting verb without a `--format` flag, and exempts a verb
  whose stdout is the transformed artifact from `--format json` when the CLI
  has a JSON reporting verb. C3 counts test-only and harness variables. C4
  points repos with host-tool release ceremonies at a `doctor` target. P1
  accepts the `@3leaps/` npm scope as the reservation and a named intended
  PyPI distribution as a planned Python binding.

## [0.2.2] - 2026-10-25

### Added

- **Repository classes (draft).** `docs/standards/repository-classes.md` picks a
  repo's class by its primary caller (prims, bolts, wits, voys; pressers as an
  adjacent class), lists per-class MUST characteristics with observable checks,
  a repo declaration and a new-repo template. Prims declare a four-language
  commitment in two profiles (Rust core, or pure-Go and Rust twins that lock
  step once both operate) and may depend on sibling prims under four rules:
  pinned and public by first public release, no sibling implementation types
  in the contract, a pure-Go tree depends only on cgo-free modules, and the
  prim graph is acyclic with declared leaves. The class check is a manual
  review step until the declaration schema ships. ADR-0018 records the
  decision.

### Changed

- **PDR-0008 is accepted.** Its proof is `v0.2.1`, the first release tagged
  under the adopted ceremony: the tag workflow and an independent verification
  both checked the committed pins with the digest-pinned checker and the
  signature against the pinned subkey.
- **The default GPG keyring is never used.** `release-tag` requires
  `THREELEAPS_CRUCIBLE_GPG_HOMEDIR`, an absolute path to a dedicated,
  non-symlink keyring; an unset value, a path that resolves to the default
  keyring, or an inherited `GNUPGHOME` naming a different directory is refused
  before any side effect. `release-verify-tag` no longer runs a check against
  the ambient keyring; it uses only the pinned check, which imports the
  committed pin into a throwaway keyring. Negative controls cover each refusal,
  and an end-to-end control proves that verification ignores the ambient
  keyring.
- **Release targets use one naming pattern.** The `release-tag-push` alias is
  removed; use `make release-push-tag`.
- **Durable-record/v1 carries record envelope `v: 1`, production time and
  keyed retirement.** Amended in place on 2026-10-25, when durable-record/v1
  had no adopters; not additive. The v1 record envelope moves to wire version
  1, so the digest and pin of every v1 record change, whether or not it
  carries `produced_at`; the v0 family is untouched. A v1 record is the v0
  envelope with `v` changed to `1` and an optional `produced_at` (`instant`,
  `source` of `producer_clock` or `trusted_time`, and evidence when trusted)
  inside the record digest. A `v: 0` record in a v1 journal is refused as
  `record_version`. Every v1 wire instant is a valid UTC date and time with
  exactly six fractional digits and no leap second; readers refuse anything
  else as `instant_spelling` and never normalize under a digest. `retired`
  gains an optional idempotency key with an accepted `retired` write
  receipt; an unkeyed retirement keeps no receipt. `seq` is stated to be
  non-portable. All v1 vectors and examples are re-derived, and new vectors
  cover each rule. ADR-0019 records the amendment.
- **Durable-record/v1 stratum profiles name the commit step from a closed set.**
  `runtime.commit_strategy` is now one of `fsync_file_and_dir`, `fsync_file`,
  `backend_acknowledged` or `none`, so profiles can be compared; free-text
  detail moves to the optional `commit_note`. Both remain information only and
  never upgrade `failure_model`. The v1 standard also states that selection by
  label is an exact string match defined by the adopter, not a store
  guarantee. Record envelopes and digests are unchanged, and v0 is untouched.

### Fixed

- **The durable-queue reference model keeps a fractional `clock_start`.** Its
  timestamp formatting took the fraction from `at_ms` alone, so a non-whole-second
  `clock_start` lost its fraction or carried wrongly; the contract already
  derives each instant from `clock_start` plus `at_ms`. The model now formats the
  computed instant. A new `fractional-clock-start-carry` vector exercises second
  carry at the ledger `at`, `lease_until` and `not_before` endpoints, and a
  mutation control requires the old formatting to fail it. The existing vectors
  are unchanged.
- **The tag-ruleset guard reports a failed GitHub read as a read failure.** An
  authentication error from `gh` produced empty output that was reported as
  "found 0" rulesets. The guard now stops with a message that the ruleset was
  not checked and the credential is the likely cause, and a negative control
  covers both reads.
- **`release-push-tag` separates a pushed tag from an unreadable verified
  flag.** After the push and the remote-object match, a failure to read
  GitHub's verified flag is reported as such, with a warning not to push or
  delete the tag again; an explicit "not verified" stays an error. The
  repository is no longer looked up through `gh`.

## [0.2.1] - 2026-10-23

### Changed

- **Release tooling adopts PDR-0008.** This release's tag is the first made
  under the adopted ceremony. The minisign pin is renamed
  `docs/security/crucible-minisign.pub`, and `keys/expected-fingerprints.ndjson`
  joins the text anchors. Both are derived by decernor (0.1.8 or newer), twice
  and compared, and tag verification checks them with that tool. CI downloads
  decernor by the digest pinned in
  `config/release/decernor-ci-sha256.txt`. `docs/security/README.md` states
  what a release carries: a signed tag only, with no signed checksum manifests.
- **Release inputs are explicit.** Every tag step requires
  `THREELEAPS_CRUCIBLE_RELEASE_TAG`, and every step that reads a pin also
  requires `THREELEAPS_CRUCIBLE_DECERNOR_BIN`. The tag is never derived from
  `VERSION` or `git describe`, the checker has no `PATH` fallback, and
  `RELEASE_TAG`, `THREELEAPS_CRUCIBLE_REQUIRE_TAG` and the unprefixed
  `CRUCIBLE_*` aliases are refused. `RELEASE_CHECKLIST.md` is
  updated to match.
- **goneat is verified against a committed key.** Bootstrap passes
  `docs/security/fulmenhq-goneat-minisign.pub` to sfetch with `--minisign-key`.
- **CI baseline.** `docs/operations/ci-baseline.md` pins images by digest,
  actions by commit and tools by version and digest, and adds gotchas for
  `grep -q` under `pipefail`, Windows runners and images missing a tool, plus a
  supply-chain section.

### Added

- **Verified immutable release publication (proposed).** PDR-0010 sets controls
  for verifying a release's staged assets before immutable publication: a
  committed release definition that resolves to an exact asset set, a
  pre-publication verification record checked again after publication, distinct
  outcomes, and enablement only once a repository's ceremony makes every asset
  change while the release is a draft. PDR-0004 carries a proposed-successor
  notice and governs until a repository adopts it.
- Negative controls for every new refusal: `make test` covers the release
  inputs, the checker binding and the checker download digest gate (offline,
  with a stubbed download), and a new `release-identity` CI job runs the
  end-to-end tag controls with the digest-pinned checker.

## [0.2.0] - 2026-10-22

### Added

- **Release public identity in the tree (proposed).** PDR-0008 generalizes the
  committed-key-pin posture of PDR-0004: public pins are committed blobs read
  from the tagged commit, one designated checker derives and verifies
  fingerprint anchors, the ceremony binds its checker and tag as explicit
  inputs with no fallback, and third-party verification keys are committed
  files named by origin. Layout is a recommended default; controls are the
  mandate.
- **Recurrence rule contract (proposed).** Add the `recurrence/v0` family: a
  canonical JSON form of an RFC 5545 RRULE subset, normative expansion
  semantics (DST gaps skipped without consuming `COUNT`, overlaps resolved to
  the first instant, inclusive `UNTIL`, half-open queries), normalization
  before JCS digests, and a conformance corpus pinned by digest to IANA tzdb
  2026e. Promotion requires two independent implementations to pass the
  corpus.
- **Durable record tombstoning (proposed, experimental).** Add the
  `durable-record/v1` family with retained audit history, scoped holds, targeted
  restoration, shared keyed replay and current-cut export decisions. Preserve
  v0 record envelopes and pins. Include schemas, a standard, ADR-0019 and
  logical vectors with mutation controls; no storage backend is qualified.
- **Data acquisition contract (proposed).** Add the experimental
  `data-acquisition/v0` family with source-policy, acquisition-plan and
  registration-result schemas, exact-byte digest pins, attributed scope
  compromises and explicit unavailable and indeterminate outcomes. Include a
  standard, ADR-0014, synthetic examples, a refusal-reason vocabulary and
  file-based schema and semantic reject fixtures. A single allocation must fit
  the policy ceiling. Registration records capacity; runtime admission and
  adopter qualification remain separate.
- **Durable index contract (proposed, experimental).** Add the
  `durable-index/v0` family: object-inventory snapshots as a segmented-snapshot
  profile, with index row, plan, metadata, publication and identity-cutover
  schemas, a standard, conformance requirements, ADR-0017 and DDR-0004.
  Observation plans use a length-framed semantic digest over canonical
  unicode-prefix scopes. Only confirmed-complete, gap-free scopes authorize
  absence-derived tombstones; reduced scope requires an acknowledgment bound to
  the exact parent and plan. Logical vectors and complete logical projection
  graphs only: physical Parquet twins and a physical reader are adoption
  gates, and no physical reader, producer or storage backend is qualified.
  Composition does not ratify `coverage-attestation/v0`.

### Changed

- **Shipping charter: validation interpreters and scope.** PDR-0006 gains Rule
  2c. Python >= 3.9 and Node.js >= 22.6 are the named validation interpreters for
  contract tooling, TypeScript tooling uses erasable syntax only, and a
  validation tool must import only its standard library and run with no install
  step. Contract tooling is limited to establishing contract compliance;
  benchmarking and load testing belong in separate test repositories using
  synthetic data only. An independent checker is distinguished from a reference
  implementation, and a known disagreement must be resolved before the next
  tagged release.
- **Durable index independent reader.** Add `scripts/durable-index-reader.ts`,
  a TypeScript checker written from the standard's text and sharing no code
  with the Python checker. It checks plan vectors, transition vectors and
  transition rejects against their authored outcomes and runs in contract
  shard 3. Windows contract shards set up Node.js, and the shard guard now
  requires every TypeScript tool under `scripts/` to run in exactly one shard.
- **Data acquisition contract hardening (proposed).** Define half-open
  allocation intervals and an aggregate span ceiling, replay and request
  identity scoped to entity/source across authority epochs, and opaque
  credential reference names. Refuse empty query and fragment delimiters and
  whitespace in target URLs, and state that URL checks are not a
  safe-to-request claim. Add ledger reject fixtures and checker-profile labels
  for profile-dependent vectors.
- **Segmented snapshot manifest profile metadata (proposed).** Add an optional,
  digest-bound `profile_metadata` binding to
  `segmented-snapshot/v0/snapshot-manifest.schema.json`. This changes the
  schema's bytes under the same `$id`. Existing manifests keep their meaning
  and remain valid. A reader that does not implement `profile_metadata` must
  refuse a manifest that contains it, including on selective reads.
- **Durable index contract clarifications (proposed).** State that a plan's
  `set_id` equals the selection's `namespace_id`, the index-set identity, not a
  scope's object `namespace`. State that only full transition verification
  establishes inherited lineage, so a snapshot-only reader must not report it as
  verified. Add rejects for timestamps with a trimmed or omitted fraction and
  for an inherited stamp naming a snapshot outside the verified chain. Clarify
  that the synthetic profile-metadata dependency cases are refused by its closed
  shape, not by cycle detection. List the durable-queue and durable-record
  standards in the docs index.
- **Goneat v0.6.5; glibc tools runner v0.5.12**, consumed by immutable digest.
  The image carries biome 2.5.15, Node.js 22.23 and Python 3.11, which meet the
  validation interpreter floors. `biome.json` declares the biome 2.5.15 schema
  and migrates the deprecated `linter.rules.recommended` to
  `"preset": "recommended"`.
- **Recurrence non-slot and shift-policy rules.** The recurrence standard
  states that a DST-skipped generated instance is a non-slot, never recorded as
  missed, and that any future shift-forward behaviour is a separately named
  policy within the rule's identity and digest.

### Fixed

- **Release guards no longer pipe into `grep -q` under `pipefail`.** The
  release-surface guard and the tag script read from here-strings, so an early
  match can no longer make the producer die of SIGPIPE and report a false
  failure on a large changelog. A large-changelog control fails the piped form
  deterministically.

## [0.1.34] - 2026-10-16

### Added

- **Agent interface classifiers (draft).** Four categorical dimensions
  describe one agent interaction separately: `agent-seat-class` (who manages
  the session lifecycle), `agent-control-surface` (the selected entrypoint),
  `agent-transport` (the carrier at one connection boundary) and
  `agent-adapter-confidence` (an evidence-derived assessment; policies accept
  explicit states rather than thresholds). `schemas/classifiers/v0/agent-interface.schema.json`
  validates a nonempty selection of values only; it confers no authority.
  The standard is `docs/standards/agent-interface-classification.md`.
  `scripts/test-agent-classifier-controls.py` checks schema/dimension parity
  and refusal cases.

- **Agent interface profiles (draft).** Add a separate revisioned profile schema
  for per-hop protocol composition, execution lifetime and context continuity,
  and distinct delivery, execution and cursor-commit signal mappings. Include
  synthetic examples, a normative local-reference checker and refusal controls.
  Profiles declare interfaces; they confer no authority or qualification.

### Changed

- **Check job timeouts** are 20 minutes on Linux and 25 minutes per Windows
  shard.
- **Windows contract checks run as three parallel shards**
  (`make check-contracts-shard-N`). `make check-contracts` runs all three; a
  single `windows` status reports the combined result.
  `scripts/test-contract-shards.sh` (part of `make test`) fails if a contract
  check runs in no shard or in more than one, or if the workflow matrix and
  the Makefile shard list disagree.
- **`RELEASE_NOTES.md`** keeps the latest three releases. Earlier releases
  remain in `CHANGELOG.md` and `docs/releases/`.
- **Offline schema validation.** Make targets validate schemas against
  goneat's embedded meta-schemas (`GONEAT_OFFLINE_SCHEMA_VALIDATION=true` by
  default), so checks make no network fetches. Set it to `false` to validate
  against the published meta-schemas instead.
- **Goneat v0.6.4; glibc tools runner v0.5.10**, consumed by immutable digest.
  Goneat v0.6.4 no longer runs package-manager version probes on every
  command, which cuts per-invocation startup time. Check fails if the runner
  image's goneat differs from `GONEAT_VERSION`.

## [0.1.33] - 2026-10-12

### Added

- **Durable record contract (proposed).** Add the experimental
  `durable-record/v0` family: revisioned records with stable identity and
  RFC 8785 digest pins, digest-bound body references, provenance, required
  retention and sensitivity classification, an append-only journal sharing the
  durable-queue consistent-cut rule, keyed idempotent writes with typed
  receipts and reconciliation, and a stratum profile declaring failure model
  and supported deletion scope. Ships `docs/standards/durable-record-contract.md`,
  ADR-0013, golden examples, one-field schema reject pairs, semantic reject
  journals, `scripts/validate-durable-record-fixtures.py` and
  `scripts/test-durable-record-controls.sh`. Redaction of journal history,
  shared stream metadata, multi-host ownership, merge, a wire binding and
  behavioral vectors are deferred.

- **Test evidence independence (proposed).** Add EPR-0005: relied-upon tests
  take expected results from a source the implementation does not determine,
  draw specimens from a separate authority where a shared corpus exists, state
  class invariants, and carry confirmed findings into durable specimens.

- **Fierce-Collaboration Review Card** (`docs/guides/`). The minimum
  conforming relied-upon review on one page: declaration, independent-pass
  rule, register shape, verdict contract, residual classes, and close-out
  checks. Indexed from `docs/README.md` and linked from the run-book.

- **Durable queue contract (proposed).** Add the experimental
  `durable-queue/v0` family, narrowed to an audit and lifecycle fold:
  at-least-once message envelope, queue-scoped fenced leases, closed ledger
  vocabulary with atomic groups and fold rules, capability profile with
  separate build and runtime facts and a guaranteed failure model, and a
  control exchange with typed per-operation requests and results. Ships
  `docs/standards/durable-queue-contract.md`, ADR-0012, golden examples, a
  service-job composition example, one-field schema reject pairs, semantic
  reject vectors, core, fan-out and canonicalization behavioral vectors,
  `scripts/validate-durable-queue-vectors.py` and
  `scripts/test-durable-queue-controls.sh`. Portable restore, `replay`,
  cross-queue fan-out and tolerant conformance are deferred. The service-job
  standard gains a composition note on idempotency scopes and transport
  versus job completion.

- **`make release-push-tag`.** Verifies the local signed tag, requires the
  tagged commit on `origin/main` and the remote tag absent, pushes the tag ref
  and confirms the remote object. `release-tag-push` is an alias.

- **Release-key anchors.** Add `keys/expected-fingerprints.txt`,
  `docs/security/release-minisign.pub` and `config/release/tagger-identity.txt`,
  matching the other 3leaps repositories. `scripts/verify-pinned-tag.sh` reads
  them and the pin from the tagged commit, and requires one good signature by
  the single pinned signing subkey and the committed tagger. The release
  workflow and `make release-verify-tag` use it.

### Changed

- **EPR-0002 evidence boundary per obligation.** The reference-implementation
  boundary is stated separately for each obligation. The principle and the
  four obligations are unchanged.

- **Fierce-collaboration standard 0.6.0 → 0.7.0: evidence-residual
  taxonomy.** §5 classifies every evidence gap that cannot be resolved before
  the gate as exactly one of four residual classes: pre-land blocker, narrowed
  claim, post-merge follow-up, or unsupported/fail-closed. A post-merge
  follow-up (owner, dependency, closure trigger, kill date) covers only
  evidence the present claim does not need; claim-critical evidence blocks or
  narrows the claim. Unclassified residuals fail closed as pre-land blockers,
  and follow-ups past their kill date escalate. §4's evidence-binding rule
  points at the taxonomy.

- **CI simplified.** Check runs full repository quality in the pinned Linux
  tools-runner plus contract checks on GitHub-hosted Windows amd64. The
  release workflow no longer re-runs Check. Removed the arm64 and macOS cells,
  the Windows arm64 Goneat source build and its pins, and the native identity
  checker; Windows path-portability and permission-fixture tests remain as
  `make test-portability`.
- **Release signing pin.** `docs/security/release-signing-keys.asc` now holds the
  public primary and signing subkey only, byte-identical to the other 3leaps
  repositories.
- **Goneat v0.6.3; glibc tools runner v0.5.9**, consumed by immutable digest.
  Goneat v0.6.3 compiles its embedded schemas on first use instead of at
  process start, which shortens every contract-control invocation.
- **Check job timeouts** are 45 minutes.

## [0.1.32] - 2026-10-01

### Added

- **Portable path boundaries (proposed).** Add DDR-0003 for forward-slash
  tool-facing path serialization, separate pointer fragments and strict
  one-to-one validation-report binding.

- **Segmented snapshots (proposed).** Add the experimental
  `segmented-snapshot/v0` publication, manifest, profile and verification schemas,
  semantic controls, conformance cases and architecture/data decisions.

- **Attribution footer check.** Add `scripts/check-attribution.py` (check,
  including `--markdown` example extraction, append, commit-msg hook, GitHub
  Action entry), a composite action and reusable workflow that fail a PR
  whose body does not end with the required trailer, and
  `docs/repository/attribution-footer.md` with caller and hook install
  snippets. The 3leaps baseline footer is `Role`, then `Co-authored-by`,
  then `Committer-of-Record: @3leapsdave`.

### Changed

- **Attribution guidance.** Align current documentation and all seven role-example
  files with the enforced three-line commit and PR footer across organizations.

- **Snapshot validation portability.** Separate catalog JSON pointers from
  filesystem paths and serialize generated metaschema input paths in
  forward-slash form. Add Windows/POSIX detecting regressions and reject duplicate,
  foreign, missing or extra metaschema report identities.

- Clarify data-artifact lifecycle, publication, coverage and representation
  boundaries.

- **Native platform checks.** Require full repository quality on Linux and
  contract validation on Linux amd64/arm64, Darwin arm64, and Windows amd64/arm64
  before CI or release verification succeeds.

- **Development toolchain.** Advance the verified Goneat bootstrap pin to
  v0.6.1 and both CI glibc tools-runner pins to v0.5.7.

- **projectmgr delivery substance.** Reshape the draft `projectmgr` prompt
  around landing a stated release arc or other quantifiable unit of work
  (critical path, risk, reshape/re-risk, owners, readiness). Encode
  inspectable state, gated completion sequences, folded HOLDs, earned
  successor acceptance, precise residuals, GO teeth on irreversible steps,
  delta-after-first-reconvene, and inactivity ownership. No required
  project methodology. `deliverylead` remains deprecated in favor of
  `projectmgr`. Inference pins stay on the adopting estate, not in this
  catalog.

## [0.1.31] - 2026-09-17

### Added

- **Inference path taxonomy (proposed).** Add `inference-path-taxonomy/v0` for
  party identities, model families, exact source-native model pins, and
  declared inference paths, with examples, rejects, and semantic controls.
- **Application control and observation contract (proposed).** Add
  `application-control/v0` schemas, conformance fixtures, semantic validation,
  the reader-facing contract standard, and ADR-0010, DDR-0001, and SecDR-0001.

### Changed

- **Release-signing key pin.** Rotate the committed OpenPGP public key used by
  the release workflow to verify newly created annotated tags before
  publication.
- **Verified development bootstrap.** Pin sfetch v0.4.12 and its immutable,
  digest-checked verification engine; install sfetch and Goneat v0.6.0
  repo-locally without trusting ambient PATH tools.
- **CI toolchain.** Align check and release jobs on the v0.5.6 glibc runner,
  which carries Goneat v0.6.0.

## [0.1.30] - 2026-08-27

### Added

- **Portable Forge Infrastructure Contract (draft).** Add the
  `forge-infra/v0` seven-lane contract, canonical capability catalog,
  evidence-backed provider and authority profiles, digest-bound binding plans,
  non-secret transition receipts, time-bounded verification receipts, object
  references, examples, rejects, and cross-document controls.
- **ADR-0009: forge infrastructure contract.** Record the separation of
  neutral forge capabilities, provider-native mappings, authority control, and
  live assurance.
- **Forge-infra reader guide.** Add a mechanics companion covering the
  information model, seven lanes, and sibling-contract boundaries.

### Changed

- **Validation coverage.** `make check` now runs the forge-infra control
  battery (examples, structural and semantic rejects, policy-input and
  bind-chain invariants) and the forge-infra contract manifest.

## [0.1.29] - 2026-08-24

### Added

- **Portable Project Work Contract (draft).** Add the `project-work/v0`
  standard, JSON Schema family (`ready-packet`, `project-state`,
  `control-record`, `progress-event`), `contract.json` entry manifest, README,
  examples, and structural rejects — a source-neutral contract for exchanging
  ready work and project projections without importing a board or runtime.
- **ADR-0008: project-work contract.** Record `project-work/v0` as a proposed
  companion portable contract family. Promotion to a stable version follows
  ADR-0001.

### Changed

- **Validation coverage.** `make check` now runs the project-work control
  battery (examples, structural rejects, classifier-key alignment) and the
  project-work contract manifest.
- **Local fallback guidance.** Use an org-qualified `3leaps/crucible` sibling
  clone from the consuming repository and consistent `../crucible/` paths in
  onboarding, adoption, and upstream-sync documentation.

## [0.1.28] - 2026-08-20

### Added

- **Agent-wait registration priority.** `agent-wait/v0` registrations may now
  carry optional integer `priority` values from `0` through `255` as
  cooperative presentation hints. Higher values express greater presentation
  urgency; the field grants no scheduling, authorization, quota, or abort
  authority.

### Changed

- **Priority contract controls.** Boundary goldens cover `0`, `50`, `100`, and
  `255`; schema reject pairs cover negative, out-of-range, fractional, and
  string values. The agent-wait control battery proves an omitted priority and
  explicit `50` retain distinct RFC 8785 digests while representing the same
  registration content after the optional field is removed.

## [0.1.27] - 2026-08-19

### Added

- **Curated agentic role catalog.** Twenty public role definitions now carry
  explicit core, supplemental, or deprecated tiers. Seven focused roles join
  the catalog, while deprecated roles name their successor roles. The new
  active-role index separates approved and draft definitions for adopters.
- **Role-catalog decision records.** PDR-0007 records the catalog curation;
  ADR-0007 separates documentation and schema registry origins; EPR-0004
  preserves the boundary between publication surfaces and their domains of
  concern.

### Changed

- **Role-prompt validation.** The v0 schema now requires a tier, models
  lifecycle status, authority, outputs, and replacement relationships, and
  rejects invalid lifecycle combinations. The role-prompt control battery runs
  as part of configuration linting.
- **Agentic adoption guidance.** Catalog, repository identity, and adoption
  documentation now distinguish the canonical role catalog from role
  documentation and describe tiering and deprecated-role migration.
- **Assessment controls.** Shell-lint scope narrows to `**/*.sh`, and the
  checkmake target-length allowance expands so the comprehensive
  configuration-lint target stays conformant. A `.goneatignore` keeps RFC 8785
  canonical JSON bytes (intentional no trailing newline) out of text
  formatting; the service-job control battery verifies their byte integrity
  rather than a formatter.

## 0.1.26 - 2026-08-15

> **Publication note:** v0.1.26 was superseded before a signed tag or GitHub
> release was published.

### Added

- **`contract: agent-wait/v0`.** Portable wait/poll family: six discriminated
  message kinds, explicit start-position XOR, live match as a proposal, and
  poll `no_change` / `logical_deadman` rules. Schemas, goldens, and
  schema/normative/set controls land under `schemas/agent-wait/v0/`; the
  standard is `docs/standards/agent-wait-contract.md`. Wired into `make check`.
- **`contract: service-job/v0`.** Portable service-job family: thirteen
  discriminated kinds, authorization-filtered catalog, local-only implicit
  default, RFC 8785 digest-bound idempotency, and legal/terminal transitions.
  Schemas, goldens, JCS vectors, and controls land under
  `schemas/service-job/v0/`; the standard is
  `docs/standards/service-job-contract.md`. Wired into `make check`.
- **Composing a Review Panel guide** (`docs/guides/`). The composition
  companion to the fierce-collaboration standard and its run-book: the
  five-layer seat composition model (identity × environment × harness+profile
  × mode × framing+capture), three harness classes with their composition
  rules and cross-class footguns, panel diversity mechanics, the six-part
  framing block with its implementation-seat variant, a preflight checklist,
  and copy-paste templates. All launch references are symbolic — harness
  classes and named profiles and environment compositions, never invocation
  detail. Indexed from
  `docs/README.md` and cross-linked from the run-book and the standard.
- **Seat execution record** in `review-journal/v0`. A manifest seat may record
  how it was actually run: symbolic `harness` token, symbolic `profile_ref`,
  symbolic `environment_ref` (`inherited` admitted), `mode` (`interactive` |
  `headless` | `subagent`), and `capture` form (no terminal-scrape form
  admitted). Together with the participant join and role-prompt digest this
  maps every layer of the composition model to a named record (the
  working-tree axis rides each disposition's exact-head anchor). Optional in
  v0 per reserve-don't-force; three new reject/baseline pairs join the
  negative-control battery (terminal-scrape capture form, execution record
  without its harness token, empty environment reference).

### Changed

- **Release-surface changelog grep.** The version-section check now consumes
  the whole changelog stream so `grep -q` plus `pipefail` cannot report a
  missing `## [version]` heading after a legitimate Unreleased addition.
- **Fierce-collaboration standard 0.5.0 → 0.6.0.** §3 gains the execution
  disclosure: a seat is a composition, and its disclosure records harness
  class, symbolic profile, mode, and capture form alongside kind and reasoner.
  §9.2 co-moves: a framing-comparison claim requires the full recorded
  composition per compared seat — participant join, role-prompt digest, and an
  execution record carrying harness, mode, capture, `environment_ref`, and an
  explicit `profile_ref` (`none` admitted) — and a comparison over seats
  lacking any of these narrows to the seats whose composition is fully
  recorded. New §9.3 makes the verdict contract for
  non-interactive seats normative: one binary disposition token mapped to the
  canonical vocabulary (fail-closed — no token is never a green), numbered
  severity-tagged findings, bounded length.

### Fixed

- Agent-wait normative deadline comparisons parse RFC3339 with a portable
  stdlib helper and fail closed on unparseable instants (no GNU `date`).
- Service-job JCS materializer follows RFC 8785 / ECMAScript number
  serialization and the I-JSON numeric domain. Official-style vectors run
  under `make check`; the JobSpec digest remains an integration case.
- JCS string serialization leaves U+2028 and U+2029 as UTF-8. Duplicate
  object members are rejected at every nesting depth. Lone surrogate code
  points are rejected. Quote, backslash, and C0 control escapes are
  unchanged.
- Agent-wait exclusive anchors are provider-opaque and distinct from source
  event IDs. Live and poll share the frozen outcome kinds; clean
  `no_change` / `logical_deadman` are rejected when required coverage is
  degraded. Poll carries fairness and ack/continuation surfaces.
- Service-job submit requires a scoped idempotency key. Receipts correlate
  by `submit_ref`; an `unknown` admission blocks a later scoped resubmit
  until resolved. Exact retry reuses `job_id`; a different digest conflicts
  regardless of job identity.
- Service-job lifecycle restores `admitted`, `partial`, `expired`, and
  observational `unknown`, monotonic `state_version`, terminal-only
  `job_result`, and cancel admission including `refused` / `unsupported`.
- Service-job offer and JobSpec restore frozen artifact, backend, and
  parameter surfaces. Changing any digest-covered JobSpec component changes
  the canonical digest.
- Agent-wait registration sets carry principal, authn mode, aggregate
  limits, and a registration digest. Each registration carries source,
  predicate, capability, lease, and bounds. Events use structured payload
  refs and replay metadata. Poll ack, retention, and coverage are
  per-registration maps.
- Service-job JobSpec digest identity includes catalog and offer revision,
  service, requester, and backend/placement choice. Catalog, offer,
  admission, result, cancel, and error restore the frozen required
  fields and conditionals. Unknown admission cannot invent job identity.
- Service-job normative checks recompute every submit digest before
  semantic use, pair catalog pages and offers by explicit refs, compare
  instants with the portable helper, and reject omitted-backend resolution
  when the offer has zero or multiple eligible local defaults.
- The portable RFC3339 helper accepts only the contract date-time
  profile (including fractional seconds and colon-separated offsets).
  Basic date/time, week dates, ordinal dates, missing seconds, a space
  separator, and offsets without a colon fail closed. Leap seconds are
  rejected rather than clamped.
- Agent-wait and service-job normative checkers fail closed when the
  target is missing, unreadable, empty, or not JSON. Paths are iterated
  without word-splitting so a filename with spaces cannot become a
  zero-record pass.
- Service-job submit carries required `catalog_id` on the envelope and
  the canonical JobSpec. Top-level `placement` and `backend_ref` are
  rejected; execution selectors are digest-bound on the JobSpec only.
  Offer and admission pairing uses catalog identity together with
  service and both revisions.
- **`coverage-attestation/v0`.** Gaps require a stable machine-readable
  `code`; observed and expected volumes reject negatives. Negative controls
  run under `make check`.

## [0.1.25] - 2026-07-31

### Added

- **PDR-0006 (accepted): Crucible ships no consumer-linked code.** The
  repository's shipping charter, written down after governing implicitly since
  creation. Two independent rules: **linkage** (crucible ships nothing that
  consuming code imports or depends on; standalone canonical tools whose sole
  purpose is making its contracts falsifiable or materializable are admitted
  by conformance fixtures, never by fiat) and **dependencies** (any canonical
  tool crucible ships is standard-library-only).
- **PDR-0006 amendment: the Rule 2 referent.** Rule 2a names which tools the
  dependency rule governs — canonical contract tooling and anything held out
  for copying or adoption; repository-internal infrastructure is not a charter
  matter. Rule 2b defines "standard-library-only" for tools that orchestrate
  other programs: a declared, closed set of external commands, each justified
  as subject-matter (named by the contract) or on a fixed baseline list;
  undeclared invocation is nonconformance.
- **Running a Fierce-Collaboration Review guide** (`docs/guides/`). The
  run-book companion to the review standard: executable steps from declaring a
  review through disposition and close-out, a redacted worked example from a
  real panel threaded through every step, common failure modes mapped to the
  step that catches each, and copy-paste templates. Indexed from `docs/README.md`
  and linked from the standard as its non-normative mechanics layer.

### Changed

- **`review-journal/v0` enforcement batch.** The contract now enforces what it
  previously documented: in-schema `access_tier ≥ sensitivity` floors on entry
  classifications and the manifest ceiling (half-`unknown` pairs fail closed);
  anchor label integrity (`sha256:` and `git-tree:<object-format>:<oid>` forms
  constrained so a label never claims an algorithm it does not use); participant
  identity on every roster seat with a **mandatory** event-side join
  (`agent.participant_ref` required; duplicate roster seats and unresolvable
  ceiling setters fail the set check) and a `reasoner` field that admits
  `not-exposed`; the maintainer seat's participant must be human;
  required `role_prompt.digest` for approving agent review seats; machine-readable finding
  `lifecycle` (deferral requires owner + closure trigger) and `defect_class`;
  claim-scoped `gate_scope` on gate events; and author-does-not-approve at seat
  level in-schema plus person level via the journal-set check
  (`scripts/validate-review-journal-set.sh`), which also enforces the
  cross-stream ceiling and roster closure.
- **Negative-control battery for `review-journal/v0`.** Every new enforcement is
  proven able to fail: reject fixtures under `schemas/review-journal/v0/rejects/`,
  each paired with a single-field-corrected baseline twin — an invariant the
  battery asserts mechanically via structural JSON diff, alongside
  schema-validity of set-level fixtures — so the rejection is pinned to its
  intended gate by construction; asserted in `make check`.
- **`review-journal/v0` examples** replaced with a redacted, fictionalized
  journal of a real panel, exercising the new fields including a `not-exposed`
  reasoner and a deferred finding with owner and trigger.
- **Fierce-Collaboration Review standard** 0.4.1 → 0.5.0: enforcement
  disclosures in §3, §9.2, §10, and §12 updated to match the mechanisms that now
  exist; the variance-comparison claim moves from "join not possible" to "join
  possible, conclusions not yet evidenced". PDR-0005's deferred-gap table
  records seven of eight gaps closed; `human-merge-authority` remains open as
  structural to the record.

## [0.1.24] - 2026-07-28

### Added

- **Fierce-Collaboration Review standard** (0.4.0, draft). A review methodology
  for AI-agent and human panels that is adversarial in verification and
  collaborative in goal. Covers seat composition, disposition vocabulary,
  provenance anchor token forms, and an optional machine-readable journal with
  sensitivity-tagged records.
- **PDR-0005** (proposed): adopt the fierce-collaboration multi-agent review
  process. Records accepted contract gaps with an owner and closure trigger for
  each, disclosed on the contract surface itself.
- **`review-journal/v0` contract.** Manifest and event schemas, examples, and a
  contract manifest; examples validated in `lint-config`. Experimental
  stability.
- **EPR-0003** (proposed): durable claim integrity. A durable claim states no
  more than its mechanism and its evidence support, and co-moves with them.
- **Release-surface guard.** `make check` now asserts that the hand-maintained
  release surfaces moved with `VERSION`: `RELEASE_NOTES.md` leads with the
  current version, `docs/releases/vX.Y.Z.md` exists, and `CHANGELOG.md` carries
  the version's section, defines its compare link, and points `[unreleased]` at
  it. Ships with negative controls that pin each rejection to its own assertion.

## [0.1.23] - 2026-07-26

A governance release: one Engineering Principle Record.

### Added

- **EPR-0002 (accepted): gates assert on resolved state and are proven able to
  fail.** A gate whose green is relied upon MUST assert on the resolved state the
  system actually reached, MUST treat absent evidence as a failure rather than
  substituting a value for it, MUST be demonstrated capable of failing (a negative
  control), and MUST NOT carry an exemption its stated coverage does not declare.
  Generalizes the domain-scoped instances (data-pipeline GP-2.2/GP-2.4, EPR-0001,
  PDR-0004) without superseding them.

### Build

- Version 0.1.22 → 0.1.23; `VERSION`, `package.json`, README version badge, and
  CHANGELOG compare links synced.

## [0.1.22] - 2026-07-22

A governance release: graduate EPR-0001 to accepted.

### Changed

- **EPR-0001 graduates proposed → accepted.** The first conforming adopter has
  landed pin/enforce/audit/parity work in a public reference implementation — pin,
  enforce, and parity demonstrated by executable negative controls, and audit by
  on-change and scheduled advisory scans, rather than merely asserted present. The
  record gains a Reference implementation section linking
  that public conformance work.

### Build

- Version 0.1.21 → 0.1.22; `VERSION`, `package.json`, README version badge, and
  CHANGELOG compare links synced.

## [0.1.21] - 2026-07-20

Signed publication-policy attestation for the release path.

### Changed

- **Release tags carry a signed policy fingerprint.** `release-tag.sh` validates
  the complete version-tag ruleset and embeds its canonical SHA-256 fingerprint
  in the annotated tag before signing.
- **Publication verifies the signed policy attestation.** Release CI validates
  the read-only ruleset view and requires the policy fingerprint after pinned-key
  signature verification.
- **Release-control tests and documentation cover both validation modes and the
  signed attestation.**

### Build

- Version 0.1.20 → 0.1.21; `VERSION`, `package.json`, README version badge, and
  CHANGELOG compare links synced.

## [0.1.20] - 2026-07-19

A governance release: two decision records, and the release process they
describe.

### Added

- **EPR-0001 (proposed): published artifacts carry an integral dependency
  graph.** Every artifact built from a resolved dependency graph ships that
  graph pinned in-repo, enforced at build, continuously audited, and held at
  parity across all distribution surfaces of the same release. Four obligations,
  surface- and language-agnostic; tooling is deliberately out of scope and left
  to adopting repositories. This is the first Engineering Principle Record in
  this lane. It graduates to accepted when a conforming reference
  implementation lands.
- **PDR-0004 (accepted): the signed tag authorizes publication.** Signing is what
  creates the tag, and the push is what triggers the release workflow — so the
  tag is already signed by the time CI runs. A draft release awaiting a
  signature guards a condition that cannot occur. The signed tag is now the
  authorization; CI verifies it and publishes.

- **Pinned release signing key.** `docs/security/release-signing-keys.asc`
  commits the public key permitted to authorize a release. Publication is gated
  on it, so the key set is reviewed like any other change.

### Changed

- **Releases publish from CI.** The release workflow asserts the tag carries a
  verified signature, then creates the release directly as published, setting
  the `Latest` flag explicitly for stable versions. Prereleases publish as
  prereleases and do not take `Latest`.
- **Signature verification asserts key identity, not just recognition.** The tag
  must verify in an isolated keyring built solely from the committed pin file,
  and GitHub must independently report it verified. Recognition alone holds for
  any key on the tagger's account, which would reduce publication authority to
  tag-push rights plus a self-uploaded key.
- **Publication is bound to one annotated tag object.** CI carries the verified
  tag-object SHA across the job boundary and reasserts the version-tag ref still
  resolves to it immediately before release creation. Lightweight tags, missing
  object identities, and changed refs fail closed.
- **Version-tag protection is executable.** `make release-tag` and the release
  workflow verify the live `Tag Publish Protection` ruleset covers only
  `refs/tags/v*`, applies the four mutation protections, and has only the
  organization-administrator bypass.
- **Third-party workflow actions are immutable.** Check and release actions use
  full commit SHAs, retaining semantic versions as comments.
- **Unverified tags fail closed.** If the signature is absent, is made by an
  unpinned key, or cannot be verified, the workflow fails and no release is
  created. A draft or missing release is now a failure signal rather than a
  normal intermediate state.
- **Release-key rotation is part of the release process.** The checklist wires
  pin updates into rotation, and notes that key expiry blocks publication the
  same way a stale pin does — without anything prompting it first.
- **Release checklist verifies published state.** Post-release items confirm the
  release is non-draft, carries `Latest`, and is reachable — rather than only
  that a release object was created.
- **Decision-record index.** The `EPR` type is listed in active use, and the
  index covers every record in the lane.

### Build

- Version 0.1.19 → 0.1.20; `VERSION`, `package.json`, README version badge, and
  CHANGELOG compare links synced.

## [0.1.19] - 2026-07-09

A contract-alignment release: loosen two over-constraints in `data-artifact/v0`
so the schema matches existing normative prose.

### Changed

- **Fully-withheld field catalogs.** A field catalog may set `fields` to an
  empty array when `withheld_field_count` is present and at least 1. Empty
  `fields` without a positive count fails closed. Non-empty catalogs are
  unchanged. Prose clarifies the fully-withheld semantic, total-count rules for
  `withheld_field_count` vs `withheld_fields`, and a Validation Requirements
  bullet under default-deny.
- **Optional grain field catalog ref.** `field_catalog_ref` is no longer
  required on every grain. Queryable or renderable grains still require a field
  catalog via Validation Requirements; raw archival grains may omit the ref.

### Added

- **Schema fixtures.** Golden descriptors for a fully-withheld catalog and a
  catalog-less raw archival grain.

### Build

- Version 0.1.18 → 0.1.19; `VERSION`, `package.json`, README version badge, and
  CHANGELOG compare links synced.

## [0.1.18] - 2026-07-06

A companion-contract release: add the portable process-run/v0 contract for
observing and steering local long-running processes.

### Added

- **Portable Process Run Contract (proposed).** Add the `process-run/v0`
  standard, JSON Schema family (`process-card`, `process-event`,
  `control-exchange`), `contract.json` entry manifest, README, and golden
  examples — a source-neutral contract for observing and steering local
  long-running processes via an append-only NDJSON event stream and a
  token-gated local control channel, at a deliberately minimal complexity floor.
- **ADR-0006: process-run contract.** Ratify `process-run/v0` as a proposed
  companion to `data-artifact/v0` (Standard + ratifying ADR vehicle), with the
  Proposed → Accepted gate set on a downstream conforming implementation.

### Changed

- **Validation coverage.** `make check` now validates the process-run
  examples — `process-card`, control exchange, and per-line NDJSON events — plus
  the process-run contract manifest.

### Build

- Version 0.1.17 → 0.1.18; `VERSION`, `package.json`, README version badge, and
  CHANGELOG compare links synced.

## [0.1.17] - 2026-07-06

A baseline release: tighten the portable data artifact contract, align
repository guidance for public standards use, and synchronize release metadata.

### Added

- **Physical file metadata handling for data artifacts.** Boundary-crossing
  columnar representations now treat physical metadata as content: row-group or
  page min/max values, page-index bounds, and per-column Bloom filters or other
  membership-oracle structures must be suppressed, opaqued, or omitted for
  restricted-class fields.
- **Reference producer citation.** The data artifact examples intentionally cite
  `fulmenhq/sumpter` as a public reference producer while keeping concrete
  producer schemas non-normative unless shared-profile convergence justifies
  promotion.

### Changed

- **Data artifact review-loop status.** The physical-file-metadata concern is
  folded into Metadata Is Content, with format-specific suppression mechanics
  reserved to producer profiles.
- **Repository guidance aligned for public standards use.** The root
  contributor-agent guide is now a concise public exemplar, AI attribution
  guidance is generic, and repository docs/examples use adopting-repository
  language.
- **ADR-0002 portable framing.** ADR-0002 is retitled and cross-references are
  updated around the portable key-material fingerprint schema contract framing.

### Removed

- **Obsolete repository safety playbook.** Remove the operational safety playbook
  from the public baseline and point contributors to forward-looking public
  standards instead.

### Build

- Version 0.1.16 → 0.1.17; `VERSION`, `package.json`, README version badge, and
  CHANGELOG compare links synced.

## 0.1.16 - 2026-07-05

A contract-and-release-readiness release: add the portable data artifact
contract family, publish a cross-repo architecture role, and harden release
version tooling.

### Added

- **Portable Data Artifact Contract.** Add the `data-artifact/v0` standard,
  examples, JSON Schema entry schema, and `contract.json` manifest for portable
  artifact descriptors with protection-aware read-path and export-gate semantics.
- **Coverage Attestation companion contract (proposed).** Add
  `coverage-attestation/v0` schema, example, README, and `contract.json` manifest
  for independent, supersedable coverage/completeness claims.
- **Data contract decision records.** Add ADR-0004 for coverage attestation and
  ADR-0005 for operation-record classification.
- **Profile-extension witness.** Add a descriptor fixture proving
  profile-qualified extension values for grain `kind`, representation `role`,
  and representation `format` validate through the quality gate.
- **Enterprise Architect role.** Add `entarch` as a supplemental governance role
  for cross-repo architecture coherence, standards propagation, compatibility, and
  release-order constraints.

### Changed

- **Role catalog expanded.** The role catalog now includes thirteen roles, with
  `entarch` recorded as a supplemental governance role and PDR-0003 amended to
  preserve the decision history.
- **Data artifact entry schema aligned with profile extensions.** The L2 entry
  schema accepts base vocabulary terms or slash-qualified profile extension tokens
  for the fields the standard defines as extensible.

### Fixed

- **Version bump release tooling.** `version-set` and version bump targets now
  synchronize changelog compare-link footers, and wrapper targets fail fast if
  the delegated version-set operation fails.

### Build

- Version 0.1.15 → 0.1.16; `VERSION`, `package.json`, README version badge, and
  CHANGELOG compare links synced.

## 0.1.15 - 2026-07-01

A governance-foundation release: establish the decision-record taxonomy, file the
first process/principle records, add the first domain standard set, and tier the
role portfolio.

### Added

- **Decision-record taxonomy (ADR-0003).** The `*DR` family — `{ADR, DDR, SecDR,
PDR, EPR}` — as a shared standard, with a thin mandate (type set + naming)
  and a normative catalog (`docs/repository/decision-records.md`) as the single
  canonical source.
- **Data-Pipeline Engineering Principles (PDR-0001).** A domain-scoped, opt-in
  standard set (28 principles across 5 axes; EPR-class) under a `data-engineering`
  namespace, plus the reusable domain standard-set ingestion pattern.
- **Worktree-per-task process standard (PDR-0002).** Each concurrent task uses its
  own `git worktree` to avoid shared-clone collisions.
- **Role portfolio tiering (PDR-0003).** An optional `tier` field
  (`core` / `supplemental` / `deprecated`) on the `role-prompt` v0 schema, set on
  every role, as propagating default guidance.
- **Baseline role catalog pages** for `cxotech`, `deliverylead`, `devrev`, and
  `dataeng`, so every advertised role resolves to a page.

### Changed

- **Role portfolio tiered and promoted.** `cxotech` → approved (core) and
  `deliverylead` → approved (supplemental); the role catalog, root README, and
  `AGENTS.md` advertise the tiers.
- **Hosted-surface references un-pinned.** The `crucible.3leaps.dev` /
  `schemas.3leaps.dev` references on current documentation are genericized from
  `v0.1.15` to `v0.1.x` — the hosted site did not land in this release and is no
  longer pinned to a specific version. Frozen release history is unchanged.
- **Decisions lane reframed.** `docs/decisions/README.md` becomes a per-lane index
  deferring to the catalog; `SDR` → `SecDR`; naming notation normalized to
  `<TYPE>-<NNNN>-<kebab-slug>.md`.

### Deprecated

- **`cicd` role.** Real-world use favored `releng` supplementing `devlead`; prefer
  that pairing on new work. The role definition and catalog page are marked
  deprecated.

### Build

- Version 0.1.14 → 0.1.15; `package.json` and README version badge synced.

## 0.1.14 - 2026-06-22

### Changed

- **Lifecycle: alpha → beta.** Crucible's standards are stable enough to reference and
  adopt; `LIFECYCLE_PHASE`, the README badge, and the project framing are updated to
  beta.
- **Schema versioning decoupled from the repository lifecycle.** The "during alpha"
  framing is removed from the README and standards docs; `v0/` is now described as
  **asset-level maturity, independent of the repository's lifecycle phase** — a `v0/`
  schema can change regardless of the repo's phase.
- **README access paths reconciled with reality.** GitHub is presented as the canonical
  source; the hosted `crucible.3leaps.dev` docs site and `schemas.3leaps.dev` endpoint
  are marked **planned (targeted v0.1.15)** rather than live/canonical.

### Build

- Version 0.1.13 → 0.1.14; `package.json` and README badges synced.

## 0.1.13 - 2026-06-17

### Added

- **Auth Session Artifact schema** (`schemas/auth/v0/`) — new `auth/v0` namespace
  - `session-artifact.schema.json` (JSON Schema 2020-12) — the decoupling contract
    between credential acquirers (emit) and inspectors (validate/parse); no
    value/secret fields, enforced structurally via `additionalProperties: false`
  - `session-artifact.example.json` — synthetic, sterile conforming fixture
    (4-layer AWS cascade incl. `unmeasured`), pinned by consumers for round-trip tests
  - `schemas/auth/v0/README.md` — schema family overview
  - `docs/standards/auth-session-artifact.md` — standard: invariants, field shape,
    SemVer compatibility policy, and governance/validation split
  - `make lint-config` now round-trip-validates the fixture against the schema
  - Identifier hardening: `source` is a **closed enum** (not free text), `expires_at`
    is **required and nullable**, JWT `aud` arrays are constrained to strings, and
    `unmeasured` `kind`/`expiry_basis`/`expires_at` coherence is enforced via schema
    conditionals (per consumer-team + devrev review)
  - Co-authored by the consuming teams; held in Crucible as a cross-cutting contract
- **ADR-0002 (proposed): Key-Material Fingerprint Contract as a Portable Schema** —
  records the proposal to promote a key-material fingerprint contract into a new
  `keymaterial` crucible schema domain (registry-first, full record schema at the
  v1.0.0 gate). Decision/rationale only; publishes no `schemas/keymaterial/` files.
- **Operator knowledge & guides**
  - `docs/guides/multi-org-github-cli-auth.md` — using `gh` across multiple orgs
  - `docs/knowledge/cicd/github-actions/container-non-root-pitfalls.md` — UID 1001 container path/`HOME` gotchas
  - `docs/knowledge/toolchains/rust/ci-parity-and-generated-tools.md` — local↔CI parity for generated-tool (cbindgen) deps

### Changed

- **CI: `actions/checkout` v4 → v5** in `check.yml` and `release.yml` — moves off the
  retiring Node 20 action runtime to Node 24.
- **Git hooks: removed the guardian intercept** from `.goneat/hooks/{pre-commit,pre-push}`.
  Commit/push no longer prompt for browser-based guardian approval; the `goneat assess`
  quality gate (format/lint/security) is unchanged.
- **YAML tooling aligned on 2-space inline comments** — `.yamlfmt` now sets
  `pad_line_comments: 2` and `.yamllint` requires `comments.min-spaces-from-content: 2`,
  so a direct `yamlfmt` (`make fmt`) and `goneat assess` produce identical output.

### Fixed

- Removed stray `#magic___^_^___line` markers that a yamlfmt quirk had leaked into the
  folded `context:` scalars of the `cicd` and `qa` role configs.

## 0.1.12 - 2026-02-18

### Added

- **CI/CD lessons learned from complex GitHub Actions workflows**
  - `docs/knowledge/cicd/github-actions/windows-runners.md` - Expanded with Windows runner behaviors and PowerShell/bash gotchas
  - `docs/knowledge/cicd/github-actions/yaml-shell-gotchas.md` - YAML/shell interaction pitfalls and common quoting issues

### Changed

- **Version bump**: 0.1.11 → 0.1.12

## 0.1.11 - 2026-02-12

### Added

- **GitHub Actions release verification and signing handoff**
  - `docs/knowledge/cicd/github-actions/artifact-handling.md` - When to use (and avoid) cross-job artifacts
  - `docs/knowledge/cicd/github-actions/manual-signing-handoff.md` - Local signing workflow for draft releases
  - `docs/knowledge/cicd/github-actions/release-verification-checklist.md` - Pre-undraft verification gate

- **TypeScript toolchain release patterns**
  - `docs/knowledge/toolchains/typescript/bun-compiled-binaries.md` - Shipping standalone TS CLI binaries with Bun

### Changed

- **Knowledge cross-linking**
  - Update GitHub Actions knowledge index with release verification topics
  - Add scope notes and cross-references between Windows runner behavior and TypeScript ecosystem gaps

## 0.1.10 - 2026-02-09

### Added

- **Windows ARM64 Gaps in TypeScript** (`docs/knowledge/toolchains/typescript/windows-arm64-gaps.md`)
  - Native binary availability status for Biome, Rollup/Vitest on Windows ARM64
  - CI matrix pattern with skip-lint/skip-test flags for unavailable tools
  - Cross-platform path handling using `path.sep` and `path.resolve()`
  - CRLF line ending fixes with `.gitattributes`
  - Status matrix: Bun (emulated), Biome (missing), Rollup (missing), TypeScript (works), esbuild (works)

- **CI/CD knowledge improvements**
  - CRLF line endings section in Windows runners (`.gitattributes` fix)
  - TypeScript native binary gaps on ARM64 (Biome, Rollup/Vitest)
  - Node.js path separators section (cross-platform path handling)
  - Updated TypeScript toolchain README with Windows ARM64 gaps reference

## 0.1.9 - 2026-02-09

### Added

- **Config Layering Pitfalls guide** (`docs/knowledge/toolchains/go/config-layering-pitfalls.md`)
  - Multi-layer configuration precedence bug patterns
  - Guard condition pattern: `cfg.Field != "" && result.Field == ""`
  - Testing cross-layer combinations to expose hidden bugs
  - Real-world example from sfetch v0.4.2 archive format override
  - Viper/Cobra integration without precedence violations

- **CI/CD knowledge improvements**
  - GitHub infrastructure outage troubleshooting (500/502/503 errors)
  - Archive format override pattern in cross-platform asset selection
  - Windows-specific archive format override examples
  - Release process hardening: signature verification step order
  - Upload script nullglob pitfalls and glob pattern solutions

### Changed

- **Build automation**
  - Added `scripts/sync-version-badge.sh` for automated README badge updates
  - Integrated badge sync into `version-patch`, `version-minor`, `version-major`, `version-set` Makefile targets
  - Version bumps now automatically synchronize VERSION file and README badge

## 0.1.8 - 2026-02-09

### Added

- **CI/CD knowledge base expansion**
  - `docs/knowledge/cicd/github-actions/cross-platform-asset-selection.md` - Multi-platform release asset handling patterns
    - OS/architecture matrix strategies (darwin, linux, windows × amd64, arm64)
    - Filename conventions and version templating
    - Platform-specific job configuration
    - Asset verification patterns
  - `docs/knowledge/cicd/github-actions/windows-runners.md` - Windows CI/CD workflow patterns
    - Shell selection and escaping (powershell, pwsh, cmd, bash)
    - PowerShell quote handling and escaping rules
    - Path normalization strategies
    - Tool installation via choco, winget, scoop
    - Line ending and executable permission handling
    - Windows Defender and antivirus considerations

### Changed

- **Knowledge base organization**
  - Restructured `docs/knowledge/cicd/README.md` with clearer section organization
  - Updated `docs/knowledge/cicd/github-actions/README.md` with platform-specific guide index
  - Added cross-references between related CI/CD patterns

## 0.1.7 - 2026-02-09

### Added

- **Governance tier roles**
  - `config/agentic/roles/deliverylead.yaml` - Project lifecycle management and sprint coordination
    - Projectbook governance for git-backed docsites
    - Sprint/kanban board structure with WIP limits
    - Timeline orchestration (dependencies, critical path)
    - Capacity planning and velocity tracking
    - Timeline: Sprint (1-4 weeks) to Quarter (3 months)
  - `config/agentic/roles/cxotech.yaml` - Strategic fulcrum for product-architecture decisions
    - Feature brief approval authority
    - Architecture Decision Records (ADRs)
    - Pattern evaluation (usability, stability, idempotency)
    - Escalation endpoint for cross-role conflicts
    - Timeline: Strategic (6-18 months)
    - Emphasizes communication as architectural principle

- **Process domain organization**
  - Added `domains` property to all 11 roles for business-process categorization
  - 15 process domains defined: analytics, architecture, automation, consulting, coordination, delivery, development, documentation, governance, implementation, marketing, product, quality, security, strategy
  - Timeline-based README reorganization for role selection
  - Three-tier governance documentation (dispatch → deliverylead → cxotech)

### Changed

- **Schema formatting**
  - Formatted `role-prompt.schema.json` and related schemas for goneat consistency
  - Expanded inline enum arrays to multi-line format
  - Resolves downstream formatting drift issues

### Schema

- Extended `role-prompt.schema.json`:
  - Added `domains` property (array of enums, 1-3 items)
  - Supported domain values: 15 business process domains

## 0.1.6 - 2026-02-04

### Changed

- **Role prompt schema**: Expanded category enum to support non-technical roles
  - Added `analytics` for BI, data science, and data analysis roles
  - Added `consulting` for advisory and strategy roles
  - Added `marketing` for product marketing and messaging roles
  - Full enum: agentic, analytics, automation, consulting, governance, marketing, review

## 0.1.5 - 2026-02-04

### Added

- **Language coding standards**
  - `docs/coding/go.md` - Go coding standard
  - `docs/coding/python.md` - Python coding standard
  - `docs/coding/rust.md` - Rust coding standard
  - `docs/coding/typescript.md` - TypeScript coding standard
- **Knowledge base** (`docs/knowledge/`)
  - CI/CD patterns: GitHub Actions gotchas, release rollback, workflow version resolution
  - Registry patterns: npm OIDC authentication
  - Testing patterns: HTTP client and server test patterns
  - Toolchain guides: Go (Cobra), Python (modern stack), Rust (cargo-audit, MSRV, FFI), TypeScript (modern stack)
- **Role prompt schema extensions**
  - `pre_push_checklist` - validations before pushing
  - `required_reading` - documents to read before starting
  - `cross_role_note` - coordination with other roles

### Changed

- **releng role**: Updated to v2.0.0 with CI/CD validation focus
- **CI workflows**: Pinned versions, added permissions, safer defaults
- **Makefile**: Renamed GPG_KEY_ID to PGP_KEY_ID

## 0.1.4 - 2026-01-22

### Added

- **Classifiers framework** - Foundation for orthogonal data classification dimensions
  - `schemas/classifiers/v0/dimension-definition.schema.json` - Meta-schema for classifier dimensions
  - `schemas/classifiers/v0/sensitivity-level.schema.json` - Data sensitivity enum schema
  - **Tier 1 dimensions** (universal infrastructure):
    - `config/classifiers/dimensions/sensitivity.dimension.json` - Sensitivity (UNKNOWN, 0-6)
    - `config/classifiers/dimensions/volatility.dimension.json` - Volatility (static → streaming)
    - `config/classifiers/dimensions/access-tier.dimension.json` - Access tier (public → eyes-only)
    - `config/classifiers/dimensions/retention-lifecycle.dimension.json` - Retention (transient → legal-hold)
    - `config/classifiers/dimensions/schema-stability.dimension.json` - Schema stability (experimental → deprecated)
  - **Tier 2 dimensions** (data platform fundamentals):
    - `config/classifiers/dimensions/volume-tier.dimension.json` - Volume tier (tiny → massive)
    - `config/classifiers/dimensions/velocity-mode.dimension.json` - Velocity mode (batch/streaming/hybrid)
  - **Standards documentation**:
    - `docs/standards/data-sensitivity-classification.md` - Comprehensive sensitivity standard
    - `docs/standards/volatility-classification.md` - Update cadence standard
    - `docs/standards/access-tier-classification.md` - Access control standard
    - `docs/standards/retention-lifecycle-classification.md` - Retention policy standard
    - `docs/standards/schema-stability-classification.md` - Schema evolution standard
    - `docs/standards/volume-tier-classification.md` - Data scale planning standard
    - `docs/standards/velocity-mode-classification.md` - Processing pattern standard
  - **Stronger default handling**
    - All dimensions define an explicit `unknown` value; missing classification is a policy error (do not default)
    - Consumers SHOULD key on string values (e.g., `daily`, `restricted`) rather than relying on numeric ordinals/order
    - Sorting/indexing hints (e.g., `ordinal_mapping`, `is_none`) are for UX/indexing only; they are not policy defaults
- **ADR framework** (`docs/decisions/`)
  - `ADR-0001-schema-config-versioning.md` - v0 + SemVer versioning standard
  - Support for ADR, DDR, SDR decision types
- **Product Marketing role** (`prodmktg`)
  - `config/agentic/roles/prodmktg.yaml` - Role definition for product messaging and personas
  - `docs/catalog/roles/prodmktg.md` - Role documentation
- **Stream Output Policy** (`docs/sop/stream-output.md`)
  - Mandatory stdout/stderr discipline for CLI tools
  - stdout = machine data (JSON, CSV), stderr = human text (logs, status)
  - Testing requirements for stdout purity verification
  - Logger configuration examples (Go, Python, TypeScript)
  - Based on implementation experience from sfetch and shellsentry teams
- **CI/CD Baseline** (`docs/operations/ci-baseline.md`)
  - Git safe.directory patterns for containerized CI
  - actionlint for GitHub Actions workflow validation
  - goneat assess integration for quality gates
  - containerized tooling usage with `--user 1001` pattern
  - Formatter check mode vs git diff approach
- **Release Phase Schema** (`schemas/foundation/v0/release-phase.schema.json`)
  - Enum: dev, rc, ga, hotfix
  - Complements lifecycle-phases (project maturity vs release cadence)
- **SOP category** (`docs/sop/`) for mandatory policies

### Changed

- **Makefile**: Updated goneat version to v0.5.1, made version overridable with `?=`
- **docs/catalog/roles/README.md**: Added prodmktg to role index table
- **README**: Removed hardcoded version badge (use VERSION file reference)
- **docs/README.md**: Added Operations and SOP sections to category index
- **docs/observability/logging-baseline.md**: Cross-reference to stream output policy

## 0.1.3 - 2026-01-01

### Added

- **Release tooling with safety checks**
  - `scripts/release-tag.sh` - Create signed tags with comprehensive safety checks
  - `scripts/release-guard-tag-version.sh` - Verify tag matches VERSION file
  - `scripts/release-verify-tag.sh` - Verify signed tag signature
  - New Makefile targets: `release-tag`, `release-verify-tag`, `release-guard-tag-version`
- **Foundation type primitives** (`schemas/foundation/v0/types.schema.json`)
  - 25 universal types: slug, semver, timestamp, url, paths, IP addresses, etc.
  - Portable across 3leaps and adopting repositories
- **Error response schema** (`schemas/foundation/v0/error-response.schema.json`)
  - Standard error structure for APIs and CLIs
  - Fields: code, message, details, path, timestamp, requestId

### Changed

- **README repository ecosystem section**
  - Renamed repository ecosystem section
  - Fixed diagram to show accurate ecosystem structure
  - Adopting projects shown as peer consumers
  - Added representative projects to diagram
- **Relationships table** expanded into three tiers:
  - 3leaps Org (Foundation Layer): crucible, oss-policies, sfetch, seekable-zstd
  - Adopting projects
  - Downstream implementations
- **RELEASE_CHECKLIST.md** updated to use `make release-tag` with safety checks
  - Added Release Tooling Reference section documenting scripts

## 0.1.2 - 2026-01-01

### Added

- **Role-based identity system** with JSON Schema validation
  - 8 baseline roles: devlead, devrev, infoarch, secrev, qa, cicd, releng, dispatch
  - `schemas/agentic/v0/role-prompt.schema.json` for role prompt validation
  - `config/agentic/roles/` with schema-validated YAML definitions
- **devrev role** for four-eyes code review pattern
- **AILink schemas** for prompt/response validation
  - `schemas/ailink/v0/prompt.schema.json`
  - `schemas/ailink/v0/search-response.schema.json`
- **Upstream sync guide** (`docs/operations/upstream-sync-guide.md`)
  - Vendoring patterns for schemas and config
  - PROVENANCE.md tracking for upstream dependencies
  - Recommendation: vendor schema + config together
- **README enhancements**
  - CI status badge and version badge
  - Complete repository structure with all schema directories
  - AI Agent Roles section with role catalog
  - Quality Gates table with goneat validation targets

### Changed

- README: Restructured Documentation Structure to reflect current layout
- Makefile: Added `lint-config` target for role YAML validation

## 0.1.1 - 2025-12-27

### Added

- **Lifecycle phases schema** with `v0/` unstable versioning pattern
  - `schemas/foundation/v0/lifecycle-phases.schema.json` (JSON Schema 2020-12)
  - `schemas/foundation/v0/lifecycle-phases.data.json` (phase definitions)
  - `LIFECYCLE_PHASE` file for machine-readable project phase (alpha)
- **Schema meta-validation** via `goneat schema validate-schema`
  - New `lint-schemas` Makefile target
  - Integrated into `lint` target for quality checks
- **README enhancements**
  - Lifecycle badge (alpha) and license badge (MIT + CC0)
  - Alpha warning callout
  - Schemas section with `v0/` versioning convention

### Changed

- Makefile: goneat now installs to user-space PATH (like prettier, biome, ruff)
- URL architecture: `schemas.3leaps.dev` for schemas, `crucible.3leaps.dev` for docs

## 0.1.0 - 2025-12-26

### Added

- Initial standards baseline for 3leaps ecosystem
- **Coding standards**: Output hygiene, exit codes, timestamps, error handling, input validation
- **Repository standards**: Makefile minimum, commit style, frontmatter, agents, agent identity
- **Observability standards**: Logging baseline
- **Role catalog**: Baseline prompts for devlead, infoarch, qa, cicd, secrev, releng, dispatch
- **Secure commit policy**: Functional vs contextual language, restricted keywords, 5-layer enforcement
- **Getting started guide**: Lightweight SSOT model, 5 adoption paths, access priority
- AI contribution attribution guidance
- Document frontmatter standard with AI attribution fields
- Commit attribution with Committer-of-Record trailer
- Bootstrap tooling with sfetch, goneat, and bun-centric workflow
- Community files: SECURITY.md, CODE_OF_CONDUCT.md

### Documentation

- Complete docs/ tree with repository, coding, observability standards
- Role catalog with usage patterns and extension guidelines
- Getting started guide for multiple user personas (new repo, existing repo, adopting org)
- Migration guidance for 3leaps and adopting ecosystems

[unreleased]: https://github.com/3leaps/crucible/compare/v0.2.3...HEAD
[0.2.3]: https://github.com/3leaps/crucible/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/3leaps/crucible/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/3leaps/crucible/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/3leaps/crucible/compare/v0.1.34...v0.2.0
[0.1.34]: https://github.com/3leaps/crucible/compare/v0.1.33...v0.1.34
[0.1.33]: https://github.com/3leaps/crucible/compare/v0.1.32...v0.1.33
[0.1.32]: https://github.com/3leaps/crucible/compare/v0.1.31...v0.1.32
[0.1.31]: https://github.com/3leaps/crucible/compare/v0.1.30...v0.1.31
[0.1.30]: https://github.com/3leaps/crucible/compare/v0.1.29...v0.1.30
[0.1.29]: https://github.com/3leaps/crucible/compare/v0.1.28...v0.1.29
[0.1.28]: https://github.com/3leaps/crucible/compare/v0.1.27...v0.1.28
[0.1.27]: https://github.com/3leaps/crucible/compare/v0.1.25...v0.1.27
[0.1.25]: https://github.com/3leaps/crucible/compare/v0.1.24...v0.1.25
[0.1.24]: https://github.com/3leaps/crucible/compare/v0.1.23...v0.1.24
[0.1.23]: https://github.com/3leaps/crucible/compare/v0.1.22...v0.1.23
[0.1.22]: https://github.com/3leaps/crucible/compare/v0.1.21...v0.1.22
[0.1.21]: https://github.com/3leaps/crucible/compare/v0.1.20...v0.1.21
[0.1.20]: https://github.com/3leaps/crucible/compare/v0.1.19...v0.1.20
[0.1.19]: https://github.com/3leaps/crucible/compare/v0.1.18...v0.1.19
[0.1.18]: https://github.com/3leaps/crucible/compare/v0.1.17...v0.1.18
[0.1.17]: https://github.com/3leaps/crucible/releases/tag/v0.1.17
