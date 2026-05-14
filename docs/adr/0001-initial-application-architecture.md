# ADR 0001: Initial Application Architecture

## Status

Accepted

## Context

CompeteHub is still in repository initialization. The product direction is stable enough to define technical boundaries, but many implementation details may evolve as the backend and frontend are scaffolded. The required base stack is Vue, Flask, and Redis. The existing `apps/api` directory is only a placeholder and does not yet represent a stable backend structure.

The PRD defines a student-centered competition discovery system with administrator-managed competition data, rule-based recommendations, subscriptions, in-app reminders, and later extensibility for content and community features.

## Decision

Use a frontend/backend separated monorepo:

- `apps/web`: Vue 3 + Vite + TypeScript frontend.
- `apps/api`: Flask backend API, reorganized into a proper `competehub_api` package.
- PostgreSQL as the primary system-of-record database.
- Redis for Celery broker/result backend, caching, rate limiting, short-lived locks, and transient runtime state.
- Celery workers for reminder generation, competition expiration jobs, and later semi-automated collection candidate tasks.
- REST API under `/api/v1`.

The existing `apps/api` placeholder may be restructured during initialization. The uv cache issue must be handled through a workspace-safe wrapper such as `scripts/agent-env.sh`.

## Consequences

- The project can satisfy the required Vue + Flask + Redis stack while avoiding Redis as a source of truth for business data.
- PostgreSQL keeps users, competitions, subscriptions, reminders, audit logs, and recommendation rules durable and queryable.
- Celery keeps reminder and maintenance work outside request/response paths.
- The backend package name should change from generic `api` to `competehub_api`.
- Every semantic folder created during initialization must include a `README.md` so local conventions remain close to the code.
- If future requirements add advanced Chinese full-text search, the project may add a dedicated search service without replacing the core data model.
