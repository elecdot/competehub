# ADR 0037: Preserve Cancelled Reminder Plans through Preference Changes

## Status

Accepted

## Context

Issue #38 uses one ordinary reminder-plan key per student, edition, logical
node, and node revision. Restoring a cancelled row after a false-to-true
subscription or global setting transition would blur the cancellation audit
trail and make a later consent change silently revive previously stopped work.

## Decision

Subscription PATCH, explicit re-subscription, and global reminder re-enablement
never reactivate a cancelled reminder plan. They may refresh a matching pending
plan; a new immutable node revision may create its own still-future plan. A
cancelled plan remains inspectable, while subscription reactivation still
reuses the single edition-bound subscription relation and records fresh consent.

## Consequences

The current P1 behavior favors explicit, one-way cancellation evidence over
automatic restoration. Future restoration requires a separately reviewed model
and migration strategy; it is not implied by a preference switch.
