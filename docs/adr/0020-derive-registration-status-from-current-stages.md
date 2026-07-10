# ADR 0020: Derive Registration Status From Current Stages

## Status

Accepted

## Context

The initial public `status` filter exposed publication lifecycle even though a
public list already contained only published records. Students instead need to
know whether they can register. Persisting a registration state would become
stale as time passes, while inferring "not applicable" from absent nodes would
confuse missing source data with invitation-only or non-registration flows.

## Decision

Expose a computed `registration_status` with `open`, `upcoming`, `closed`,
`unknown`, and `not_applicable`. Compute it at read time from the current public
revision's registration stages and `occurs_at` instants in absolute time.
`not_applicable` requires an explicit administrator fact.

For one stage, a future start is `upcoming`; a future deadline with no future
start is `open`; elapsed deadlines with no open or future stage are `closed`;
insufficient boundaries are `unknown`. For multiple rounds, aggregate with
`open` first, then `upcoming`, then `closed`; if no higher-confidence state can
be established, return `unknown`. The API returns the stage and node facts used
as the basis.

## Consequences

The public `status` query parameter is removed and replaced by
`registration_status`. Publication lifecycle remains a backend governance and
visibility concern. Queries, filters, UI labels, and tests must evaluate status
against a controlled clock and support incomplete but explicitly represented
source facts.
