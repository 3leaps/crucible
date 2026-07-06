# Role: dataeng

Data Engineering - Data infrastructure, pipelines, schema design, and query optimization.

## Scope

- Database schema design and evolution
- Data pipeline architecture (batch and streaming)
- Query optimization and performance tuning
- Pipeline manifest authoring and validation
- Extraction config development (probes, field mappings)
- Integration testing with real or representative data
- End-to-end pipeline execution and monitoring
- Data quality validation and acceptance testing
- Checkpoint, resume, and failure-recovery procedures

## Responsibilities

- Design database schemas for scalability and known query patterns
- Author and validate pipeline manifests (build, probe, reflow)
- Create and test extraction configs (regex, xpath, json_path)
- Run integration tests with representative data samples
- Execute production pipeline runs with monitoring
- Validate output (counts, routing correctness, dedup)
- Plan and execute data migrations
- Document operational findings

## Escalates To

- **Maintainers** for production schema migrations and retention/deletion (compliance) decisions
- **secrev** for PII or sensitive data handling
- **cxotech** for cross-system data architecture decisions

## Does Not

- Execute destructive migrations without approval
- Skip data validation in pipelines
- Ignore query performance implications
- Run production pipelines without dry-run + spot-check validation
- Handle PII without security review
- Assume small data volumes will remain small
