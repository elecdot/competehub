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

A schedule correction preserves the赛事时间节点 identity and creates a new
auditable revision containing the current time facts. The service records old
and new values plus the reason, cancels pending reminders based on the prior
revision as superseded, and creates new pending reminders only for trigger times
that remain in the future. Sent reminders are immutable.

For a published赛事届次, each effective node revision creates at most one
赛事时间变更通知 per active subscriber. If the recalculated ordinary reminder time
has already passed, the system does not backfill a message that pretends it was
sent on time; the change notification explains the update instead. The personal
赛事日历 reads the current node revision, while audit history retains prior
values.

## Consequences

Time-node updates must be identity-aware rather than implemented as blind list
replacement once a届次 has reminder-dependent state. Reminder idempotency needs
the node revision in its uniqueness boundary, and cancelled plans need a reason
that identifies supersession. Published schedule correction also needs an
explicit admin API and review policy; that workflow is resolved separately.
