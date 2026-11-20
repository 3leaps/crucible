# Durable runner schema family v0

**Proposed / experimental.** The capability is `contract: durable-runner/v0`.
Resolve it through a trusted, pinned `contract.json`; never treat
instance-provided retrieval addresses as a schema registry. The normative
companion is the
[durable runner standard](../../../docs/standards/durable-runner-contract.md).
Decision record:
[ADR-0021](../../../docs/decisions/ADR-0021-durable-runner-contract.md).

The contract is logical only. It admits the modes `basic`, `retrying`,
`journaled` and `scheduled`, and reserves `sealed`, which no profile may
advertise yet. Process supervision, storage layouts, schedulers and runtimes
belong to adopting repositories.

| Artifact | Responsibility |
| --- | --- |
| `contract.json` | Capability manifest; entry is the runner profile |
| `runner-profile.schema.json` | Discovery root: modes, authority, independent durability properties, journal pin, idempotency windows |
| `task-definition.schema.json` | The immutable specification whose canonical digest is `task_spec_digest` |
| `task-submission.schema.json` | Authority, invocation key and derived identities around one definition |
| `transition.schema.json` | Payload of one single-revision durable-record/v1 record: state change plus attempt fact |
| `checkpoint.schema.json` | Journal cursor and verified state body pin as one payload |
| `supplied-slot.schema.json` | Caller-supplied slot, occurrence set or coverage, and catch-up link |
| `examples/` | One golden per object, plus a governed-acquisition composition |
| `rejects/schema/` | Baseline and reject pairs differing in exactly one field |

`task-submission` embeds the task-definition schema under `$defs.taskDefinition`
so it validates standalone; the controls fail if the copy drifts. Run
`python3 scripts/test-durable-runner-controls.py`, also included in
`make check`. It validates every example, recomputes `task_id`,
`task_spec_digest` and `attempt_id` from RFC 8785 canonical bytes, and
asserts each reject pair differs in exactly one field.

Fixture data is synthetic. Identifiers are public-safe tokens.
