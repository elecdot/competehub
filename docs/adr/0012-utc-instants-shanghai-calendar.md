# ADR 0012: UTC Instants And Shanghai Product Calendar

## Status

Accepted

## Context

CompeteHub serves Chinese university students, while its API, PostgreSQL data,
workers, tests, and development environments may run in different system time
zones. Storing offsetless China-local timestamps would make reminder execution
and comparisons ambiguous. Interpreting a date-only discovery filter as a UTC
calendar date would also disagree with the date students see in China.

## Decision

Persist timezone-aware instants and normalize API timestamp responses to UTC.
Use `Asia/Shanghai` as the product calendar time zone for user-facing display,
date-only filters, and offsetless administrator datetime input. Explicitly
offset datetime input is converted to the same UTC instant. A selected product
date maps to the half-open UTC interval bounded by midnight in
`Asia/Shanghai`; browser or server-local time zones do not change that mapping.

## Consequences

The current timezone-aware timestamp columns need no schema migration. Frontend
formatters must specify `Asia/Shanghai`, and backend date-range queries must
convert product-calendar boundaries to UTC. A future source that uses another
time zone or provides only an imprecise date will need explicit source-time-zone
or date-precision modeling instead of silently changing this convention.
