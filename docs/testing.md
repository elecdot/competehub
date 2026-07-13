# Testing And Non-Functional Validation Model

This document defines the project-wide testing model for CompeteHub. It explains
what kind of evidence each delivery slice should produce and how the team checks
the course-inspection path without adding speculative test infrastructure too
early.

This is a release-sprint validation model, not a complete operations or
production quality plan. A layer becomes required only when the corresponding
runtime surface exists and the current issue touches that risk.

`docs/agents/tdd.md` remains the workflow for agents and developers who are
implementing a testable behavior change. This document defines the coverage
model; `docs/agents/tdd.md` defines how to work test-first when a suitable
automated test surface exists.

## Scope

Included:

- Backend unit, API, integration, frontend static, frontend component, manual
  acceptance, and non-functional validation layers.
- The shared Playwright browser harness, deterministic actor provisioning, and
  failure-artifact policy used by feature slices.
- Practical TDD usage for bugs, business rules, API validation, permissions,
  reminders, subscriptions, recommendations, and review publication workflows.
- Course-inspection evidence for the student and administrator main workflow.

Out of scope for this model slice:

- Feature-specific Playwright paths that belong to their implementation issues.
- Replacing the existing agent TDD workflow.
- Full performance benchmarking, deployment observability, or production SLOs.

Normal maintenance should keep this document current when test commands,
validation evidence, CI checks, or the release-sprint acceptance path change.
Implementation details such as fixtures, seed scripts, and framework-specific
test helpers should live with the relevant app or issue until they become stable
project conventions.

## Layered Test Model

| Layer | Project target | Current strategy | Evidence |
|---|---|---|---|
| Backend unit tests | Services, repositories, recommendation rules, state transitions, idempotency rules. | Use `pytest`. Prefer TDD for business rules and regression-prone state changes. | `just api-test` or a narrower pytest command. |
| API tests | Auth, competitions, subscriptions, review publication, notifications, recommendations, admin permissions. | Use the Flask test client to verify request validation, response envelopes, status codes, permissions, and visible state. | `just api-test` plus focused test names in the PR summary. |
| Database and migration checks | SQLAlchemy models, migration scripts, seed data, and state enum changes. | Run SQLite coverage in `just api-test`; use disposable PostgreSQL databases through `just api-migration-test-postgres` for fresh/legacy upgrade and downgrade evidence. When a migration follows an existing committed revision, seed that exact predecessor with representative business rows and prove data-preserving upgrade plus public/read-model behavior. The fresh path also proves re-upgrade after downgrade and runs Alembic's schema-drift check, excluding only documented internal migration bookkeeping tables. Keep seed data reproducible. | Both migration command outputs, or a documented skipped reason when no schema changed. |
| Integration tests | Admin creates and publishes a 赛事 record, student searches it, subscribes, reminders create messages and calendar nodes. | Start with focused service/API integration tests when the database fixtures exist. Use manual acceptance until the automated surface is ready. | Test command output or an acceptance-script run record. |
| Frontend static checks | Vue routes, TypeScript types, build output, import correctness. | Keep `vue-tsc --noEmit` through `just web-lint`; keep production build through `just web-build`. | `just web-lint` and `just web-build`. |
| Frontend component tests | Search filters, detail status display, subscription state, message read state. | Add Vitest or equivalent after the P1 UI stabilizes. Do not add the dependency in a docs-only slice. | Future component-test command and changed component names. |
| E2E or manual acceptance | Course demo main workflow and cross-role handoff. | Use the shared Playwright Chromium harness through `just web-e2e`. It starts with deterministic student/editor/reviewer Cookie sessions and a nonblank smoke path, then feature issues add distinct editor/reviewer publication, calendar, recommendation, and governance scenarios. Use manual acceptance for exploratory and visual checks. | `just web-e2e` plus an acceptance record with date, actor, environment, result, and linked defects. |
| Documentation and workflow checks | MkDocs navigation, source-of-truth alignment, PR checklist completeness. | Use `just docs-build`; require issue/PR validation evidence before marking done. | `just docs-build` and PR checklist review. |

Issue #38 adds SQLite-backed API and migration coverage plus a PostgreSQL-only
concurrency suite. The latter is not interchangeable with SQLite: run
`just api-migration-test-postgres` and
`apps/api/tests/test_issue38_postgresql_concurrency.py` against a real
PostgreSQL environment before claiming the slice or issue complete.

## TDD Usage

Use TDD when the change affects observable behavior and a reasonable automated
test surface exists:

- Backend rules, state transitions, reminders, subscriptions, recommendations,
  review publication, API validation, auth, and permissions should usually start
  with a failing test.
- Bug fixes should reproduce the bug with a failing test when practical.
- Frontend behavior uses static checks, targeted Playwright for the accepted P1
  cross-role publication/calendar paths and P2 recommendation/governance paths,
  and component tests after that harness is intentionally introduced.
- Pure documentation, process, template, or exploratory changes use manual
  validation and `just docs-build` instead of test-first implementation.

