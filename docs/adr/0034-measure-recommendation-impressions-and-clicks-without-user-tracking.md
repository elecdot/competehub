# ADR 0034: Measure Recommendation Impressions and Clicks without User Tracking

## Status

Accepted

## Context

The P2 PRD listed recommendation click counts but did not decide whether to
implement or defer them. A click count without an impression denominator cannot
describe how often displayed recommendations are opened, while treating every
API-returned item as displayed would overcount items that never rendered.
Connecting events to named users or profile facts would add unnecessary privacy
risk, and analytics delivery must not become a dependency of recommendation
display or navigation.

## Decision

Each recommendation response creates an opaque random
`recommendation_request_id` and server-side 90-day request-item snapshots for
the returned editions. A snapshot owns server-assigned position,
personalized/general mode, active rule-set version when applicable, controlled
reason codes, actor kind, and returned time. It contains no user id or profile
facts.

After items actually render, the frontend sends a best-effort batched
`impression` event. Opening an item from the recommendation page sends a
best-effort `click` without delaying detail navigation. The event API accepts
only request id, event type, and edition id and verifies the item existed in
that response. It reads position, mode, version, reasons, and actor kind from
the snapshot, so clients cannot forge those dimensions.

Impression and click are each idempotent per request item, and click requires a
recorded impression. Raw rows store optional impressed and clicked timestamps
but no account identity, profile fields, IP address, User-Agent, or identifier
that links separate requests or days. Events do not automatically tune an
individual's recommendations.

Raw request items expire after 90 days. Before expiry, an idempotent job
aggregates recorded impressions and clicks by `Asia/Shanghai` product date,
rule-set version, mode, position, reason code, actor kind, and edition. Admin
surfaces may derive recorded clicks divided by recorded impressions but must
label it as a best-effort station interaction ratio, not unique users,
recommendation quality, or registration conversion.

## Consequences

P2 gains an interpretable recommendation interaction measure without a
third-party analytics SDK or named-student tracking. Implementation adds raw
request-item and daily aggregate tables, render/click calls, validation,
retention, and statistics tests. A/B experiments, funnel attribution,
user-level drill-down, and automated learning remain outside P2 thin.
