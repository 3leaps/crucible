# Role Catalog

**Canonical URL** (planned): `https://crucible.3leaps.dev/catalog/roles`

Reusable, schema-validated role prompts for supervised and autonomous agent
sessions. The machine-readable source is
[`config/agentic/roles/`](../../../config/agentic/roles/README.md).

Start with the [active role portfolio](active-roles.md) for a human- and
agent-readable selection guide that excludes deprecated roles from the working
set.

## Portfolio

### Core

- [`devlead`](../../../config/agentic/roles/devlead.yaml) — implementation
- [`devrev`](../../../config/agentic/roles/devrev.yaml) — independent correctness review
- [`secrev`](../../../config/agentic/roles/secrev.yaml) — security review
- [`cxotech`](../../../config/agentic/roles/cxotech.yaml) — product-side direction

### Supplemental

- [`entarch`](../../../config/agentic/roles/entarch.yaml) — technology-side coherence
- [`uxdev`](../../../config/agentic/roles/uxdev.yaml) — interactive experience
- [`dataeng`](../../../config/agentic/roles/dataeng.yaml) — data systems
- [`prodmktg`](../../../config/agentic/roles/prodmktg.yaml) — positioning and messaging
- [`analyst`](../../../config/agentic/roles/analyst.yaml) — evidence and findings
- [`strategist`](../../../config/agentic/roles/strategist.yaml) — strategic choices
- [`watcher`](../../../config/agentic/roles/watcher.yaml) — bounded monitoring
- [`delegate`](../../../config/agentic/roles/delegate.yaml) — privileged, compartmented assistance
- [`secops`](../../../config/agentic/roles/secops.yaml) — privileged infrastructure and asset operations
- [`projectmgr`](../../../config/agentic/roles/projectmgr.yaml) — project control
- [`dispatch`](../../../config/agentic/roles/dispatch.yaml) — estate routing
- [`infoarch`](../../../config/agentic/roles/infoarch.yaml) — information structure
- [`releng`](../../../config/agentic/roles/releng.yaml) — complex release systems

### Deprecated

- [`qa`](../../../config/agentic/roles/qa.yaml) — use `devrev` plus task acceptance criteria
- [`deliverylead`](../../../config/agentic/roles/deliverylead.yaml) — use `projectmgr`
- [`cicd`](../../../config/agentic/roles/cicd.yaml) — use `devlead`; add `releng` only when warranted

Tier indicates default adoption, not status or authority. Consult each prompt's
`status`, `outputs`, `authority`, escalation paths, and exclusions.

## Product and technology actors

Long-running agent systems benefit from a durable product/technology pair:

- `cxotech` acts on the product side: problem choice, user value, bets, and priority.
- `entarch` acts on the technology side: system boundaries, contracts, compatibility,
  and architectural integrity.

They are peers with different decision domains. Human maintainers retain
authority for consequential organizational, financial, public, and breaking
commitments.

`delegate` is the principal-facing coordination role. It receives no authority
from the role alone: each deployment requires explicit, compartmented grants
for information access, actions, and disclosure.

`secops` is the asset-facing privileged operator. It receives operational
authority only through an explicit custodianship grant and remains separate
from independent security review by `secrev`.

## Adoption

Reference a canonical role from `AGENTS.md`, then keep repository commands and
local constraints in repository guidance. If vendoring, pin the source and do
not hand-maintain a divergent full copy.

The `extends` field is provenance-only in the experimental `v0` schema; it does
not merge role documents.

See the [machine-readable catalog](../../../config/agentic/roles/README.md) for
selection guidance and validation commands.
