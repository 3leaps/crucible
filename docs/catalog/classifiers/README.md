# Classifiers Catalog

**Canonical URL** (hosted site planned — v0.1.x): `https://crucible.3leaps.dev/catalog/classifiers`

Index of Crucible classifier dimensions and their canonical sources.

## How To Use This Catalog

- Use the narrative standards to decide what a value means.
- Use the dimension definition JSON for machine validation, UI dropdowns, and automation.
- Vendor `config/classifiers/` alongside `schemas/classifiers/` when you need offline or pinned behavior.

Missing classification is a policy error. Use explicit `unknown` until classification is complete.

## Dimensions

| Dimension                   | Key                   | Standard                                               | Definition                                                         |
| --------------------------- | --------------------- | ------------------------------------------------------ | ------------------------------------------------------------------ |
| Data Sensitivity            | `sensitivity`         | `docs/standards/data-sensitivity-classification.md`    | `config/classifiers/dimensions/sensitivity.dimension.json`         |
| Volatility & Update Cadence | `volatility`          | `docs/standards/volatility-classification.md`          | `config/classifiers/dimensions/volatility.dimension.json`          |
| Access Tier                 | `access-tier`         | `docs/standards/access-tier-classification.md`         | `config/classifiers/dimensions/access-tier.dimension.json`         |
| Retention & Lifecycle       | `retention-lifecycle` | `docs/standards/retention-lifecycle-classification.md` | `config/classifiers/dimensions/retention-lifecycle.dimension.json` |
| Schema Stability            | `schema-stability`    | `docs/standards/schema-stability-classification.md`    | `config/classifiers/dimensions/schema-stability.dimension.json`    |
| Volume Tier                 | `volume-tier`         | `docs/standards/volume-tier-classification.md`         | `config/classifiers/dimensions/volume-tier.dimension.json`         |
| Velocity Mode               | `velocity-mode`       | `docs/standards/velocity-mode-classification.md`       | `config/classifiers/dimensions/velocity-mode.dimension.json`       |
| Agent Seat Class (draft) | `agent-seat-class` | `docs/standards/agent-interface-classification.md` | `config/classifiers/dimensions/agent-seat-class.dimension.json` |
| Agent Control Surface (draft) | `agent-control-surface` | `docs/standards/agent-interface-classification.md` | `config/classifiers/dimensions/agent-control-surface.dimension.json` |
| Agent Transport (draft) | `agent-transport` | `docs/standards/agent-interface-classification.md` | `config/classifiers/dimensions/agent-transport.dimension.json` |
| Agent Adapter Confidence (draft) | `agent-adapter-confidence` | `docs/standards/agent-interface-classification.md` | `config/classifiers/dimensions/agent-adapter-confidence.dimension.json` |

Agent classifier values have a closed, composable validation shape at
`schemas/classifiers/v0/agent-interface.schema.json`. It validates vocabulary,
not the subject's authority or the evidence behind a confidence assessment.

The companion [agent interface profiles](../../standards/agent-interface-profiles.md)
standard adds a separate revisioned shape at
`schemas/classifiers/v0/agent-interface-profile.schema.json` for protocol bindings,
continuity and delivery signal meanings. It reuses the value vocabularies without
changing their meaning. Profiles are declarations, not observations or grants.

## Framework Overview

See `docs/standards/classifiers-framework.md` for how the pieces fit together.
