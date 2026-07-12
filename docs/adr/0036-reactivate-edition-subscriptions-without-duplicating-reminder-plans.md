# ADR 0036: Reactivate Edition Subscriptions without Duplicating Reminder Plans

## Status

Accepted

## Context

A student may cancel and later explicitly re-subscribe to the same赛事届次. Creating
a second subscription or ordinary reminder plan would weaken edition-bound
ownership and the existing reminder idempotency key, while refusing to reuse a
cancelled plan could make a fresh valid consent ineffective. Keeping immutable
consent generations would preserve more history but would add a new persistence
model that P1 does not require.

## Decision

One `(user_id, competition_id)` subscription relation is reused. Re-subscription
requires a fresh complete提醒确认, moves the cancelled relation back to active,
and stores only the latest confirmed configuration and confirmation time. A
future, unsent plan may return to pending only when its cancellation came from
the student's subscription configuration: `subscription_cancelled`,
`reminder_disabled`, `node_type_removed`, or
`subscription_offset_not_future`. The service recalculates the trigger from the
current immutable node snapshot and new offset. It never restores sent or failed
plans, plans cancelled by global, lifecycle, deletion, or supersession effects,
or a plan from an old node revision.

Initial relation creation returns `201`; idempotent active POST and explicit
re-subscription return `200`. Plan creation and restoration require both the
subscription's confirmed reminder choice and the current global reminder switch
to be enabled. Changes to the global switch and their cross-subscription
reconciliation remain a separate workflow.

## Consequences

The ordinary reminder unique key remains stable and sent evidence cannot be
duplicated. Cancellation rows remain inspectable, while the subscription stores
current consent rather than an immutable consent history. POST, PATCH, and DELETE
must serialize the subscription and plan reconciliation, and tests must cover
duplicate requests, opposite concurrent actions, new node revisions, and every
allowed or forbidden cancellation reason.
