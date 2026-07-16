# Competition Publication And Discovery

## Status

- Accepted
- Roadmap phase: P1
- Owner: Product owner / tech lead
- Related issues: #23, #24, #25

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
   tag, 报名截止日期, and participant form where data exists, so that I can
   reduce irrelevant results.
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
16. As an 管理员, I want a recurring 赛事 to retain one赛事系列 identity while each
    annual participation cycle has a separate赛事届次, so that new dates do not
    overwrite prior history.
17. As an 管理员, I want a schedule correction within the same赛事届次 to update
    that届次 with audit evidence, so that reminders can be recalculated without
    creating a duplicate annual record.
18. As a reviewer, I want a submitted赛事届次 revision to be reviewed by someone
    other than its submitter, so that source governance is not self-attestation.
19. As an editor, I want to prepare a replacement revision while the last
    approved revision stays public, so that ordinary corrections do not create
    unnecessary downtime or overwrite reviewed facts.
20. As a status maintainer, I want to take seriously unsafe or misleading public
    content offline immediately, so that withdrawal is fast but restoration
    still requires a corrected independently approved revision.

## Functional Requirements

- FR-001: 管理员 can create a draft 赛事 with title, source name, source URL,
  category, organizer, summary, detail, time nodes, suitable majors, suitable
  grades, tags, value notes, official URL, and attachment URL where available.
- FR-002: Draft 赛事 are not visible in public student list, detail, or
  recommendation surfaces.
- FR-003: 管理员 can submit a draft, a returned record restored to `draft`, or a
  corrected `rejected` 赛事 for review only when minimum required publication
  fields are present. P1 requires series identity, source-backed edition label,
  title, source name, valid HTTP(S) source URL, category, organizer, summary,
  eligibility, at least one participant form, explicit major and grade scope,
  at least one赛事阶段, and at least one primary core赛事时间节点 with a valid
  `occurs_at`. Team entry requires team-size facts. An empty time-node list
  cannot be published as an implicit "time to be announced" state.
- FR-004: 管理员 reviewer can approve, reject, or return a pending 赛事 with a
  comment.
- FR-005: Approved 赛事 become `published`; rejected or returned 赛事 remain
  non-public.
- FR-006: Create, submit-review, review-decision, and status-maintenance actions
  append audit events. Approve, reject, and return decisions also append an
  immutable review record for the submitted revision.
- FR-007: Public list API returns only default-public 赛事, supports pagination,
  and supports keyword and field filters described in `docs/api_spec.md`.
- FR-008: Public detail API returns source facts, visible status, publication
  and current-content update times, time nodes, fit fields, tags, value notes,
  official URL, attachment URL, and authenticated engagement state when
  available. Published 赛事 are publicly discoverable;
  cancelled, expired, and archived 赛事 retain public detail with a status
  warning; offline and never-published records do not have public detail.
- FR-009: Frontend list page consumes the public list API and renders loading,
  populated, empty, and error states.
- FR-010: Frontend detail page consumes the public detail API and renders source,
  content update time, time nodes, tags, value notes, official channels, status
  warnings, and a notice that selection guidance does not replace official or
  school recognition.
- FR-011: Official, source, and attachment links open directly and record a
  best-effort non-blocking outbound click using controlled target/surface values.
  Tracking failure never prevents navigation. Raw events omit user and device
  identifiers, expire after 90 days, and feed daily click-count aggregates. This
  is a required P1 discovery follow-up and a prerequisite for P2 click stats,
  but it does not block the already working publication-to-detail path.
- FR-012: Every赛事届次 belongs to a赛事系列. A new annual or otherwise distinct
  participation cycle creates a new届次; a schedule correction within the same
  cycle updates the existing届次. Similarity can suggest a series association or
  duplicate, but an administrator confirms it from source facts.
