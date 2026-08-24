# Rejects — project-work/v0

Negative fixtures, grouped by schema. Each `reject-*.json` must fail the
schema of its directory.

## ready-packet

| File                                  | Why                                                           |
| ------------------------------------- | ------------------------------------------------------------- |
| `reject-nested-children.json`         | Hierarchy is forbidden.                                       |
| `reject-lifecycle-todo.json`          | `todo` is not a lifecycle class.                              |
| `reject-unassigned-ready.json`        | `unassigned` owner cannot be `ready`.                         |
| `reject-unassigned-with-id.json`      | `unassigned` must omit `id` and `display`.                    |
| `reject-escalation-not-slug.json`     | `escalation.default` is a role slug, not an estate seat enum. |
| `reject-role-id-hyphen.json`          | Role `id` must match role-prompt slug (no hyphens).           |
| `reject-classifier-half-unknown.json` | `unknown` is valid only as a pair.                            |
| `reject-classifier-floor.json`        | `access-tier` below the sensitivity floor.                    |

## progress-event

| File                                             | Why                                                 |
| ------------------------------------------------ | --------------------------------------------------- |
| `reject-missing-seq.json`                        | `seq` is the ledger order key.                      |
| `reject-class-changed-no-to.json`                | `class-changed` requires `from` and `to`.           |
| `reject-blocked-wrong-to.json`                   | `blocked` requires `to=blocked`.                    |
| `reject-dual-subject.json`                       | Exactly one of `packet_id` or `project_id`.         |
| `reject-created-no-class.json`                   | `created` requires initial `lifecycle_class`.       |
| `reject-created-with-from-to.json`               | `created` forbids contract `from`/`to`.             |
| `reject-class-changed-from-done.json`            | Terminal exits are `reopened`, not `class-changed`. |
| `reject-class-changed-with-lifecycle-class.json` | Transition kinds forbid contract `lifecycle_class`. |

## control-record

| File                                     | Why                                         |
| ---------------------------------------- | ------------------------------------------- |
| `reject-dual-subject.json`               | Exactly one of `packet_id` or `project_id`. |
| `reject-missing-actor.json`              | Records must be attributable.               |
| `reject-unassigned-decider.json`         | A decision `decider` is a person or role.   |
| `reject-untyped-subject.json`            | Bare `subject_id` is not a typed subject.   |
| `reject-status-cross-kind.json`          | Status forbids blocker and decision fields. |
| `reject-blocker-with-decider.json`       | Blockers forbid `decider`.                  |
| `reject-decision-with-waiting-on.json`   | Decisions forbid blocker-only fields.       |
| `reject-decision-missing-affects.json`   | A decision requires `affects`.              |
| `reject-decision-empty-affects.json`     | Decision `affects` must be non-empty.       |
| `reject-decision-duplicate-affects.json` | Decision `affects` must be unique.          |
| `reject-status-with-affects.json`        | Status forbids decision-owned `affects`.    |
| `reject-blocker-with-affects.json`       | Blockers forbid decision-owned `affects`.   |

## project-state

| File                                    | Why                                              |
| --------------------------------------- | ------------------------------------------------ |
| `reject-milestone-impossible-date.json` | Milestone `target` must be a real ISO-8601 date. |
