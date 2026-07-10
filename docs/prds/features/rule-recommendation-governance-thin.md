# Rule Recommendation And Governance Thin Slice

## Status

- Accepted
- Roadmap phase: P2
- Owner: Product owner / tech lead
- Related issues: #27

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
- 管理员: maintains versioned recommendation rules and shared vocabulary, and
  inspects Review, Audit, and Statistics governance evidence.
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
9. As a 管理员, I want separate Review and Audit views, so that I can explain
   both governed decisions and the key operations that changed system state.
10. As a 管理员, I want defined current and 7-day/30-day statistics for content,
    follow-up, messages, outbound clicks, and recommendation interactions, so
    that the system demonstrates operational control without a large dashboard.
11. As a reviewer, I want tests that assert reasons come from rules or 赛事
    fields, so that implementation does not drift toward opaque ranking.
12. As the team owner, I want P2 thin work to be issue-sized and dependent on P1
    contracts, so that recommendation and governance do not block the core demo
    path.

## Functional Requirements

- FR-001: Recommendation API returns published 赛事 only, with each item wrapped
  in the standard response envelope and at least one controlled 推荐理由.
- FR-002: Authenticated students receive profile-aware reasons only when their
  dynamically derived profile status is `recommendation_ready`, requiring a
  valid controlled college, major, grade, and at least one interest tag. Reasons
  come from explicit fields such as major, grade, interest tags, category,
  suitable majors, suitable grades, tags, and deadline urgency.
- FR-003: Anonymous or profile-incomplete users receive general actionable
  recommendations from upcoming or configured fallback rules. The response
  identifies general mode and, for an authenticated student, exact missing
  profile fields; it does not imply a personal match.
- FR-004: Each recommendation item exposes reasons and ordering, not a public
  numeric score or 赛事 value rating.
- FR-005: Recommendation reasons must not contradict visible detail-page tags,
  suitable majors, suitable grades, or value notes.
- FR-006: Personalized recommendation uses one immutable active
  `recommendation_rule_set` with controlled rule codes, bounded integer weights,
  structured validated conditions, and reason templates. Responses identify the
  active version; hidden service constants and executable rule expressions are
  forbidden.
- FR-007: A reproducible seed creates the initial active rule set. The thin admin
  workbench supports candidate cloning/editing, synthetic preview, submission,
  independent diff review, activation, and retained history. The submitter
  cannot review the same version.
- FR-007A: Base dictionaries and school-level governance belong to the configured
  部署高校. External赛事 sources do not create another tenant or dictionary scope.
- FR-008: The administrator governance workbench has required Review, Audit,
  and Statistics tabs. Review exposes immutable competition-revision and
  recommendation-rule-set decisions with stable pagination, filters, reviewed
  differences, impact, comments, and decision time. Audit exposes immutable
  key-operation events with stable pagination and actor/action/target/result/date
  filters through action-specific safe detail fields.
- FR-009: The Statistics tab exposes current published and pending-review
  counts, active favorites and subscriptions, message delivery states, and
  7-day/30-day outbound click and recommendation impression/click counts. Every
  metric includes a definition, `as_of`, time zone, window, and best-effort
  caveat where applicable. Recommendation totals and ratio count each request
  item once; reason breakdown is separate non-additive attribution. Neither
  claims unique people, causality, quality, or registration conversion.
- FR-010: Frontend recommendation page consumes the recommendation API and
  renders loading, populated, empty, and error states with visible 推荐理由.
- FR-011: The administrator governance home shows pending-task counts,
  recommendation configuration faults, and only a few summary metrics. Detailed
  evidence stays in the required Review, Audit, and Statistics tabs.
- FR-012: Activating an approved candidate atomically retires the prior active
  rule set. Draft/pending candidates do not affect current results, and decided
  or active snapshots cannot be edited in place.
