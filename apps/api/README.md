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
- `migrations/`: Alembic migration files for reproducible schema upgrades.

## Local Commands

Preferred commands from the repository root:

```bash
just api-sync
just api-dev
just api-worker
just api-worker-beat
just api-db-upgrade
just api-test
just api-migration-test-postgres
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

Apply committed migrations with:

```bash
./scripts/agent-env.sh uv run --project apps/api flask \
  --app competehub_api.app:create_app db upgrade --directory apps/api/migrations
```

`migrations/README` defines the first-baseline adoption policy. In particular,
an older disposable development database created with `db.create_all()` must be
reset before upgrade; stamping is valid only after confirming that a database
already matches the exact current metadata.
Databases already on the committed `61f2c8e4a9bd` predecessor automatically
bridge owned mutable competition data into immutable publication revisions;
unowned rows stop before schema mutation and must be assigned an owner first.

The Playwright harness uses `create_e2e_app` and the guarded `seed-e2e --reset`
command to rebuild only `.cache/tmp/competehub-e2e.db`. That factory is test
support for `just web-e2e`; it is not a development or production seed path.
It alone tolerates a one-second future skew in signed Cookie timestamps so a
small host-clock correction cannot invalidate a deterministic browser actor;
development and production session validation are unchanged.

## Local Conventions

- Keep route handlers thin; business logic belongs in `services/`.
- Put reusable database queries in `repositories/`.
- Keep database facts in PostgreSQL; Redis is not a source of truth.
- Use Marshmallow for request and response schemas unless an ADR supersedes this choice.
- Add or update migrations whenever model changes require database schema changes.
- Keep Celery tasks idempotent and call services instead of duplicating business rules.
- Verification-email HTTP paths only commit transactional outbox rows. Run both
  `just api-worker` and `just api-worker-beat` when public registration is enabled;
  SMTP delivery belongs to the worker.
- Reminder delivery also uses PostgreSQL as its source of truth. Beat dispatches
  due `pending` rows, requeues eligible scheduled failures, and drains expired
  in-app messages. Run both worker processes anywhere reminder delivery or the
  message center is enabled; Redis is scheduling infrastructure, never the sole
  reminder record.
- Reminder dispatch/requeue intervals, batch sizes, retry attempts, and retry
  base delay have bounded environment-backed defaults in `config.py`; all
  operator-facing names and defaults are listed in the repository `.env.example`.
  Message retention itself is not configurable: every message is retained for
  exactly 365 days from `created_at`; only cleanup cadence and batch size are
  tunable.
