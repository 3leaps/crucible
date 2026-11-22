# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file keeps the latest three releases. Earlier releases, back to
> v0.1.17 (the first public baseline), are in [CHANGELOG.md](CHANGELOG.md) and
> [docs/releases/](docs/releases/).

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

## v0.2.11 (2026-11-13)

**Adds the proposed, experimental `filesystem-access/v0` contract for portable access relative to a held directory object.**

- Defines root-relative name admission, `containment/v0` and `no-links/v0`
  profiles, held-handle identity, bounded reads and directory listings, and
  exclusive creation without final-link following.
- Adds request/result schemas, per-operation capability reports, 62 declarative
  recipe cases, and logical, schema, mutation and bounded native availability
  controls.

The contract remains proposed/experimental. Schema validity, logical agreement
and primitive availability do not qualify a production resolver or concurrent
filesystem enforcement.

See [docs/releases/v0.2.11.md](docs/releases/v0.2.11.md).

---
