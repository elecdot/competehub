---
name: competehub-workflow
description: Route non-trivial CompeteHub work through the project delivery workflow. Use when a task touches product scope, architecture, implementation, testing, documentation, GitHub issues or PRs, course reports, or agent-assisted delivery decisions.
---

# CompeteHub Workflow

Run the project delivery workflow router: align, classify, route, guard, and hand off.

## 1. Align

Read the source documents needed for the task:

- Always for non-trivial work: `AGENTS.md`, `docs/project_workflow.md`, `docs/roadmap.md`, and `CONTEXT.md`.
- For product behavior: `docs/PRD.zh.md` or `docs/prds/features/*`.
- For Feature PRD drafting: `docs/agents/feature-prd.md` and `docs/prds/features/template.md`.
- For APIs, data, architecture, or technical design: the matching docs under `docs/`.
- For GitHub issue work: `docs/agents/issue-tracker.md` and the relevant `.github/ISSUE_TEMPLATE/*` form.

Completion criterion: be able to state the task type, roadmap phase, source documents, affected surfaces, external writes, and validation plan from `AGENTS.md`.

## 2. Route

Choose the smallest primary route:

- Fuzzy plan or design -> use `grill-with-docs`.
- Domain language or ADR question -> use `domain-modeling`.
- New feature requirement -> create or update a Feature PRD under `docs/prds/features/` using the local template; do not overwrite `docs/PRD.zh.md` unless explicitly requested.
- Focused implementation, fix, test, or docs slice -> use `delivery-slice`.
- UI/UX audit -> use `web-design-guidelines`.
- Local web app behavior testing -> use `webapp-testing`.

Completion criterion: name one primary route and any secondary skill only when it is actually needed.

>tip: If a local personal helper such as `/to-prd` or `/to-issue` exists, it may be used only as a drafting aid. The final artifact must follow this repository's Feature PRD template, issue forms, source-of-truth matrix, and confirmation policy. In this repo, `/to-prd` drafts `docs/prds/features/*.md`; it does not publish the PRD itself as a GitHub issue or apply `ready-for-agent`.

## 3. Guard The Scope

Keep the slice reviewable. Split unrelated changes into follow-up issues. Preview and wait for confirmation before GitHub writes, Git history changes, or major durable document rewrites.

Completion criterion: the planned diff can be reviewed as one logical change.

## 4. Validate And Sync

Use layered validation from `AGENTS.md`. Update owning documents from the source-of-truth matrix in `docs/project_workflow.md` instead of duplicating rules across documents.

Completion criterion: validation results and docs impact are ready to paste into a PR or handoff.
