# Role Catalog

**Canonical URL** (hosted site planned — v0.1.x): `https://crucible.3leaps.dev/catalog/roles`

Baseline role prompts for AI agent sessions in 3leaps repositories.

## Usage

Repos configure roles in `AGENTS.md` using a roles table:

```markdown
## Roles

| Role      | Source                                                                 | Customization    |
| --------- | ---------------------------------------------------------------------- | ---------------- |
| `devlead` | [crucible baseline](https://crucible.3leaps.dev/catalog/roles/devlead) | —                |
| `qa`      | [crucible baseline](https://crucible.3leaps.dev/catalog/roles/qa)      | See [below](#qa) |
| `proxy`   | `roles/proxy.md`                                                       | Project-specific |
```

### Source Options

1. **Crucible baseline** - Use standard role as-is (link to this catalog)
2. **Inline section** - Extend in `AGENTS.md` with `## Role: <identifier>` section
3. **Separate file** - Define in `roles/<identifier>.md` for complex roles

### Customization Patterns

**No customization** - Reference crucible baseline:

```markdown
| `devlead` | [crucible baseline](https://crucible.3leaps.dev/catalog/roles/devlead) | — |
```

**Inline extension** - Add section in AGENTS.md:

```markdown
| `qa` | [crucible baseline](https://crucible.3leaps.dev/catalog/roles/qa) | See [below](#role-qa) |

...

## Role: qa

Extends [crucible qa baseline](https://crucible.3leaps.dev/catalog/roles/qa).

### Additional Scope

- Integration tests for proxy modes
- Session artifact validation
```

**Separate file** - For complex project-specific roles:

```markdown
| `proxy` | `roles/proxy.md` | Project-specific |
```

## Available Roles

Each role carries a **tier** — default guidance, not a mandate. A repo that adopts this
catalog may re-tier (see [PDR-0003](../../decisions/PDR-0003-role-portfolio-tiering.md)).
The full registry, including each role's tier, lives in
[`config/agentic/roles/`](../../../config/agentic/roles/README.md).

### Core — the always-on default spine

| Role                                              | Identifier | Typical Scope                                                                     |
| ------------------------------------------------- | ---------- | --------------------------------------------------------------------------------- |
| [Development Lead](devlead.md)                    | `devlead`  | Implementation, architecture                                                      |
| [Development Reviewer](devrev.md)                 | `devrev`   | Code review, four-eyes audit                                                      |
| [Security Review](secrev.md)                      | `secrev`   | Security analysis, vulnerability review                                           |
| [Chief Experience Technology Officer](cxotech.md) | `cxotech`  | Strategic fulcrum: product-architecture decisions, brief/ADR approval, tie-breaks |

### Supplemental — adopt by need

| Role                                 | Identifier     | Typical Scope                                                       |
| ------------------------------------ | -------------- | ------------------------------------------------------------------- |
| [Quality Assurance](qa.md)           | `qa`           | Testing, validation, quality gates                                  |
| [Enterprise Architect](entarch.md)   | `entarch`      | Cross-repo architecture alignment, standards propagation            |
| [Information Architect](infoarch.md) | `infoarch`     | Documentation, structure, standards                                 |
| [Data Engineering](dataeng.md)       | `dataeng`      | Data infrastructure, pipelines                                      |
| [Release Manager](releng.md)         | `releng`       | Versioning, releases, changelogs                                    |
| [Product Marketing](prodmktg.md)     | `prodmktg`     | Product positioning, audience understanding, messaging              |
| [Dispatcher](dispatch.md)            | `dispatch`     | Cross-session coordination, message routing                         |
| [Delivery Lead](deliverylead.md)     | `deliverylead` | Project lifecycle, sprint coordination — large multi-sprint efforts |

### Deprecated

| Role                        | Identifier | Note                                                                                |
| --------------------------- | ---------- | ----------------------------------------------------------------------------------- |
| [CI/CD Automation](cicd.md) | `cicd`     | Retired — real-world use favored `releng` supplementing `devlead` for complex CI/CD |

## Creating Custom Roles

Project-specific roles (e.g., `proxy`, `tui`, `crawler`) should:

1. Use lowercase identifier (kebab-case if multi-word)
2. Follow the same structure as baseline roles
3. Document in `AGENTS.md` roles table or `roles/` directory
4. Define clear scope boundaries and escalation paths

## Role Prompt Structure

Each role prompt follows this structure:

```markdown
# Role: <identifier>

<One-line description>

## Scope

- What this role owns
- Boundaries of responsibility

## Responsibilities

- Specific tasks and duties
- Quality expectations

## Escalates To

- When to escalate
- Who to escalate to

## Does Not

- Explicit exclusions
- Out-of-scope items
```