Implementation slices should first choose the relevant layer from this document,
then follow `docs/agents/tdd.md` for the red-green-refactor workflow when TDD is
practical.

The repository-local `.agents/skills/tdd` skill is a thin wrapper over this
model and `docs/agents/tdd.md`. The durable workflow remains
`docs/agents/tdd.md`; the skill must stay aligned with this model instead of
duplicating or silently replacing it.

## Shared Browser Harness

Install dependencies and the Chromium browser from a clean checkout with:

```bash
just setup
```

Run the browser gate with:

```bash
just web-e2e
```

The underlying project command, also used by CI, is
`npm --prefix apps/web run test:e2e`. It rebuilds only the isolated
`.cache/tmp/competehub-e2e.db` database and provisions distinct Day 1 student,
editor, and reviewer accounts through controlled test setup. Actor fixtures use
the real login endpoint and browser Cookie state; they do not inject privileged
frontend state or imply that public registration bypasses verification.

The harness currently runs Chromium and treats uncaught page errors and browser
console errors as failures. Screenshots are captured on failure, while traces
and video are retained on failure. Reports and test results stay under
`.cache/playwright`, are ignored by Git, and are uploaded by CI only when the
browser job fails.

## Non-Functional Validation

Non-functional checks should be small, repeatable, and tied to current product
risk.

| Dimension | Practical target | Validation method |
|---|---|---|
| Permission safety | Students cannot access admin APIs; users cannot read or mutate other users' profiles, subscriptions, reminders, or messages. | API tests for `401` and `403` cases; manual role-switch check before demos. |
| Data consistency | Status changes affect list/detail/recommendation visibility; cancelling a subscription cancels future pending reminders and calendar nodes. | Service or API tests around state transitions and subscription changes. |
| Idempotency and reliability | Reminder dispatch does not create duplicate messages when retried; failed reminder work can be retried without corrupting state. | Service tests for dispatch keys and repeated worker calls. |
| Revision concurrency | One edition has at most one active draft/pending revision; approval locks and rejects a stale base without a terminal review decision. | Constraint/service/API tests for `active_revision_exists`, `stale_revision`, public-pointer stability, and server-owned node revisions. |
| Workbench read model | Authorized admins can search/select series and editions, derive the pending queue, and load completeness, base/current-public diff, stale state, and impact. | API contract tests for filters, pagination, capability reads, immutable terminal review separation, and impact `as_of`. |
| Lifecycle engagement | Historical-viewable editions accept favorite only; new/update subscription mutations require published state; owners can always delete existing relations. | Table-driven API tests across published, cancelled, archived, expired, offline, and unpublished states. |
| Schedule-change messaging | Planning-semantic changes create at most one consolidated message per subscriber and approved revision; presentation-only changes refresh pending content without a message. | Service/API tests for occurrence, selected-node add/remove/type changes, description/prominence-only changes, and repeated handlers. |
| Response-time smoke | With a documented local seed size, list/search/detail pages remain usable and do not exceed the PRD's 3-second target in ordinary local conditions. | Local smoke script or manual browser/API timing record with seed size and machine context. |
| Usability | A teacher or student can complete the main workflow from script without hidden setup knowledge. | Manual acceptance script run by someone other than the implementer when possible. |
| Maintainability | Repository checks stay aligned with CI; docs change with behavior and public contracts. | `just check` before broad merges, or relevant component checks plus `just docs-build` for focused slices. |

These checks are not a promise of production-grade load testing. They are the
course-project evidence needed to show that the system is safe, usable,
maintainable, and aligned with its current P1-P3 scope.

## Release Sprint Acceptance Script

Use this as the default manual acceptance path for the midterm release sprint:

1. Student registers or logs in and maintains a basic profile.
2. Editor admin logs in, creates a 赛事 record from a trusted source, and submits it for review.
3. A distinct reviewer admin inspects the revision diff and impact, then approves and publishes the 赛事; self-review remains blocked.
4. Student searches and filters public 赛事, opens the detail page, and verifies
   source information and key time nodes.
5. Student favorites and subscribes to the 赛事.
6. System shows the subscription in the personal 赛事 calendar and message or
   reminder surface.
7. Recommendation list shows published 赛事 with a traceable recommendation
   reason, not a public value score.
8. Admin uses the Review, Audit, and Statistics tabs to inspect immutable
   decisions, key state-change events, and defined current/7-day/30-day metrics;
   a student cannot access those surfaces.

Record manual acceptance evidence with:

- Date and branch or commit.
- Actor or owner.
- Environment and seed data size.
- Steps passed, failed, or skipped.
- Linked issue for each defect found.

## Definition Of Done For Test Evidence

Every implementation PR should state:

- Which test layers were relevant.
- Which commands or manual scripts were run.
- Which non-functional risks were checked or intentionally deferred.
- Why any expected automated test was skipped.

Documentation-only slices can satisfy this with `just docs-build` and a manual
source-document review. Behavior changes need stronger evidence from the
relevant automated or manual test layer.
