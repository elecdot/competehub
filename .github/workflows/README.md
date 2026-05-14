# GitHub Actions Workflows

This directory contains GitHub Actions workflow definitions.

## Workflows

- `ci.yml`: runs backend checks, frontend checks, and local infrastructure configuration validation on pull requests and pushes to `main`.

## CI Command Mapping

- Backend dependency sync: `./scripts/agent-env.sh uv sync --project apps/api --locked`
- Backend lint: `./scripts/agent-env.sh ruff check .`
- Backend tests: `./scripts/agent-env.sh pytest`
- Frontend dependency install: `npm --prefix apps/web ci`
- Frontend typecheck: `npm --prefix apps/web run lint`
- Frontend build: `npm --prefix apps/web run build`
- Infrastructure config check: `docker compose -f infra/docker-compose.yml config`

## Local Conventions

- Keep workflow jobs aligned with semantic repository areas: backend, frontend, infrastructure, and documentation.
- Use lockfile-backed installs in CI.
- Keep CI checks deterministic and avoid services unless an integration test explicitly requires them.
- Update this README when adding, renaming, or removing workflows.