- FR-013: When no valid active rule set exists, personalization explicitly
  degrades to general actionable results with `no_active_rule_set` metadata and
  a visible admin configuration fault; it never silently uses code constants.
- FR-014: Each recommendation response creates opaque 90-day request-item
  snapshots. Frontend rendering records idempotent impressions and detail
  navigation records idempotent non-blocking clicks only for returned items.
  Raw rows omit user/device/profile identifiers and feed two Shanghai-date
  aggregates: item-level totals that count each request item once, and separate
  non-additive reason attribution that counts each distinct displayed reason.

## Non-Functional Requirements

- Performance: Recommendation should be synchronous and fast for the demo seed
  dataset; caching is optional and should not hide correctness.
- Security or permission: Student recommendation can use only the current
  student's profile. Admin configuration, audit, and statistics endpoints are
  admin-only.
- Maintainability: Recommendation logic remains rule-based and explainable;
  implementation should not introduce model-based ranking or hidden scoring.
- Observability or audit: Review decisions and audit events are immutable;
  statistics are read-only. Audit detail excludes passwords, verification
  codes, session values, full account identifiers, profile content, and raw
  analytics identifiers.
- Analytics privacy: Recommendation events do not store user id, account
  identity, profile fields, IP, User-Agent, or cross-request identifiers and do
  not automatically tune individual recommendations. Overall metrics come only
  from item-level totals; reason attribution is explicitly non-additive.
- Governance: Recommendation editing and review use
  `recommendation_editor`/`recommendation_reviewer` administrator capabilities.
  Submission, review, activation, retirement, version differences, and reasons
  are auditable.

## Out Of Scope

- Not included: machine-learning ranking, embeddings, or personalized model
  training.
- Not included: public 赛事 value scores, percentile scores, or "含金量" scoring.
- Not included: advanced recommendation feedback such as not-interested tuning
  unless it is trivial and non-blocking.
- Not included: a general-purpose executable rules engine or full configuration
  management for every dictionary. The bounded recommendation rule-set
  workbench is included.
- Not included: broad analytics dashboards, charts, exports, or teacher-facing
  reports.
- Not included: real-time event streams, user-level drill-down, or a general BI
  query surface.
- Not included: M7 materials, team posts, certified Q&A, or post-competition
  review content.

## Acceptance Criteria

- [ ] Given published 赛事 and an authenticated student profile exist, when the
      recommendation API is called, then it returns recommended 赛事 with
      traceable 推荐理由.
- [ ] Given an anonymous user calls the recommendation API, when enough
      published 赛事 exist, then the API returns general recommendations without
      requiring login.
- [ ] Given an authenticated student's profile is incomplete, when the
      recommendation API is called, then it returns general mode, exact missing
      fields, and only general fallback reasons rather than profile-match claims.
- [ ] Given draft, pending, rejected, offline, or cancelled 赛事 exist, when
      recommendations are generated, then those records are excluded from
      default recommendation results.
- [ ] Given a recommendation reason says a 赛事 matches a major, grade, tag, or
      deadline, when the detail data is inspected, then the reason can be traced
      to explicit profile, rule, or 赛事 fields.
- [ ] Given recommendation results are returned, when the frontend renders them,
      then users see 推荐理由 and do not see a raw score or public value rating.
- [ ] Given an active rule-set version exists, when personalized results are
      returned, then metadata identifies that immutable version and every reason
      traces to a controlled active rule or explicit competition fact.
- [ ] Given an editor previews and submits a candidate rule set, when the same
      account attempts review, then it is denied; a distinct reviewer can inspect
      synthetic preview and differences, activate it, and atomically retire the
      prior active version.
- [ ] Given no active rule set exists, when a recommendation-ready student calls
      the endpoint, then results explicitly use general actionable mode with a
      configuration fallback reason and the admin surface exposes the fault.
- [ ] Given competition and recommendation-rule decisions exist, when an admin
      opens the Review tab, then stable filters and pagination expose immutable
      target versions, differences, impact summaries, comments, reviewers, and
      decision times.
