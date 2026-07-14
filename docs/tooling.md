# Tooling

This guide introduces the development tools used in this project.

## `mise`

The repository includes `mise.toml` as an optional tool-version manifest for
Python, Node.js, uv, and just. Developers may use mise to install matching tool
versions, but project workflows still run through `just`, `uv`, npm, and Docker
Compose.

```bash
mise install
mise run setup
mise run check
```

## `just`

`just` is a command runner that encapsulates complex or multi-step commands into simple single-line invocations.

For example, here is a `justfile`:
```bash
api-test:
    ./scripts/agent-env.sh uv run --project apps/api pytest
```
Then you type:
```bash
just api-test
```

Current project recipes include:

- `default`: list available recipes.
- `setup`: install backend and frontend dependencies.
- `doctor`: show workspace status and required tool availability.
- `check`: run the main local gate.
- `agent`: run any command with the agent-safe environment.
- `agent-uv`: run a raw `uv` command with the agent-safe environment.
- `fmt`: run configured formatters.
- `lint`: run backend and frontend checks.
- `test`: run backend and Playwright browser tests.
- `build`: run build checks.
- `api-sync`: sync backend dependencies.
- `api-dev`: start the Flask backend.
- `api-worker`: start the Celery worker.
- `api-worker-beat`: schedule periodic Celery tasks, including verification outbox delivery.
- `api-db-upgrade`: apply committed Alembic revisions to the configured database.
- `seed-recommendation-rules`: invoke the standard Flask CLI command that
  idempotently provisions the reproducible initial active v1; see
  [Setup](setup.md#start-local-services) for conflict and legacy-data handling.
- `api-test`: run backend tests.
- `api-lint`: run backend Ruff checks.
- `api-format`: format backend Python files.
- `web-install`: install frontend dependencies.
- `docs-build`: build the MkDocs Material documentation site.
- `docs-serve`: start the local MkDocs documentation server.
- `web-dev`: start the Vue dev server.
- `web-e2e-install`: install the Chromium binary used by Playwright.
- `web-e2e`: reset the isolated browser seed and run the Playwright suite.
- `web-lint`: run frontend type checks.
- `web-build`: build the Vue app.
- `infra-up`: start local PostgreSQL and Redis.
- `infra-down`: stop local PostgreSQL and Redis.
- `infra-config`: validate the Docker Compose configuration.
- `pre-commit`: install and run pre-commit hooks.

---

### Quick Start

#### Installation

```pwsh
winget install --id Casey.Just --exact
```

---

## `uv`

We use `uv` to manage the backend API package and Python-based documentation tooling under `apps/api`.

Do not create a root-level `uv` project. Run Python commands through `just`
recipes or prefix explicit commands with `./scripts/agent-env.sh` so tool caches
and temporary files stay under `.cache/`.

- [GitHub Repo](https://github.com/astral-sh/uv?tab=readme-ov-file)
- [Official Doc](https://docs.astral.sh/uv/)

---

### Quick Start

#### Installation

Install uv with our standalone installers:

```bash
# On macOS and Linux.
curl -LsSf https://astral.sh/uv/install.sh | sh
```
```pwsh
# On Windows.
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
#### Add backend dependencies

```bash
just agent-uv add --project apps/api requests
./scripts/agent-env.sh uv add --project apps/api requests
./scripts/agent-env.sh uv add --project apps/api 'requests==2.31.0'
```
Add a package to the `dev` group:
```bash
just agent-uv add --project apps/api --dev ipykernel
./scripts/agent-env.sh uv add --project apps/api --dev ipykernel
```

#### Run command in `uv` environment

```bash
./scripts/agent-env.sh uv run --project apps/api <command here>
```

In this repository, prefer the workspace-safe wrapper:

```bash
./scripts/agent-env.sh uv run --project apps/api pytest
./scripts/agent-env.sh uv run --project apps/api ruff check .
```

#### Update the backend environment

```bash
just api-sync
just web-install
just api-dev
```

---

## `npm`

The frontend app in `apps/web` uses npm.

```bash
just web-install
npm --prefix apps/web install
npm --prefix apps/web run dev
npm --prefix apps/web run build
```

Prefer the equivalent `just` recipes when available.

---

## MkDocs

The documentation site uses MkDocs Material and publishes from `docs/` through GitHub Pages.

```bash
just docs-build
just docs-serve
```

`just docs-build` runs MkDocs in strict mode, so broken navigation or links fail before deployment.

---

## Docker Compose

Local PostgreSQL and Redis are defined in `infra/docker-compose.yml`.

```bash
just infra-up
docker compose -f infra/docker-compose.yml ps
just infra-config
just infra-down
```
