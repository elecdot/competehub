# Git Workflow

This repository uses [Conventional Commits](https://www.conventionalcommits.org/)
with the repo-specific rules below. These conventions apply to collaborators
and coding agents.

Agents must not commit, push, or rewrite Git history unless the user explicitly
asks for that action.

## Rules

- One commit should contain one logical, reviewable, reversible change.
- Split unrelated changes instead of hiding them behind a broad commit.
- Run relevant checks before committing when practical; otherwise state what was
not run and why.
- Use targeted staging. Avoid `git add .` unless the whole worktree has been
reviewed.

## Commit Format

```text
<type>(<scope>): <subject>
```

Examples:

```text
feat(api): add competition creation endpoint
fix(web): handle empty competition list
docs(setup): document local infrastructure startup
test(api): cover invalid deadline validation
meta(agents): define repository agent workflow
```

Use a body only when the subject does not explain the reason, trade-off, or
behavior change clearly enough.

## Decision Rules

- Choose the type by the primary intent of the commit.
- Keep tests and docs in the same commit when they validate or explain the same
behavior change.
- Use separate `docs` or `test` commits when documentation or tests are the
actual change.
- Use `ci` for workflow behavior changes and `docs` for workflow documentation
only.
- Use `build(deps)` for dependency and lockfile changes.
- Use `meta` for repository process, Git rules, and agent coordination.

## Types

| Type | Use when |
| --- | --- |
| `feat` | user-visible feature or capability |
| `fix` | incorrect behavior |
| `docs` | documentation only |
| `style` | formatting or whitespace only |
| `refactor` | code restructuring without behavior change |
| `perf` | performance improvement |
| `test` | tests or fixtures |
| `build` | build system, package manager, dependencies, lockfiles, packaging |
| `ci` | GitHub Actions or automation |
| `chore` | routine maintenance that does not fit another type |
| `meta` | repository rules, agent instructions, process, coordination docs |
| `revert` | reverting a previous commit |

If tooling rejects `meta`, use `chore(meta)`.

## Scopes

Scopes are not a closed list. Prefer the most specific stable scope that helps
reviewers understand where the change belongs.

Use a recommended repo scope when the change maps to a stable area. Use a more
specific module, feature, file, or function scope when that is clearer and
likely to remain meaningful in history.

| Scope | Use when |
| --- | --- |
| `api` | backend API |
| `web` | frontend app |
| `db` | schema, migrations, persistence |
| `auth` | authentication or authorization |
| `ui` | shared UI or visual behavior |
| `docs` | documentation structure or content |
| `infra` | Docker, deployment, local services, environment setup |
| `ci` | GitHub Actions and automation |
| `tests` | test infrastructure |
| `deps` | dependency updates |
| `config` | project configuration |
| `agents` | coding-agent instructions or workflows |
| `git` | Git workflow, commit rules, branch rules |
| `project` | cross-cutting project organization |

Specific scope examples:

```text
fix(deadline-parser): handle timezone-only input
refactor(competition-card): simplify status rendering
test(auth-guard): cover expired session redirect
docs(mkdocs): add agent guideline navigation
```

Avoid scopes that only describe a temporary detail:

```text
fix(if-block): handle null
refactor(helper): clean up code
fix(line-42): update condition
```

For multi-area work, split by logical change:

```text
feat(api): add competition creation endpoint
feat(web): add competition creation form
test(api): cover competition creation validation
docs(api): document competition creation flow
```

Use broad scopes only for truly cross-cutting changes:

```text
refactor(project): standardize error response handling
build(deps): update application dependencies
```

## Special Commits

Breaking changes use `!` and a `BREAKING CHANGE` footer:

```text
feat(api)!: require authentication for competition creation

BREAKING CHANGE: unauthenticated requests to POST /competitions now return 401.
```

Reverts use `revert` and identify the reverted commit:

```text
revert(api): remove competition creation endpoint

Reverts commit abc1234.
```

## Branches

Use short descriptive branch names:

```text
<type>/<short-topic>
```

Examples:

```text
feat/competition-creation
fix/api-deadline-validation
docs/local-setup
meta/git-rules
```

## Commit Checklist

Before committing:

1. Inspect `git status`, `git diff`, and `git diff --staged`.
2. Separate unrelated changes.
3. Run relevant checks from `AGENTS.md`.
4. Stage deliberate paths only.
5. Confirm no secrets, `.env`, `.cache/`, `site/`, build outputs, editor
state, temporary files, debug output, personal notes, or unrelated generated
files are staged.

## Pull Requests

PRs should be focused and easy to review.

Before opening a PR:

- Remove unrelated changes.
- Run relevant checks or state what was skipped and why.
- Update docs for behavior, setup, CI, deployment, or public interface changes.
- Summarize what changed, validation performed, known risk, and follow-up work.

PR and issue templates live under `.github/` and should keep this workflow as
their source of truth.
