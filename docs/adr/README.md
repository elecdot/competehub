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
- [0008 Ant Design Vue UI Library](./0008-ant-design-vue-ui-library.md)
- [0009 Flask Cookie Session Auth](./0009-flask-cookie-session-auth.md)
- [0010 Staged Frontend Quality Gates](./0010-staged-frontend-quality-gates.md)
- [0011 PostgreSQL Search First](./0011-postgresql-search-first.md)
- [0012 UTC Instants and Shanghai Product Calendar](./0012-utc-instants-shanghai-calendar.md)
- [0013 Competition Status Public Visibility](./0013-competition-status-public-visibility.md)
- [0014 Separate Competition Series and Editions](./0014-separate-competition-series-and-editions.md)
- [0015 Version Time Node Changes and Rebuild Reminders](./0015-version-time-node-changes-and-rebuild-reminders.md)
- [0016 Time Nodes Are Single-Instant Milestones](./0016-time-nodes-are-single-instant-milestones.md)
- [0017 Group Time Nodes into Stages and Prominence](./0017-group-time-nodes-into-stages-and-prominence.md)
- [0018 Disallow Self-Review of Competition Revisions](./0018-disallow-self-review-of-competition-revisions.md)
- [0019 Publish Immutable Competition Revisions](./0019-publish-immutable-competition-revisions.md)
- [0020 Derive Registration Status from Current Stages](./0020-derive-registration-status-from-current-stages.md)
- [0021 Default Public Discovery to Actionable Order](./0021-default-public-discovery-to-actionable-order.md)
- [0022 Single-Institution Deployment Boundary](./0022-single-institution-deployment-boundary.md)
- [0023 Model Typed User Identities](./0023-model-typed-user-identities.md)
- [0024 Gate Public Registration on Real Verification Delivery](./0024-gate-public-registration-on-real-verification-delivery.md)
- [0025 Use Length-First Passwords and Explicit Adaptive Hashing](./0025-use-length-first-passwords-and-explicit-adaptive-hashing.md)
- [0026 Enforce Versioned Role-Specific Cookie Sessions](./0026-enforce-versioned-role-specific-cookie-sessions.md)
- [0027 Derive Recommendation Readiness from Profile Facts](./0027-derive-recommendation-readiness-from-profile-facts.md)
- [0028 Require Explicit Per-Subscription Reminder Confirmation](./0028-require-explicit-per-subscription-reminder-confirmation.md)
- [0029 Keep Delivered Events in a Retained In-App Message Center](./0029-keep-delivered-events-in-a-retained-in-app-message-center.md)
- [0030 Record Privacy-Minimized Non-Blocking Outbound Clicks](./0030-record-privacy-minimized-non-blocking-outbound-clicks.md)
- [0031 Require a P1 Administrator Publication Workbench](./0031-require-a-p1-administrator-publication-workbench.md)
- [0032 Provide Month Week and List Personal Calendar Views](./0032-provide-month-week-and-list-personal-calendar-views.md)
- [0033 Activate Versioned Recommendation Rule Sets through Independent Review](./0033-activate-versioned-recommendation-rule-sets-through-independent-review.md)
- [0034 Measure Recommendation Impressions and Clicks without User Tracking](./0034-measure-recommendation-impressions-and-clicks-without-user-tracking.md)
- [0035 Require Complementary Review Audit and Statistics Evidence](./0035-require-complementary-review-audit-and-statistics-evidence.md)
- [0036 Reactivate Edition Subscriptions without Duplicating Reminder Plans](./0036-reactivate-edition-subscriptions-without-duplicating-reminder-plans.md)
- [0037 Preserve Cancelled Reminder Plans through Preference Changes (withdrawn; see ADR 0036)](./0037-preserve-cancelled-reminder-plans-through-preference-changes.md)

## Template

An ADR may be a single paragraph when the decision is straightforward. The
important part is recording what was decided and why future readers should not
reverse it casually.

Add structured sections only when they add useful clarity:

- Status: proposed, accepted, superseded, deprecated, or withdrawn. A withdrawn
  ADR records a decision that must not be used; it should name the authoritative
  replacement when one exists.
- Context: what problem or constraint forced the decision.
- Decision: what was chosen.
- Consequences: expected benefits, tradeoffs, and follow-up work.
