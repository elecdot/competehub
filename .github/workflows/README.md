# GitHub Actions Workflows

This directory contains GitHub Actions workflow definitions.

## Workflows

- `ci.yml`: runs backend checks, frontend checks, Chromium Playwright browser
  acceptance, and local infrastructure configuration validation on pull requests
  and pushes to `main`.
- `docs.yml`: builds the MkDocs Material documentation site on pull requests and deploys it to GitHub Pages after pushes to `main`. The repository Pages source must be set to GitHub Actions in the GitHub Pages settings.

## CI Command Mapping

- Backend dependency sync: `./scripts/agent-env.sh uv sync --project apps/api --locked`
- Backend lint: `./scripts/agent-env.sh uv run --project apps/api ruff check .`
- Backend tests: `./scripts/agent-env.sh uv run --project apps/api pytest`
- Frontend dependency install: `npm --prefix apps/web ci`
- Frontend typecheck: `npm --prefix apps/web run lint`
- Frontend build: `npm --prefix apps/web run build`
- Browser dependency install: `npm --prefix apps/web run e2e:install -- --with-deps`
- Browser acceptance: `npm --prefix apps/web run test:e2e`
- Infrastructure config check: `docker compose -f infra/docker-compose.yml config`
- Documentation dependency sync: `./scripts/agent-env.sh uv sync --project apps/api --group docs --locked`
- Documentation build: `./scripts/agent-env.sh uv run --project apps/api --group docs mkdocs build --strict`

## Local Conventions

- Keep workflow jobs aligned with semantic repository areas: backend, frontend, infrastructure, and documentation.
- Use lockfile-backed installs in CI.
- Keep CI checks deterministic and avoid services unless an integration test explicitly requires them.
- Upload `.cache/playwright/report` and `.cache/playwright/test-results` for
  browser-job failures only; retain them for seven days and never commit them.
- Update this README when adding, renaming, or removing workflows.
