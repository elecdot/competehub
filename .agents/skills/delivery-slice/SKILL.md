---
name: delivery-slice
description: Deliver one focused CompeteHub implementation, bug fix, test, documentation, or process slice from issue or objective through impact analysis, TDD decision, code/docs changes, validation, and PR-ready summary.
---

# Delivery Slice

Deliver one focused CompeteHub change without broadening scope.

## 1. Understand The Slice

Read:

- `AGENTS.md`
- `docs/project_workflow.md`
- `README-GIT.md`
- the linked issue, Feature PRD, or user objective
- relevant product, API, data, architecture, technical, report, or app README docs

Completion criterion: scope, out-of-scope, affected surfaces, and validation commands are known.

## 2. Check Readiness

If acceptance criteria, scope, or validation are missing, define them before editing. If the slice is too broad, split it or propose follow-up issues.

Completion criterion: the work can be implemented and reviewed as one logical change.

## 3. Decide The Test Strategy

Use TDD when practical for bugs, backend rules, API validation, auth/permission behavior, state transitions, reminders, subscriptions, recommendations, and review/publication workflows.

For docs-only, process-only, exploratory, or visual-only work without a test harness, state the manual validation path.

Completion criterion: automated test-first, automated-after, or manual validation is explicitly chosen with a reason.

## 4. Implement And Sync Contracts

Make the smallest passing change. Keep public contracts synchronized:

- API -> `docs/api_spec.md`
- Data model or states -> `docs/data_model.md`
- Product behavior -> `docs/PRD.zh.md` or `docs/prds/features/*`
- Architecture or technical design -> `docs/architecture.md`, `docs/tech_spec.zh.md`, or ADR
- Course deliverable -> `docs/reports/*`
- New, moved, or removed docs page -> `mkdocs.yml`

Completion criterion: no affected public behavior or document page is left unsynchronized without an explicit reason.

## 5. Validate

Run the narrowest useful check while developing, then all relevant checks before handoff:

- Backend: `just api-test`, `just api-lint`, `just api-format`
- Frontend: `just web-lint`, `just web-build`
- Docs: `just docs-build`
- Infrastructure: `just infra-config`
- Broad shared change: `just check`

Completion criterion: validation output or skipped-check reasons are ready to report.

## 6. Prepare The PR Summary

Produce:

- Summary
- Validation
- Docs Impact
- Risk
- Follow-up

Preview and wait for confirmation before editing GitHub PR bodies, comments, labels, or issue state.