- FR-013: A same-edition schedule correction preserves an edition-scoped
  `logical_node_key`, creates a new immutable time-node snapshot with an
  incremented `node_revision` when behavior-bearing node facts change or the key
  is reintroduced after an approved removal, records old and new values plus a
  reason, and exposes both identifiers for reminder reconciliation. An
  unchanged node copied to another content revision keeps its node revision; a
  snapshot id refers only to its exact competition revision and must not be
  reused as the cross-revision identity. A logical key never present in
  approved edition history starts at revision `1`; re-adding a previously
  approved and removed key uses the approved historical maximum plus one, even
  when its facts match an older snapshot.
- FR-014: P1 accepts only the controlled赛事时间节点 types in the API contract.
  `other` requires a user-facing description and remains display-only; it does
  not satisfy the core-node publication gate or participate in default
  deadline filtering and reminder generation.
- FR-015: Each赛事时间节点 belongs to an ordered赛事阶段 and has `primary` or
  `secondary` prominence. Admin editing groups known milestone pairs, validates
  ordering, warns about a missing side, and audits prominence overrides. Public
  list and detail use stage and prominence metadata instead of reconstructing
  relationships from labels.
- FR-016: `participant_forms` is a non-empty set that may contain `individual`,
  `team`, or both. Major and grade适配范围 are each explicit `all`, `selected`,
  or `unknown`; `selected` requires a non-empty controlled-value list. Empty
  arrays do not mean both universal applicability and missing information.
- FR-017: 赛事编辑权限, 赛事审核权限, and赛事维护权限 are admin capabilities,
  not new formal roles. An account may hold multiple capabilities, but a
  submitted revision cannot be reviewed by its submitter. An editor may withdraw
  a still-pending submission to draft. `competition_maintainer` authorizes
  cancellation, expiry, archival, and emergency offline with required impact
  context and reason, but not revision editing, approval, or direct restoration.
- FR-018: 赛事届次 content is stored as numbered revisions. Published reads use
  the immutable `published_revision_id`; a later draft or pending revision is
  backend-only until independent approval atomically selects it. Submitted and
  decided revisions cannot be edited in place. P1 allows only one active draft
  or pending revision per edition. Replacements persist the public
  `base_revision_id`; approval locks the edition and returns
  `409 stale_revision` if that baseline is no longer current.
- FR-019: Emergency offline is an immediate audited lifecycle action with a
  required reason and status-maintenance permission. It removes public detail;
  restoration requires a corrected revision and independent approval rather
  than a direct status transition.
- FR-020: Public discovery exposes computed `registration_status`: `open`,
  `upcoming`, `closed`, `unknown`, or `not_applicable`. It derives the value from
  current public registration stages and nodes, returns the basis facts, and
  aggregates multiple rounds with open then upcoming precedence.
- FR-021: Public discovery defaults to deterministic `actionable` ordering:
  open, upcoming, unknown, not applicable, then closed; relevant registration or
  next-primary times order each group, followed by published-time and edition-id
  tie-breakers. Explicit P1 sorts are `registration_deadline` and `published_at`.
- FR-022: P1 includes a required赛事治理工作台 for series/edition selection,
  source-backed revision editing, staged paired-node controls, publication
  completeness, submission, independent diff review, status maintenance, and
  emergency offline. API, CLI, and seed paths are intermediate or test support
  and do not satisfy product acceptance by themselves. Its read API supports
  series search, edition/revision lists, edition workspace state, a global
  pending queue, complete revision reads, completeness, base/current-public
  comparison, stale state, and public/reminder impact previews.
- FR-023: `archived` and `expired` are routine historical lifecycle states and
  are allowed only when the current public revision has no future time node.
  Otherwise status maintenance returns a conflict with the blocking nodes.
  Successful transition retains favorite/subscription history and past calendar
  nodes, cancels any stale pending reminder, and creates no subscriber message.

## Non-Functional Requirements

- Performance: Public list and detail pages should remain comfortably under the
  PRD's 3-second local target for the seed dataset used in demo.
