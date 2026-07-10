# ADR 0035: Require Complementary Review, Audit, and Statistics Evidence

## Status

Accepted

## Context

The P2 thin scope previously allowed review records, audit logs, or basic
statistics to stand in for one another. They answer different governance
questions: reviews explain why a controlled revision was accepted or rejected,
audit events explain which key operation changed system state, and statistics
summarize current workload and recorded activity. Making any one optional would
leave an acceptance path that could not explain both decisions and operational
state.

A broad dashboard, export center, or user-level analytics system would exceed
the four-day delivery boundary. The governance surface therefore needs a
bounded evidence model rather than an open-ended business-intelligence product.

## Decision

P2 thin requires one administrator governance workbench with three read-only
tabs:

- Review shows competition-revision and recommendation-rule-set decisions. It
  supports stable pagination and filters for target type, status, submitter,
  and date, and exposes the reviewed version, differences, impact summary,
  reviewer comment, and decision time.
- Audit shows key operation events with stable pagination and filters for
  actor, controlled action, target, result, and date. Action-specific details
  use an allowlist and exclude passwords, verification codes, session values,
  full account identifiers, profile content, and raw analytics identifiers.
- Statistics shows current published and pending-review counts, active favorite
  and subscription counts, message delivery states, and 7-day/30-day outbound
  and recommendation interaction counts. Every metric includes a definition,
  `as_of`, time zone, window, and any best-effort caveat.

The governance home shows only pending-task counts, recommendation
configuration faults, and a small number of summary metrics; detailed evidence
lives in the three tabs. Review decisions and audit events are immutable after
creation, and statistics are read-only. All three surfaces require an
administrator; students receive `403 forbidden`.

The P2 acceptance path includes Playwright coverage for navigating all three
tabs, applying representative filters, inspecting evidence, and enforcing the
student permission boundary.

## Consequences

The system can explain review decisions, reconstruct key administrative
actions, and report bounded operational signals without claiming real-time BI,
unique-user analytics, recommendation quality, or registration conversion.
Implementation must deliver all three surfaces for P2 completion, plus API,
permission, immutability, sensitive-field, pagination, and browser-path tests.
Real-time streams, charts-heavy dashboards, exports, and named-user drill-down
remain outside P2 thin.
