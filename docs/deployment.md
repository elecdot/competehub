# Course Demo Deployment

This guide owns Deployment v1: the first project-supported, owner-operated
single-server deployment for CompeteHub course acceptance. Its identity is
`Deployment v1` plus one complete Git commit SHA.

Deployment v1 is a repeatable, time-bounded public demonstration with fictional
data and an explicit teardown. It is not a production security, capacity,
availability, operational-certification, or SLA claim.

## Supported topology

```text
public browser
    -> Cloudflare Quick Tunnel (temporary HTTPS URL)
    -> Nginx: Vue static files and /api reverse proxy
    -> Gunicorn API
       -> PostgreSQL (the only persistent application-data volume)
       -> Redis (transient Celery broker/runtime state)
          <- Celery worker and scheduler
```

The stable Compose namespace is `competehub-course-deployment`. Labels and
`just course-demo-status` record generation `v1` and the complete release SHA.
This namespace does not match the historical v0
`competehub-course-demo` objects. The stable namespace is the cleanup ownership
boundary; generation/release labels make containers, the default network, and
the named PostgreSQL volume inventory-visible. Destruction additionally
refuses a same-name data volume with unexpected labels.

Only Nginx publishes a host port, at `127.0.0.1:8080` by default. PostgreSQL,
Redis, API, worker, and scheduler have no host-published ports. The tunnel makes
an outbound connection; the host does not need public HTTP/HTTPS listeners.

Redis mounts `/data` as an explicit container tmpfs, has no Docker volume, and
disables RDB and AOF. PostgreSQL uses one volume labelled with both generation
`v1` and its complete release SHA.
Migration, bootstrap, and deploy refuse a volume created for another SHA.
Deployment v1 does not restore v0 data, perform an in-place v0 upgrade, or
promise application/schema upgrades between different releases. Rebuilding a
different release is a fresh-dataset operation.

The demo bootstrap uses #57's fictional institution, accounts, and business
facts. Deployment v1 does not add a configurable host institution or a
first-administrator provisioning workflow and must not be described as a
conforming real-institution rollout.

## Host prerequisites and capability boundary

The host needs:

- Git;
- Docker Engine and Docker Compose v2 available to the deployment owner;
- an x86_64/amd64 Linux host and Docker target (the checksum-pinned
  cloudflared build input is `cloudflared-linux-amd64`);
- Python 3, `curl`, and `sha256sum`;
- outbound access to GitHub, ECR Public, GHCR, PyPI/files.pythonhosted, the npm
  registry, and Cloudflare;
- enough disk for the checkout, Docker images/build cache, and PostgreSQL
  volume.

Deployment v1 does **not** install host `uv`, Node.js, Nginx, cloudflared, a
systemd unit, a Docker daemon, a Docker group membership, firewall rules, TLS
certificates, or a Cloudflare account token. `uv`, Node, Nginx, and cloudflared
exist only inside Docker build/runtime layers. The verified cloudflared binary
is also retained under the ignored repository `.cache/` solely as a Docker
build input; it is not added to the host `PATH`. Prewarm refuses symlink or
non-directory cache boundaries and a symlink/non-regular cached binary.

The small server is not the full validation machine. Run the repository gates
on the development machine and in CI before choosing the release SHA. The
server performs only configuration, sequential image build, explicit data
initialization, startup, and smoke checks.

`just infra-config` includes a Docker context regression. It creates and
removes one Git-ignored Python-bytecode probe plus a temporary local export. On
a host without Buildx, its compatibility path also creates and removes one
exact temporary image and stopped container. Either builder may retain a small
cache entry; the check never prunes unrelated Docker state.

The first server rollout must wait until the Celery result-accumulation fix is
merged into the same exact `origin/main` release.

## Private operations ledger

Before the first server mutation, copy the repository file
`infra/course-demo/OPERATIONS.template.md` to an owner-controlled private path.
Record the release SHA, checkout, current Docker state, commands, validation
evidence, public URL, retained assets, and teardown trigger there. Never record
the SMTP DSN or commit the filled ledger.

