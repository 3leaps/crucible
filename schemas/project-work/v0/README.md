# Project Work Schemas v0

Machine-readable companion schemas for the portable project-work contract.

The normative standard is
[`docs/standards/project-work-contract.md`](../../../docs/standards/project-work-contract.md).
These schemas provide a **structural** validation surface. Journal-set rules
(an open blocker when class is `blocked`; a `class-changed` to `done` as
evidence of completion) **MUST** be enforced by consumers. Kind
discriminants close reserved transition keys and kind-owned control
fields. The reference controls in `scripts/test-project-work-controls.sh`
cover structural examples/rejects and classifier-key alignment only.
`make check` does **not** prove blocked↔blocker or done↔event.

The contract identity is the opaque capability token
`contract: project-work/v0`. Consumers resolve that token through local
configuration, a vendored copy, or another trusted registry. Instances must
not embed a schema host as their identity.

The L2 contract entry point is `contract.json`. Consumers resolve the
capability to that manifest, verify its `capability`, and load the relative
`entry_schema` (`ready-packet.schema.json` — the packet is the dispatchable
root). Resolution fails closed when the manifest is missing, the capability
does not match, or the entry schema is missing.

| Schema                       | Governs                                                                |
| ---------------------------- | ---------------------------------------------------------------------- |
| `ready-packet.schema.json`   | Dispatchable unit of work                                              |
| `project-state.schema.json`  | Inspectable project projection (sibling of packets, not a parent task) |
| `control-record.schema.json` | Status note, blocker, or decision                                      |
| `progress-event.schema.json` | One NDJSON line of the append-only work ledger                         |

Worked examples in [`examples/`](examples/). Negative fixtures in [`rejects/`](rejects/).
