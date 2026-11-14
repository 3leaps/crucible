# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file keeps the latest three releases. Earlier releases, back to
> v0.1.17 (the first public baseline), are in [CHANGELOG.md](CHANGELOG.md) and
> [docs/releases/](docs/releases/).

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
