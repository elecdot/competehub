# AGENTS.md

This file is the repository-level behavior contract for coding agents.

## Repository Orientation

- Read `README.md`, `docs/project_workflow.md`, and relevant directory-level
`README.md` files before editing code or documentation.
- Read `CONTEXT.md` for canonical project language and `docs/roadmap.md` for
the current product and engineering delivery route when changing product,
architecture, module, or report documents.
- Treat `CONTEXT.md` as a glossary only. Put decision rationale, rejected
alternatives, and consequences in `docs/adr/`, and read `docs/adr/README.md`
before adding or changing ADRs.
- Prefer existing repository commands, conventions, and helper scripts over
introducing new workflow shapes.
- Keep changes small, reviewable, and scoped to the user request.

## Agent Task Contract

For non-trivial tasks, before editing files or performing external writes,
state:

- Task type: docs, feature, bug, refactor, CI, report, process, or other.
- Roadmap phase when applicable: P0, P1, P2, P3, P4, or not applicable.
- Source documents read, plus any intentionally skipped documents.
- Affected surfaces: code, API, data model, UI, docs, reports, CI, issue
tracker, or none.
- External writes needed: GitHub issue, PR body/comment, labels, close issue,
commit, push, or none.
- Validation plan: targeted checks to run, or why validation is not needed.

This contract applies to code changes, public behavior changes, API/data model
changes, CI/setup changes, durable documentation changes, issue/PR operations,
and report work. Tiny read-only questions and simple local inspection commands
do not require the full contract.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues for `elecdot/competehub`; external PRs are
not a triage request surface. See `docs/agents/issue-tracker.md`.

### Triage labels

The five Matt Pocock triage roles map directly to same-name GitHub labels:
`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and
`wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This repo uses a single-context domain-doc layout: root `CONTEXT.md` plus
repo-wide ADRs in `docs/adr/`. See `docs/agents/domain.md`.

## Change Workflow

- For bug fixes and behavior changes, prefer the TDD workflow in
`docs/agents/tdd.md`: reproduce with a failing test when practical, make the
smallest passing change, then refactor.
- Do not use `to-prd` or feature planning work to overwrite `docs/PRD.zh.md`.
Feature PRDs live under `docs/prds/features/`; changing the stable product PRD
requires an explicit request and confirmation.
- Do not rewrite unrelated files, reformat entire files unnecessarily, or
change public contracts without updating documentation and validation.
- When preparing commits, branches, or pull requests, follow `README-GIT.md`.
- Preserve user changes already present in the worktree; do not revert work you
did not make unless explicitly requested.
- Add appropriate comments when working, especially where a decision or complex
block would otherwise be hard to understand.

## External Write Policy

Preview and wait for user confirmation before:

- Creating or editing GitHub issues, PR bodies, PR comments, labels, or issue
state.
- Committing, pushing, tagging, or rewriting Git history.
- Closing issues or PRs.
- Replacing or substantially rewriting durable project documents such as
`docs/PRD.zh.md`, `docs/api_spec.md`, `docs/data_model.md`,
`docs/tech_spec.zh.md`, and `docs/reports/*`.

Before creating a GitHub issue, read `.github/ISSUE_TEMPLATE/config.yml` and the
relevant issue form. If the user asks for a task issue, prefer
`.github/ISSUE_TEMPLATE/task.yml`. Show the title, labels, and body field
mapping before creating the issue.

## Dependency And Tooling Policy

- Prefer `just` recipes for routine commands. When bypassing recipes, prefix
commands with `./scripts/agent-env.sh` so tool caches and temporary files stay
inside the workspace; spell out project commands explicitly, for example
`./scripts/agent-env.sh uv run --project apps/api pytest`.
- Do not add a root-level `uv` project. Python dependencies and dependency
groups should live in the relevant application project, such as `apps/api`.
- Documentation Python dependencies belong in the `apps/api` dependency groups.
- Frontend dependencies belong in `apps/web/package.json` and managed by `npm`.
- When a task reasonably needs a missing regular dependency, add it through the
project's dependency-management conventions and document the related command.

## Temporary Tools

- Agents may use `.cache/` for temporary tool caches, downloaded helper
binaries, and one-off task dependencies.
- Do not commit `.cache/` contents or make normal development, CI, or
deployment depend on files that only exist in `.cache/`.
- If a temporary tool becomes part of the regular workflow, promote it into the
project dependency system and document it.

## Validation Matrix

- Use layered validation. During development, run the narrowest relevant check.
Before handoff, run the checks for every affected surface. Before merge,
release, or broad cross-cutting changes, prefer the full local gate or explain
why it was not run.
- Full local gate: `just check`.
- Backend code: `just api-test`, `just api-lint` and `just api-format`.
- Frontend code: `just web-lint` and `just web-build`.
- Documentation: `just docs-build`.
- Infrastructure: `just infra-config`.
- CI workflow changes: keep local commands, `justfile`, package scripts, and
workflow commands aligned where applicable.

## Documentation And CI

- Treat GitHub Actions as the repository validation contract.
- When changing GitHub Actions, update `.github/workflows/README.md`.
- Keep documentation complete and in sync throughout development.
- When adding, removing, or renaming documentation pages, update `mkdocs.yml`
so the published documentation site stays in sync.
- Treat product, architecture, API, data model, roadmap, and module documents as
alignment documents that may be refined together; do not assume any one of them
is an untouchable absolute source when they conflict.
- Keep each kind of project knowledge in its owning document as defined by
`docs/project_workflow.md`; use links and short summaries instead of duplicating
the same rules across documents.
- Put durable product and architecture docs in `docs/`, time-bound decisions in
`docs/adr/`, and course-style reports or generated analysis in `docs/reports/`.

## Definition Of Done

- Relevant tests, builds, or checks were run, or the reason for skipping is
stated.
- Documentation changed with behavior, setup, CI, deployment, or public
interfaces.
- `mkdocs.yml` changed when documentation pages were added, removed, or
renamed.
- CI workflow documentation changed when workflows or validation commands
changed.
- No generated caches, build outputs, local secrets, or temporary files were
added to version control.
