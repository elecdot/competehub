# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs).

## Purpose

Use ADRs for decisions that explain why the project chose a direction at a point in time. Stable product requirements belong in `docs/PRD.zh.md`; stable engineering structure and conventions belong in `docs/tech_spec.zh.md`; time-bound reasoning, alternatives, tradeoffs, and superseded choices belong here.

## Naming

Use numbered lowercase filenames:

```text
0001-initial-application-architecture.md
```

## Records

- [0001 Initial Application Architecture](./0001-initial-application-architecture.md)
- [0002 Initial Framework Supporting Choices](./0002-initial-framework-supporting-choices.md)
- [0003 Explainable Rule-Based Recommendation](./0003-explainable-rule-based-recommendation.md)
- [0004 In-App Reminders First](./0004-in-app-reminders-first.md)
- [0005 Trusted Source Manual Entry](./0005-trusted-source-manual-entry.md)
- [0006 Student and Admin Current Roles](./0006-student-admin-current-roles.md)
- [0007 Separate Favorites and Subscriptions](./0007-separate-favorites-and-subscriptions.md)

## Template

An ADR may be a single paragraph when the decision is straightforward. The
important part is recording what was decided and why future readers should not
reverse it casually.

Add structured sections only when they add useful clarity:

- Status: proposed, accepted, superseded, or deprecated.
- Context: what problem or constraint forced the decision.
- Decision: what was chosen.
- Consequences: expected benefits, tradeoffs, and follow-up work.
