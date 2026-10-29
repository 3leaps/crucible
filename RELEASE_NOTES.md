# Release Notes

Current release notes for 3leaps Crucible. For complete history, see [CHANGELOG.md](CHANGELOG.md).

For detailed release content, see [docs/releases/](docs/releases/).

> **Note**: This file keeps the latest three releases. Earlier releases, back to
> v0.1.17 (the first public baseline), are in [CHANGELOG.md](CHANGELOG.md) and
> [docs/releases/](docs/releases/).

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

---

## v0.2.4 (2026-10-28)

**Durable-record/v1 records body lifecycle; release tag tooling closes four silent defaults.**

- **Body lifecycle (durable-record/v1, additive)**: a store that supports
  removing external bodies names a `body_removal_stream` and records
  `body_published`, `body_removal_started` and `body_removed` there, per body
  and incarnation. A removal is evidenced only by `body_removed`; a later
  publication abandons an open removal. Reader states are defined at a
  consistent cut. Lifecycle grants no removal eligibility, and physical
  removal stays fail-closed. Existing v1 records and journals are unchanged.
  The logical controls qualify no store.
- **Release tag tooling**: `make release-tag` refuses the default keyring and
  signs with a pinned OpenPGP `gpg` signer, reporting any configured signer it
  overrides; `make release-push-tag` uses the
  explicit HTTPS URL with only the org token, isolated from home credentials,
  proxy and TLS overrides. The read-only ruleset check no longer reports a
  hidden bypass list as a match.

See [docs/releases/v0.2.4.md](docs/releases/v0.2.4.md).

---

## v0.2.3 (2026-10-27)

**Durable-record/v1 gains continuation streams and restriction review.**

- **Continuation streams (durable-record/v1, additive)**: a stream that
  re-records another stream's content declares `continues` and marks imports
  with `imported_from`. A `restrictions_reviewed` entry binds the reviewed
  source cut, the effective source restrictions and the destination's applied
  restrictions. Serving, export and reuse fail closed as `restrictions_pending`
  until a current review exists. Existing v1 records and journals are
  unchanged. The logical controls qualify no store.
- **Repository classes (draft 0.1.1)**: C5 requires a `version` subcommand
  and settles JSON-only and artifact-output verbs; C3 counts test variables;
  C4 points host-tool ceremonies at `make doctor`; P1 settles npm and PyPI
  reservation.

See [docs/releases/v0.2.3.md](docs/releases/v0.2.3.md).
