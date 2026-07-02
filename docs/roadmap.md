# Development Roadmap

This roadmap describes the product and engineering delivery route for CompeteHub. It is a planning document for implementation order, not a course-report checklist and not a substitute for detailed requirements, architecture, API, or data-model documents.

Course reports under `docs/reports/` can be prepared from the current aligned docs at any time. They are not roadmap phases.

## Alignment Rules

- `CONTEXT.md` owns canonical project language.
- `docs/roadmap.md` owns implementation sequencing and release shape.
- `docs/PRD.zh.md`, `docs/architecture.md`, `docs/api_spec.md`, `docs/data_model.md`, `docs/tech_spec.zh.md`, and module reports should be refined together when they disagree.
- ADRs under `docs/adr/` record hard-to-reverse architecture choices and tradeoffs.

## Current Delivery Strategy

The project should move from a runnable vertical skeleton toward the student-facing core workflow before adding recommendation depth, admin analytics, or optional community features.

| Phase | Name | Goal | Main Outcomes |
|---|---|---|---|
| P0 | Minimum runnable loop | Make the repository reliably runnable for local development. | Local PostgreSQL and Redis start cleanly; Flask API boots; Vue app boots; health checks work; root `just` commands and CI-aligned checks are usable. |
| P1 | Core business workflow | Deliver the student and administrator workflow that proves the product value. | Student registration/login, profile maintenance, administrator manual赛事录入, review publication, status management, public赛事 search/filter/detail, favorite, subscription, in-app reminders, and personal赛事 calendar. |
| P2 | Recommendation and governance | Add explainable recommendations and operational control. | Rule-based recommendations, recommendation reasons, fit tags, value basis notes, configurable dictionaries/rules, audit logs, user management, and basic statistics. |
| P3 | Quality and operations hardening | Make the system maintainable beyond the demo path. | Focused backend/frontend tests, database migrations and seed data, error handling, permission checks, documentation alignment, performance checks for search/list/detail pages, and deployable environment documentation when deployment becomes concrete. |
| P4 | Later extensions | Expand beyond the current core loop only after P1-P3 are stable. | Content materials, team posts, certified Q&A, post-competition reviews, semi-automated collection candidates, external notification channels, advanced Chinese search, model-based ranking, and dedicated teacher or organizer workflows. |

## Phase Boundaries

### P0 Minimum Runnable Loop

P0 is complete when a developer can follow documented commands to start the local infrastructure, backend, and frontend, then verify that the browser app and API are connected at a basic level. P0 should avoid building broad business behavior before the development loop is reliable.

### P1 Core Business Workflow

P1 is the first product-complete slice. It should let an administrator create and publish trustworthy赛事 data, and let a student discover a relevant赛事, inspect details, subscribe to it, and see follow-up reminders or calendar nodes.

P1 should not include public赛事 scoring, automatic collection and publication, external notification channels, or dedicated teacher/organizer workspaces.

### P2 Recommendation and Governance

P2 builds on P1 data. Recommendations must be explainable through explicit rules and赛事 fields. Admin governance should focus on configuration, auditability, and visibility into usage, rather than broad platform operations.

### P3 Quality and Operations Hardening

P3 turns the working product into a maintainable system. This includes test coverage around state transitions, permissions, reminders, recommendation reasons, and API contracts. Operational documentation should be added when the corresponding runtime surface exists.

### P4 Later Extensions

P4 items remain useful product directions, but they should not distort the current core model. Later extensions should reuse users,赛事, review records, audit logs, reminders, and configuration where possible.