## Prepare fresh secrets

Use a dedicated checkout. Before running a release command, fetch and detach at
the reviewed current main revision:

```bash
git fetch --no-tags origin refs/heads/main:refs/remotes/origin/main
git switch --detach origin/main
git status --short
git rev-parse HEAD
```

`git status --short` must print nothing. Save the full `git rev-parse HEAD`
value as the reviewed release SHA.

Create a fresh ignored environment:

```bash
just course-demo-prepare
just course-demo-config
```

`prepare` writes `infra/course-demo/.env` with mode `0600`, fresh random
application/database secrets, generation `v1`, registration disabled, and no
SMTP DSN. It refuses any symlink, including a broken symlink, refuses to reuse
or overwrite an existing path, and refuses to generate a new database password
while the formal PostgreSQL volume already exists. If either asset exists
unexpectedly, run `just course-demo-status`, inspect and privately archive
evidence/data when needed, then explicitly remove the formal project with
`just course-demo-destroy DESTROY` (or explicitly archive/remove the old
environment path) before a fresh `prepare`. Never silently carry an old secret
or volume into v1.

Runtime commands accept exactly one assignment for each of the six generated
keys and reject blank/comment, duplicate, unknown, or non-assignment lines.
This prevents private env files from embedding `COMPOSE_PROJECT_NAME`,
`COMPOSE_REMOVE_ORPHANS`, `RELEASE_SHA`, or another control override.

### Explicitly authorize public registration

Registration remains disabled unless the owner separately runs:

```bash
just course-demo-registration enable
just course-demo-registration status
just course-demo-config
```

The enable operation asks interactively for the private `smtp://` or `smtps://`
sender DSN with hidden input, then requires the literal confirmation `ENABLE`.
It writes only the ignored mode-0600 environment and never prints the DSN. The
application still fails closed if sender configuration is invalid.

Disable and clear the stored DSN with:

```bash
just course-demo-registration disable
```

Enable/disable changes only the private `.env`. Already-created API, worker,
and beat containers retain their prior environment and possibly the old DSN
until `deploy` recreates them or `destroy` removes them. `stop` makes that
environment inactive but retains it in stopped container metadata. `status`
reports the configured value; smoke compares the live public capability with
that value and fails on a mismatch.

Configuration is not delivery: actual registration can create provider-side
mail, delivery, abuse, and authentication logs. Removing `.env` does not recall
mail or revoke an SMTP authorization token. Rotate/revoke that credential
separately after the demo when required.

## Release equality gate and prewarm

Set the reviewed full SHA explicitly:

```bash
export EXPECTED_RELEASE_SHA=<40-character-origin-main-sha>
just course-demo-prewarm
```

Every `prewarm`, `migrate`, `bootstrap-demo`, and `deploy` invocation fetches
`origin/main` and refuses unless:

```text
HEAD == origin/main == EXPECTED_RELEASE_SHA
```

The worktree must also be clean. A descendant commit, PR head, dirty checkout,
abbreviated SHA, stale remote-tracking ref, or release-bypass flag is not
accepted.

All Compose calls fix `--project-name competehub-course-deployment`, clear
material ambient Compose/secret/port/registration variables, and pass only the
script-owned release SHA. Stop/log/destroy use the checked-in non-secret example
for interpolation, never a possibly damaged private environment.

`prewarm` validates Compose, pulls version-selected base/runtime image tags,
downloads the official cloudflared `2026.5.2` Linux binary into `.cache/`,
verifies its pinned SHA-256, builds the tunnel image, then builds API and web
images sequentially. Registry tags are not digest pins, so this is not a
byte-for-byte image-reproducibility claim; the exact source SHA remains the
release identity. Prewarm starts no containers and opens no public entry point.
It retains Docker images, BuildKit layers, and the verified ignored cache file.
Downloads use a unique temporary file inside that verified cache directory,
remove it on failure or interruption, and atomically replace the cached binary
only after checksum verification. The tunnel build refuses a
non-x86_64/amd64 host or Docker target before using that
architecture-specific binary.

