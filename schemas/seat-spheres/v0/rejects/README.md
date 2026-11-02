# Rejects — seat-spheres/v0

Negative fixtures, grouped by schema. Each `reject-*.json` must fail the
schema of its directory.

## seat-view

| File                                         | Why                                                                                              |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `reject-bad-relation.json`                   | `relation` is a closed enum.                                                                     |
| `reject-bad-relation-assurer.json`           | `relation` is a closed enum; `assurer` is not `assure`.                                          |
| `reject-capabilities-wrong-token.json`       | `capabilities` must contain the exact contract token.                                            |
| `reject-cover-list.json`                     | `cover` is one id, not a list.                                                                   |
| `reject-cover-run.json`                      | `cover` is an agent or person id, not a run.                                                     |
| `reject-exception-allow-without-reason.json` | An `allow` exception (widening) requires `reason`. A `deny` may omit it; see the assure example. |
| `reject-exception-bad-effect.json`           | An exception `effect` is `allow` or `deny`.                                                      |
| `reject-exception-missing-effect.json`       | An exception requires `effect`.                                                                  |
| `reject-exception-missing-right.json`        | An exception requires `right`.                                                                   |
| `reject-exception-unknown-field.json`        | Unknown exception fields are rejected.                                                           |
| `reject-exceptions-empty.json`               | `exceptions`, when present, must be non-empty.                                                   |
| `reject-function-not-in-enum.json`           | `function` is a closed enum.                                                                     |
| `reject-holder-agent-bad-id.json`            | An agent id must start with `agent-`.                                                            |
| `reject-holder-agent-double-hyphen.json`     | An agent id cannot contain an empty segment (`agent--`).                                         |
| `reject-holder-agent-trailing-hyphen.json`   | An agent id cannot end with a hyphen.                                                            |
| `reject-holder-person-leading-digit.json`    | A person id must start with a letter.                                                            |
| `reject-holder-person-run-id.json`           | A person id must not carry the `run-` prefix.                                                    |
| `reject-holder-run-kind.json`                | A run is never a holder.                                                                         |
| `reject-holder-unknown-field.json`           | Unknown holder fields are rejected.                                                              |
| `reject-impossible-date.json`                | `since` must be a real ISO-8601 date.                                                            |
| `reject-measure-missing-as-of.json`          | A measure requires `as_of`.                                                                      |
| `reject-measure-missing-expires.json`        | A measure requires `expires`; none are permanent.                                                |
| `reject-measure-missing-name.json`           | A measure requires `name`.                                                                       |
| `reject-measure-missing-set-by.json`         | A measure requires `set_by`.                                                                     |
| `reject-measure-missing-target.json`         | A measure requires `target`.                                                                     |
| `reject-measure-set-by-leading-digit.json`   | A `set_by` person id must start with a letter.                                                   |
| `reject-measure-set-by-run.json`             | A measure `set_by` is an agent or person, not a run.                                             |
| `reject-measure-unknown-field.json`          | Unknown measure fields are rejected.                                                             |
| `reject-measures-empty.json`                 | `measures`, when present, must be non-empty.                                                     |
| `reject-missing-spheres.json`                | `spheres` is required (an empty array is valid).                                                 |
| `reject-no-apply-not-boolean.json`           | `no_apply` is a boolean.                                                                         |
| `reject-reports-to-run.json`                 | `reports_to` is an agent or person id, not a run.                                                |
| `reject-review-by-impossible-date.json`      | `review_by` must be a real ISO-8601 date.                                                        |
| `reject-subject-id-uppercase.json`           | Subject `id` must be lowercase (`^[a-z0-9]+([._/-][a-z0-9]+)*$`).                                |
| `reject-subject-kind-not-slug.json`          | Subject `kind` must be a slug.                                                                   |
| `reject-subject-missing-id.json`             | A subject requires `id`.                                                                         |
| `reject-subject-missing-kind.json`           | A subject requires `kind`.                                                                       |
| `reject-subject-unknown-field.json`          | Unknown subject fields are rejected.                                                             |
| `reject-unknown-field.json`                  | Unknown top-level fields are rejected.                                                           |
| `reject-unknown-sphere-field.json`           | Unknown sphere fields are rejected.                                                              |
