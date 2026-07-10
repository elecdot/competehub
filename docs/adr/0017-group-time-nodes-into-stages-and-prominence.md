# ADR 0017: Group Time Nodes Into Stages And Prominence

## Status

Accepted

## Context

Single-instant milestones remove timestamp ambiguity but do not explain which
opening and deadline belong together, especially when one赛事届次 has school,
regional, preliminary, and final rounds. A flat timeline also gives every node
the same visual weight, while students usually need the next registration,
submission, or competition milestone first. Inferring pairs from labels in the
frontend would make admin validation and public display inconsistent.

## Decision

Add赛事阶段 as an ordered, user-labeled grouping within a赛事届次. A stage has a
controlled type, display label, and stable order. Each赛事时间节点 belongs to one
stage and has a controlled `primary` or `secondary` prominence. Registration
deadline, submission deadline, and competition start default to `primary`;
administrators may override prominence only with a reason captured in audit
evidence.

Known pairs within one stage are registration start/deadline and competition
start/end. Admin editing presents them as paired controls, validates ordering,
and warns when a source provides only one side, while persistence retains two
single-instant nodes. Multiple rounds use separate labeled stages rather than
duplicate unlabeled nodes.

Public lists show the nearest future primary node, falling back to the nearest
future secondary node. Detail pages group the timeline by stage, place paired
milestones together, highlight the current stage and next primary node, and
mark revised times. Personal calendars include all selected subscribed nodes
but give primary nodes stronger visual prominence.

## Consequences

The data model needs `competition_stages`, node `stage_id`, and node prominence.
Admin UI requires a stage-oriented editor with pair, completeness, ordering,
prominence, and change-impact feedback. Public API responses need enough stage
metadata for consistent grouping instead of making each client reconstruct
relationships from free text.
