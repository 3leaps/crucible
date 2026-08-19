# Active Role Portfolio

**Canonical URL** (planned):
`https://crucible.3leaps.dev/catalog/roles/active-roles`

A common role-selection reference for human and agent readers.

Here, **active portfolio** means every non-deprecated role definition. An
`approved` role is ready for ordinary adoption. A `draft` role has a defined
boundary and valid prompt but still requires practical review before it should
be represented as approved.

The linked YAML files are canonical. This page summarizes selection boundaries;
it does not duplicate the full prompts.

## Approved roles

| Role                                                      | Use it when                                                                                   | Keep distinct from                                    |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| [`devlead`](../../../config/agentic/roles/devlead.yaml)   | Implementing or repairing software and its tests                                              | `devrev`, which independently reviews the result      |
| [`devrev`](../../../config/agentic/roles/devrev.yaml)     | Independently reviewing correctness, contracts, failure behavior, and test strategy           | `secrev`, whose primary lens is security              |
| [`secrev`](../../../config/agentic/roles/secrev.yaml)     | Independently assessing security, privacy, supply-chain, and trust risk                       | `secops`, which operates controls and infrastructure  |
| [`cxotech`](../../../config/agentic/roles/cxotech.yaml)   | Choosing product direction, product-architecture bets, and priorities                         | `entarch`, which protects technical coherence         |
| [`entarch`](../../../config/agentic/roles/entarch.yaml)   | Governing cross-system boundaries, contracts, compatibility, and architecture coherence       | `cxotech`, which owns product-side choices            |
| [`uxdev`](../../../config/agentic/roles/uxdev.yaml)       | Designing and implementing interactive terminal, desktop, mobile, or web experiences          | `devlead` for general implementation                  |
| [`dataeng`](../../../config/agentic/roles/dataeng.yaml)   | Building and operating data models, pipelines, migrations, lineage, and quality controls      | `analyst`, which uses evidence to answer questions    |
| [`prodmktg`](../../../config/agentic/roles/prodmktg.yaml) | Developing evidence-grounded positioning, messaging, and audience narrative                   | `strategist`, which advises on strategic posture      |
| [`dispatch`](../../../config/agentic/roles/dispatch.yaml) | Routing work and preserving handoffs across an agent estate                                   | `projectmgr`, which defines and controls project work |
| [`infoarch`](../../../config/agentic/roles/infoarch.yaml) | Structuring documentation, schemas, terminology, and information systems                      | `entarch` for cross-system technical decisions        |
| [`releng`](../../../config/agentic/roles/releng.yaml)     | Engineering a genuinely complex release, publication, signing, provenance, or platform system | `devlead` for routine CI and release work             |

## Draft roles

| Role                                                          | Use it when                                                                                                        | Review focus before approval                                                                  |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| [`analyst`](../../../config/agentic/roles/analyst.yaml)       | Turning a defined question and evidence into reproducible findings with explicit uncertainty                       | Stress-test web and social-source research, analytical assurance, and handoff to `strategist` |
| [`strategist`](../../../config/agentic/roles/strategist.yaml) | Developing strategic diagnosis, plausible futures, options, trade-offs, and recommendations                        | Verify that advice does not absorb accountable product, technical, or human decisions         |
| [`watcher`](../../../config/agentic/roles/watcher.yaml)       | Monitoring a bounded surface, handling documented routine conditions, and escalating uncertainty                   | Validate polling, cursor, retry, deadman, and low-cost/local-model operation                  |
| [`delegate`](../../../config/agentic/roles/delegate.yaml)     | Assisting one or more principals through privileged access to communications, calendars, and commitments           | Prove compartment isolation and separate read, action, and disclosure grants                  |
| [`secops`](../../../config/agentic/roles/secops.yaml)         | Curating and operating identities, infrastructure, security controls, and technology assets with privileged access | Prove custodianship grants, rollback, emergency powers, and operator-reviewer separation      |
| [`projectmgr`](../../../config/agentic/roles/projectmgr.yaml) | Turning an approved objective into ready tasks, dependencies, milestones, ownership, and delivery state            | Verify clean handoffs to `dispatch` without absorbing product or technical authority          |

## Common operating chains

Product and technology:

`cxotech chooses product direction ↔ entarch protects technical coherence`

Implementation:

`projectmgr prepares work → dispatch routes → devlead implements → devrev reviews`

Monitoring and advice:

`watcher observes → analyst explains → strategist recommends → accountable actor decides`

Privileged principal assistance:

`principal grant → delegate assists within compartments → principal approves consequential action`

Privileged infrastructure:

`custodianship grant → secops operates → secrev independently reviews → human accepts risk`

These are composable patterns, not mandatory panels. Use the smallest set of
roles that covers the work's real decision and risk boundaries.

## Role is not deployment authority

A role describes purpose, outputs, judgment, and escalation. It does not grant
credentials, data access, action authority, or approval rights.

Keep these deployment choices independent:

- Model or capability tier.
- Information-access tier.
- Action and autonomy tier.
- One-shot, scheduled, event-driven, or continuous operation.
- Self-check, sampled, independent, or qualified-human assurance.

A stronger model receives no automatic increase in authority. A lower-cost or
local model receives no reduction in professional standing or control
obligations.

## Deprecated names

`qa`, `deliverylead`, and `cicd` remain resolvable only as migration adapters.
See the [full catalog](README.md#deprecated) for replacements.
