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
- `course-demo.sh`: Operates the bounded Deployment v1 Compose stack through
  explicit prepare, registration, build, migration, fictional bootstrap,
  deploy, inventory, stop, and exact-scope destroy operations. Prefer its
  `course-demo-*` `just` entry points.
- `test-course-demo.sh`: Exercises the Deployment v1 failure-time public-access
  report and the exact-source Docker context boundary. The context check uses a
  BuildKit local export when Buildx is present. Its compatibility path creates
  and removes one exact temporary image and stopped container through the
  legacy builder; either path may retain a small Docker build-cache entry.

Examples:

```bash
./scripts/agent-env.sh
./scripts/agent-env.sh uv sync --project apps/api
./scripts/agent-env.sh uv run --project apps/api pytest
./scripts/agent-env.sh uv run --project apps/api ruff check .
./scripts/agent-env.sh npm --prefix apps/web run lint
```

Prefer `just` recipes for routine workflows.
