# Setup

This guide provides a quick-start setup for contributors.

## Prerequisites

Install these tools before starting development:

- `git`
- `just`
- `uv`
- Node.js and npm
- Docker Desktop with WSL integration enabled, if using the local PostgreSQL and Redis services

Refer to [Tooling](./tooling.md) for installation notes and command usage.

## Configure Git Before Committing

Set Git to normalize line endings to `LF` before your first commit. This prevents platform-specific `CRLF` changes from being introduced, especially on Windows.

```bash
git config core.eol lf
git config core.autocrlf input
```

>[!warning] This does not mean the `CRLF` (Windows style line endings) is permitted .

## Install pre-commit

Ensure that `just` and `uv` are available on your `PATH`. If not, refer to [Tooling](./tooling.md) for installation instructions.

```bash
just pre-commit
```

## Install Dependencies

Backend dependencies are managed by `uv` under `apps/api`. Use the workspace-safe wrapper through `just`:

```bash
just api-sync
```

Frontend dependencies are managed by npm under `apps/web`:

```bash
npm --prefix apps/web install
```

## Configure Environment

Copy the example environment file for local development:

```bash
cp .env.example .env
```

The default values point to the PostgreSQL and Redis services defined in `infra/docker-compose.yml`.

## Start Local Services

Start PostgreSQL and Redis:

```bash
just infra-up
```

Stop them when finished:

```bash
just infra-down
```

## Start Applications

Run the backend API:

```bash
just api-dev
```

Run the frontend app:

```bash
just web-dev
```

By default, the frontend proxies `/api` requests to the Flask API on `localhost:5000`.

## Verify The Workspace

Run the main checks before committing:

```bash
just api-test
just api-lint
just web-lint
just web-build
docker compose -f infra/docker-compose.yml config
```
