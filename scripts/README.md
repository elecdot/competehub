# Scripts

This directory contains repository-level helper scripts.

## Local Conventions

- Scripts must be safe to run from the repository root.
- Scripts should be idempotent when possible.
- Agent-facing scripts must write caches and temporary files inside the workspace.
- Document new scripts here and expose common workflows through the root `justfile`.

## Scripts

- `agent-env.sh`: Runs Python and uv commands with a workspace-safe uv cache.
