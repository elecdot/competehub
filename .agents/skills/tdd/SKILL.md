---
name: tdd
description: Use CompeteHub's TDD workflow for testable behavior changes, bug regressions, backend rules, API validation, auth/permission checks, state transitions, reminders, subscriptions, recommendations, and review/publication workflows.
---

# TDD

Use this skill as a thin wrapper over CompeteHub's durable testing docs.
Do not duplicate the full TDD policy here.

## Workflow

1. Read `docs/agents/tdd.md`.

   Completion criterion: you can state whether this change should use test-first,
   automated-after, or manual validation.

2. Read `docs/testing.md` to choose the relevant test layer, validation command,
   manual acceptance path, and non-functional evidence.

   Completion criterion: the relevant layer and evidence are named before editing.

3. For implementation slices, use `delivery-slice` for scope, contract sync,
   validation, and PR-ready reporting.

   Completion criterion: scope, affected surfaces, and validation reporting are
   handled by the delivery slice, not redefined here.

4. Choose the validation mode explicitly:

   - Test-first: observable behavior changes with a reasonable automated surface.
   - Automated-after: automated coverage is valuable, but writing the test first is
     impractical; explain why.
   - Manual validation: docs-only, process-only, exploratory, visual-only without a
     test harness, formatting-only, tiny copy, or other non-behavioral changes.

   Completion criterion: skipped or deferred automated tests have a reason and a
   manual or automated follow-up path.

5. For TDD work, follow red-green-refactor:

   - Red: add or update the failing test that captures the behavior.
   - Green: make the smallest change that passes.
   - Refactor: clean up with tests still passing.

   Completion criterion: the report identifies the red test, implementation change,
   and final validation command.

6. Run the narrow relevant command first, then broader checks when the affected
   surface requires it.

   Completion criterion: validation output or blocked-check reasons are ready to
   paste into the handoff or PR summary.

## Guardrails

- Preserve test strength: do not delete, weaken, skip, or rewrite tests just to
  make a change pass.
- Do not add test dependencies unless the issue or user request explicitly includes
  that scope.
- Keep public contracts synchronized through `delivery-slice`.
- When validation fails, report the command, failure summary, likely cause, and
  next suggested fix.
