# AGENTS.md

Read `README.md` and relevant directory-level `README.md` files first for the
overview and local conventions.

## Working Notes

- Since `uv` is blocked by a read-only cache path in the agent's sandbox,
use a workspace-safe cache directory instead, e.g., `./scripts/agent-env.sh uv <command>` which uses `UV_CACHE_DIR=.cache/uv uv run <command>`.
Tips: `justfile` encapsulates the agent-specific commands, refer to them.
- Do not be constrained by the repository's current dependency set. When a task
reasonably needs a missing dependency, add it autonomously using the project's
dependency-management conventions.
- Do not add a root-level `uv` project. Python dependencies and dependency
groups should live in the relevant application project, such as `apps/api`.
- If you identify commands during development that should be documented or
reused, consider adding them to `justfile` with appropriate guidance (for
example, comments).
- Keep documentation complete and in sync throughout development; if you find
gaps, fill them in.
- When adding, removing, or renaming documentation pages, update `mkdocs.yml`
so the published documentation site stays in sync.
- Always add appropriate comments when working.
