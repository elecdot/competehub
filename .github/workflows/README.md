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
- Backend tests: `./scripts/agent-env.sh uv run --project apps/api pytest`; CI
  supplies an isolated PostgreSQL 16 service so fresh and legacy migration
  upgrade/downgrade tests run on the production database family as well as SQLite.
- Frontend dependency install: `npm --prefix apps/web ci`
- Frontend typecheck: `npm --prefix apps/web run lint`
- Frontend build: `npm --prefix apps/web run build`
- Browser dependency install: `npm --prefix apps/web run e2e:install -- --with-deps`
- Browser acceptance: `npm --prefix apps/web run test:e2e`
- Infrastructure/static checks:
  `bash -n scripts/course-demo.sh scripts/test-course-demo.sh`,
  `docker compose -f infra/docker-compose.yml config`, and
  `./scripts/course-demo.sh config-example`, followed by
  `./scripts/test-course-demo.sh`. The example check fixes the project name,
  neutralizes material ambient Compose/environment overrides, and verifies the
  rendered non-secret example. The regression script verifies failure-time
  public-access reporting and proves that Git-ignored Python bytecode cannot
  enter the Docker build context.
- Documentation dependency sync: `./scripts/agent-env.sh uv sync --project apps/api --group docs --locked`
- Documentation build: `./scripts/agent-env.sh uv run --project apps/api --group docs mkdocs build --strict`

## Local Conventions

- Keep workflow jobs aligned with semantic repository areas: backend, frontend, infrastructure, and documentation.
- Use lockfile-backed installs in CI.
- Keep CI checks deterministic. The backend PostgreSQL service exists only for
  disposable migration integration databases created and dropped by the test fixture.
- Upload `.cache/playwright/report` and `.cache/playwright/test-results` for
  browser-job failures only; retain them for seven days and never commit them.
- Update this README when adding, renaming, or removing workflows.
