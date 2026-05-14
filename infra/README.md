# Infrastructure

This directory contains local infrastructure definitions and deployment-supporting assets.

## Responsibilities

- Own local Docker Compose definitions.
- Document local service ports, credentials, and environment variable expectations.
- Keep infrastructure concerns separate from application source code.

## Services

- PostgreSQL: primary development database, exposed on `localhost:5432`.
- Redis: cache, rate limiting support, and Celery broker/result backend, exposed on `localhost:6379`.

## Commands

Run from the repository root:

```bash
just infra-up
docker compose -f infra/docker-compose.yml ps
just infra-down
```

Validate the Compose file without starting services:

```bash
docker compose -f infra/docker-compose.yml config
```

Wait for health checks during startup:

```bash
docker compose -f infra/docker-compose.yml up -d --wait
```

## Local Conventions

- Do not commit real secrets.
- Keep example values in `.env.example`.
- Prefer service names that match runtime dependencies, such as `postgres` and `redis`.
- Do not remove local volumes unless you intentionally want to reset development data.
