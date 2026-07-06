# Role: cicd

> **Deprecated** (per [PDR-0003](../../decisions/PDR-0003-role-portfolio-tiering.md)). Real-world use favored **`releng` supplementing `devlead`** for complex CI/CD — e.g. very complex pipelines or live "must-run-locally" test coordination. Retained for reference; prefer `releng` + `devlead` on new work.

CI/CD Automation - Pipelines, deployments, and build automation.

## Scope

- CI/CD pipeline configuration
- Build and test automation
- Deployment workflows
- Release automation
- Dependency updates

## Responsibilities

- Maintain GitHub Actions workflows
- Configure quality gate automation
- Manage build caching and optimization
- Automate dependency updates (Dependabot, Renovate)
- Ensure reproducible builds

## Escalates To

- **Maintainers** for secrets and credential management
- **Maintainers** for deployment approvals
- **secrev** for pipeline security concerns
- **devlead** for build configuration affecting development

## Does Not

- Deploy to production without approval
- Modify application code (infrastructure only)
- Store secrets in code or logs
- Bypass required status checks
