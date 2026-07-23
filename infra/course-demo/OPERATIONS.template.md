# CompeteHub Deployment Operations Ledger

Copy this template to an owner-controlled private location before the first
server mutation. Do not fill or commit this repository copy.

## Identity

- Deployment generation: `v1`
- Full release SHA:
- Deployment owner:
- Checkout path:
- Compose project: `competehub-course-deployment`
- Started at:
- Planned teardown trigger/date:

## Pre-existing state

- Docker/Compose versions:
- Host/Docker architecture (required: x86_64/amd64):
- Existing `competehub-course-deployment` objects:
- Historical v0 objects/archive location and confirmation left untouched:
- Host capability changes authorized for this run: none

## Private configuration

- Environment path:
- File mode: `0600`
- Fresh v1 secrets created: yes/no
- Public registration: enabled/disabled
- SMTP sender configured: yes/no (never record the DSN)
- SMTP credential rotation/revocation owner:

## Release evidence

- Development-machine/full-gate evidence:
- CI run:
- Exact-main equality check:
- Prewarm result:
- Migration result:
- Explicit fictional demo bootstrap result:
- Deploy result:
- Local/public smoke result:
- Runtime SMTP acceptance when registration is enabled: pass/fail/not applicable
  (never record the DSN, code, or disposable address)
- SMTP acceptance side effects recorded: test user row and provider/mail logs
- Current Quick Tunnel URL:

## Server asset inventory

Paste or attach the non-secret output of:

```bash
just course-demo-status
```

Record any additional server path, process, service, timer, firewall, group, or
package change. Expected value for Deployment v1 is `none`.

## Stop or teardown evidence

- Operation: stop/destroy
- Performed at:
- Public URL no longer responds:
- Removed project containers/network/volume:
- Retained private environment:
- Retained project/base images and BuildKit cache:
- Retained checkout:
- Retained provider mail/tunnel logs:
- SMTP credential revoked separately when required:
- Preserved v0 archive unchanged:
