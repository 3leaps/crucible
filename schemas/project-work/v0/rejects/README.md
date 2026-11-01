# Rejects — project-work/v0

Negative fixtures, grouped by schema. Each `reject-*.json` must fail the
schema of its directory.

## ready-packet

| File                                      | Why                                                                   |
| ----------------------------------------- | --------------------------------------------------------------------- |
| `reject-nested-children.json`             | Hierarchy is forbidden.                                               |
| `reject-lifecycle-todo.json`              | `todo` is not a lifecycle class.                                      |
| `reject-unassigned-ready.json`            | `unassigned` owner cannot be `ready`.                                 |
| `reject-unassigned-with-id.json`          | `unassigned` must omit `id` and `display`.                            |
| `reject-escalation-not-slug.json`         | `escalation.default` is a role slug, not an estate seat enum.         |
| `reject-role-id-hyphen.json`              | Role `id` must match role-prompt slug (no hyphens).                   |
| `reject-classifier-half-unknown.json`     | `unknown` is valid only as a pair.                                    |
| `reject-classifier-floor.json`            | `access-tier` below the sensitivity floor.                            |
| `reject-check-by-not-datetime.json`       | `check_by` is an RFC 3339 date-time.                                  |
| `reject-requested-by-unassigned.json`     | `requested_by` names a person or role, never `unassigned`.            |
| `reject-requested-by-role-hyphen.json`    | `requested_by` role `id` must match role-prompt slug.                 |
| `reject-check-by-date-only.json`          | `check_by` needs a `T` time part with `Z` or an offset.               |
| `reject-requested-by-extra-property.json` | `requested_by` is closed; extra properties fail.                      |
| `reject-requested-by-missing-id.json`     | `requested_by` requires `id`.                                         |
| `reject-agent-missing-role.json`          | An `agent` party requires `role`.                                     |
| `reject-agent-id-pattern.json`            | An `agent` `id` must match `^agent-<slug>$`.                          |
| `reject-run-missing-parent.json`          | A `run` requires `parent`.                                            |
| `reject-run-missing-expires.json`         | A `run` requires `expires`.                                           |
| `reject-run-requested-by.json`            | A `run` is never a `requested_by`.                                    |
| `reject-run-expires-date-only.json`       | `run` `expires` needs a `T` time part with `Z` or an offset.          |
| `reject-run-parent-is-run.json`           | A `run` `parent` is an agent or person, never another run.            |
| `reject-person-id-agent-prefix.json`      | A person `id` may not start with the reserved `agent-`.               |
| `reject-person-id-run-prefix.json`        | A person `id` may not start with the reserved `run-`.                 |
| `reject-run-parent-leading-space.json`    | A `run` `parent` with a leading space is neither agent nor person id. |
| `reject-run-parent-uppercase-run.json`    | A `run` `parent` `RUN-…` is neither agent nor person id.              |
| `reject-run-parent-embedded-space.json`   | A `run` `parent` may not contain a space.                             |
| `reject-run-parent-newline.json`          | A `run` `parent` may not contain a newline.                           |
| `reject-run-id-lowercase.json`            | A `run` `id` ULID is canonical uppercase.                             |
| `reject-run-id-ulid-overflow.json`        | A `run` `id` ULID cannot start above `7`.                             |
| `reject-person-with-role.json`            | A `person` party does not carry `role`.                               |
| `reject-role-with-parent.json`            | A `role` party does not carry `parent`.                               |
| `reject-unassigned-with-expires.json`     | An `unassigned` party does not carry `expires`.                       |
| `reject-run-owner-missing-check-by.json`  | A non-terminal packet with a `run` owner requires `check_by`.         |
| `reject-person-id-at-handle.json`         | A person `id` is stored without a leading `@`.                        |

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
| `reject-actor-agent-id-pattern.json`             | An `agent` actor `id` must match `^agent-<slug>$`.  |

## control-record

| File                                     | Why                                               |
| ---------------------------------------- | ------------------------------------------------- |
| `reject-dual-subject.json`               | Exactly one of `packet_id` or `project_id`.       |
| `reject-missing-actor.json`              | Records must be attributable.                     |
| `reject-unassigned-decider.json`         | A decision `decider` is a person, role, or agent. |
| `reject-untyped-subject.json`            | Bare `subject_id` is not a typed subject.         |
| `reject-status-cross-kind.json`          | Status forbids blocker and decision fields.       |
| `reject-blocker-with-decider.json`       | Blockers forbid `decider`.                        |
| `reject-decision-with-waiting-on.json`   | Decisions forbid blocker-only fields.             |
| `reject-decision-missing-affects.json`   | A decision requires `affects`.                    |
| `reject-decision-empty-affects.json`     | Decision `affects` must be non-empty.             |
| `reject-decision-duplicate-affects.json` | Decision `affects` must be unique.                |
| `reject-status-with-affects.json`        | Status forbids decision-owned `affects`.          |
| `reject-blocker-with-affects.json`       | Blockers forbid decision-owned `affects`.         |
| `reject-decider-run.json`                | A `decider` is never a `run`.                     |
| `reject-actor-agent-missing-role.json`   | An `agent` actor requires `role`.                 |

## project-state

| File                                    | Why                                              |
| --------------------------------------- | ------------------------------------------------ |
| `reject-milestone-impossible-date.json` | Milestone `target` must be a real ISO-8601 date. |
| `reject-owner-run.json`                 | A project `owner` is never a `run`.              |
| `reject-owner-agent-missing-role.json`  | An `agent` project `owner` requires `role`.      |
