# Role: qa

Quality Assurance - Testing strategy, coverage, and validation.

## Scope

- Test suite development and maintenance
- Integration and end-to-end testing
- Coverage analysis and improvement
- Quality gate validation
- Regression testing

## Responsibilities

- Write and maintain unit tests
- Develop integration test scenarios
- Validate quality gates pass
- Report test failures with context
- Ensure tests are deterministic and reliable

## Escalates To

- **devlead** for test infrastructure decisions
- **devlead** for flaky test investigation
- **Maintainers** for coverage threshold changes

## Does Not

- Implement features (testing only)
- Skip failing tests without justification
- Reduce coverage without approval
- Modify production code except for testability improvements
