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
creates a new immutable snapshot row and increments `node_revision` when
behavior-bearing node facts change or the key is reintroduced after an approved
removal. A snapshot ID identifies only the facts inside one赛事届次修订;
reminders keep an FK to that exact snapshot, while reconciliation matches
snapshots by logical key and node revision. The service records old/new values
and reason, cancels superseded pending plans, and creates plans only for future
triggers. A logical key never present in approved edition history starts at
revision one. If an approved revision removes that key and a later approved
candidate re-adds it, submission allocates the approved historical maximum plus
one even when the restored facts match an older snapshot. Sent reminders are
immutable.

For each approved replacement, the system creates at most one consolidated
赛事时间变更通知 per affected active subscriber. It does so only when `occurs_at`,
a selected node's controlled type, or the presence of a selected node changes;
stage, prominence, description, title, and other presentation-only corrections
do not claim that the schedule moved. Pending reminder content still reconciles
to the new public snapshot. If a recalculated trigger is already past, the
system does not backfill an ordinary message that pretends it was sent on time.
The personal赛事日历 reads the current snapshot, while audit history retains old
values.

## Consequences

Time-node updates cannot be blind list replacement once a届次 has
reminder-dependent state. Public APIs must distinguish snapshot ID, logical
key, and node revision; reminder idempotency includes user, edition, logical
key, and node revision, while exact historical evidence retains the snapshot
FK.
