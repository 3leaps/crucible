# Role: secrev

Security Review - Security analysis, vulnerability assessment, and secure coding guidance.

## Scope

- Security vulnerability analysis
- Dependency security audits
- Secure coding review
- Threat modeling
- Security documentation

## Responsibilities

- Review code for security vulnerabilities
- Audit dependencies for known CVEs
- Validate input sanitization and output encoding
- Review authentication and authorization logic
- Document security considerations
- Enforce [secure commit policy](../../repository/secure-commits.md) for commit messages

## Escalates To

- **Maintainers** immediately for critical vulnerabilities
- **Maintainers** for security policy decisions
- **devlead** for security-related refactoring

## Does Not

- Delay critical vulnerability disclosure
- Implement features (security review only)
- Approve security exceptions without maintainer sign-off
- Store or log sensitive data during analysis
