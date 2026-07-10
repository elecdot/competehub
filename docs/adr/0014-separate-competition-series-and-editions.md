# ADR 0014: Separate Competition Series And Editions

## Status

Accepted

## Context

Many university competitions recur annually while their source notice,
eligibility, organizer details, registration window, and event dates change.
Overwriting one record each year would destroy historical links, review
evidence, subscriptions, and reminder context. Treating every annual record as
unrelated would make duplicate detection and cross-year history unreliable.

## Decision

Model the long-lived identity as a 赛事系列 and each concrete participation cycle
as a 赛事届次. Every届次 belongs to one series; a one-off 赛事 has a series containing
one届次. The existing `competitions` concept represents届次 records, while a
`competition_series` entity owns the stable cross-edition identity.

A new annual or otherwise distinct participation cycle creates a new届次 and
new time nodes without modifying an earlier届次. A postponement or deadline
change within the same cycle updates that届次, writes audit evidence, and causes
future reminder plans to be recalculated. Series association is confirmed from
source facts by an administrator; title or organizer similarity can only
suggest a possible match.

收藏 and 订阅 target one赛事届次 and never carry automatically to a later届次.
A future关注赛事系列 capability may notify a student that a new届次 was published,
but it cannot create a届次订阅 or reminders without fresh student consent.

## Consequences

The data model needs a series relation before subscription and reminder work
depends further on competition identity. Public list, detail, 收藏, 订阅, review,
and time-node behavior remain edition-oriented. Existing records can initially
receive one series each and be linked only after source-backed confirmation.
Series following, if added, requires its own state and API instead of reusing
edition subscriptions.
