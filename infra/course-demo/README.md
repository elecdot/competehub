# Deployment v1 Compose Stack

This directory owns the bounded, owner-operated course deployment described in
[Course Demo Deployment](../../docs/deployment.md). It runs PostgreSQL, a
transient Redis, the Gunicorn API, Celery worker/scheduler, an Nginx-hosted Vue
build, and a checksum-pinned Cloudflare Quick Tunnel.

Use the repository entry points instead of invoking partial Compose service
sets:

```bash
just course-demo-prepare
just course-demo-registration enable
just course-demo-config
EXPECTED_RELEASE_SHA=<full-origin-main-sha> just course-demo-prewarm
EXPECTED_RELEASE_SHA=<full-origin-main-sha> just course-demo-migrate
EXPECTED_RELEASE_SHA=<full-origin-main-sha> just course-demo-bootstrap
EXPECTED_RELEASE_SHA=<full-origin-main-sha> just course-demo-deploy
```

Important boundaries:

- Docker object names use the stable `competehub-course-deployment` namespace;
  labels and `status` record generation `v1` and the complete release SHA.
- Every mutating release command fetches `origin/main` and requires
  `HEAD == origin/main == EXPECTED_RELEASE_SHA` plus a clean worktree.
- Compose calls fix the formal project name and neutralize material ambient
  interpolation/control overrides; private env files accept only the exact six
  generated keys.
- `prepare` creates fresh private secrets and refuses to inherit or overwrite
  an existing `.env`.
- Registration is disabled by default. Its interactive enable command stores
  the SMTP DSN only in the ignored mode-0600 `.env` and never prints it.
- The checksum-pinned cloudflared build input supports only an x86_64/amd64
  Linux host/target and fails closed on other host architectures. Its ignored
  cache boundary refuses symlinks/non-directories, and a failed unique
  temporary download is removed before it can become the cached binary.
- Migration, fictional demo bootstrap, and public deployment are separate
  operations. `deploy` does not run either data command.
- PostgreSQL is the only persistent application-data volume. Redis disables
  RDB and AOF, mounts `/data` as container tmpfs, and has no Docker volume.
- Only Nginx binds to the host, on loopback. The Quick Tunnel URL is temporary.
- Failed deployment cleanup confirms that no project tunnel remains running;
  otherwise it reports that public access may still be active and names the
  explicit status/stop recovery commands.
- Runtime containers use `restart: unless-stopped`; see the deployment guide
  before relying on Docker daemon or host restarts.
- `destroy DESTROY` removes only this Compose project's containers, network,
  and PostgreSQL volume. It retains the private environment, images, caches,
  checkout, provider-side records, and preserved v0 assets.

Use [the operations ledger template](OPERATIONS.template.md) for the private
record created before the first server mutation. Do not commit the filled
ledger or any SMTP credential.
