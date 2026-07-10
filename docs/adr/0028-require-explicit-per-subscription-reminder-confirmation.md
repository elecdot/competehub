# ADR 0028: Require Explicit Per-Subscription Reminder Confirmation

## Status

Accepted

## Context

The initial models silently defaulted profiles, global reminder settings, and
subscriptions to enabled with a three-day offset. Product text said that
subscription enabled reminders by default, but did not define when a student saw
or accepted the configuration. It also left unclear whether disabling reminders
removed a subscription or calendar entry and whether passed triggers should be
delivered immediately.

## Decision

Favorite never creates subscription or reminder state. The first subscription
interaction shows a confirmation surface with reminder enabled state, one
advance-day offset, and the current edition's available controlled primary core
node types. Global settings prefill enabled, three days, and registration
deadline, submission deadline, and competition start where those nodes exist.
They are displayed defaults, not consent. The API requires the confirmed fields
and does not infer them when omitted.

Each subscription may enable or disable reminders independently. When enabled,
P1 accepts one integer offset from 0 through 30 days and a non-empty controlled
node-type set, creating at most one ordinary reminder per selected time node. A
reminder-disabled subscription remains active in follow lists and the personal
calendar. Subsequent subscription actions may prefill the saved defaults but
must report the effective reminder configuration and offer undo or settings.

`reminder_settings` is the single source of truth for the global enabled state,
default offset, and default node types; profile rows do not duplicate these
fields. Disabling the global switch cancels all pending plans but preserves
subscriptions and calendar nodes. Re-enabling either global or per-subscription
reminders reconciles only future eligible triggers. Passed triggers are not
backfilled as immediate ordinary reminders, and sent messages remain immutable.

## Consequences

The three-day default remains ergonomic without becoming hidden consent.
Students can follow an edition or use its calendar without receiving messages.
Implementation needs a visible confirmation interaction, strict subscription
request validation, update behavior, plan reconciliation, and explicit response
metadata for scheduled count, next reminder, or why no plan was created.
