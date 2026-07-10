# ADR 0016: Time Nodes Are Single-Instant Milestones

## Status

Accepted

## Context

The initial model allowed one赛事时间节点 to contain both `starts_at` and
`due_at`. This produced competing representations such as a registration
period versus separate registration-start and registration-deadline nodes. It
also forced discovery, reminders, calendar ordering, and revision logic to
guess which timestamp represented the node.

## Decision

A赛事时间节点 represents one semantic milestone and contains exactly one
timezone-aware `occurs_at` instant. Registration opening and registration
deadline are separate nodes, as are competition start and competition end. If
an official source gives a period, the system records its boundaries as two
milestones grouped in one赛事阶段. The stage provides semantic grouping and does
not reintroduce two timestamps into one time node.

P1 uses a controlled node-type vocabulary: `registration_start`,
`registration_deadline`, `submission_deadline`, `competition_start`,
`competition_end`, `defense_or_review`, `result_announcement`, and `other`.
`other` requires a user-facing description and is display-only: it does not
satisfy the core-node publication gate or participate in default filters and
reminders. New behavior-bearing types require coordinated schema, docs, and
test changes rather than administrator-created strings.

## Consequences

Public and admin time-node API contracts use `occurs_at` instead of
`starts_at`/`due_at`. Next-node selection, date filtering, reminder planning,
calendar ordering, and node revisions all compare one unambiguous instant. The
current models, schemas, frontend types, tests, and persistence shape require a
coordinated migration before downstream reminder work relies on them.
