set shell := ["bash", "-cu"]

# List recipes.
default:
    @just --list

# Prepare backend and frontend dependencies.
setup: api-sync web-install

# Show workspace status and required tool availability.
doctor:
    @missing=0; \
    printf 'Git status:\n'; \
    git status --short; \
    printf '\nTools:\n'; \
    for tool in git just uv npm; do \
      if command -v "$tool" >/dev/null 2>&1; then \
        printf '  %-8s %s\n' "$tool" "$(command -v "$tool")"; \
      else \
        printf '  %-8s missing\n' "$tool"; \
        missing=1; \
      fi; \
    done; \
    if docker compose version >/dev/null 2>&1; then \
      printf '  %-8s %s\n' "docker" "$(command -v docker)"; \
    else \
      printf '  %-8s missing or unavailable\n' "docker"; \
      missing=1; \
    fi; \
    exit "$missing"

# Run the main local gate.
check: test lint build infra-config

# Run with the agent-safe environment.
agent *args:
    ./scripts/agent-env.sh {{args}}

# Run a raw uv command with the agent-safe environment.
agent-uv *args:
    ./scripts/agent-env.sh uv {{args}}

# Format backend Python files.
fmt: api-format

# Run all lint and type checks.
lint: api-lint web-lint

# Run all tests.
test: api-test

# Run all build checks.
build: web-build docs-build

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

# Install frontend dependencies.
web-install:
    ./scripts/agent-env.sh npm --prefix apps/web install

# Build the MkDocs Material documentation site.
docs-build:
    ./scripts/agent-env.sh uv run --project apps/api --group docs mkdocs build --strict

# Start the MkDocs Material documentation server.
docs-serve:
    ./scripts/agent-env.sh uv run --project apps/api --group docs mkdocs serve

# Start the Vue development server.
web-dev:
    ./scripts/agent-env.sh npm --prefix apps/web run dev

# Build the Vue application.
web-build:
    ./scripts/agent-env.sh npm --prefix apps/web run build

# Run frontend static checks.
web-lint:
    ./scripts/agent-env.sh npm --prefix apps/web run lint

# Start local PostgreSQL and Redis.
infra-up:
    docker compose -f infra/docker-compose.yml up -d

# Stop local PostgreSQL and Redis.
infra-down:
    docker compose -f infra/docker-compose.yml down

# Validate local infrastructure configuration.
infra-config:
    docker compose -f infra/docker-compose.yml config

# Sync backend uv environment and run pre-commit git hooks.
pre-commit:
    ./scripts/agent-env.sh uv run --project apps/api pre-commit install
    ./scripts/agent-env.sh uv run --project apps/api pre-commit run --all-files
