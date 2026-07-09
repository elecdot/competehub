# Rule Recommendation And Governance Thin Slice

## Status

- Draft
- Roadmap phase: P2
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

The four-day delivery target asks for P1 plus a P2 thin product increment
without reducing quality or collapsing the product into unmanaged demo code. For
CompeteHub, the minimum valuable P2 slice is explainable 规则推荐 plus enough
governance evidence to show that recommendations, configuration, review, audit,
and basic statistics are controlled rather than hidden.

This PRD defines the smallest P2 thin layer that can sit on top of the P1
publication, discovery, and follow-up workflow. It intentionally avoids machine
learning, public scoring, broad dashboards, and later M7 content extensions.

## Users

- 学生: sees recommended 赛事 and 推荐理由.
- 管理员: maintains basic dictionaries or rule weights where included, and
  checks minimal governance evidence.
- Reviewer / validation owner: verifies recommendation traceability, no public
  score behavior, and governance evidence for demo.

## User Stories

1. As a 学生, I want to see recommended published 赛事, so that I can discover
   relevant opportunities without manually searching every time.
2. As a 学生, I want recommendation results to show 推荐理由, so that I can judge
   whether the recommendation is credible.
3. As a 学生, I want recommendation reasons to reflect my profile, interests,
   grade, and 赛事 fields where available, so that the output feels personal but
   explainable.
4. As an anonymous visitor, I want recommendations to degrade to general recent
   or relevant published 赛事, so that the page remains useful without a profile.
5. As a 学生, I want recommendations to exclude draft, pending, rejected, offline,
   and cancelled 赛事 by default, so that I am not guided toward unavailable
   records.
6. As a 学生, I want recommendation output to avoid public scores or value
   ratings, so that I am not misled into treating 赛事 value as an absolute
   system judgment.
7. As a 管理员, I want recommendation rules or weights to be represented as
   explicit configuration, so that recommendation behavior can be explained and
   adjusted later.
8. As a 管理员, I want base dictionaries such as category, suitable grades,
   majors, tags, and message templates to have an initial governance surface or
   seed path, so that P1 data entry and P2 recommendations share vocabulary.
9. As a 管理员, I want audit or review records visible enough for demo, so that
   the team can prove publication and governance are traceable.
10. As a 管理员, I want basic statistics for published 赛事, favorites,
    subscriptions, outbound clicks, or recommendation clicks where available, so
    that the system demonstrates operational control without a large dashboard.
11. As a reviewer, I want tests that assert reasons come from rules or 赛事
    fields, so that implementation does not drift toward opaque ranking.
12. As the team owner, I want P2 thin work to be issue-sized and dependent on P1
    contracts, so that recommendation and governance do not block the core demo
    path.

## Functional Requirements

- FR-001: Recommendation API returns published 赛事 only, with each item wrapped
  in the standard response envelope and at least one 推荐理由 when a reason can be
  derived.
- FR-002: Authenticated students receive profile-aware reasons from explicit
  fields such as major, grade, interest tags, category, suitable majors,
  suitable grades, tags, and deadline urgency.
- FR-003: Anonymous or profile-incomplete users receive general recommendations
  from recent, upcoming, or configured fallback rules.
- FR-004: Each recommendation item exposes reasons and ordering, not a public
  numeric score or 赛事 value rating.
- FR-005: Recommendation reasons must not contradict visible detail-page tags,
  suitable majors, suitable grades, or value notes.
- FR-006: Recommendation rules use explicit configuration or service constants
  that can later map to `recommendation_rules` and `system_configs`.
- FR-007: A thin admin configuration path or seed path exists for base
  dictionaries and recommendation weights used in Day 1 data.
- FR-008: A thin governance surface exists for review records, audit logs, or
  both, enough to prove publication decisions and key admin operations during
  acceptance.
- FR-009: A thin statistics response exists for counts available from the
  implemented data, prioritizing published 赛事, pending reviews, favorites,
  subscriptions, outbound clicks, and recommendation clicks.
- FR-010: Frontend recommendation page consumes the recommendation API and
  renders loading, populated, empty, and error states with visible 推荐理由.
- FR-011: Frontend admin home may show thin governance and stats evidence if it
  can be completed without delaying the student recommendation page.

## Non-Functional Requirements

