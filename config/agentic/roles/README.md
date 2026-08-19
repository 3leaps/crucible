# Role Catalog

Canonical reusable role prompts for AI agent sessions.

**Schema**: [`role-prompt.schema.json`](../../../schemas/agentic/v0/role-prompt.schema.json)

Roles carry a portfolio **tier**. `core` is the default operating spine,
`supplemental` is adopted when the work needs it, and `deprecated` retains a
superseded role and its migration path. Tier is portfolio guidance, not a
measure of a role's importance or authority.

## Operating model

The default implementation loop is:

`cxotech chooses product direction ↔ entarch protects technical coherence → projectmgr prepares work → dispatch routes → devlead implements → devrev reviews`

`secrev` joins wherever security or trust boundaries warrant it. Supplemental
roles provide specialist work without changing the accountable decision owner.

For monitoring and advisory work:

`watcher observes → analyst explains → strategist recommends → accountable role decides`

For privileged human coordination, `delegate` assists only through explicit,
principal-specific grants. Access, action authority, and disclosure authority
are evaluated separately; multiple principals' grants remain compartmented.

## Core roles

| Role                                                | Slug      | Category   | Purpose                                                   |
| --------------------------------------------------- | --------- | ---------- | --------------------------------------------------------- |
| [Development Lead](devlead.yaml)                    | `devlead` | agentic    | Implementation and self-verification                      |
| [Development Reviewer](devrev.yaml)                 | `devrev`  | review     | Independent correctness and contract review               |
| [Security Review](secrev.yaml)                      | `secrev`  | review     | Security, privacy, supply-chain, and trust review         |
| [Chief Experience Technology Officer](cxotech.yaml) | `cxotech` | governance | Product-side direction and product-architecture decisions |

## Supplemental roles

| Role                                                  | Slug         | Category   | Purpose                                                             |
| ----------------------------------------------------- | ------------ | ---------- | ------------------------------------------------------------------- |
| [Enterprise Architect](entarch.yaml)                  | `entarch`    | governance | Technology-side architecture and contract coherence                 |
| [UX Developer](uxdev.yaml)                            | `uxdev`      | agentic    | User-centered interactive design and implementation                 |
| [Data Engineering](dataeng.yaml)                      | `dataeng`    | analytics  | Data architecture, pipelines, quality, lineage, and operations      |
| [Product Marketing](prodmktg.yaml)                    | `prodmktg`   | marketing  | Positioning, messaging, and audience narrative                      |
| [Analyst](analyst.yaml)                               | `analyst`    | analytics  | Evidence, methods, uncertainty, and decision-ready findings         |
| [Strategist](strategist.yaml)                         | `strategist` | consulting | Strategic diagnosis, foresight, choices, and advice                 |
| [Watcher](watcher.yaml)                               | `watcher`    | automation | Bounded monitoring, routine triage, and escalation                  |
| [Delegated Assistant](delegate.yaml)                  | `delegate`   | governance | Compartmented assistance under explicit principal grants            |
| [Security and Infrastructure Operations](secops.yaml) | `secops`     | automation | Privileged asset curation and security operations                   |
| [Project Manager](projectmgr.yaml)                    | `projectmgr` | governance | Tasking, project state, dependencies, milestones, and risk          |
| [Dispatch Coordinator](dispatch.yaml)                 | `dispatch`   | governance | Estate routing, handoffs, coordination health, and operator tooling |
| [Information Architect](infoarch.yaml)                | `infoarch`   | agentic    | Documentation, schemas, and information structure                   |
| [Release Engineering](releng.yaml)                    | `releng`     | automation | Complex release, publication, signing, provenance, and CI systems   |

Draft roles remain supplemental but should not be represented as approved until
their `status` changes after review.

## Deprecated roles

| Role                               | Slug           | Replacement                                                                 |
| ---------------------------------- | -------------- | --------------------------------------------------------------------------- |
| [Quality Assurance](qa.yaml)       | `qa`           | `devrev` plus task-specific acceptance criteria; `devlead` implements tests |
| [Delivery Lead](deliverylead.yaml) | `deliverylead` | `projectmgr`                                                                |
| [CI/CD Automation](cicd.yaml)      | `cicd`         | `devlead`; add `releng` only for complex release systems                    |

Deprecated prompts retain migration scope, escalation, and exclusions but do
not declare independent outputs or authority. Their `replaced_by` entries are
the canonical migration path.

## Selection guide

| Need                                     | Primary role | Escalation or partner                              |
| ---------------------------------------- | ------------ | -------------------------------------------------- |
| Implement or fix software                | devlead      | devrev; secrev when security-sensitive             |
| Review correctness or test strategy      | devrev       | devlead for intent; secrev for security            |
| Make a product bet                       | cxotech      | entarch for technical consequences                 |
| Protect shared architecture or contracts | entarch      | cxotech for product-priority conflicts             |
| Design and implement an interface        | uxdev        | devlead, cxotech, secrev                           |
| Build or operate data systems            | dataeng      | analyst, entarch, secrev                           |
| Produce decision-support evidence        | analyst      | independent assurance; strategist for implications |
| Develop strategic choices                | strategist   | analyst, cxotech, entarch                          |
| Monitor a bounded surface                | watcher      | dispatch, analyst, secrev                          |
| Assist with privileged communications    | delegate     | principals, secrev, projectmgr                     |
| Operate privileged infrastructure        | secops       | secrev, entarch, maintainers                       |
| Plan and control project work            | projectmgr   | dispatch for routing                               |
| Route sessions and maintain coordination | dispatch     | projectmgr or accountable owner                    |
| Engineer a complex release system        | releng       | devlead, secrev, maintainers                       |

## Usage

Reference roles by slug in `AGENTS.md`:

```yaml
roles:
  - slug: devlead
    source: config/agentic/roles/devlead.yaml
  - slug: projectmgr
    source: config/agentic/roles/projectmgr.yaml
  - slug: entarch
    source: config/agentic/roles/entarch.yaml
  - slug: cxotech
    source: config/agentic/roles/cxotech.yaml
```

## Validation

```bash
goneat validate data \
  --schema-file schemas/agentic/v0/role-prompt.schema.json \
  --data config/agentic/roles/projectmgr.yaml

make lint-config
```

## Extension and specialization

Canonical prompts are complete documents. In `v0`, `extends` records provenance
only; it does not define or perform a merge.

Prefer, in order:

1. Reference the canonical role and keep repository instructions in `AGENTS.md`.
2. Vendor a pinned canonical role without hand-editing the vendored copy.
3. Publish a complete specialized role when the distinction is durable and
   reusable.

Do not maintain an unpinned full fork under an `extends` declaration.

## Adding a role

1. Establish a decision boundary distinct from existing roles.
2. Name expected outputs and explicit authority.
3. Assign tier, category, and one to three process domains.
4. Define escalation and out-of-scope behavior.
5. Validate the prompt and update this catalog.
6. Leave new roles in `draft` until practical review supports approval.
