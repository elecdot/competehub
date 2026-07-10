# ADR 0015: Version Time Node Changes And Rebuild Reminders

## Status

Accepted

## Context

Official sources can postpone a competition or change a deadline within the
same赛事届次 after students have subscribed. Replacing time-node rows loses the
identity needed to cancel old reminder plans. Mutating already-sent reminders
would also rewrite what a student actually received, while silently changing a
calendar can leave the student unaware of the correction.

## Decision

A schedule correction preserves an edition-scoped `logical_node_key` but
creates a new immutable snapshot row and increments `node_revision` only when
behavior-bearing node facts change. A snapshot ID identifies only the facts
inside one赛事届次修订; reminders keep an FK to that exact snapshot, while
reconciliation matches snapshots by logical key and node revision. The service
records old/new values and reason, cancels superseded pending plans, and creates
plans only for future triggers. Sent reminders are immutable.

For a published赛事届次, each effective node revision creates at most one
赛事时间变更通知 per active subscriber. If the recalculated ordinary reminder time
has already passed, the system does not backfill a message that pretends it was
sent on time; the change notification explains the update instead. The personal
赛事日历 reads the current node revision, while audit history retains prior
values.

## Consequences

Time-node updates cannot be blind list replacement once a届次 has
reminder-dependent state. Public APIs must distinguish snapshot ID, logical
key, and node revision; reminder idempotency includes user, edition, logical
key, and node revision, while exact historical evidence retains the snapshot
FK.
