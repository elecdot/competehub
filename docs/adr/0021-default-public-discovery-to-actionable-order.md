# ADR 0021: Default Public Discovery To Actionable Order

## Status

Accepted

## Context

The initial repository conflicted between newest-publication order in the
stable PRD and nearest-any-node order in code. Neither answer used the student's
ability to register, and nearest-any-node could elevate a result announcement
over a closing registration opportunity. Public discovery also lacks the
profile context required for recommendation ordering.

## Decision

Use `actionable` as the default public list order. Rank derived registration
status as `open`, `upcoming`, `unknown`, `not_applicable`, then `closed`. Within
open results, sort known future registration deadlines ascending and place open
records without a deadline after them. Within upcoming results, sort registration
starts ascending. Other groups use the next primary node ascending, with absent
future nodes last.

Every group uses `published_at DESC, competition_id DESC` as deterministic
tie-breakers. P1 also offers `registration_deadline` and `published_at` explicit
sorts. Recommendation ordering belongs to the recommendation surface, and
popularity is deferred until reliable behavior data and governance exist.

## Consequences

Public pagination is stable and prioritizes opportunities students can act on.
The frontend stores sort choice in the URL, preserves filters, and resets to
page one when the sort changes. Queries need indexes for public revision time
facts and publication time, while tests need a controlled clock and tie cases.
