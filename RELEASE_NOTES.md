# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file keeps the latest three releases. Earlier releases, back to
> v0.1.17 (the first public baseline), are in [CHANGELOG.md](CHANGELOG.md) and
> [docs/releases/](docs/releases/).

---

## v0.2.14 (2026-11-23)

**Adds the proposed, experimental `record-collection/v0` contract family, files proposed PDR-0011 and PDR-0013, refines proposed PDR-0010, adds a non-normative timestamp source-precision adopter guide, and strengthens release-surface guards and checklist triage.**

- Adds sibling contract family `schemas/record-collection/v0/` (`set` and `list`
  of exact `durable-record/v1` revision pins, `member_count`, `append_only`,
  `closure_claim`, body-backed evidence verification, 6 examples, 14 schema
  reject pairs, 27 behavioral vectors, 7 semantic rejects, and offline controls)
  with zero changes to `durable-record/v1` or `project-work/v0`.
- Files proposed PDR-0011 (package registry publication against verified final
  archive) and proposed PDR-0013 (byte-exact repository data declared in
  `.gitattributes` and verified with Git, plus CI/Windows guidance updates), and
  refines proposed PDR-0010 obligations.
- Adds the non-normative adopter guide
  `docs/guides/durable-record-timestamp-source-precision.md` and strengthens
  `RELEASE_CHECKLIST.md`, `version-set`, and `release-guard-release-surfaces`.

`record-collection/v0` remains proposed/experimental, and PDR-0010, PDR-0011,
and PDR-0013 remain proposed. Crucible stays on PDR-0004 for release publication
and is not yet covered by PDR-0013.

See [docs/releases/v0.2.14.md](docs/releases/v0.2.14.md).

---

## v0.2.13 (2026-11-22)

**Adds the proposed, experimental `durable-runner/v0` contract for portable task execution with journaled recovery, and proposed PDR-0012 on publishing presser qualification claims.**

- Defines task identity, closed task and attempt transitions, retry and
  backoff bounds, single-authority recovery with generation handles, supplied
  schedules with catch-up, and independent durability properties. Modes
  `basic`, `retrying`, `journaled` and `scheduled` are specified; `sealed` is
  reserved and refused.
- Adds six schemas, examples, schema and semantic rejects, 413 behavioral
  vectors, a reference model and mutation, refusal-isolation, type-fuzz and
  wire-record controls. Contract scripts also run on Python 3.15.
- Adds proposed PDR-0012, a reporting practice for published presser results
  (what ran, expectations and scope, conclusions with evidence, verifiable
  claims), with provisional fuzz guidance and no new schema or runner.

The contract remains proposed/experimental. The reference model is a fixture
checker: it qualifies no runtime, storage, cloud or language implementation.

See [docs/releases/v0.2.13.md](docs/releases/v0.2.13.md).

---

## v0.2.12 (2026-11-14)

**Adds draft secret-surface boundaries and extends library implementation profiles and qualification-harness rules.**

- Defines value-free control, observation, MCP and graphical surfaces; explicit
  secret input and local CLI/TUI output boundaries; child/helper hygiene; and
  protected file custody with adopter non-disclosure controls.
- Extends library profiles to unsuffixed toolkits, documents legacy Go module
  cutover and Rust-generated native/WebAssembly TypeScript delivery, and
  separates qualification-harness verification authority and reporting axes.

The standards remain draft and their companion decisions proposed. Repository
class checks remain manual; these documentation changes do not qualify an
existing product, binding or harness implementation.

See [docs/releases/v0.2.12.md](docs/releases/v0.2.12.md).

---
