# `filesystem-access/v0`

This experimental family defines portable request, result, capability-report and
synthetic recipe shapes for operations relative to a held root object. It does
not implement filesystem access or qualify an operating-system backend. The
[normative standard](../../../docs/standards/filesystem-access.md) defines the
operation semantics and qualification requirements.

| File                              | Purpose                                                                                                                         |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `root-relative-name.schema.json`  | A lexical, portable no-links name after admission. Consumers still reject malformed Unicode scalar input before UTF-8 encoding. |
| `observed-name.schema.json`       | One representable observed directory-entry name. Reserved or aliasing spellings remain observable and are not normalized.       |
| `access-request.schema.json`      | Operation-specific requests using opaque root or held-handle references, never host paths.                                      |
| `access-result.schema.json`       | Typed accepted or refused results.                                                                                              |
| `capability-report.schema.json`   | Per-cell claims keyed by OS, architecture, filesystem, backend, operation, profile, observation point, adversary and evidence.  |
| `cases.schema.json`, `cases.json` | Declarative, repository-safe logical recipes. Recipes do not name host paths or execute filesystem operations.                  |

`root_ref`, `handle_ref` and lifetime generation values are local adapter
references, not transferable authorization. A numeric object identity is comparable only while its referenced
handles remain live; reopening an object after every such handle closes is not
continuity evidence. `stat` and `same_object` inspect held handles and never
perform path re-lookup.

Capability cells qualify one stated observation point. A manual walker can claim
only `stable_tree`. In v0, concurrent-rename resistance is limited to a
qualified Linux `openat2` final-open cell; an API availability probe or backend
label is not qualification. A requested unavailable guarantee returns
`unsupported_capability`, not a fallback.

The contract rejects portable aliases including ADS colons and trailing-dot or
space spellings. Native directory observations can contain names that admission
would reject; representable observed names remain in a listing and are not
authority to reopen them.

Run the checks with:

```sh
python3 scripts/test-filesystem-access-controls.py
```

The command includes logical, schema and bounded native availability controls.
It does not establish production race resistance or implementation conformance.
