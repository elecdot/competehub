# Competition Publication And Discovery

## Status

- Draft
- Roadmap phase: P1
- Owner: Product owner / tech lead
- Related issues: None yet

## Source Documents Checked

- `docs/PRD.zh.md`
- `docs/roadmap.md`
- `docs/data_model.md`
- `docs/api_spec.md`
- `docs/tech_spec.zh.md`
- Other: `CONTEXT.md`, `docs/project_workflow.md`, `docs/testing.md`,
  `docs/reports/module_breakdown_v1.0.md`

## Background And Goal

CompeteHub is entering formal development with a short delivery window. The
first product-critical capability is a trustworthy 赛事 supply path: an
administrator can create a 赛事 from a 可信来源, move it through review, publish
it, and then students can search, filter, inspect, and follow official links.

The current repository already has backend domain models and frontend route
shells, but the public business workflow is not yet connected. This PRD defines
the P1 thin slice that lets the team turn those existing structures into a
demonstrable administrator-to-student 赛事 flow without expanding into later
platform features.

## Users

- 学生: discovers 赛事, inspects details, and uses official channels.
- 管理员: creates, submits, reviews, publishes, and maintains 赛事 records.
- Reviewer / validation owner: checks source trust, API behavior, UI behavior,
  and demo readiness.

## User Stories

1. As an 管理员, I want to create a draft 赛事 from a 可信来源, so that the system
   can hold structured source-backed information before publication.
2. As an 管理员, I want required fields to be validated before review
   submission, so that incomplete 赛事 records do not reach students.
3. As an 管理员, I want to submit a draft 赛事 for review, so that publication is
   controlled by a visible state transition.
4. As an 管理员 reviewer, I want to approve or reject a pending 赛事 with a
   comment, so that publication decisions have traceable review context.
5. As an 管理员 reviewer, I want approved 赛事 to become public immediately in
   the product flow, so that students can discover newly published records.
6. As an 管理员, I want rejected 赛事 to remain hidden from students, so that
   untrusted or incomplete information is not exposed.
7. As an 管理员, I want every create, submit, review, and status action to be
   auditable, so that the team can explain information governance during demo.
8. As a 学生 or visitor, I want to search published 赛事 by keyword, so that I
   can quickly find relevant opportunities.
9. As a 学生 or visitor, I want to filter public 赛事 by category, major, grade,
   tag, deadline, and participant form where data exists, so that I can reduce
   irrelevant results.
10. As a 学生 or visitor, I want list results to show title, category,
    organizer, status, tags, and the next important time node, so that I can
    compare 赛事 quickly.
11. As a 学生 or visitor, I want to open a 赛事 detail page, so that I can inspect
    source facts, time nodes, eligibility, value notes, and official links.
12. As a 学生 or visitor, I want draft, pending, rejected, and offline 赛事 hidden
    from default public lists, so that public discovery stays trustworthy.
13. As a 学生 or visitor, I want cancelled, archived, or expired 赛事 to be
    shown only with explicit status behavior, so that I am not misled about
    active opportunities.
14. As a 学生, I want official and source links to be clearly typed, so that I
    can decide where to complete报名 or verify information.
15. As the team owner, I want this slice to be small enough for Day 1 work, so
    that later subscription, recommendation, and governance issues can depend on
    a stable 赛事 contract.

## Functional Requirements

- FR-001: 管理员 can create a draft 赛事 with title, source name, source URL,
  category, organizer, summary, detail, time nodes, suitable majors, suitable
  grades, tags, value notes, official URL, and attachment URL where available.
- FR-002: Draft 赛事 are not visible in public student list, detail, or
  recommendation surfaces.
- FR-003: 管理员 can submit a draft or returned 赛事 for review only when minimum
  required publication fields are present.
- FR-004: 管理员 reviewer can approve, reject, or return a pending 赛事 with a
  comment.
- FR-005: Approved 赛事 become `published`; rejected or returned 赛事 remain
  non-public.
- FR-006: Create, submit review, approve, reject, return, and status-maintenance
  actions write audit or review evidence.
- FR-007: Public list API returns only default-public 赛事, supports pagination,
  and supports keyword and field filters described in `docs/api_spec.md`.
- FR-008: Public detail API returns source facts, visible status, time nodes,
  fit fields, tags, value notes, official URL, attachment URL, and authenticated
  engagement state when available.
