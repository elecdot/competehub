# ADR 0019: Publish Immutable Competition Revisions

## Status

Accepted

## Context

The initial model made publication status and editable content one row. It
therefore either blocked every correction after publication or required direct
mutation of facts students had already seen. Direct mutation loses the exact
version a reviewer approved, while taking the whole record offline for an
ordinary typo creates unnecessary public downtime.

## Decision

Separate赛事届次 identity and lifecycle from numbered赛事届次修订 content.
`competitions` retains edition identity, lifecycle status, and the selected
`published_revision_id`. A revision contains source-backed display fields,
revision-scoped tag links, stages, and time-node snapshots. Draft revisions are
editable; submitted, approved, rejected, and returned snapshots are immutable.

After initial publication, an editor copies the public revision into a new
draft. The current approved revision remains public while the replacement is
edited and reviewed. Independent approval atomically switches
`published_revision_id`. Review UI shows field-level differences and side-effect
impact before the decision. There is no self-review bypass for minor copy edits.

An administrator with `competition_maintainer` may immediately set an edition
to `offline` with a required reason when current public content creates a
serious safety, fraud, link-hijacking, or misinformation risk. This withdrawal
is audited and does not require prior review. Restoration is never a direct
status flip: a corrected revision must receive independent approval, which then
selects it and returns the edition to `published`.

## Consequences

Public reads resolve through the selected immutable revision. Search and
recommendation indexes refresh after an approved switch. Time-node differences
invoke ADR 0015 reminder reconciliation. Cancellation, expiry, and archival
remain reasoned lifecycle actions with historical detail; emergency offline
remains distinct because it removes public detail immediately.
