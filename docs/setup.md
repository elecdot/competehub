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
just seed-recommendation-rules
```

This runs the committed Alembic revisions against `DATABASE_URL`. Do not use
`db.create_all()` for a development or production database. Migration authors
can exercise fresh and legacy upgrade/downgrade paths against disposable local
PostgreSQL databases with `just api-migration-test-postgres` after `just infra-up`.
The legacy path safely bridges authentication data but does not infer immutable
publication identities from unknown older business-table shapes. Reset an old
disposable database; use a reviewed data-preserving bridge for shared data.
The committed `61f2c8e4a9bd` predecessor is a known shape and is bridged
automatically when every existing competition has `created_by_id`; assign an
owner before upgrade if the migration reports unattributed competition ids.

The recommendation-governance migration is deliberately fail-closed when the
legacy mutable `recommendation_rules` predecessor contains rows. It checks
before destructive DDL, leaves the legacy table and data intact, and does not
promote unaudited mutable rules into active v1. Back up that database and make
an explicit, reviewed data-migration decision before retrying. After a fresh or
empty-predecessor upgrade, `just seed-recommendation-rules` invokes the standard
Flask CLI seed. The first run creates immutable active v1. Re-running it is
idempotent when persisted v1 exactly matches the reproducible snapshot and null
seed lineage, whether v1 is still active or has been normally retired by a
governed successor. The command reports the persisted status and never
reactivates, overwrites, or rolls back v1; a conflicting v1 fails without
overwrite.

## Bootstrap The Development Demo

After migrations, provision or verify the final-demo dataset with:

```bash
just bootstrap-development-demo
```

The command runs only with `COMPETEHUB_ENV=development`. It does not create,
drop, or migrate tables. The default operation is idempotent: exact demo facts
are retained, missing owned facts are recreated, and conflicting or manually
changed reserved facts cause a full rollback instead of an overwrite.

The public development-only credentials are:

| Actor | Account | Password |
| --- | --- | --- |
| Student | `student.day1@example.edu` | `violet harbor lantern orbit 47` |
| Editor | `admin.day1@example.edu` | `copper meadow signal river 82` |
| Reviewer | `reviewer.day1@example.edu` | `silver orchard compass cloud 59` |
| User owner | `owner.day1@example.edu` | `indigo summit owner path 73` |

These values are demonstration credentials, not production secrets or default
production accounts.

When the registered demo facts must be replaced, run:

```bash
just bootstrap-development-demo --reset-demo
```

Reset ownership comes only from the `development_demo.bootstrap.v1`
`system_configs` registry. The reset fails and rolls back when data outside
that registry references a demo account or business record. It never deletes
or rewrites the shared reproducible recommendation rule-set v1.

Do not substitute `seed-e2e --reset`. That command deliberately drops and
recreates only the isolated browser-test database and is rejected by the normal
development app.

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

By default, the frontend proxies `/api` requests to the Flask API on
`127.0.0.1:5000`. Browser E2E uses `E2E_API_PORT` as the single API port source
and derives `VITE_API_PROXY_TARGET` from it. Override `VITE_API_PROXY_TARGET`
only when you intentionally proxy to a separately managed API process.

## Verify The Workspace

Run the main checks before committing:

```bash
just doctor
just check
```

Use component recipes such as `just api-test`, `just web-build`,
`just web-e2e`, `just docs-build`, or `just infra-config` when you only need one
area.
