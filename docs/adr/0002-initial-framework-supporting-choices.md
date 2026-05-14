# ADR 0002: Initial Framework Supporting Choices

## Status

Accepted

## Context

The initial architecture ADR fixes Vue, Flask, PostgreSQL, Redis, and Celery as the broad application shape. Repository initialization also needs smaller framework choices so the first code skeleton is coherent instead of leaving every layer undecided.

These decisions can be superseded later, but changing them should be intentional because they affect scaffolding, local conventions, and tests.

## Decision

- Use Marshmallow for backend request validation and response serialization.
- Use Flask-SQLAlchemy and Flask-Migrate for ORM integration and Alembic migrations.
- Start the frontend without a committed UI component library; document any later UI library choice in a new ADR and `apps/web/README.md`.
- Use npm scripts for the Vue app until there is a concrete reason to standardize on a different JavaScript package manager.
- Use `justfile` as the root developer command entrypoint, with Python commands wrapped by `scripts/agent-env.sh`.

## Consequences

- Backend validation has one clear home under `apps/api/src/competehub_api/schemas`.
- Database migrations can be generated from the Flask app once models stabilize.
- Frontend initialization stays light and avoids early design-system lock-in.
- JavaScript dependency locking will be handled when frontend dependencies are installed.
- Agent and human commands share the same root recipes, reducing drift between documented setup and actual development.
