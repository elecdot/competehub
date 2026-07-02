set shell := ["bash", "-cu"]

# Run a raw uv command with the agent-safe environment.
agent-uv *args:
    ./scripts/agent-env.sh uv {{args}}

# Sync backend dependencies.
api-sync:
    ./scripts/agent-env.sh uv sync --project apps/api

# Start the Flask API in development mode.
api-dev:
    ./scripts/agent-env.sh uv run --project apps/api flask --app competehub_api.app:create_app run --debug

# Run backend tests.
api-test:
    ./scripts/agent-env.sh uv run --project apps/api pytest

# Run backend lint checks.
api-lint:
    ./scripts/agent-env.sh uv run --project apps/api ruff check .

# Format backend Python files.
api-format:
    ./scripts/agent-env.sh uv run --project apps/api ruff format .

# Build the MkDocs Material documentation site.
docs-build:
    ./scripts/agent-env.sh uv run --project apps/api --group docs mkdocs build --strict

# Start the MkDocs Material documentation server.
docs-serve:
    ./scripts/agent-env.sh uv run --project apps/api --group docs mkdocs serve

# Start the Vue development server.
web-dev:
    npm --prefix apps/web run dev

# Build the Vue application.
web-build:
    npm --prefix apps/web run build

# Run frontend static checks.
web-lint:
    npm --prefix apps/web run lint

# Start local PostgreSQL and Redis.
infra-up:
    docker compose -f infra/docker-compose.yml up -d

# Stop local PostgreSQL and Redis.
infra-down:
    docker compose -f infra/docker-compose.yml down

# Sync backend uv environment and run pre-commit git hooks.
pre-commit:
    ./scripts/agent-env.sh uv run --project apps/api pre-commit install
    ./scripts/agent-env.sh uv run --project apps/api pre-commit run --all-files
