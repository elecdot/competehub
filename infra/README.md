# Infrastructure

This directory contains local infrastructure definitions and deployment-supporting assets.

`infra/docker-compose.yml` is development-only infrastructure. It publishes
PostgreSQL and Redis with fixed development credentials and must not be exposed
as a public application deployment. The temporary public course stack lives
under [course-demo](course-demo/README.md), uses the isolated
`competehub-course-deployment` Compose namespace, and is operated through
`scripts/course-demo.sh`.

## Responsibilities

- Own local Docker Compose definitions.
- Own the bounded course deployment without turning it into a general
  production platform.
- Document local service ports, credentials, and environment variable expectations.
- Keep infrastructure concerns separate from application source code.

## Services

- PostgreSQL: primary development database, exposed on `localhost:5432`.
- Redis: cache, rate limiting support, and Celery broker/runtime coordination,
  exposed on `localhost:6379`.

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
- Never expose the development Compose file to the public network.
- Read [Course Demo Deployment](../docs/deployment.md) before running any
  formal deployment command or cleanup.
