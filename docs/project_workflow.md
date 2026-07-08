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

Agent helpers such as `to-prd` may be used only as drafting aids. The final
Feature PRD must live under `docs/prds/features/`, use the local template, and
follow `docs/agents/feature-prd.md`. Do not publish a Feature PRD itself as a
GitHub issue or mark it `ready-for-agent`; split accepted PRDs into vertical
implementation issues first.

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

Each active implementation or documentation slice should also make responsibility
explicit:

- DRI: the person who drives the issue to completion.
- Contributors: people responsible for backend, frontend, docs, data, or report
  parts when the issue crosses surfaces.
- Reviewer: the person expected to review the change before merge.
- Validation owner: the person responsible for collecting test, build, or manual
  acceptance evidence.
- Docs impact: source documents that must be updated or explicitly left
  unchanged.

### Delivery Ownership Fields

The default issue model is still one person completing one issue with agent
assistance. Ownership fields make cross-module alignment visible; they do not
turn every listed contributor into a co-implementer.

Use the current module-owner mapping from
`docs/reports/module_breakdown_v1.0.md` when assigning issue ownership:

| Module | Default owner |
|---|---|
| M1 用户与画像管理 | a |
| M2 赛事治理 | b |
| M3 赛事发现与展示 | c |
| M4 赛事跟进 | e |
| M5 规则推荐与推荐解释 | d |
| M6 后台运营、配置与审计统计 | f |
| M7 内容沉淀与交流扩展 | f unless a submodule owner is more specific |

`DRI` must be one concrete member or role, usually the owner of the primary
module affected by the issue. For cross-module work, choose the owner of the
main accepted outcome or core state/data change. Do not use multiple DRIs. If an
agent cannot infer the DRI reliably, mark it as a candidate or `TBD` in the
preview and ask for confirmation before publishing the issue as ready for an
agent.

`Contributors` should include only members with a real relationship to the
issue. Normal implementation issues should not list all members by default. Use
these relationship types:

- `Active`: actually co-produces code, documentation, tests, or design.
- `Align with`: must align on API, data, UI, documentation, requirements, or
  validation boundaries.
- `FYI`: should know about the work, but is not expected to participate.

Parent issues, release sprint issues, and coordination issues may list all
members a-f when the whole team needs visibility. Ordinary vertical slices
should keep contributors scoped to the affected modules.

`Reviewer` should usually be `f` or the relevant tech/product/repo-admin role,
because member f also carries M6 quality support and often performs final
review or repository administration. A neighboring module owner may be the main
reviewer when that creates a better domain check. Avoid making the reviewer the
same person as the DRI except for small documentation or process fixes.

`Validation owner` must be a human member or role, not an agent. The DRI may own
validation for ordinary work; `f` or another reviewer should own final
validation for critical paths. An agent may run checks and collect evidence, but
the validation owner accepts whether the evidence is sufficient.

`Docs impact` must name concrete paths, such as `docs/api_spec.md` or
`docs/data_model.md`, or explicitly say `None - explicitly reviewed`.

An issue is not ready for `ready-for-agent` until Delivery Ownership is complete:

- DRI is one concrete member or role, not `TBD`.
- Contributors are scoped and typed as `Active`, `Align with`, or `FYI`.
- Reviewer is set and preferably not the DRI.
- Validation owner is a human member or role, not an agent.
- Docs impact lists concrete paths or `None - explicitly reviewed`.

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

The project-wide test layers, manual acceptance path, and non-functional
validation model live in `docs/testing.md`.

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

Use three levels of responsibility:

- Role responsibilities keep product, technology, backend, frontend,
  validation, and documentation concerns covered.
- Module owners keep each core module explainable. A module owner must
  understand the module's requirements, APIs, key data, test method, and demo
  path; they do not have to implement every task in that module alone.
- Issue DRIs drive current work. Concrete contributors, reviewers, validation
  owners, and docs impact belong on the issue or PR rather than in a giant
  submodule responsibility matrix.

## Release Sprint Mode

For milestone checks such as the midterm inspection, the team may enter Release Sprint Mode.

Release Sprint Mode means:
- Freeze scope around the current roadmap target.
- Prefer vertical slices over horizontal layer-only tasks.
- Use an explicit issue table for current work: issue, DRI, contributors,
  reviewer, validation owner, docs impact, and demo path.
- Run small, frequent checks instead of waiting for one late integration review.
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
