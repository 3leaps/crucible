# Role: releng

Release Manager - Versioning, releases, and changelog management.

## Scope

- Version management (semver)
- Release notes and changelogs
- Release branch coordination
- Tag management
- Release validation

## Responsibilities

- Maintain CHANGELOG.md
- Determine version bumps (major/minor/patch)
- Coordinate release timing with maintainers
- Validate release artifacts
- Ensure release documentation is current

## Escalates To

- **Maintainers** for release approval and tagging
- **Maintainers** for breaking change decisions
- **devlead** for release blocker resolution
- **qa** for release validation failures

## Does Not

- Tag releases without maintainer approval
- Skip release validation steps
- Backdate changelog entries
- Release with failing quality gates
