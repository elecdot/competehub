# Scripts

This directory contains repository-level helper scripts.

## Local Conventions

- Scripts must be safe to run from the repository root.
- Scripts should be idempotent when possible.
- Agent-facing scripts must write caches and temporary files inside the workspace.
- Document new scripts here and expose common workflows through the root `justfile`.

## Scripts

- `agent-env.sh`: Runs Python and uv commands with a workspace-safe uv cache.

Examples:

```bash
./scripts/agent-env.sh pytest
./scripts/agent-env.sh ruff check .
./scripts/agent-env.sh uv sync --project apps/api
```

Prefer `just` recipes for routine workflows.
