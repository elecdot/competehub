# ADR 0009: Flask Cookie Session Auth

## Status

Accepted

## Context

The current product is a Vue SPA backed by a Flask API with student and administrator roles. The system does not yet need mobile app token sharing, third-party API access, or microservice-to-microservice authentication. Treating Cookie-based JWT as an equal current option would add refresh, revocation, blacklist, frontend storage, and permission-change invalidation complexity before the core workflow needs it.

## Decision

Use Flask Cookie Session authentication for the current implementation. The frontend must not store long-lived tokens in `localStorage`; authenticated requests rely on the browser session cookie. The session should store only minimal identity facts, and backend authorization should use explicit helpers such as `login_required`, `require_role("admin")`, and `require_self_or_admin`.

## Consequences

Cookie security settings are part of the auth design: use `HttpOnly`, `SameSite=Lax`, and `Secure` in production. State-changing APIs must not use GET, and backend write operations should check `Origin` or `Referer`; a CSRF token can be added later if the write surface requires stronger protection. If the project later needs external clients, stateless scaling constraints, or cross-service auth, token-based auth needs a new decision.
