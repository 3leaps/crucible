# Inference Path Taxonomy v0 (PROPOSED)

This family defines reusable names for parties, model families, exact
source-native model pins, and declared inference paths. The contract identity
is the host-less capability token
`contract: inference-path-taxonomy/v0`.

Status: **proposed**. Consumers should vendor an exact reviewed revision and
record the source revision and artifact digests.

## Boundary

The taxonomy describes identity only. It deliberately excludes observations,
probe origins, effective routes, health, latency, result classes, incidents,
scores, billing identity, secrets, and product-local display aliases.

The four record kinds are:

- `party`: an organization or product identity plus roles it may represent;
- `model_family`: an author-scoped family, not a provider request string;
- `model_pin`: an exact source-native identifier and its evidence;
- `path_identity`: a declared model, ordered route, endpoint, service region,
  and access-class identity.

The entry schema is `inference-path-taxonomy.schema.json`. It is a closed union
over those four schemas.

## Industry alignment

Party aliases may carry OpenTelemetry GenAI well-known provider values under
the `otel.gen_ai.provider.name` namespace. This does not collapse the estate
party into an instrumentation-time provider claim.

Model pins preserve the source's grammar, including forms such as OpenRouter
`author/slug` and Hugging Face `namespace/name@revision`. A consumer must not
infer author, family equivalence, execution host, or billing route from a
convenient model string.

See [semantic-validation.md](./semantic-validation.md) for cross-record and
digest rules that JSON Schema cannot prove.
