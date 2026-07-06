# Role Catalog

Baseline role prompts for AI agent sessions.

**Schema**: [`role-prompt.schema.json`](../../../schemas/agentic/v0/role-prompt.schema.json)

## Quick Reference by Timeline

| Timeline               | Roles               | Use When                                                       |
| ---------------------- | ------------------- | -------------------------------------------------------------- |
| **Minutes - Hours**    | devlead, devrev, qa | Writing code, reviewing changes, fixing bugs                   |
| **Days - Week**        | dispatch, secrev    | Session handoffs, security reviews, coordination               |
| **Sprint (1-4w)**      | deliverylead        | Sprint planning, delivery coordination                         |
| **Quarter (3mo)**      | releng, prodmktg    | Release planning, marketing campaigns, roadmaps                |
| **Strategic (6-18mo)** | cxotech, entarch    | Architecture decisions, product direction, cross-repo strategy |

## Role Categories

| Category   | Purpose                              | Roles                                    |
| ---------- | ------------------------------------ | ---------------------------------------- |
| agentic    | Implementation and creation          | devlead, infoarch, prodmktg, dataeng     |
| automation | Pipeline and release automation      | cicd, releng                             |
| review     | Quality, security, and correctness   | devrev, qa, secrev                       |
| governance | Strategy, coordination, architecture | dispatch, cxotech, deliverylead, entarch |

## Process Domains

Roles are organized across these business process domains:

| Domain         | Description                              | Primary Roles                        |
| -------------- | ---------------------------------------- | ------------------------------------ |
| development    | Code creation, testing, implementation   | devlead, devrev, qa, secrev, dataeng |
| analytics      | Data infrastructure, pipelines, queries  | dataeng                              |
| delivery       | Release, deployment, project management  | cicd, releng, deliverylead           |
| governance     | Strategy, coordination, architecture     | dispatch, cxotech, entarch           |
| strategy       | Long-term decisions, product direction   | cxotech, prodmktg, entarch           |
| architecture   | System design, pattern selection         | cxotech, infoarch, entarch           |
| coordination   | Session handoff, task routing            | dispatch, deliverylead               |
| marketing      | Brand, messaging, positioning            | prodmktg                             |
| documentation  | Schema governance, information structure | infoarch                             |
| security       | Vulnerability review, infosec            | secrev                               |
| quality        | Testing, validation, review              | devrev, qa                           |
| implementation | Code writing, feature delivery           | devlead                              |

## Available Roles

Roles carry a **tier** — default guidance, not a mandate; adopting repos may re-tier (see
[PDR-0003](../../../docs/decisions/PDR-0003-role-portfolio-tiering.md)). **core** = always-on
default spine; **supplemental** = adopt by need; **deprecated** = retired.

| Role                                                | Slug           | Tier         | Category   | Domains                            | Timeline       | Purpose                                            |
| --------------------------------------------------- | -------------- | ------------ | ---------- | ---------------------------------- | -------------- | -------------------------------------------------- |
| [Development Lead](devlead.yaml)                    | `devlead`      | core         | agentic    | development, implementation        | Hours-Days     | Implementation, architecture                       |
| [Development Reviewer](devrev.yaml)                 | `devrev`       | core         | review     | development, quality               | Hours-Days     | Code review, four-eyes audit                       |
| [Security Review](secrev.yaml)                      | `secrev`       | core         | review     | development, security              | Days-Week      | Security analysis, vulnerabilities                 |
| [Chief Experience Technology Officer](cxotech.yaml) | `cxotech`      | core         | governance | strategy, architecture, product    | Strategic      | Strategic fulcrum for product-architecture         |
| [Quality Assurance](qa.yaml)                        | `qa`           | supplemental | review     | development, quality               | Hours-Week     | Testing, validation                                |
| [Enterprise Architect](entarch.yaml)                | `entarch`      | supplemental | governance | governance, architecture, strategy | Strategic      | Cross-repo architecture coherence                  |
| [Information Architect](infoarch.yaml)              | `infoarch`     | supplemental | agentic    | development, documentation         | Days-Sprint    | Documentation, schemas                             |
| [Data Engineering](dataeng.yaml)                    | `dataeng`      | supplemental | agentic    | development, analytics             | Hours-Sprint   | Data infrastructure, pipelines, query optimization |
| [Release Engineering](releng.yaml)                  | `releng`       | supplemental | automation | delivery, development              | Quarter        | Versioning, releases                               |
| [Product Marketing](prodmktg.yaml)                  | `prodmktg`     | supplemental | agentic    | delivery, marketing                | Quarter        | Branding, messaging, personas                      |
| [Dispatch Coordinator](dispatch.yaml)               | `dispatch`     | supplemental | governance | coordination, governance           | Days-Sprint    | Cross-session coordination                         |
| [Delivery Lead](deliverylead.yaml)                  | `deliverylead` | supplemental | governance | coordination, delivery             | Sprint-Quarter | Project lifecycle, sprint coordination             |
| [CI/CD Automation](cicd.yaml)                       | `cicd`         | deprecated   | automation | automation, delivery               | —              | Retired — use `releng` + `devlead`                 |

