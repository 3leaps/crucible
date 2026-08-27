# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file starts at v0.1.17, the first public release baseline.

---

## v0.1.30 (2026-08-27)

**A portable forge-infrastructure contract for resolving capabilities, binding
authority, and verifying live grants without wrapping a provider CLI.**

- **Portable forge-infra family (draft)** — `forge-infra/v0` defines a seven-lane
  model: intent/resolution, authority control, native git, forge resources,
  automation, events/telemetry, and assurance. Neutral capabilities stay
  separate from curated provider profiles.
- **Non-secret bind and verify** — digest-bound binding plans, transition
  receipts, and time-bounded verification receipts carry non-secret
  identifiers, grant names, and observations. Secrets stay out of band.
- **Reader guide** — a mechanics companion walks the information model, four
  coupled concerns, and sibling-contract boundaries.
- **Executable contract coverage** — examples, structural and semantic
  rejects, policy-input and bind-chain controls, and the contract manifest run
  through the repository quality gates.

See [docs/releases/v0.1.30.md](docs/releases/v0.1.30.md).

---

## v0.1.29 (2026-08-24)

**A portable project-work contract for exchanging ready work and project
projections, with executable controls and clearer local adoption guidance.**

- **Portable project-work family** — `project-work/v0` defines source-neutral
  ready packets, project state, control records, and progress events without
  importing a board or runtime.
- **Explicit lifecycle and governance boundaries** — the draft contract
  distinguishes work readiness from lifecycle class, uses typed subjects for
  durable records, and keeps decision impact explicit through decision-owned
  `affects` references.
- **Executable contract coverage** — positive examples, structural rejects,
  classifier-key alignment checks, and the project-work manifest run through
  the repository quality gates.
- **Org-qualified local fallback** — onboarding and adoption documentation now
  clones `3leaps/crucible` as `../crucible/` from the consuming repository and
  uses that path consistently in upstream-sync examples.

See [docs/releases/v0.1.29.md](docs/releases/v0.1.29.md).

---

## v0.1.28 (2026-08-20)

**A bounded, cooperative presentation-priority hint for portable agent-wait
registrations, with canonical-digest semantics preserved.**

- **Optional registration priority** — `agent-wait/v0` registrations accept an
  integer `priority` from `0` through `255`. Higher values express greater
  presentation urgency; the field does not grant scheduling, authorization,
  quota, or abort authority and does not override frozen wait rules.
- **Stable omitted-field behavior** — consumers interpret an omitted priority
  as `50` without materializing it before RFC 8785 canonicalization, so
  omitted and explicit-`50` registrations retain distinct canonical digests.
- **Executable boundary coverage** — goldens validate priorities at `0`, `50`,
  `100`, and `255`; reject pairs demonstrate failure for negative,
  out-of-range, fractional, and string values. The agent-wait control battery
  verifies every recorded digest and the omitted-versus-explicit-`50`
  invariant.

See [docs/releases/v0.1.28.md](docs/releases/v0.1.28.md).

---

## v0.1.27 (2026-08-19)

**A curated agentic role catalog with explicit lifecycle semantics, so adopters
can select a coherent public role set and migrate away from retired roles.**

- **Twenty role definitions** — explicit `core`, `supplemental`, and
  `deprecated` tiers; seven focused additions; and documented successors for
  the three retired roles. The active-role index separates approved from draft
  definitions.
- **Fail-closed lifecycle validation** — role prompts require a tier, model
  status, authority, outputs, and replacement metadata, with schema and
  fixture controls rejecting inconsistent lifecycle combinations under
  `make check`.
- **Decision and adoption documentation** — PDR-0007 is accepted alongside
  ADR-0007 and EPR-0004; catalog, identity, and adoption documentation now
  describe the canonical catalog, its publication boundaries, and migration
  guidance.
- **Assessment-control alignment** — shell-lint scope narrows to `**/*.sh`,
  the checkmake target-length allowance expands, and a `.goneatignore` keeps
  RFC 8785 canonical JSON bytes out of text formatting so byte integrity stays
  with the control battery.

See [docs/releases/v0.1.27.md](docs/releases/v0.1.27.md).

---

## v0.1.26 (2026-08-15)

> **Publication note:** v0.1.26 was superseded before a signed tag or GitHub
> release was published.

**A contract-boundary cut: portable wait/poll and service-job families land
as `v0`, so a consumer can wait and submit against a shared message contract
instead of a provider-specific protocol.**

- **`contract: agent-wait/v0`** — six discriminated message kinds, explicit
  start-position XOR, live match as a proposal, poll `no_change` /
  `logical_deadman` rules. Schemas, goldens, and `make check` controls.
