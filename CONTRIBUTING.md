# Contributing to CompeteHub

This guide is the short entry point for collaborators. The full project
delivery workflow lives in `docs/project_workflow.md`.

## Start Here

Read these first:

1. `README.md` for setup and repository structure.
2. `CONTEXT.md` for canonical project language.
3. `docs/roadmap.md` for delivery phase boundaries.
4. `docs/project_workflow.md` for the full workflow.
5. `README-GIT.md` before committing or opening a PR.

When changing product behavior, also read `docs/PRD.zh.md`. When changing APIs,
data, architecture, or technical design, read the matching documents under
`docs/`.

## Delivery Flow

Use this flow for non-trivial work:

```text
Roadmap -> Feature PRD -> Issue -> Design Impact -> Code/Test -> PR -> Docs
```

Small bugs and pure documentation fixes do not need a Feature PRD. They still
need a clear issue or objective, focused changes, validation, and documentation
sync when behavior or public contracts change.

## Feature PRDs

Do not overwrite `docs/PRD.zh.md` for individual features. Feature PRDs live in
`docs/prds/features/` and use `docs/prds/features/template.md`.

A Feature PRD should name the roadmap phase, source documents checked, user
value, out-of-scope items, acceptance criteria, affected surfaces, and validation
plan.

## Issues And PRs

Use GitHub Issues for work tracking. Before creating an issue, use the matching
form under `.github/ISSUE_TEMPLATE/`.

Each PR should be one logical change. Before opening a PR:

- Keep the diff focused.
- Run relevant checks or explain what was not run.
- Update affected docs.
- Confirm no secrets, local env files, caches, build outputs, or temporary
files are included.

## Validation

Run the narrowest useful checks while developing, then run all checks relevant
to the changed surfaces before handoff.

- Backend: `just api-test`, `just api-lint`, `just api-format`.
- Frontend: `just web-lint`, `just web-build`.
- Documentation: `just docs-build`.
- Infrastructure: `just infra-config`.
- Broad or release-like changes: `just check`.

## Using Agents

For non-trivial tasks, ask agents to follow `AGENTS.md`. Agents should identify
the task type, roadmap phase, source documents, affected surfaces, external
writes, and validation plan before editing. They must preview GitHub writes,
Git history changes, and major durable document rewrites before acting.
