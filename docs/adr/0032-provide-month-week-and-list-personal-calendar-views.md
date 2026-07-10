# ADR 0032: Provide Month Week and List Personal Calendar Views

## Status

Accepted

## Context

The student-following feature PRD allowed a date-ordered list to substitute for
the month and week calendar modes already described by the stable product PRD.
A list alone is useful on mobile but does not support scanning a competition
schedule across a month or a dense week. Hand-building date grids, event
overflow, navigation, and responsive behavior would add avoidable calendar
logic and accessibility risk.

## Decision

P1 provides month, week, and list views over one calendar API source of truth.
Desktop defaults to month and mobile defaults to list. Students can switch views
and the current device retains the most recent choice. View selection changes
presentation and requested range, not the meaning or ownership of nodes.

The frontend uses FullCalendar's Vue 3 open-source standard capabilities for
month, week, and list views, pinned through the normal npm dependency workflow.
No premium resource/scheduler features are required, and the project does not
implement a custom date-grid engine.

Only active subscriptions contribute nodes. Favorite alone never adds calendar
state, while a reminder-disabled subscription continues to show its selected
nodes. Events are grouped and rendered in `Asia/Shanghai`, include stage and
pair metadata, emphasize primary/current/next nodes, and expose all same-day
nodes through a compact accessible expansion. Clicking an available target
opens its detail; unavailable targets retain status without a broken link.

Calendar reads current node revisions. Schedule changes refresh every view;
cancellation and emergency offline remove future nodes while the durable event
message remains in the message center. Playwright covers desktop and mobile
defaults, all view switches, same-day nodes, reminder-disabled subscriptions,
revision refresh, and non-overlap.

## Consequences

Students receive both scan-oriented and compact calendar workflows without a
hand-rolled calendar engine. The frontend adds regular FullCalendar dependencies
and styling integration with Ant Design Vue, while API and tests must keep all
views on the same subscription, stage, time-zone, and revision semantics.