- Security or permission: Only 管理员 can create, submit, review, or change
  backend publication state. Anonymous users can read only public 赛事 data.
- Maintainability: Route handlers stay thin; review and publication rules belong
  in services; query behavior belongs in repositories when reusable.
- Time semantics: Time points remain timezone-aware UTC instants, while public
  date display and date-only filtering use the `Asia/Shanghai` product calendar.
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
- [ ] Given a draft permits team entry without team-size facts, uses an empty
      participant-form set, or omits explicit major or grade scope, when it is
      submitted for review, then the API rejects the request and identifies the
      missing publication facts.
- [ ] Given a draft 赛事 has no recognized 赛事时间节点 with a valid `occurs_at`
      instant, when the 管理员 submits it for review, then the API rejects the
      request and the record remains non-public.
- [ ] Given a pending 赛事 is approved by a 管理员 reviewer, when a student opens
      the public list, then the 赛事 appears in the default public results.
- [ ] Given a pending 赛事 is rejected or returned, when a student searches public
      赛事, then that 赛事 is not visible.
- [ ] Given a previously published 赛事 becomes cancelled, expired, or archived,
      when a student opens its saved detail URL, then the detail remains
      available with an explicit status warning but is absent from default
      discovery and recommendation results.
- [ ] Given an administrator tries to archive or expire an edition with a
      future node, when status maintenance runs, then it returns a conflict and
      changes no lifecycle, subscription, reminder, calendar, or message fact.
- [ ] Given every node has elapsed, when an administrator archives or expires
      the edition, then historical follow relations and past calendar nodes
      remain, stale pending reminders are cancelled, and no event message is
      created.
- [ ] Given a previously published 赛事 becomes offline, when a visitor opens its
      former detail URL, then the public API returns `404 not_found`.
- [ ] Given public 赛事 exist, when a student searches or filters the list, then
      the results preserve the response envelope and pagination shape in
      `docs/api_spec.md`.
- [ ] Given a 赛事 has a submission deadline inside a selected date range but its
      报名截止日期 is outside that range, when a student filters the public list
      by 报名截止日期, then that 赛事 is not returned for the submission deadline.
- [ ] Given a 报名截止日期 crosses a UTC calendar boundary, when a student views
      and filters by its `Asia/Shanghai` calendar date, then the displayed date
      and filtered result agree.
- [ ] Given a student opens a public 赛事 detail page, when the API returns data,
      then source facts, content update time, time nodes, tags, value notes,
      official channels, and the reference-only notice are visible.
- [ ] Given a student activates a source, official, or attachment link, when
      best-effort tracking succeeds or fails, then the real HTTP(S) target opens
      without waiting; accepted events use only controlled dimensions and no
      user, account, IP, User-Agent, or cross-day visitor identifier.
- [ ] Given raw outbound events cross 90 days, when daily aggregation and
      retention run repeatedly, then aggregate click counts remain idempotent,
      raw rows expire, and statistics are labeled as clicks rather than people
      or registration conversion.
- [ ] Given a publication or review action happens, when the reviewer checks
      records, then review or audit evidence exists for the operation.
- [ ] Given a new annual cycle of an existing赛事系列 is announced, when an
      administrator records it, then a new赛事届次 with independent time nodes is
      created and the prior届次 remains unchanged.
- [ ] Given an official source changes a date within the same赛事届次, when an
      administrator updates the node, then the existing届次 is updated with audit
      evidence rather than duplicated.
- [ ] Given a赛事届次 has multiple rounds and paired milestones, when a student
      views its list card and detail, then the list prefers the nearest future
      primary node and the detail groups correctly ordered pairs by labeled
      stage.
- [ ] Given an administrator submitted the current赛事届次 revision, when the same
      account attempts to approve, reject, or return it, then the API denies the
      action and another review-capable administrator must decide it.
- [ ] Given a published赛事届次 receives an ordinary correction, when a replacement
      revision is drafted or pending, then public reads continue returning the
      prior approved revision until another reviewer approves the replacement.