The root Docker ignore rules recursively exclude environment/auth files,
caches, dependencies, build/test outputs, and ignored binary/media artifacts
from the BuildKit context. The web Dockerfile copies only its tracked package
files, HTML/type/config inputs, and `src/`; ignored `.env.local` or other local
frontend files cannot silently alter the exact-SHA build.

## Initialize data explicitly

Migration and demo bootstrap are intentionally separate and neither is part of
`deploy`:

```bash
just course-demo-migrate
just course-demo-bootstrap
```

`migrate` creates/starts PostgreSQL and transient Redis if absent, refuses a
same-name PostgreSQL volume without the v1 generation and exact release-SHA
labels, applies Alembic migrations, and prints the current revision. It does
not seed demo data.

`bootstrap` runs `bootstrap-development-demo` once in a one-off container with
`COMPETEHUB_ENV=development`. Persistent services remain in production mode.
The bootstrap is non-destructive and idempotent, but this deployment contract
uses it only for the fresh fictional v1 dataset. Never use `--reset-demo`,
`seed-e2e --reset`, or a v0 dump/volume.

If an abandoned formal-deployment volume must be discarded before a fresh
attempt, first inspect `just course-demo-status`, preserve evidence if needed,
then run the explicit destructive command documented below.

## Deploy, verify, and share

Start the already-built, migrated, and explicitly bootstrapped stack:

```bash
just course-demo-deploy
just course-demo-status
just course-demo-url
just course-demo-smoke
```

`deploy` uses the exact prebuilt SHA-tagged images and does not build, migrate,
or bootstrap. It first stops this project's existing tunnel so a rerun cannot
leave an old public path open during local validation. It then starts/recreates
API/worker/scheduler/web, verifies the SPA shell and its built JavaScript asset,
requires discovery to return at least one bootstrapped item, and verifies that
the runtime auth capability exactly matches configured registration. Worker
and scheduler checks follow. A bounded, read-only Redis inspection must also
find no `celery-task-meta-*` result key, guarding the #68 result-suppression
contract against renewed accumulation. It starts the Quick Tunnel only
afterward and repeats the SPA/health/discovery/capability checks publicly. Once
deployment enters this stop-and-switch stage, any later failure keeps this
project's tunnel stopped. A preflight failure leaves the previously running
release unchanged. Failure cleanup verifies that the tunnel is no longer
running. If Docker cannot stop it or the stopped state cannot be confirmed, the
command prints `PUBLIC ACCESS MAY STILL BE ACTIVE` with explicit status/stop
recovery commands instead of claiming that public access ended.

`status` is the non-secret owner inventory. It reports:

- generation, checkout HEAD, fetched `origin/main`, and runtime release label;
- configured registration state without the sender DSN;
- containers, image references, health/status, and published ports;
- the labelled PostgreSQL volume and Compose network;
- current Quick Tunnel URL;
- retained environment/images/cache boundary and restart-policy behavior.

