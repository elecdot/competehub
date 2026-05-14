# Infrastructure

This directory contains local infrastructure definitions and deployment-supporting assets.

## Responsibilities

- Own local Docker Compose definitions.
- Document local service ports, credentials, and environment variable expectations.
- Keep infrastructure concerns separate from application source code.

## Services

- PostgreSQL: primary development database.
- Redis: cache, rate limiting support, and Celery broker/result backend.

## Commands

Run from the repository root:

```bash
just infra-up
just infra-down
```

## Local Conventions

- Do not commit real secrets.
- Keep example values in `.env.example`.
- Prefer service names that match runtime dependencies, such as `postgres` and `redis`.
