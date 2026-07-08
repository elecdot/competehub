---
name: tdd
description: Use CompeteHub's TDD workflow for testable behavior changes, bug regressions, backend rules, API validation, auth/permission checks, state transitions, reminders, subscriptions, recommendations, and review/publication workflows.
---

# TDD

Use this skill as a thin wrapper over CompeteHub's durable testing docs, with
behavior-first TDD guardrails. Do not duplicate the full project testing policy.

## Workflow

1. Read `docs/agents/tdd.md`.

   Completion criterion: the change is classified as test-first, automated-after,
   or manual validation.

2. Read `docs/testing.md`.

   Completion criterion: the relevant test layer, validation command, manual
   acceptance path, and non-functional evidence are known.

3. For implementation slices, use `delivery-slice`.

   Completion criterion: scope, public contract sync, validation, and PR reporting
   are handled through the delivery workflow.

4. Choose the public seam before writing a test.

   A seam is the public boundary where behavior is observed: service method, API
   route, repository contract, UI route, command, or documented manual workflow.

   Completion criterion: name the seam and the observable behavior under test.

5. Write behavior tests, not implementation tests.

   Good tests verify behavior through public interfaces. They should read like a
   specification and survive refactoring.

   Avoid:
   - Implementation-coupled tests: private methods, internal collaborators, or
     database side channels when the public API is the real contract.
   - Tautological tests: assertions that recompute the expected value using the
     same logic as the implementation.
   - Horizontal slicing: writing many speculative tests before the first minimal
     implementation.

6. Follow one vertical TDD cycle at a time.

   - Red: add or update one failing test for one observable behavior.
   - Green: make the smallest implementation change that passes.
   - Review/refactor: clean up only with tests passing, without expanding scope.

   Completion criterion: report the failing test added, the minimal implementation
   change, and the final validation command.

7. Run the narrow relevant command first, then broader checks when the affected
   surface requires it.

   Completion criterion: validation output or skipped-check reasons are ready for
   the handoff or PR summary.

## Guardrails

- Do not delete, weaken, skip, or rewrite tests just to make a change pass.
- Do not add test dependencies unless the issue or user request explicitly includes
  that scope.
- If automated tests are skipped or deferred, state why and provide the manual
  validation path.
- Keep public contracts synchronized through `delivery-slice`.
- When validation fails, report the command, failure summary, likely cause, and
  next suggested fix.