- FR-009: Frontend list page consumes the public list API and renders loading,
  populated, empty, and error states.
- FR-010: Frontend detail page consumes the public detail API and renders source,
  time nodes, tags, value notes, official channels, and status warnings.
- FR-011: Official outbound click recording is included only if it can be
  implemented without delaying the publication-to-detail demo path; otherwise it
  becomes a follow-up issue linked from this PRD.

## Non-Functional Requirements

- Performance: Public list and detail pages should remain comfortably under the
  PRD's 3-second local target for the seed dataset used in demo.
- Security or permission: Only 管理员 can create, submit, review, or change
  backend publication state. Anonymous users can read only public 赛事 data.
- Maintainability: Route handlers stay thin; review and publication rules belong
  in services; query behavior belongs in repositories when reusable.
- Observability or audit: Publication decisions and status changes must leave
  review or audit evidence that can be shown during acceptance.

## Out Of Scope

- Not included: full admin management UI beyond what is needed to prove the
  publication state flow.
- Not included: automatic collection, crawler candidates, or automatic
  publication.
- Not included: advanced Chinese full-text search or a dedicated search engine.
- Not included: public 赛事 value scores, machine-learning ranking, or score-like
  recommendation output.
- Not included: teacher or organizer workspaces.
- Not included: complete operational dashboards; basic governance evidence is
  handled by the P2 thin governance PRD.

## Acceptance Criteria

- [ ] Given a 管理员 creates a draft 赛事 from a 可信来源, when it is saved, then it
      exists as non-public structured data with source name and source URL.
- [ ] Given a draft 赛事 lacks minimum required publication fields, when the
      管理员 submits it for review, then the API rejects the request with a
      validation error.
- [ ] Given a pending 赛事 is approved by a 管理员 reviewer, when a student opens
      the public list, then the 赛事 appears in the default public results.
- [ ] Given a pending 赛事 is rejected or returned, when a student searches public
      赛事, then that 赛事 is not visible.
- [ ] Given public 赛事 exist, when a student searches or filters the list, then
      the results preserve the response envelope and pagination shape in
      `docs/api_spec.md`.
- [ ] Given a student opens a public 赛事 detail page, when the API returns data,
      then source facts, time nodes, tags, value notes, and official channels
      are visible.
- [ ] Given a publication or review action happens, when the reviewer checks
      records, then review or audit evidence exists for the operation.

## Impact Surface

- Product docs: This PRD refines P1 behavior under the stable product boundary.
- API: Public competition list/detail; admin competition create/update/submit
  review/review/status endpoints; optional outbound click endpoint.
- Data model: Reuses `competitions`, `competition_time_nodes`,
  `competition_tags`, `competition_tag_links`, `review_records`, and
  `audit_logs`. New schema work should be handled by implementation issues if
  model gaps are found.
- Frontend: Competition list and detail pages; minimal admin publication
  surface if included in implementation slice.
- Backend: Competition, admin, review, and audit services/routes.
- Permissions: Admin-only write/review actions; public read-only visibility for
  published 赛事.
- Tests: API tests for visibility, state transitions, validation, and response
  envelope; frontend lint/build; manual release-sprint acceptance path.
- Reports: Module report references M2 and M3; update course reports only when
  preparing deliverables.
- MkDocs navigation: This PRD is listed under Feature PRDs.

## Validation Plan

- Automated: `just api-test` for API behavior; `just api-lint` for backend
  quality; `just web-lint` and `just web-build` for frontend surfaces touched;
  `just docs-build` when docs change.
- Manual: Run the release-sprint acceptance path through administrator
  publication and student discovery/detail. Record branch or commit, seed data,
  passed steps, failed steps, and linked defects.

## Risks And Open Questions

- Risk: If migrations or seed data are not ready, the team may need a temporary
  in-memory or fixture-backed implementation for early API tests, then follow up
  with durable persistence.
- Risk: Splitting admin UI too early could delay the student-facing discovery
  path; backend/API should be the first stable contract.
- Open question: For Day 1, should admin publication be exposed through UI, CLI,
  seed script, or API-only acceptance?
- Open question: Which fields are the minimum required publication fields for
  the first implementation issue beyond source name, source URL, title, and at
  least one meaningful time or detail field?
