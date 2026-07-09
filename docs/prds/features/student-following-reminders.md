# Student Following And Reminders

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

Students need more than a public 赛事 list: they need a personal way to keep
interesting 赛事, actively subscribe to time nodes, and see follow-up reminders
or calendar entries. This PRD defines the P1 thin slice that turns a published
赛事 into a student-owned follow-up workflow while keeping 收藏 and 订阅
separate.

The current codebase already models users, profiles, favorites, subscriptions,
reminders, messages, and frontend route shells. The goal is to connect the
smallest useful student workflow that supports the course demo path without
building a broad account-management platform.

## Users

- 学生: logs in, maintains a minimal profile, favorites and subscribes to 赛事,
  and follows reminders or calendar nodes.
- 管理员: indirectly affects this workflow through published 赛事 and status
  changes.
- Reviewer / validation owner: verifies ownership, permissions, reminder
  consistency, and demo behavior.

## User Stories

1. As a 学生, I want to register or log in, so that my profile, 收藏, 订阅,
   reminders, and calendar can be saved.
2. As a 学生, I want to see my current user identity, so that the frontend can
   show the right personal actions.
3. As a 学生, I want to maintain college, major, grade, interests, and reminder
   preferences, so that search defaults, recommendations, and reminders have
   useful input.
4. As a 学生, I want unauthenticated personal actions to guide me to login, so
   that I understand why 收藏 or 订阅 cannot be saved yet.
5. As a 学生, I want to 收藏 a 赛事, so that I can find it again later without
   committing to reminders.
6. As a 学生, I want to cancel 收藏, so that my saved list stays relevant.
7. As a 学生, I want to 订阅 a 赛事, so that future key time nodes can appear in
   my reminders and 个人赛事日历.
8. As a 学生, I want 收藏 and 订阅 to be independent, so that saving a 赛事 does
   not automatically create reminder obligations.
9. As a 学生, I want duplicate 收藏 or 订阅 requests to be idempotent, so that
   repeated clicks do not corrupt my state.
10. As a 学生, I want cancelling 订阅 to cancel future pending reminders, so that
    I stop receiving follow-up for that 赛事.
11. As a 学生, I want 订阅 to generate reminders from registration deadline,
    submission deadline, and competition start nodes where present, so that I do
    not miss important steps.
12. As a 学生, I want a 个人赛事日历 list or calendar view, so that I can see
    upcoming subscribed 赛事 nodes in date order.
13. As a 学生, I want a message surface for sent 站内提醒, so that I can read and
    acknowledge reminder messages.
14. As a 学生, I want to mark messages as read, so that I can distinguish new
    reminders from old ones.
15. As a 学生, I want下架 or cancelled 赛事 to stop future reminders, so that I am
    not misled by stale follow-up.
16. As a reviewer, I want permission tests around personal data, so that one
    user cannot read or change another user's profile, calendar, messages, or
    engagement state.
17. As the team owner, I want this slice to be demo-ready before broader
    preference features, so that the product proves the student follow-up value
    inside the four-day window.

## Functional Requirements

- FR-001: Students can register, log in, log out, and fetch current session user
  information using the cookie-session model defined in the API spec.
- FR-002: Students can fetch and update their own profile and reminder
  preferences.
- FR-003: Students can favorite and unfavorite visible 赛事.
- FR-004: Students can subscribe and unsubscribe from visible 赛事.
- FR-005: 收藏 and 订阅 are separate records and state changes.
- FR-006: Public list and detail responses include the authenticated student's
  favorite and subscription state when a session exists.
- FR-007: Subscription creates pending reminders for selected future time node
  types when reminders are enabled.
- FR-008: Unsubscription cancels future pending reminders for that student and
  赛事.
- FR-009: Calendar API returns subscribed 赛事 nodes by date range and supports a
  thin list view even if full month/week UI is deferred.
- FR-010: Message API returns current user's in-app messages and supports marking
  a message as read.
- FR-011: Reminder dispatch is idempotent: repeated dispatch for the same due
  reminder must not create duplicate messages.
- FR-012: Frontend surfaces show personal action states on list/detail, plus a
  calendar or list page for subscribed nodes. A dedicated message page may be
  deferred if reminder evidence is visible another way in Day 1 implementation.

