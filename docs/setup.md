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

The repository includes `mise.toml` for developers who prefer managing tool
versions through mise. Using mise is optional; the documented `just`, `uv`, npm,
and Docker commands remain the source of truth.

## Configure Git Before Committing

Set Git to normalize line endings to `LF` before your first commit. This prevents platform-specific `CRLF` changes from being introduced, especially on Windows.

```bash
git config core.eol lf
git config core.autocrlf input
```

!!! warning

    This does not mean the `CRLF` Windows-style line endings are permitted.

## Install pre-commit

Ensure that `just` and `uv` are available on your `PATH`. If not, refer to [Tooling](./tooling.md) for installation instructions.

```bash
just pre-commit
```

## Install Dependencies

Install backend and frontend dependencies plus the Chromium browser used by
Playwright through the root setup recipe:

```bash
just setup
```

The equivalent component commands are:

```bash
just api-sync
just web-install
just web-e2e-install
```

## Configure Environment

Copy the example environment file for local development:

```bash
cp .env.example .env
```

The default values point to the PostgreSQL and Redis services defined in `infra/docker-compose.yml`.

Public email registration is disabled by default. To enable it, set both:

```dotenv
PUBLIC_EMAIL_REGISTRATION_ENABLED=true
EMAIL_VERIFICATION_SENDER_DSN=smtp://username:password@smtp.example.edu:587?from=CompeteHub%20%3Cnoreply%40example.edu%3E&starttls=true
```

Use `smtp://` with `starttls=true` for STARTTLS or `smtps://` for implicit TLS.
Percent-encode credentials and the `from` query value. The API fails fast at
startup when public email registration is enabled without a valid sender; when
registration is disabled, the endpoint returns `registration_unavailable`.
Registration and resend commit a verification-delivery outbox row and return
without contacting SMTP. A running Celery worker and scheduler are therefore
required whenever public registration is enabled.

## Start Local Services

Start PostgreSQL and Redis:

```bash
just infra-up
```

Create or upgrade the application schema before starting the API:

```bash
just api-db-upgrade
```

This runs the committed Alembic revisions against `DATABASE_URL`. Do not use
`db.create_all()` for a development or production database. Migration authors
can exercise fresh and legacy upgrade/downgrade paths against disposable local
PostgreSQL databases with `just api-migration-test-postgres` after `just infra-up`.
The legacy path safely bridges authentication data but does not infer immutable
publication identities from unknown older business-table shapes. Reset an old
disposable database; use a reviewed data-preserving bridge for shared data.

Stop them when finished:

```bash
just infra-down
```

## Start Applications

Run the backend API:

```bash
just api-dev
```

When public email registration is enabled, run the verification-delivery worker
and scheduler in two additional terminals:

```bash
just api-worker
just api-worker-beat
```

The worker polls committed outbox rows, retries transient delivery failures with
bounded backoff, and discards rows whose challenge was consumed or expired.
Starting only the API accepts registration requests but cannot deliver their
verification messages.

Run the frontend app:

```bash
just web-dev
```

By default, the frontend proxies `/api` requests to the Flask API on `localhost:5000`.

## Verify The Workspace

Run the main checks before committing:

```bash
just doctor
just check
```

Use component recipes such as `just api-test`, `just web-build`,
`just web-e2e`, `just docs-build`, or `just infra-config` when you only need one
area.