- **`contract: service-job/v0`** — thirteen kinds, authorization-filtered
  catalog, local-only implicit default, RFC 8785 digest-bound idempotency,
  legal/terminal transitions. Schemas, goldens, JCS vectors, and controls.
- **Composing a Review Panel guide** — five-layer seat composition, harness
  classes, panel diversity, framing block, preflight and templates. All
  launch references are symbolic.
- **`review-journal/v0` seat execution record** — optional symbolic harness,
  profile, environment, mode, and capture. Fierce-collaboration standard
  0.5.0 → 0.6.0 with execution disclosure and a normative non-interactive
  verdict contract.
- **Contract close-out** — portable RFC3339 helper, JCS materializer, fail
  closed on missing/unreadable targets, scoped idempotency, restored
  lifecycle and digest identity. Coverage-attestation gaps require a
  machine-readable `code`; volumes reject negatives.

See [docs/releases/v0.1.26.md](docs/releases/v0.1.26.md).

---

## v0.1.25 (2026-07-31)

**The machinery catches up to the records: an executable run-book for the
review standard, and a review-journal contract that now enforces what it
documented — with every enforcement demonstrated able to fail.**

- **PDR-0006 (accepted)** — the repository shipping charter: no consumer-linked
  code; canonical tools standard-library-only, with the Rule 2 referent amended
  in for tools that orchestrate other programs (declared invocation sets).
- **Running a Fierce-Collaboration Review guide** — executable steps from
  declaration to disposition, a redacted real worked example throughout,
  failure modes mapped to the steps that catch them, copy-paste templates.
- **`review-journal/v0` enforcement batch** — classification floors in-schema
  (half-`unknown` fails closed), anchor label integrity, mandatory participant
  join with `not-exposed` reasoner admission, required prompt digests for
  approving agent review seats, human maintainer participant, finding
  lifecycle + claim-scoped gates, author-does-not-approve at seat and person
  level.
- **Negative-control battery** — 19 reject/baseline pairs, single-field
  mutation machine-asserted, self-tested distance function; runs in
  `make check`.
- **PDR-0005** — seven of eight deferred gaps closed; `human-merge-authority`
  honestly open. Standard 0.4.1 → 0.5.0 with disclosures co-moved.

See [docs/releases/v0.1.25.md](docs/releases/v0.1.25.md).

---

## v0.1.24 (2026-07-28)

**A process release: a multi-agent review standard, its adoption record, an
optional review-journal contract, and one Engineering Principle Record on the
integrity of durable claims.**

- **Fierce-Collaboration Review standard** (0.4.0, draft) — review methodology
  for AI-agent and human panels; seat composition, disposition vocabulary,
  provenance anchors, optional machine-readable journal.
- **PDR-0005** (proposed) — adopts the process; discloses accepted contract gaps
  with an owner and closure trigger for each.
- **`review-journal/v0`** — manifest and event schemas, examples, contract
  manifest. Experimental stability.
- **EPR-0003** (proposed) — a durable claim states no more than its mechanism
  and evidence support, and co-moves with them.
- **Release-surface guard** — `make check` asserts the hand-maintained release
  surfaces moved with `VERSION`, with negative controls.

See [docs/releases/v0.1.24.md](docs/releases/v0.1.24.md).

---

## v0.1.23 (2026-07-26)

**A governance release: gate integrity as a durable principle.**

### Highlights

- **EPR-0002 (accepted)** — a gate whose green is relied upon must assert on the
  resolved state the system reached, must treat absent evidence as a failure
  rather than substituting a value for it, must be proven able to fail by an
  executable negative control, and must carry no exemption its stated coverage
  does not declare
- **Generalizes without superseding** — the domain-scoped instances
  (data-pipeline GP-2.2/GP-2.4, EPR-0001, PDR-0004) keep their scoping; where a
  domain record states a sharper obligation, the domain record governs within its
  domain
- **Cited with its evidence boundary** — the reference implementation includes a
  producer-path negative control for its memory-provenance gate, cited with what
  that control does and does not cover

### Changes

| Area           | Change                                                                                  |
| -------------- | --------------------------------------------------------------------------------------- |
| **Governance** | Add EPR-0002 (accepted); decisions index updated                                        |
| **Build**      | Version 0.1.22 → 0.1.23; package metadata, README badge, and changelog links are synced |

**Full release notes**: [docs/releases/v0.1.23.md](docs/releases/v0.1.23.md)

---

## v0.1.22 (2026-07-22)

**A governance release: EPR-0001 graduates to accepted.**

### Highlights

- **EPR-0001: proposed → accepted** — the record's own graduation condition, a
  conforming reference implementation, has been met in public
- **Four obligations discharged** — pin, enforce, audit, and parity, across two
  published surfaces of one shared cryptographic core
