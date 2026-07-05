# Test-Driven Development

This workflow applies to bug fixes, testable behavior changes, and new
features where an automated test surface exists or can reasonably be added.

## When To Use TDD

- Bug fixes: reproduce the bug with a failing test when practical.
- Backend business rules or state transitions: write or update tests before
implementation when practical.
- API validation, auth, and permission behavior: cover expected behavior before
implementation when practical.
- Reminder, subscription, recommendation, and review/publication workflows:
cover the critical state transition or regression path.
- New features: start from observable behavior, then implement the smallest code
needed to pass.

Manual validation is acceptable for pure documentation changes, template or
process-only changes, visual-only frontend work without a test harness,
formatting-only changes, CI metadata changes, small copy edits, and exploratory
spikes. They still require explicit validation.

## Workflow

1. Red: identify the relevant test surface and add or update a failing test.
2. Green: make the smallest implementation change that passes the test.
3. Refactor: clean up only after the test passes, keeping behavior covered.
4. Validate: run the narrow relevant command first, then broader checks when the change affects shared behavior.

Do not delete, weaken, skip, or rewrite existing tests to make a change pass unless the reason is explicit and tied to a corrected requirement.

## Validation Commands

- Backend behavior: `just api-test` and `just api-lint`.
- Frontend behavior: `just web-lint` and `just web-build`.
- Documentation behavior or navigation: `just docs-build`.
- Infrastructure behavior: `just infra-config`.

If a full command is too expensive or blocked, run the narrowest useful
alternative and state what remains unverified.

If automated tests are skipped for behavior changes, state why and provide the
manual validation path.

## Failure Reporting

When validation fails, report:

- The command that failed.
- The failure summary.
- Whether the failure appears caused by the current change or pre-existing state.
- The next suggested fix or investigation step.
