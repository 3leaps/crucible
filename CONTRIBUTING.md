# Contributing to 3leaps Crucible

Thank you for your interest in contributing to 3leaps Crucible!

## What is Crucible?

Crucible is the **Single Source of Truth (SSOT)** for policies, standards, and processes across 3leaps open source projects. It contains documentation and specifications - no runtime code.

| Repository            | Purpose                                    |
| --------------------- | ------------------------------------------ |
| `3leaps/crucible`     | Standards, policies, processes (this repo) |
| `3leaps/.github`      | PR templates, issue templates, workflows   |
| `3leaps/oss-policies` | Governance, legal, Code of Conduct         |

## How to Contribute

### Proposing Changes

1. **Open an issue** describing the change you'd like to make
2. **Reference existing Crucible patterns** where applicable
3. **Keep it simple** - repo-specific complexity belongs in the adopting repository

### Prerequisites

**bun is required** for 3leaps development:

```bash
curl -fsSL https://bun.sh/install | bash
```

### Making Changes

1. Fork the repository
2. Install dependencies: `make bootstrap`
3. Create a branch for your changes
4. Make your changes
5. Run quality checks: `make check`
6. Commit with proper attribution (see below)
7. Open a pull request

### Commit Style

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>
```

Types: `feat`, `fix`, `docs`, `refactor`, `chore`

See [docs/repository/commit-style.md](docs/repository/commit-style.md) for details.

### AI-Assisted Contributions

AI agents are welcome contributors under human supervision. If contributing via AI:

1. Read [AGENTS.md](AGENTS.md) for operational protocols
2. Follow attribution patterns in [docs/repository/agent-identity.md](docs/repository/agent-identity.md)
3. Include `Committer-of-Record` trailer identifying the supervising human
4. Ensure a human maintainer reviews before merge

### Quality Checks

Before submitting:

```bash
make check
```

This runs:

- Markdown/JSON formatting (prettier)
- YAML formatting (yamlfmt)
- YAML linting (yamllint)

## What We Accept

- Improvements to existing standards
- New standards that fill genuine gaps
- Corrections and clarifications
- Examples that help understanding

## What We Redirect

For complex, implementation-specific standards, keep the shared baseline thin and document local requirements in the adopting repository.

## Code of Conduct

- Project entrypoint: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Full policy source: [3leaps/oss-policies](https://github.com/3leaps/oss-policies)

## Security Policy

- Project entrypoint: [SECURITY.md](SECURITY.md)
- Full policy source: [3leaps/oss-policies](https://github.com/3leaps/oss-policies)

## License

By contributing, you agree that your contributions will be licensed under the same terms as the project (CC0 for documentation, MIT for code). See [LICENSE](LICENSE).