- **Conformance by negative control** — pin, enforce, and parity are each
  demonstrated by an executable control showing the gate fail; audit by
  on-change and scheduled advisory scans rather than asserted present in CI

### Changes

| Area           | Change                                                                                        |
| -------------- | --------------------------------------------------------------------------------------------- |
| **Governance** | EPR-0001 graduated proposed → accepted; Reference implementation section added; index updated |
| **Build**      | Version 0.1.21 → 0.1.22; package metadata, README badge, and changelog links are synced       |

**Full release notes**: [docs/releases/v0.1.22.md](docs/releases/v0.1.22.md)

---

## v0.1.21 (2026-07-20)

**Signed publication-policy attestation.**

### Highlights

- **Complete pre-tag validation** — the release script checks the configured
  version-tag policy before creating a tag
- **Signed policy fingerprint** — annotated release tags carry the canonical
  publication-policy fingerprint
- **Publication verification** — CI checks the read-only policy view and the
  signed fingerprint after pinned-key signature verification

### Changes

| Area        | Change                                                                                  |
| ----------- | --------------------------------------------------------------------------------------- |
| **Release** | Add complete/read-only ruleset modes and signed policy-attestation handling             |
| **CI**      | Verify the read-only policy view and signed fingerprint after pinned-key verification   |
| **Tests**   | Cover validation modes and missing or incorrect attestations                            |
| **Docs**    | Update the release gate decision and operator checklist                                 |
| **Build**   | Version 0.1.20 → 0.1.21; package metadata, README badge, and changelog links are synced |

**Full release notes**: [docs/releases/v0.1.21.md](docs/releases/v0.1.21.md)

---

## v0.1.20 (2026-07-19)

**Governance records: dependency-graph integrity, and the release process that publishes them.**

### Highlights

- **EPR-0001 (proposed)** — this lane's first Engineering Principle Record:
  every artifact built from a resolved dependency graph ships that graph
  pinned in-repo, enforced at build, continuously audited, and held at parity
  across all distribution surfaces of the same release. Obligations are fixed;
  tooling is deliberately left to adopting repositories
- **PDR-0004 (accepted)** — the signed tag authorizes publication. Signing
  creates the tag and the push triggers the workflow, so the tag is already
  signed when CI runs; a draft awaiting a signature guarded a condition that
  could not occur
- **Releases publish from CI** — the workflow asserts a verified tag signature,
  binds authorization to the exact annotated tag object, then publishes
  directly, setting `Latest` explicitly for stable versions; prereleases
  publish as prereleases and do not take `Latest`
- **Unverified tags fail closed** — no release is created, making an
  unpublished release a failure signal rather than a normal waiting state
- **Version-tag policy is executable** — release tagging and publication verify
  the live ruleset protects `refs/tags/v*` with only the
  organization-administrator bypass; workflow actions are pinned to immutable
  commits

### Changes

| Area           | Change                                                                                        |
| -------------- | --------------------------------------------------------------------------------------------- |
| **Governance** | Add EPR-0001 (proposed) and PDR-0004 (accepted); `EPR` listed in active use; index completed  |
| **CI**         | Release workflow verifies the exact tag object, publishes non-draft, pins third-party actions |
| **Process**    | Checklist, tagging, and publication verify the live version-tag ruleset                       |
| **Build**      | Version 0.1.19 → 0.1.20; package metadata, README badge, and changelog links are synced       |

**Full release notes**: [docs/releases/v0.1.20.md](docs/releases/v0.1.20.md)

---

## v0.1.19 (2026-07-09)

**Data artifact contract alignment: fully-withheld catalogs and optional grain catalogs.**

### Highlights

- **Fully-withheld field catalogs** — `fields: []` is valid when
  `withheld_field_count >= 1`, matching the protection model that already
  allows disclosing only a withheld count when field names are sensitive
- **Optional grain catalog refs** — raw archival grains that are not queryable
  or renderable may omit `field_catalog_ref`; queryable/renderable enforcement
  stays in Validation Requirements
- **Golden fixtures** — positive descriptors for both shapes; empty fields
  without a positive count fail closed

### Changes

| Area          | Change                                                                                          |
| ------------- | ----------------------------------------------------------------------------------------------- |
| **Standards** | Align field-catalog and grain catalog prose with fully-withheld and archival-optional semantics |
| **Schemas**   | Loosen `data-artifact/v0` constraints for empty catalogs and optional grain `field_catalog_ref` |
| **Examples**  | Add fully-withheld and raw-archival golden descriptors                                          |
| **Build**     | Version 0.1.18 → 0.1.19; package metadata, README badge, and changelog links are synced         |

**Full release notes**: [docs/releases/v0.1.19.md](docs/releases/v0.1.19.md)

---

[View complete changelog →](CHANGELOG.md)
