# ADR 0037: Preserve Cancelled Reminder Plans through Preference Changes

## Status

Withdrawn. This ADR does not supersede ADR 0036.

## Context

This record proposed treating every cancelled reminder plan as permanently
terminal. The owner confirmed that this conflicts with ADR 0036: a fresh,
explicit subscription confirmation or semantic PATCH may restore only eligible
future plans cancelled for controlled subscription-level reasons.

## Decision

Withdraw this decision. ADR 0036 is authoritative: using the newly confirmed
consent and current eligible future nodes, explicit re-subscription or semantic
PATCH may restore only unsent plans cancelled as `subscription_cancelled`,
`reminder_disabled`, `node_type_removed`, or
`subscription_offset_not_future`. Delivered messages and sent, failed, elapsed,
prior-revision, offline, deletion, lifecycle, supersession, global-setting, and
other system-owned evidence remain terminal and are never restored or replayed.
Global `message_enabled` false-to-true restoration remains Issue #40 scope.

## Consequences

The rejected one-way rule must not be used to interpret Issue #38. Implementers
must follow ADR 0036 and keep all excluded terminal evidence inspectable.
