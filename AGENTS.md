# AGENTS.md

This file is the repository-level behavior contract for coding agents.

## Repository Orientation

- Read `README.md` and relevant directory-level `README.md` files before
editing code or documentation.
- Prefer existing repository commands, conventions, and helper scripts over
introducing new workflow shapes.
- Keep changes small, reviewable, and scoped to the user request.

## Dependency And Tooling Policy

- Use `./scripts/agent-env.sh` or `just` recipes for Python commands so `uv`
uses the workspace-safe cache under `.cache/uv`.
- Do not add a root-level `uv` project. Python dependencies and dependency
groups should live in the relevant application project, such as `apps/api`.
- Documentation Python dependencies belong in the `apps/api` dependency groups.
- Frontend dependencies belong in `apps/web/package.json`.
- When a task reasonably needs a missing regular dependency, add it through the
project's dependency-management conventions and document the related command.

## Temporary Tools

- Agents may use `.cache/` for temporary tool caches, downloaded helper
binaries, and one-off task dependencies.
- Do not commit `.cache/` contents or make normal development, CI, or
deployment depend on files that only exist in `.cache/`.
- If a temporary tool becomes part of the regular workflow, promote it into the
project dependency system and document it.

## Change Workflow

- For bug fixes and behavior changes, prefer the TDD workflow in
`docs/agent/tdd.md`: reproduce with a failing test when practical, make the
smallest passing change, then refactor.
- Do not rewrite unrelated files, reformat entire files unnecessarily, or
change public contracts without updating documentation and validation.
- Preserve user changes already present in the worktree; do not revert work you
did not make unless explicitly requested.
- Add appropriate comments when working, especially where a decision or complex
block would otherwise be hard to understand.

## Validation Matrix

- Backend code: `just api-test` and `just api-lint`.
- Frontend code: `just web-lint` and `just web-build`.
- Documentation: `just docs-build`.
- Infrastructure: `docker compose -f infra/docker-compose.yml config`.
- CI workflow changes: keep local commands, `justfile`, package scripts, and
workflow commands aligned where applicable.

## Documentation And CI

- Treat GitHub Actions as the repository validation contract.
- When changing GitHub Actions, update `.github/workflows/README.md`.
- Keep documentation complete and in sync throughout development.
- When adding, removing, or renaming documentation pages, update `mkdocs.yml`
so the published documentation site stays in sync.
- Put durable product and architecture docs in `docs/`, time-bound decisions in
`docs/adr/`, and course-style reports or generated analysis in `reports/`.

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
