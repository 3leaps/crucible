# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[unreleased]: https://github.com/3leaps/crucible/compare/v0.1.22...HEAD
[0.1.22]: https://github.com/3leaps/crucible/compare/v0.1.21...v0.1.22
[0.1.21]: https://github.com/3leaps/crucible/compare/v0.1.20...v0.1.21
[0.1.20]: https://github.com/3leaps/crucible/compare/v0.1.19...v0.1.20
[0.1.19]: https://github.com/3leaps/crucible/compare/v0.1.18...v0.1.19
[0.1.18]: https://github.com/3leaps/crucible/compare/v0.1.17...v0.1.18
[0.1.17]: https://github.com/3leaps/crucible/releases/tag/v0.1.17
