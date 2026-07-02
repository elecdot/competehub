# Scripts

This directory contains repository-level helper scripts.

## Local Conventions

- Scripts must be safe to run from the repository root.
- Scripts should be idempotent when possible.
- Agent-facing scripts must write caches and temporary files inside the workspace.
- Document new scripts here and expose common workflows through the root `justfile`.

## Scripts

- `agent-env.sh`: Sets agent-safe environment variables and then runs the
  requested command. It keeps tool caches and temporary files inside `.cache/`.

Examples:

```bash
./scripts/agent-env.sh
./scripts/agent-env.sh uv sync --project apps/api
./scripts/agent-env.sh uv run --project apps/api pytest
./scripts/agent-env.sh uv run --project apps/api ruff check .
./scripts/agent-env.sh npm --prefix apps/web run lint
```

Prefer `just` recipes for routine workflows.
