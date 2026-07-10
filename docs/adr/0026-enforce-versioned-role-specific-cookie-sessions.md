# ADR 0026: Enforce Versioned Role-Specific Cookie Sessions

## Status

Accepted

## Context

The initial Flask Cookie Session stored only a user id. Protected routes loaded
that user but did not consistently reject a user disabled after login, and no
idle or absolute lifetime was defined. Clearing one browser cookie cannot revoke
signed cookies already held by other devices. A single short timeout would also
make the low-risk student workflow unnecessarily inconvenient or leave
administrator access open for too long.

## Decision

Each user account has a monotonically increasing `session_version`. A signed
cookie session contains only `user_id`, that version, `issued_at`, and
`last_activity_at`. Login clears the prior session before issuing new values.
Every protected request reloads the account before route behavior and requires
an active status, matching version, and valid role-specific deadlines.

Student sessions expire after 24 hours without authenticated activity or seven
days from login, whichever occurs first. Administrator sessions expire after 30
minutes idle or eight hours absolute. Activity refreshes only the idle timestamp
and cannot extend the absolute deadline. P1 has no user-selectable remember-me
mode.

Changing an account's role or capabilities, disabling it, confirming credential
compromise, or explicitly terminating all sessions atomically increments
`session_version`. All existing devices are rejected on their next request, the
presented session is cleared, and the API returns a generic `401` before
executing route behavior. Ordinary logout clears only the current browser. P1
permits concurrent sessions and does not add a device-session registry or
per-device revocation UI.

## Consequences

Student sessions can survive normal cross-day use when activity remains within
the idle window, but no session lasts longer than one week. Administrator
exposure remains substantially shorter. The system gains server-authoritative
revocation without introducing a server-side session store, at the cost of one
account lookup on protected requests and timestamp validation in the shared
authentication guard.