- [ ] Given one edition already has a draft or pending revision, when an editor
      tries to create another, then the API returns
      `409 active_revision_exists` with the existing revision and creates no
      parallel node-revision namespace.
- [ ] Given a submitted replacement's base differs from the current public
      pointer, when approval is attempted, then the locked transaction returns
      `409 stale_revision`, writes no terminal review decision, and requires a
      successor from the current public revision.
- [ ] Given a status maintainer urgently offlines a harmful public赛事届次, when a
      visitor opens it, then public detail is unavailable immediately; when the
      team wants to restore it, a corrected independently approved revision is
      required.
- [ ] Given registration stages are open, upcoming, closed, incomplete, or
      explicitly not applicable, when public discovery is filtered by
      `registration_status`, then the derived results match current stage facts
      and do not expose publication lifecycle as报名状态.
- [ ] Given mixed registration states and equal node times exist, when the public
      list uses default or explicit sorting across pages, then actionable records
      are prioritized and deterministic tie-breakers prevent duplicates or
      omissions.
- [ ] Given editor and reviewer administrator accounts are distinct, when a
      Playwright run creates a source-backed revision, edits stages and paired
      nodes, submits it, reviews the diff and impact, and approves it, then the
      public revision changes and the submitter cannot self-review through UI or
      API.
- [ ] Given series, editions, drafts, and pending revisions exist, when an
      authorized administrator uses the workbench read APIs, then searchable
      selection, the pending queue, complete revision content, completeness,
      base/current-public differences, stale state, and impact are available
      without treating terminal review records as pending work.
- [ ] Given a published edition requires cancellation, archival, expiry, or
      emergency offline, when the status maintainer uses the governance
      workbench, then impact is shown, required reasons are captured, public and
      reminder behavior follows the contract, and restoration cannot bypass an
      independently reviewed corrected revision.

## Impact Surface

- Product docs: This PRD refines P1 behavior under the stable product boundary.
- API: Public competition list/detail; admin series/edition/revision list and
  detail reads; admin competition create/update/submit/review/status commands;
  required non-blocking outbound click endpoint.
- Data model: Adds `competition_series` and `competition_revisions`, treats
  `competitions` as赛事届次 identity, and versions stages and time-node facts;
  reuses logical `competition_time_nodes`,
  `competition_tags`, `competition_tag_links`, `review_records`, and
  `audit_logs`; adds privacy-minimized outbound click event and daily aggregate
  tables. New schema work should be handled by implementation issues if model
  gaps are found.
- Frontend: Competition list and detail pages plus required administrator
  editing, review-diff, and status-maintenance workbench surfaces.
- Backend: Competition, admin, review, and audit services/routes.
- Permissions: Admin-only write/review actions; public read-only visibility for
  published 赛事.
- Tests: API tests for visibility, state transitions, validation, response
  envelope, controlled click targets, privacy fields, aggregation, and retention;
  frontend lint/build, non-blocking navigation acceptance, and Playwright for
  the distinct-editor/reviewer publication path and status maintenance.
- Reports: Module report references M2 and M3; update course reports only when
  preparing deliverables.
- MkDocs navigation: This PRD is listed under Feature PRDs.

## Validation Plan

- Automated: `just api-test` for API behavior; `just api-lint` for backend
  quality; `just web-lint` and `just web-build` for frontend surfaces touched;
  the project Playwright recipe for the administrator publication path; and
  `just docs-build` when docs change.
- Manual: Run the release-sprint acceptance path through administrator
  publication and student discovery/detail. Record branch or commit, seed data,
  passed steps, failed steps, and linked defects.

## Risks

- Risk: If migrations or seed data are not ready, the team may need a temporary
  in-memory or fixture-backed implementation for early API tests, then follow up
  with durable persistence.
- Risk: The backend/API remains the first stable implementation contract, but
  leaving the governance UI until after P1 would make the accepted product flow
  unusable by its administrator audience.