- [ ] Given key administrative and system operations exist, when an admin opens
      the Audit tab, then stable actor/action/target/result/date filters expose
      immutable allowlisted events without passwords, verification codes,
      session values, full account identifiers, profile content, or raw
      analytics identifiers.
- [ ] Given an admin opens the Statistics tab, when current facts and daily
      aggregates exist, then the standard response envelope shows current
      publication/review/follow/message counts and 7-day/30-day outbound and
      recommendation counts with definitions, `as_of`, time zone, and
      best-effort caveats.
- [ ] Given an admin opens the governance home, when pending work or a missing
      active rule set exists, then a compact summary exposes task counts and the
      configuration fault while detailed evidence remains in the three tabs.
- [ ] Given outbound click aggregates exist, when an admin views thin stats,
      then counts can be broken down by date, edition, target type, source
      surface, and actor kind, with an explicit best-effort click-count caveat
      and no user-level drill-down.
- [ ] Given recommendation items are returned but only some are rendered and one
      is opened, when event delivery is retried, then only rendered items count
      once as impressions, the real opened item counts once as a click, and
      client attempts to forge position/rule/reason/item dimensions are denied.
- [ ] Given recommendation raw request items cross 90 days, when aggregation and
      retention run repeatedly, then raw rows expire, item-level totals remain
      idempotent and drive the displayed best-effort ratio, while multi-reason
      attribution remains separately labeled and is never summed as overall
      user count, quality, or conversion.
- [ ] Given a non-admin user calls admin governance or config endpoints, when the
      API checks permissions, then access is denied.

## Impact Surface

- Product docs: This PRD refines P2 thin behavior under the stable product
  boundary.
- API: Recommendation endpoint; versioned recommendation-rule-set list, draft,
  preview, submit, and review endpoints; admin audit and stats endpoints.
- Data model: Reuses `student_profiles`, `competitions`, `competition_tags`,
  `competition_tag_links`, versioned `recommendation_rule_sets` and rules,
  `system_configs`,
  `review_records`, `audit_logs`, the discovery slice's
  `outbound_click_daily_stats`, and privacy-minimized recommendation request-item,
  item-total, and reason-attribution daily tables. User-level tracking tables
  are not part of scope.
- Frontend: Recommendation page plus the required governance home and Review,
  Audit, and Statistics tabs.
- Backend: Recommendation, configuration, audit, review, and admin stats
  services/routes.
- Permissions: Anonymous general recommendation read; profile-aware student
  recommendation; admin-only config/governance/stat surfaces.
- Tests: API tests for recommendation filtering, reason traceability, no public
  score, fallback, request-item validation, event idempotency, privacy fields,
  aggregation/retention, governance filters and pagination, immutable evidence,
  sensitive-field exclusion, and admin permissions; frontend lint/build plus
  Playwright for the recommendation path and all three governance tabs.
- Reports: Module report references M5 and M6; update course reports only when
  preparing deliverables.
- MkDocs navigation: This PRD is listed under Feature PRDs.

## Validation Plan

- Automated: `just api-test` for recommendation and admin permission behavior;
  `just api-lint`; `just web-lint` and `just web-build` for frontend surfaces
  touched; the project Playwright suite introduced with the workbench for tab,
  filter, evidence-detail, and permission paths; `just docs-build` when docs
  change.
- Manual: Run release-sprint acceptance steps for recommendation reasons and
  admin governance evidence after P1 publication/discovery and student profile
  data exist. Record branch or commit, seed data, passed steps, failed steps,
  and linked defects.

## Risks

- Risk: P2 thin depends on P1 published 赛事 and profile data; recommendation
  implementation should not start from isolated mock data unless the issue
  explicitly says it is a temporary contract test.
- Risk: Configuration UI can expand quickly; Day 1 should prefer explicit seed
  data or a narrow admin API over a broad settings interface.
