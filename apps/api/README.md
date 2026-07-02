# Backend API

This directory contains the Flask backend API for CompeteHub.

## Responsibilities

- Own HTTP APIs under `/api/v1`.
- Own backend business rules, persistence models, migrations, and asynchronous tasks.
- Integrate with PostgreSQL as the system of record and Redis for transient runtime concerns.

This directory does not own frontend code, infrastructure definitions, course reports, or product documents.

## Structure

- `src/competehub_api/`: Flask application package.
- `src/competehub_api/blueprints/`: HTTP route groups.
- `src/competehub_api/models/`: SQLAlchemy models and enums.
- `src/competehub_api/services/`: Business workflows and state transitions.
- `src/competehub_api/repositories/`: Database query helpers.
- `src/competehub_api/schemas/`: Marshmallow validation and serialization schemas.
- `src/competehub_api/tasks/`: Celery workers and scheduled task entrypoints.
- `tests/`: Backend tests.
- `migrations/`: Alembic migration files, created when migrations are initialized.

## Local Commands

Preferred commands from the repository root:

```bash
just api-sync
just api-dev
just api-test
just api-lint
just api-format
```

Raw Python commands should go through the workspace-safe helper:

```bash
./scripts/agent-env.sh uv sync --project apps/api
./scripts/agent-env.sh uv run --project apps/api pytest
./scripts/agent-env.sh uv run --project apps/api ruff check .
./scripts/agent-env.sh uv run --project apps/api flask --app competehub_api.app:create_app run --debug
```

Local PostgreSQL and Redis can be started with `just infra-up`.

## Local Conventions

- Keep route handlers thin; business logic belongs in `services/`.
- Put reusable database queries in `repositories/`.
- Keep database facts in PostgreSQL; Redis is not a source of truth.
- Use Marshmallow for request and response schemas unless an ADR supersedes this choice.
- Add or update migrations whenever model changes require database schema changes.
- Keep Celery tasks idempotent and call services instead of duplicating business rules.
