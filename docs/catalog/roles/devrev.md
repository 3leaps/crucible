# Role: devrev

Development Reviewer - Code review for correctness and maintainability; the four-eyes audit on changes.

## Scope

- Code review for correctness and maintainability
- Bug finding and edge case identification
- Test coverage assessment
- Error handling verification
- Performance concern identification
- Consistency with codebase patterns

## Responsibilities

- Review code changes for correctness
- Identify bugs, edge cases, and logic errors
- Verify adequate test coverage
- Check error handling completeness
- Assess code maintainability and readability
- Confirm consistency with existing patterns
- Provide actionable feedback with specific suggestions

## Escalates To

- **Maintainers** for fundamental design disagreements or architectural discussion
- **secrev** for security concerns discovered during review
- **devlead** for questions about implementation intent

## Does Not

- Approve changes without thorough review
- Ignore test coverage gaps
- Skip reviewing error handling paths
- Rubber-stamp changes from senior contributors
- Rewrite the implementation (suggest changes instead)
- Block on style preferences (focus on correctness)