- Performance: Recommendation should be synchronous and fast for the demo seed
  dataset; caching is optional and should not hide correctness.
- Security or permission: Student recommendation can use only the current
  student's profile. Admin configuration, audit, and statistics endpoints are
  admin-only.
- Maintainability: Recommendation logic remains rule-based and explainable;
  implementation should not introduce model-based ranking or hidden scoring.
- Observability or audit: Admin configuration and status changes that exist in
  this slice should create or expose enough audit evidence for acceptance.

## Out Of Scope

- Not included: machine-learning ranking, embeddings, or personalized model
  training.
- Not included: public 赛事 value scores, percentile scores, or "含金量" scoring.
- Not included: advanced recommendation feedback such as not-interested tuning
  unless it is trivial and non-blocking.
- Not included: full configuration management for every dictionary and rule.
- Not included: broad analytics dashboards, charts, exports, or teacher-facing
  reports.
- Not included: M7 materials, team posts, certified Q&A, or post-competition
  review content.

## Acceptance Criteria

- [ ] Given published 赛事 and an authenticated student profile exist, when the
      recommendation API is called, then it returns recommended 赛事 with
      traceable 推荐理由.
- [ ] Given an anonymous user calls the recommendation API, when enough
      published 赛事 exist, then the API returns general recommendations without
      requiring login.
- [ ] Given draft, pending, rejected, offline, or cancelled 赛事 exist, when
      recommendations are generated, then those records are excluded from
      default recommendation results.
- [ ] Given a recommendation reason says a 赛事 matches a major, grade, tag, or
      deadline, when the detail data is inspected, then the reason can be traced
      to explicit profile, rule, or 赛事 fields.
- [ ] Given recommendation results are returned, when the frontend renders them,
      then users see 推荐理由 and do not see a raw score or public value rating.
- [ ] Given an admin checks governance evidence, when review or audit records
      exist from publication work, then the admin surface or API can show them.
- [ ] Given basic statistics are requested by an admin, when implemented data
      exists, then the API returns useful counts through the standard response
      envelope.
- [ ] Given a non-admin user calls admin governance or config endpoints, when the
      API checks permissions, then access is denied.

## Impact Surface

- Product docs: This PRD refines P2 thin behavior under the stable product
  boundary.
- API: Recommendation endpoint; admin config endpoint if included; admin review,
  audit, and stats endpoints for thin governance evidence.
- Data model: Reuses `student_profiles`, `competitions`, `competition_tags`,
  `competition_tag_links`, `recommendation_rules`, `system_configs`,
  `review_records`, and `audit_logs`. New tracking tables should be deferred
  unless required by the issue scope.
- Frontend: Recommendation page and optional admin home governance/stat widgets.
- Backend: Recommendation, configuration, audit, review, and admin stats
  services/routes.
- Permissions: Optional public recommendation read; profile-aware student
  recommendation; admin-only config/governance/stat surfaces.
- Tests: API tests for recommendation filtering, reason traceability, no public
  score behavior, fallback behavior, and admin permission boundaries; frontend
  lint/build; manual acceptance.
- Reports: Module report references M5 and M6; update course reports only when
  preparing deliverables.
- MkDocs navigation: This PRD is listed under Feature PRDs.

## Validation Plan

- Automated: `just api-test` for recommendation and admin permission behavior;
  `just api-lint`; `just web-lint` and `just web-build` for frontend surfaces
  touched; `just docs-build` when docs change.
- Manual: Run release-sprint acceptance steps for recommendation reasons and
  admin governance evidence after P1 publication/discovery and student profile
  data exist. Record branch or commit, seed data, passed steps, failed steps,
  and linked defects.

## Risks And Open Questions

- Risk: P2 thin depends on P1 published 赛事 and profile data; recommendation
  implementation should not start from isolated mock data unless the issue
  explicitly says it is a temporary contract test.
- Risk: Configuration UI can expand quickly; Day 1 should prefer explicit seed
  data or a narrow admin API over a broad settings interface.
- Open question: For the first demo, which governance evidence matters most:
  review records, audit logs, or basic statistics?
- Open question: Should recommendation click tracking be included in P2 thin, or
  deferred until after recommendation display works?
- Open question: Should rule weights be stored in `recommendation_rules` from
  the first implementation, or can service-level constants be accepted for the
  first tracer bullet with a follow-up persistence issue?
