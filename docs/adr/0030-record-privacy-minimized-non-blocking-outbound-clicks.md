# ADR 0030: Record Privacy-Minimized Non-Blocking Outbound Clicks

## Status

Accepted

## Context

The stable product requirements expected official-channel click statistics, the
API named an endpoint, and P2 governance prioritized the metric, while the P1
feature PRD treated it as optional and no implementation existed. Making the
analytics request a prerequisite for opening an official site would harm the
primary user task. Identifying individual students or adopting a third-party
analytics SDK is also unnecessary for aggregate course-project statistics.

## Decision

Outbound click recording is a required non-blocking P1 discovery follow-up and
a prerequisite for P2 outbound statistics. External HTTP(S) links remain real
browser links and open directly with `noopener/noreferrer`. Frontend code sends
a best-effort beacon or keepalive request at activation; failure, timeout, or
blocking of that request never delays or prevents navigation. The API does not
proxy or redirect the target.

Clients submit only a controlled target type and source surface. The server
resolves `source_url`, `official_url`, or `attachment_url` from the edition's
currently viewable public revision and rejects missing or unavailable targets.
It records edition id, revision id, target type, source surface, server time,
and `actor_kind` as authenticated or anonymous.

Analytics rows do not store user id, account identifiers, IP address,
User-Agent, or a cross-day visitor identifier. Request-source information may
be held ephemerally for rate limiting but is not copied into analytics storage.
Every accepted event is counted as a click; the metric is not a unique-person or
registration-conversion measure and may undercount because delivery is
best-effort.

Raw events are retained for 90 days. A repeatable job aggregates them by
`Asia/Shanghai` product date, edition, target type, source surface, and actor
kind before expiry. Daily counts are durable and idempotent. Admin surfaces must
label the metric as recorded outbound clicks and disclose its interpretation
and possible undercount.

## Consequences

The product can demonstrate useful channel engagement without tracking named
students, depending on an external analytics provider, or compromising the
official-link workflow. Implementation needs a small event table, aggregate
table, rate-limited endpoint, best-effort frontend call, retention job, and
tests proving navigation independence and absence of user-level fields.
