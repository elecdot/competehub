# ADR 0027: Derive Recommendation Readiness from Profile Facts

## Status

Accepted

## Context

The initial profile implementation created an all-null profile at registration,
while product text referred to unspecified required fields. Recommendation could
therefore treat any authenticated student as personalized without enough facts,
or profile completion could accidentally become a gate for unrelated search and
follow-up workflows. A stored `is_complete` flag would also drift when fields or
deployment dictionaries change.

## Decision

Account activation creates an editable profile with a derived status of
`incomplete`. Students may skip profile completion. Search, detail, favorite,
subscription, calendar, and reminder behavior never depend on profile readiness.

A profile is `recommendation_ready` only when `college`, `major`, `grade`, and
at least one `interest_tag` are present and valid against deployment-controlled
dictionaries. The major must belong to the selected college, interest tags are
unique, and a profile may select at most 10 interest tags. Competition
experience, goal preferences, blocked tags, and account display name remain
optional and do not affect readiness.

`profile_status` and `missing_fields` are derived from current facts at read and
recommendation time and are not persisted. Invalid dictionary values and
college-major combinations are rejected with field-specific feedback. A profile
may be saved while incomplete.

Personalized recommendation runs only for `recommendation_ready` profiles.
Anonymous and profile-incomplete users receive general actionable ordering with
an explicit fallback reason. Authenticated incomplete responses expose the
missing profile fields and never describe a result as a personal match.

## Consequences

Students can use the core product before completing optional onboarding, while
personalized claims remain explainable. Frontend profile surfaces can show exact
missing fields without a blocking modal. Dictionary changes can immediately
recompute readiness, so services and tests must share one readiness function and
must not cache or store a separate completion flag.
