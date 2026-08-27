# Rejects

| Fixture                                               | Kind       | Why                                                                    |
| ----------------------------------------------------- | ---------- | ---------------------------------------------------------------------- |
| `authority-profile.handoff-without-uri.json`          | structural | operator handoff lacks its required URI template                       |
| `binding-receipt.secret-field.json`                   | structural | secret-bearing field appears under public identifiers                  |
| `forge-object-ref.missing-provider.json`              | structural | provider context is absent                                             |
| `provider-profile.supported-without-mode.json`        | structural | supported operation has no interaction mode                            |
| `provider-profile.unknown-capability.semantic.json`   | semantic   | schema-valid mapping cites a capability absent from the catalog        |
| `requirement-profile.unknown-operation.semantic.json` | semantic   | schema-valid requirement cites an operation absent from its capability |

Semantic fixtures deliberately pass their object schema and fail the
cross-document controls in `scripts/test-forge-infra-controls.sh`.