## Non-Functional Requirements

- Performance: Calendar and message views should remain responsive for the demo
  seed dataset and should not block public search/detail.
- Security or permission: Students can only access their own profile,
  favorites, subscriptions, reminders, calendar, and messages.
- Maintainability: Reminder generation and cancellation rules belong in
  services; Celery tasks call services instead of duplicating business rules.
- Observability or audit: This P1 slice does not require audit logs for ordinary
  student actions, but reminder state should be inspectable enough to validate
  pending, sent, read, cancelled, and failed behavior.

## Out Of Scope

- Not included: external notification channels such as email, SMS, WeChat, or
  enterprise messaging.
- Not included: advanced notification preference UI beyond default remind days,
  enabled state, and node types needed by the thin slice.
- Not included: social following, comments, team posts, or content materials.
- Not included: full account recovery, verification-code flows, or enterprise
  identity integration.
- Not included: teacher or organizer access to student follow-up state.
- Not included: a polished full calendar component if a date-ordered subscribed
  node list satisfies the first demo path.

## Acceptance Criteria

- [ ] Given a student registers or logs in successfully, when the frontend calls
      current-user API, then the student identity and role are returned through
      the standard response envelope.
- [ ] Given a logged-in student updates their profile, when they fetch it again,
      then the latest profile and reminder preference fields are returned.
- [ ] Given a logged-in student favorites a published 赛事, when they revisit the
      list or detail response, then `is_favorited` is true for that 赛事.
- [ ] Given a logged-in student subscribes to a published 赛事 with future time
      nodes, when the subscription completes, then active subscription state and
      pending reminder records exist.
- [ ] Given a logged-in student cancels a subscription, when calendar and
      pending reminders are checked, then future nodes for that subscription are
      removed or cancelled.
- [ ] Given due reminders exist, when reminder dispatch runs more than once,
      then the student receives no duplicate message for the same reminder.
- [ ] Given a student opens their calendar date range, when subscriptions exist,
      then subscribed 赛事 nodes are returned in a usable order with links to
      detail.
- [ ] Given a student tries to access another user's personal data, when the API
      is called, then the response is unauthorized or forbidden.

## Impact Surface

- Product docs: This PRD refines P1 student follow-up behavior under the stable
  product boundary.
- API: Auth, current user, profile, preferences, favorite, subscription,
  calendar, messages, and message read APIs.
- Data model: Reuses `users`, `student_profiles`, `favorites`,
  `subscriptions`, `reminder_settings`, `reminders`, `messages`, and
  `competition_time_nodes`.
- Frontend: Auth-aware list/detail actions, profile surface if included,
  personal calendar route, and optional message/read state surface.
- Backend: Auth, user/profile, subscription, notification, and reminder task
  services/routes.
- Permissions: Cookie-session authentication; student ownership checks for all
  personal data.
- Tests: API tests for auth/session, ownership, favorite/subscription
  idempotency, reminder generation/cancellation, dispatch idempotency, and
  calendar/message shape; frontend lint/build; manual acceptance.
- Reports: Module report references M1 and M4; update course reports only when
  preparing deliverables.
- MkDocs navigation: This PRD is listed under Feature PRDs.

## Validation Plan

- Automated: `just api-test` for API behavior and reminder services;
  `just api-lint`; `just web-lint` and `just web-build` for frontend surfaces
  touched; `just docs-build` when docs change.
- Manual: Run release-sprint acceptance steps from student login/profile through
  search, favorite, subscribe, calendar, and reminder/message evidence. Record
  branch or commit, seed data, passed steps, failed steps, and linked defects.

## Risks And Open Questions

- Risk: Full authentication can consume more time than the Day 1 half-day
  allows; the first implementation issue may need a thin but real session-based
  login before richer profile UX.
- Risk: Reminder behavior depends on durable time-node data from the publication
  PRD; implementation sequencing should not start reminder UI before the 赛事
  detail contract is stable.
- Open question: For the first demo, is a date-ordered 个人赛事日历 list acceptable,
  or must it visually present month/week calendar modes?
- Open question: Should Day 1 include a message center page, or is API-backed
  reminder evidence enough until the next day?
- Open question: Which exact profile fields are mandatory for first registration
  versus optional profile completion?
