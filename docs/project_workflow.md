# Project Delivery Workflow

This document defines how the team turns requirements into working software,
tests, documentation, reports, and demo-ready increments.

The short collaborator entry point is `CONTRIBUTING.md`. Agent behavior
requirements live in `AGENTS.md`.

## Operating Constraints

CompeteHub is a course project with a small team, short delivery window, and
agent-assisted coding. The workflow should stay light enough to use daily while
still preventing drift between code, product documents, technical documents, and
course reports.

The project should prioritize the current roadmap phase over speculative later
extensions. P4 ideas should not distort P1/P2 delivery.

## Workflow Summary

```text
Roadmap -> Feature PRD -> Issue -> Design Impact -> Code/Test -> PR -> Docs
```

Use the full flow for new features and behavior changes. Use a smaller flow for
bug fixes, documentation-only work, and process changes, but still keep the diff
focused and validate the affected surfaces.

## Source Of Truth

| Knowledge | Owning document |
|---|---|
| Canonical domain language | `CONTEXT.md` |
| Delivery phases and sequencing | `docs/roadmap.md` |
| Stable product boundary | `docs/PRD.zh.md` |
| Single-feature requirements | `docs/prds/features/*.md` |
| Architecture and runtime structure | `docs/architecture.md` |
| API contract | `docs/api_spec.md` |
| Data model and states | `docs/data_model.md` |
| Technical implementation design | `docs/tech_spec.zh.md` |
| Hard-to-reverse decisions | `docs/adr/` |
| Course reports and generated analysis | `docs/reports/` |
| Git workflow | `README-GIT.md` |
| Agent behavior contract | `AGENTS.md` |
| GitHub issue and PR fields | `.github/` templates |

Do not duplicate full rules across documents. Link to the owning document and
include only the short summary needed for the local context.

## Work Item Types

- Feature: a user-visible capability or behavior change. Use a Feature PRD
unless the change is very small and already specified.
- Bug: incorrect behavior. Reproduce with a failing test when practical.
- Task: documentation, CI, refactor, maintenance, or coordination work.
- Spike: time-boxed exploration. Record findings and follow-up decisions.
- Report work: course-deliverable updates under `docs/reports/`.

## Feature PRD Rules

`docs/PRD.zh.md` is the stable total PRD. Do not use `to-prd` or ad hoc feature
planning to overwrite it.

Feature PRDs live under `docs/prds/features/` and must use the local template.
They should align with:

- `docs/PRD.zh.md`
- `docs/roadmap.md`
- `docs/data_model.md`
- `docs/api_spec.md`
- `docs/tech_spec.zh.md`

If a feature changes the product boundary, update the stable PRD explicitly and
call out the reason in the PR.

## Issue Workflow

GitHub Issues carry implementation work. A good issue should include:

- Goal.
- Scope and out of scope.
- Acceptance criteria.
- Affected surfaces.
- Validation plan.
- Links to Feature PRDs or source documents when relevant.

Prefer vertical slices that can be implemented and reviewed independently. Avoid
issues that split all data work, all API work, all UI work, and all tests into
separate piles unless there is a clear integration plan.

## Design Impact Checklist

Before implementing non-trivial work, identify whether it affects:

- Product behavior or acceptance criteria.
- API endpoints, request bodies, response bodies, or auth boundaries.
- Data model, persistence states, migrations, or seed data.
- Frontend routes, UI state, or visible workflows.
- Permissions, audit behavior, reminders, subscriptions, recommendations, or
review/publication state.
- CI, setup, dependencies, or local infrastructure.
- Documentation, course reports, ADRs, or MkDocs navigation.

## Agent Task Contract

Agents must follow `AGENTS.md`. For non-trivial tasks, they should state the task
type, roadmap phase, source documents, affected surfaces, external writes, and
validation plan before editing.

External writes include GitHub issues, PR bodies/comments, labels, issue state,
commits, pushes, tags, and major durable document rewrites. These require a
preview and confirmation.

## Validation Strategy

Use layered validation:

- During development, run the narrowest check that exercises the changed surface.
- Before handoff, run relevant checks for every affected surface.
- Before merge, release, or broad shared changes, prefer `just check`; if it is
not run, state why.

Validation matrix:

- Backend: `just api-test`, `just api-lint`, `just api-format`.
- Frontend: `just web-lint`, `just web-build`.
- Documentation and navigation: `just docs-build`.
- Infrastructure: `just infra-config`.
- Full local gate: `just check`.

## TDD Strategy

Use TDD when practical for:

- Bug fixes with reproducible behavior.
- Backend business rules or state transitions.
- API validation, auth, and permission behavior.
- Reminder, subscription, recommendation, and review/publication workflows.
- Regression-prone behavior changes.

Manual validation is acceptable for pure documentation changes, template/process
changes, visual-only frontend work without a test harness, exploratory spikes,
and small copy edits. If automated tests are skipped for behavior changes,
record the reason and the manual validation path.

## Documentation Sync

Use this ownership rule:

- Product behavior: `docs/PRD.zh.md` or a Feature PRD.
- API: `docs/api_spec.md`.
- Data model and states: `docs/data_model.md`.
- Architecture or technical design: `docs/architecture.md`,
  `docs/tech_spec.zh.md`, or an ADR.
- Setup and tooling: `docs/setup.md` or `docs/tooling.md`.
- Course deliverables: `docs/reports/`.
- New, moved, or removed docs pages: `mkdocs.yml`.

If a change touches multiple alignment documents, update them together or call
out the conflict and proposed follow-up.

## Team Roles

One person may hold multiple hats, but each active slice should have clear
ownership:

- Product owner: roadmap fit, PRD quality, acceptance criteria.
- Tech lead: architecture, data/API contracts, ADR decisions.
- Backend owner: API, data model, services, tests.
- Frontend owner: routes, UI flows, state, build checks.
- QA/validation owner: test plan, manual acceptance, validation evidence.
- Docs/report owner: project docs, course reports, MkDocs navigation.

## Release Sprint Mode

For milestone checks such as the midterm inspection, the team may enter Release Sprint Mode.

Release Sprint Mode means:
- Freeze scope around the current roadmap target.
- Prefer vertical slices over horizontal layer-only tasks.
- Keep the runnable branch demo-ready every day.
- Require validation evidence before marking work done.
- Stop feature work before the inspection and use the final day for bug fixes, docs, and demo rehearsal.

## Explicit Avoids

- Do not build P4 extensions before P1/P2 are stable.
- Do not turn `CONTRIBUTING.md` or `AGENTS.md` into long project-management
manuals.
- Do not make every small bug or docs edit require a Feature PRD.
- Do not duplicate the same requirements across every document.
- Do not let AI-generated code or docs bypass review and source-document
alignment.