Verify the URL from a different network before sharing it. Use the fictional
accounts documented in [Setup](setup.md#bootstrap-the-development-demo), and
share credentials only for the acceptance window.

When registration is enabled, capability smoke proves configuration alignment,
not SMTP delivery. The owner must separately authorize one runtime acceptance:
use a disposable test address through the public UI/API, receive and verify the
code, then log in. Record only pass/fail in the private operations ledger;
never record the DSN, code, or address. This creates a test user/identity row in
PostgreSQL and provider/mail delivery logs. Decide explicitly whether to retain
that fictional test user until teardown; removing `.env` does not remove either
the database row or provider records.

Quick Tunnels are a development/testing facility. The random
`trycloudflare.com` URL can change after tunnel recreation and has no project
SLA. Always rerun `just course-demo-url` before redistribution.

## Operate and diagnose

Bound log output to the latest 200 lines:

```bash
just course-demo-logs
just course-demo-logs api
just course-demo-logs web
just course-demo-logs tunnel
```

Docker uses its `json-file` driver with rotation (`10m`, three files) for each
container. Application access, error, worker, SMTP-delivery, and tunnel logs can
remain in Docker or external provider records until their own retention or
explicit cleanup. The script never prints the environment.

All runtime containers use `restart: unless-stopped`. If they still exist, they
may restart after the Docker daemon or host restarts, and the tunnel may return
with a different public URL. `stop` manually stops and retains the containers,
which suppresses automatic restart until an explicit start/deploy. `destroy`
uses Compose `down`, removing the project containers entirely.

## Stop, destroy, and recover

Stop public access and runtime while retaining PostgreSQL:

```bash
just course-demo-stop
```

`stop` manually stops the current Compose services. It retains:

- the stopped containers, network, and their bounded Docker logs;
- the PostgreSQL volume;
- `infra/course-demo/.env`;
- project and base images;
- Docker BuildKit cache and `.cache/course-demo-tunnel/cloudflared`;
- repository checkout;
- external mail/tunnel/provider records;
- the preserved v0 archive and any historical v0 Docker namespace.

Docker records the manual stop, so `restart: unless-stopped` does not restart
those containers after a daemon/host restart. A later explicit `deploy` starts
them again.

For an exact fresh rebuild, inspect the preview and authorize destruction:

```bash
just course-demo-destroy DESTROY
```

`destroy` prints this project's containers, network, and labelled volume, then
removes only those Compose objects. It does not run a global Docker prune,
remove images/cache/checkout, delete `.env`, revoke SMTP credentials, erase
provider records, or touch v0 assets. A same-name PostgreSQL volume without the
expected project and v1 generation labels causes a refusal before Compose can
delete it.

After destroy, confirm `just course-demo-status` has no project containers,
network, or volume. Remove the private environment only with a separately
reviewed exact path, and revoke the SMTP credential separately if required.

Deployment v1 has no database downgrade or in-place release upgrade procedure.
Recovery is: stop public access, preserve evidence when needed, destroy the
formal project data explicitly, detach the exact reviewed `origin/main`, then
repeat prepare/config/prewarm/migrate/bootstrap/deploy with fresh data.

## Command side-effect matrix

| Operation | Host/project changes | Retained afterward |
| --- | --- | --- |
| `prepare` | After proving the formal volume is absent, creates one non-symlink ignored mode-0600 environment with fresh secrets | `.env`; no Docker objects |
| `registration enable/disable` | Atomically changes only registration keys in `.env`; existing containers retain prior values until deploy/destroy (`stop` only makes them inactive) | Private configured flag/DSN state; provider effects begin only when mail is sent |
| `config` | Reads files and parses Compose without starting services | No intentional runtime asset |
| release guard | Fetches `origin/main`, updating the remote-tracking ref and `FETCH_HEAD` | Git fetch metadata |
| `prewarm` | Pulls/builds images and downloads verified cloudflared build input | Images, BuildKit cache, ignored `.cache` file |
| `migrate` | Creates/changes PostgreSQL schema; starts PostgreSQL and transient Redis | PostgreSQL volume, containers/network/logs; Redis `/data` tmpfs and no Redis volume |
| `bootstrap` | Inserts/verifies #57 fictional demo facts | Business data in PostgreSQL |
| `deploy` | Starts runtime/tunnel and creates a temporary public URL | Containers/network/logs, images/cache, PostgreSQL, provider tunnel record |
| `status`, `url`, `smoke`, `logs` | Read/health traffic; smoke checks SPA/data/capability and read-only-scans Redis for result keys | Existing assets plus diagnostic/access logs |
| `stop` | Manually stops current services and ends public access | Stopped containers/network/logs, PostgreSQL, `.env`, images/cache, checkout, provider/v0 records |
| `destroy DESTROY` | Removes exact project containers/network/PostgreSQL volume | `.env`, images/cache, checkout, provider/v0 records |
