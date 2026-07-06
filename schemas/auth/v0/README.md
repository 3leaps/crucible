# Auth Schemas v0

Schemas for non-secret auth metadata exchanged between 3leaps tools.

**Status**: Unstable (v0) — breaking changes may occur without notice.

## Schemas

| Schema                         | Purpose                                             |
| ------------------------------ | --------------------------------------------------- |
| `session-artifact.schema.json` | Inspectable metadata about an acquired auth session |

## Session Artifact

The single versioned contract that decouples credential **acquirers** (which emit
a conforming artifact, e.g. in Go) from **inspectors** (which validate and parse
it, e.g. in Rust). No shell-out, no FFI — both sides pin the same schema and a
synthetic round-trip fixture.

See the standard for the full rationale, compatibility policy, and governance split:
[docs/standards/auth-session-artifact.md](../../../docs/standards/auth-session-artifact.md).

### Invariants

1. **No value/secret fields, ever — structural.** `additionalProperties: false` on
   the root and the token object. A stray `value` / `SecretAccessKey` /
   `SessionToken` / raw-JWT field makes the artifact **non-conforming**; consumers
   reject loudly and never normalize it. Permanent across all versions.
2. **Metadata only; no identifiers.** Expirations and structural/provenance
   metadata only. A free-text `label` was deliberately dropped — free text can't be
   policed by `additionalProperties: false`; display names resolve consumer-side
   from `kind` + `source`.
3. **JWT = decoded payload claims only**, non-PII subset (`iss/aud/exp/iat/nbf`).
   No signature, no verification key; `sub`/`email` redacted or omitted by default.
4. **`unmeasured` is first-class** in both `kind` and `expiry_basis` for off-disk,
   browser-held upstream-IdP sessions. It is excluded from the weakest-link;
   top-level `expires_at` is the weakest **observable** expiry.

### Fixture

`session-artifact.example.json` is a synthetic, sterile conforming fixture (a
4-layer AWS cascade including an `unmeasured` upstream-IdP layer; all values are
`example-*`-class placeholders with zero real identifiers). Publish it **alongside**
the schema; both consuming repos pin it for round-trip tests.

> Note: the fixture intentionally omits a `$schema` key — the root is
> `additionalProperties: false`, so a `$schema` property would make it
> non-conforming. Validate it with an explicit `--schema-file` instead.

## Schema URLs

```
https://schemas.3leaps.dev/auth/v0/session-artifact.schema.json
```

## Validation / pinning

- **Crucible owns the contract** — source of truth, `schema_version`, and
  authoritative metaschema validation at publish (`goneat schema validate-schema
--schema-id json-schema-2020-12`).
- **Consumers vendor a SHA256-pinned copy** (not a live git ref — preserves
  offline/standalone-binary determinism), run goneat meta-validation at build (fail
  on malformed schema or SHA drift), and runtime-validate every artifact. Consumers
  do **not** own the file.

## Related

- [docs/standards/auth-session-artifact.md](../../../docs/standards/auth-session-artifact.md) - The standard
- [docs/decisions/ADR-0001-schema-config-versioning.md](../../../docs/decisions/ADR-0001-schema-config-versioning.md) - v0 + SemVer versioning
- [FulmenHQ Crucible](https://github.com/fulmenhq/crucible) - Enterprise extensions