## When to Use Which Role

### By Work Phase

| Phase                          | Primary Role     | Escalation                           | Timeline      |
| ------------------------------ | ---------------- | ------------------------------------ | ------------- |
| **Emergency fix**              | devlead          | secrev (security)                    | Minutes-hours |
| **Feature implementation**     | devlead          | devrev (review)                      | Hours-days    |
| **Bug investigation**          | devlead → devrev | qa (validation)                      | Days          |
| **Security review**            | secrev           | human maintainers                    | Days-week     |
| **Session handoff**            | dispatch         | deliverylead (project context)       | Days          |
| **Sprint planning**            | deliverylead     | cxotech (priority conflicts)         | 1-4 weeks     |
| **Pipeline setup**             | releng + devlead | maintainers (secrets/deploy)         | Days-week     |
| **Release prep**               | releng           | cxotech (strategic timing)           | Week          |
| **Architecture decision**      | cxotech          | human maintainers                    | Weeks-months  |
| **Documentation**              | infoarch         | prodmktg (messaging)                 | Days-sprint   |
| **Data pipeline / schema**     | dataeng          | secrev (PII), cxotech (cross-system) | Hours-sprint  |
| **Multi-project coordination** | deliverylead     | dispatch (session routing)           | Sprint        |
| **Cross-repo strategy**        | cxotech          | entarch (ecosystem-wide)             | Quarter       |

### By Decision Type

| Decision Scope                  | Role             | Typical Timeline |
| ------------------------------- | ---------------- | ---------------- |
| Code pattern selection          | devlead          | Minutes-hours    |
| Session routing                 | dispatch         | Minutes          |
| Sprint commitment               | deliverylead     | 1-4 weeks        |
| Release versioning              | releng           | Quarter          |
| Feature brief approval          | cxotech          | Weeks            |
| Product direction               | cxotech          | Months           |
| Ecosystem architecture          | entarch          | Quarter          |
| Security vulnerability handling | secrev           | Hours-days       |
| Test strategy                   | qa               | Sprint           |
| Pipeline architecture           | releng + devlead | Days-week        |

### By Complexity Level

- **Simple coding task**: devlead
- **Multi-step feature**: devlead → devrev → qa (sequential)
- **Cross-role conflict**: cxotech resolves
- **Multi-session delivery**: deliverylead coordinates, dispatch routes sessions
- **Cross-project dependencies**: entarch evaluates architecture impact, deliverylead sequences
- **Strategic architecture decision**: cxotech evaluates, deliverylead sequences, devlead implements

## Timeline Contrast: Governance Roles

The governance roles operate at different time horizons:

| Role             | Timeline           | Scope                  | Key Question                               |
| ---------------- | ------------------ | ---------------------- | ------------------------------------------ |
| **dispatch**     | Minutes - Days     | Session handoff        | "What context does the next session need?" |
| **deliverylead** | Sprint - Quarter   | Project coordination   | "When do we ship this?"                    |
| **entarch**      | Quarter+           | Ecosystem architecture | "What breaks or drifts across repos?"      |
| **cxotech**      | Strategic (6-18mo) | Product-architecture   | "Should we build this? Which pattern?"     |

**Relationship**: Cxotech approves feature briefs → Entarch checks cross-repo architecture consequences → Deliverylead sequences the work → Dispatch routes individual sessions

## Usage

Reference roles by slug in `AGENTS.md`:

```yaml
roles:
  - slug: devlead
    source: config/agentic/roles/devlead.yaml
  - slug: deliverylead
    source: config/agentic/roles/deliverylead.yaml
  - slug: entarch
    source: config/agentic/roles/entarch.yaml
  - slug: cxotech
    source: config/agentic/roles/cxotech.yaml
```

## Schema Validation

All role files conform to the [role-prompt schema](../../../schemas/agentic/v0/role-prompt.schema.json).

Validate with:

```bash
# Using goneat
goneat validate data --schema-file schemas/agentic/v0/role-prompt.schema.json --data config/agentic/roles/deliverylead.yaml

# Or validate all
make lint-config
```

## Extending Roles

To extend a baseline role:

```yaml
slug: devlead
extends: https://schemas.3leaps.dev/roles/devlead.yaml
# Add or override fields
scope:
  - ...additional scope items...
```

## New Roles

When adding roles to this catalog:

1. **Determine timeline**: Minutes, Days, Sprint, Quarter, or Strategic
2. **Assign category**: agentic | automation | review | governance
3. **Assign domains**: 1-3 process domains (see table above)
4. **Define escalation paths**: Which roles does this escalate to/from?
5. **Validate**: Run `make lint-config` before committing
6. **Update README**: Add to Available Roles table with timeline
