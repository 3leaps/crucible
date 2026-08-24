# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[unreleased]: https://github.com/3leaps/crucible/compare/v0.1.29...HEAD
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
