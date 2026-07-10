# ADR 0029: Keep Delivered Events in a Retained In-App Message Center

## Status

Accepted

## Context

Reminder plans previously ended at worker status and a minimally defined message
row. Without a durable user destination, a due reminder or competition-side
change could become invisible after delivery, while mixing read state into the
reminder state machine made plans and user-visible history ambiguous. Expanding
immediately to email, SMS, push, and a generic notification platform would be
unnecessary for the P1 student workflow.

## Decision

P1 includes a thin but complete in-app message center. A reminder is a future
delivery plan; a message is an immutable delivered event snapshot; unread/read
is mutable user state on that message. A sent reminder remains `sent` and never
transitions to `read`.

The global navigation shows an unread badge and opens a compact message list
with all and unread tabs, controlled-type filtering, stable pagination,
one-message read, and read-all. The four P1 message types are `reminder_due`,
`competition_time_changed`, `competition_cancelled`, and
`competition_offline`. The system remains in-app only.

Messages snapshot their title, body, event time, competition reference, relevant
node time, and reason summary at delivery. Later competition edits do not
rewrite them. If the current target is unavailable, the snapshot remains
readable and the target link is disabled. Message creation uses a unique key per
user and domain event so duplicate workers or event handling cannot duplicate
history.

User-triggered unsubscription or reminder disablement does not create a message
because the action itself provides feedback. Competition cancellation or
emergency offline creates one event message per active subscriber and event
before future plans stop. An approved competition revision creates at most one
consolidated schedule-change message per affected subscriber and only for a
planning-semantic time, selected-node-presence, or selected-node-type change;
presentation-only corrections update current pending content without adding a
message.

Read and unread messages are retained for 365 days. Reading does not delete or
rewrite a message. P1 offers no per-message deletion; a periodic task purges
expired messages, and account deletion follows the account-data cleanup policy.

## Consequences

Students gain a predictable place for unread and historical reminders without a
multi-channel delivery dependency. Implementation must separate reminder and
message state, add unread count and list/read APIs, build the compact page, add
domain-event message producers, and test idempotency, unavailable targets, and
retention cleanup.
