# ADR 0013: Competition Status Public Visibility

## Status

Accepted

## Context

Students may retain detail links after a 赛事 is published, including through
收藏, 订阅, reminders, and shared URLs. Treating cancellation or expiry as if
the content never existed removes the explanation students need, while keeping
an intentionally offline record public defeats the administrator's withdrawal
action. Earlier product documents and the Day 1 runbook encoded conflicting
answers for these states.

## Decision

A `published` 赛事 appears in default public list, search, recommendation, and
detail surfaces. A previously published `cancelled`, `expired`, or `archived`
赛事 is excluded from default discovery and recommendation, but its public
detail remains accessible with a clear status warning. An `offline` 赛事 is
withdrawn from both discovery and public detail. Draft, pending-review, and
rejected records have never entered public visibility and also have no public
detail.

Archival and expiry are routine historical transitions, permitted only after
the current public revision has no future node. They retain historical
subscriptions and past calendar nodes, cancel only stale pending plans, and do
not create a subscriber message. A future schedule that must stop uses
cancellation or emergency offline instead.

## Consequences

Public list eligibility and public detail eligibility are separate policies.
The detail API and frontend must support historical-viewable statuses, while
default list and recommendation queries remain published-only. Tests and demo
acceptance must distinguish a cancelled or expired historical detail from an
offline or never-published `404`. Historical list filters can be added later
without changing this status boundary. Status maintenance must reject
archival/expiry while any future node remains. Historical detail may create a
favorite, but new or reconfigured subscriptions require `published`; owned
engagement deletion remains available even when detail is offline.
