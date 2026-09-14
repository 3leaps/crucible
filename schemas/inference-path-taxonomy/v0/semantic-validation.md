# Inference path taxonomy semantic validation

JSON Schema validates one record at a time. A conforming catalog additionally
enforces these rules:

1. Every `*_ref` resolves to exactly one record of the required kind and
   revision in the pinned catalog.
2. `model_family.author_party_ref` resolves to a party with
   `model_author`.
3. `model_pin.source_party_ref` resolves to its actual identifier issuer or
   source. `family_ref`, when present, is evidence-backed and resolves to a
   model family.
4. Every route segment's party has the segment's declared role.
5. Route order is preserved. Consumers do not sort or deduplicate segments.
6. `execution_host_mode: declared` has a declared execution-host segment.
   `router_selected` has none; an observed effective host belongs to an
   observation contract and never rewrites this record.
7. `service_region` describes the service side. Probe/scout origin is not part
   of path identity.
8. `access_class` contains no account, tenant, subscription, credential, or
   billing identifier.
9. A source-native `model_id` is opaque. Consumers do not parse it to infer
   family, author, provider, route, or equivalence.
10. Revisions are immutable. A changed frozen identity is a new revision.

## Identity digests

`identity_digest` is `sha256:` followed by the lowercase SHA-256 digest of the
RFC 8785 JSON Canonicalization Scheme encoding of these fields:

| Kind | Frozen fields |
| --- | --- |
| `party` | `kind`, `party_id`, `revision`, `display_name`, `aliases`, `roles` |
| `model_family` | `kind`, `model_family_id`, `revision`, `author_party_ref`, `slug`, `display_name` |
| `model_pin` | `kind`, `model_pin_id`, `revision`, `source_party_ref`, `model_id`, `canonical_model_id`, `family_ref`, `resolution_state`, `source_evidence` |
| `path_identity` | `kind`, `path_id`, `revision`, `model_family_ref`, `model_pin_ref`, `route`, `execution_host_mode`, `endpoint_ref`, `service_region`, `access_class`, `source_evidence` |

Omitted optional fields remain omitted from the canonical digest input. The
`capabilities` and `identity_digest` fields are excluded. Producers must not
serialize an absent optional field as `null`.

## Unknowns

An unresolved model-to-family mapping uses `resolution_state: unknown` or
`indeterminate` and omits `family_ref`. It never fabricates `model_id:
unknown`. An unknown access class may use the published value `unknown`.
