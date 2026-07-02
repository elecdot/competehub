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
    ./scripts/agent-env.sh pytest
```
Then you type:
```bash
just api-test
```

Current project recipes include:

- `api-sync`: sync backend dependencies.
- `api-dev`: start the Flask backend.
- `api-test`: run backend tests.
- `api-lint`: run backend Ruff checks.
- `api-format`: format backend Python files.
- `docs-build`: build the MkDocs Material documentation site.
- `docs-serve`: start the local MkDocs documentation server.
- `web-dev`: start the Vue dev server.
- `web-lint`: run frontend type checks.
- `web-build`: build the Vue app.
- `infra-up`: start local PostgreSQL and Redis.
- `infra-down`: stop local PostgreSQL and Redis.
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

Do not create a root-level `uv` project. Run Python commands through `just` recipes or `./scripts/agent-env.sh` so uv uses the workspace-safe cache under `.cache/uv`.

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
./scripts/agent-env.sh uv add --project apps/api requests
./scripts/agent-env.sh uv add --project apps/api 'requests==2.31.0'
```
Add a package to the `dev` group:
```bash
./scripts/agent-env.sh uv add --project apps/api --dev ipykernel
```

#### Run command in `uv` environment

```bash
./scripts/agent-env.sh <command here>
```

In this repository, prefer the workspace-safe wrapper:

```bash
./scripts/agent-env.sh pytest
./scripts/agent-env.sh ruff check .
```

#### Update the backend environment

```bash
just api-sync
just api-dev
```

---

## `npm`

The frontend app in `apps/web` uses npm.

```bash
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
just infra-down
```
