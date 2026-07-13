# Student Following And Reminders

## Status

- Accepted
- Roadmap phase: P1
- Owner: Product owner / tech lead
- Related issues: #22, #25, #26

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

P1 runs inside one configured部署高校. Student numbers and colleges are local
to that deployment; multi-institution account tenancy is not part of this
slice. Typed identity support is separate from registration-channel scope:
email self-registration is available only with a configured real sender,
student numbers use a controlled institution path, and phone registration is
deferred.

## Users

- 学生: logs in, maintains a minimal profile, favorites and subscribes to 赛事,
  and follows reminders or calendar nodes.
- 管理员: indirectly affects this workflow through published 赛事 and status
  changes.
- Reviewer / validation owner: verifies ownership, permissions, reminder
  consistency, and demo behavior.

## User Stories

1. As a 学生, I want to activate and log in with an institution-provisioned
   account or an enabled verified registration method, so that my profile,
   收藏, 订阅, reminders, and calendar can be saved.
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
18. As a 学生, I want 收藏 and 订阅 to remain attached to the赛事届次 I selected,
    so that a future届次 does not create reminders without new consent.
19. As a 学生, I want an explicit赛事时间变更通知 when a subscribed published届次
    is rescheduled, so that stale pending reminders are replaced without
    rewriting messages I already received.

## Functional Requirements

- FR-001: Students can log in, log out, and fetch current session user
  information using the cookie-session model and explicitly typed account
  identities defined in the API spec. Login never cross-searches identity types,
  and only active accounts can establish a session. Current-user responses
  include a controlled capability array, empty for students, for frontend
  discovery while backend checks remain authoritative.
- FR-002: Students can fetch and update their own profile and reminder
  preferences.
- FR-003: Students can favorite published or historical-viewable 赛事 and can
  unfavorite an owned relation in every lifecycle state.
- FR-004: Only published 赛事 accept new subscriptions or setting changes;
  students can unsubscribe an owned relation in every lifecycle state,
  including when public detail is offline.
- FR-005: 收藏 and 订阅 are separate records and state changes.
- FR-006: Public list and detail responses include the authenticated student's
  favorite and subscription state when a session exists.
- FR-007: Subscription creates pending reminders for selected future time node
  types when reminders are enabled.
- FR-008: Unsubscription cancels future pending reminders for that student and
  赛事.
- FR-009: Calendar API returns subscribed赛事 nodes by date range as one source
  for the required month, week, and list views.
- FR-010: Message API returns only the current user's retained in-app messages,
  supports all/unread and controlled-type filters, unread count, one-message
  read, and read-all actions.
- FR-011: Reminder dispatch is idempotent: repeated dispatch for the same due
  reminder must not create duplicate messages.
- FR-012: Frontend surfaces show personal action states on list/detail, a
  calendar or list page for subscribed nodes, and a dedicated compact message
  center reached from a global unread badge.
- FR-013: 收藏, 订阅, reminders, and calendar nodes belong to one赛事届次. A new届次
  in the same赛事系列 does not inherit engagement state. A future关注赛事系列 action
  is separate and cannot create a届次订阅 automatically.
- FR-014: A赛事时间节点 correction preserves its edition-scoped logical key and
  creates a new immutable snapshot with an incremented node revision only when
  behavior-bearing node facts change. Pending reminders retain an FK to the
  exact prior snapshot and are cancelled as superseded, future plans are
  rebuilt from the new snapshot, and sent reminders remain immutable. Each
  approved revision creates at most one consolidated赛事时间变更通知 per affected
  subscriber, only for occurrence, selected node presence, or selected node
  type changes; presentation-only changes refresh pending content without a
  message.
- FR-015: Calendar results retain赛事阶段 and时间节点重点级别 metadata. All node
  types selected by the subscription remain visible, while primary nodes receive
  stronger display treatment without changing reminder consent.
- FR-016: When a real email sender is configured, P1 email registration creates
  a pending account, verifies it through a single-use limited-lifetime code, and
  activates it without creating a session. Without that sender, public
  registration is unavailable and demo or deployed users come from a controlled
  provisioning path. Phone registration and self-asserted student-number
  registration are unavailable.
- FR-017: P1 single-factor passwords contain 15 to 128 Unicode code points after
  NFC normalization, allow spaces and password-manager workflows, have no
  character-composition rule, and are rejected by a local weak-password
  blocklist when commonly compromised or context-specific. Authentication uses
  explicit adaptive-hash parameters and rate-limited generic failures.
- FR-018: Every protected request requires an active account and matching
  session version. Student sessions expire after 24 hours idle or seven days
  absolute; administrator sessions expire after 30 minutes idle or eight hours
  absolute. Changing an account's role or capabilities, disabling it, or
  terminating all sessions invalidates every device on its next request, while
  ordinary logout affects only the current browser.
- FR-019: Student profile readiness is derived as `recommendation_ready` only
  when controlled college, major, grade, and 1 to 10 interest tags are valid,
  including the college-major relationship. Other profile fields are optional.
  Incomplete profiles remain usable for search, detail, favorite, subscription,
  and reminders, while recommendation explicitly falls back to general mode.
- FR-020: Favorite never creates reminder obligations. First subscription shows
  and requires confirmation of reminder enabled state, one 0-to-30-day offset,
  and a non-empty set of controlled primary core node types regardless of
  whether reminders are enabled. Global defaults are enabled, three days, and
  registration deadline, submission deadline, and competition start, but they
  only prefill the choice. Reminder-disabled subscriptions create no reminder
  plans but retain the confirmed node selection for follow lists and calendars.
- FR-021: Disabling global reminders cancels all pending plans without deleting
  subscriptions or calendar nodes. Re-enabling does not restore cancelled plans
  or create plans from existing subscriptions. P1 creates one ordinary reminder
  per selected node and never backfills a trigger that already passed as an
  immediate due reminder.
- FR-022: Delivered messages are immutable 365-day snapshots with independent
  unread/read state. P1 types are `reminder_due`,
  `competition_time_changed`, `competition_cancelled`, and
  `competition_offline`. Domain-event idempotency prevents duplicates; user
  cancellation creates no message, while competition-side cancellation or
  emergency offline creates one message per active subscriber and event.
- FR-023: The personal calendar provides month, week, and list views over one
  subscribed-node source of truth. Desktop defaults to month and mobile to list,
  with the last device choice retained. Favorites never enter the calendar;
  reminder-disabled subscriptions do. Views preserve Shanghai date grouping,
  stage/pair metadata, primary prominence, same-day access, current revisions,
  and unavailable-target state.
- FR-024: Every actual reminder delivery attempt increments an attempt count.
  Transient failures record a controlled error and next-attempt time, then move
  through `failed -> pending` before retry; permanent or exhausted failures
  remain `failed` and are not selected by ordinary pending dispatch.
- FR-025: Archival or expiry is accepted only after all edition nodes have
  elapsed. Existing subscriptions remain historical follow relations and past
  selected nodes remain queryable in calendar ranges; stale pending reminders
  are cancelled, no new plan is eligible, and no archival/expiry message is
  created.
- FR-026: Explicit re-subscription reuses the cancelled edition-bound relation
  and records a fresh reminder confirmation. It never creates a second relation,
  restores cancelled, sent, or failed reminder evidence, or carries engagement
  to another edition.

## Non-Functional Requirements

- Performance: Calendar and message views should remain responsive for the demo
  seed dataset and should not block public search/detail.
- Security or permission: Students can only access their own profile,
  favorites, subscriptions, reminders, calendar, and messages. Pending accounts
  cannot authenticate or create those records, and registration responses do
  not expose whether an identity already exists.
- Maintainability: Reminder generation and cancellation rules belong in
  services; Celery tasks call services instead of duplicating business rules.
- Observability or audit: This P1 slice does not require audit logs for ordinary
  student actions, but reminder state should be inspectable enough to validate
  pending, sent, cancelled, and failed plan behavior, while message state is
  separately inspectable as unread or read.
- Retention: Read and unread messages remain available for 365 days. P1 does not
  support per-message deletion, and target unavailability does not erase the
  historical snapshot.

## Out Of Scope

- Not included: external notification channels such as email, SMS, WeChat, or
  enterprise messaging.
- Not included: advanced notification preference UI beyond default remind days,
  enabled state, and node types needed by the thin slice.
- Not included: social following, comments, team posts, or content materials.
- Not included: phone/SMS registration, full account recovery, or enterprise
  identity integration. The bounded email activation flow is included only when
  a real sender is configured.
- Not included: teacher or organizer access to student follow-up state.
- Not included: 关注赛事系列 or automatic cross-edition subscription renewal.
- Not included: external calendar synchronization, custom calendar-grid logic,
  or calendar views beyond the required FullCalendar month, week, and list
  capabilities.

## Acceptance Criteria

- [ ] Given a provisioned and active student logs in successfully, when the
      frontend calls current-user API, then the student identity and role are
      returned through the standard response envelope.
- [ ] Given email registration is enabled, when a student registers, then the
      account remains pending and no session exists until a valid single-use
      code is accepted; verification activates the account but still requires a
      normal login.
- [ ] Given no real email sender is configured, when the registration surface is
      loaded or called, then the frontend hides the entry and the API reports
      registration unavailable; no verification code is returned or logged.
- [ ] Given a new password is shorter than 15 characters, longer than 128
      characters, or appears in the local weak-password blocklist, when account
      creation is requested, then it is rejected with actionable guidance; a
      valid Unicode passphrase with spaces is accepted without a composition
      requirement or truncation.
- [ ] Given repeated failed logins for one typed identity or request source,
      when the configured threshold is reached, then attempts are progressively
      rate-limited without revealing account state or permanently locking the
      account.
- [ ] Given an authenticated student account is disabled or its session version
      is incremented, when an existing browser next calls any protected API,
      then the session is cleared, a generic `401` is returned, and no route
      behavior is executed.
- [ ] Given a student or administrator session crosses its role-specific idle or
      absolute deadline, when the next protected request is made, then the
      server rejects it; activity may refresh the idle deadline but never the
      absolute deadline.
- [ ] Given the same account has two active sessions, when one browser logs out,
      then only that browser is logged out; when terminate-all is applied, both
      are rejected on their next request.
- [ ] Given a student has not completed college, major, grade, or one interest
      tag, when profile and recommendation APIs are called, then the profile
      reports `incomplete` with exact missing fields and recommendation uses an
      explicit general fallback without blocking personal follow-up actions.
- [ ] Given a student submits a complete dictionary-backed profile, when it is
      read again, then the API derives `recommendation_ready`; an invalid
      college-major pair, unknown dictionary value, duplicate tag, or more than
      10 interest tags is rejected without losing the submitted form state.
- [ ] Given two users have the same literal text under different identity types,
      when either logs in with an explicit type, then only the matching typed
      identity is considered and password matching cannot select another user.
- [ ] Given a logged-in student updates their profile, when they fetch it again,
      then the latest profile and reminder preference fields are returned.
- [ ] Given a logged-in student favorites a published 赛事, when they revisit the
      list or detail response, then `is_favorited` is true for that 赛事.
- [ ] Given a cancelled, archived, or expired edition retains public detail,
      when a student favorites it, then the relation is created; given an
      offline target with existing engagement, owned DELETE operations still
      remove favorite or subscription while new or update mutations are denied.
- [ ] Given a logged-in student opens first subscription, when the confirmation
      is shown, then enabled state, one 0-to-30-day offset, and controlled node
      types are visible and editable; only explicit confirmation creates the
      subscription and eligible pending plans.
- [ ] Given a student favorites a赛事 or subscribes with reminders disabled, when
      records are inspected, then favorite creates no reminder obligation and
      the reminder-disabled subscription remains visible in follow and calendar
      surfaces without pending plans.
- [ ] Given a logged-in student cancels a subscription, when calendar and
      pending reminders are checked, then future nodes for that subscription are
      removed or cancelled.
- [ ] Given that student explicitly re-subscribes to the same currently
      published edition, when fresh complete reminder consent is submitted, then
      the existing relation becomes active with the latest confirmation without
      restoring cancelled, sent, or failed reminder evidence.
- [ ] Given global reminders are disabled and later re-enabled, then
      subscriptions and calendar nodes remain, old pending plans stay cancelled,
      and no existing-subscription plan is recreated.
- [ ] Given due reminders exist, when reminder dispatch runs more than once,
      then the student receives no duplicate message for the same reminder.
- [ ] Given reminder delivery fails transiently, when its retry time arrives,
      then the retry scheduler moves it from failed to pending before another
      idempotent dispatch; permanent or exhausted failures remain inspectable
      without being selected again.
- [ ] Given retained read and unread messages exist, when the student opens the
      global unread badge and message center, then all/unread and controlled-type
      filters, stable pagination, one-message read, and read-all update the
      unread count without changing message snapshots.
- [ ] Given a subscribed competition is cancelled or emergency-offlined, when
      the domain event is handled repeatedly, then one durable event message per
      student and event remains readable even if its target is unavailable, and
      future reminders stop without duplicate messages.
- [ ] Given a message reaches 365 days old, when retention cleanup runs, then it
      is removed regardless of read state; no per-message delete API or UI is
      available before expiry.
- [ ] Given a student opens their calendar date range, when subscriptions exist,
      then month, week, and list views render the same subscribed nodes in
      `Asia/Shanghai`, with primary/current/next prominence, paired labels,
      stable same-day order, and only available detail links.
- [ ] Given a subscription has reminders disabled, when the calendar is opened,
      then its selected nodes remain; given only a favorite exists, no calendar
      node is created.
- [ ] Given desktop and mobile viewports, when the calendar is first opened and
      switched, then desktop defaults to month, mobile defaults to list, the
      device remembers the last selection, and Playwright verifies non-overlap
      and usable same-day expansion.
- [ ] Given a student 收藏s or 订阅s one赛事届次, when a new届次 is published in the
      same赛事系列, then the new届次 is neither favorited nor subscribed and no
      reminder is created without a new student action.
- [ ] Given a student tries to access another user's personal data, when the API
      is called, then the response is unauthorized or forbidden.
- [ ] Given a subscribed published赛事届次 time node changes, when reminder plans
      are reconciled, then old pending plans are cancelled, eligible future
      plans use the new revision, sent reminders remain unchanged, and at most
      one idempotent consolidated time-change message is visible when an
      occurrence, selected node presence, or selected node type changed.
- [ ] Given only stage, prominence, description, title, or another
      presentation field changes, when the revision is approved, then calendar
      and pending reminder content refresh without a
      `competition_time_changed` message or due-time change.

## Impact Surface

- Product docs: This PRD refines P1 student follow-up behavior under the stable
  product boundary.
- API: Auth, current user, profile, preferences, favorite, subscription,
  calendar, messages, and message read APIs.
- Data model: Reuses `users`, `user_identities`,
  `identity_verification_challenges`, `student_profiles`, `favorites`,
  `subscriptions`, `reminder_settings`, `reminders`, `messages`, and
  `competition_time_nodes`.
- Frontend: Auth-aware list/detail actions, profile surface if included,
  personal calendar route, global unread badge, and required compact message
  center with all/unread filters and read actions. Calendar uses FullCalendar's
  Vue 3 standard month/week/list capabilities rather than a hand-built grid.
- Backend: Auth, user/profile, subscription, notification, and reminder task
  services/routes.
- Permissions: Cookie-session authentication; student ownership checks for all
  personal data.
- Tests: API tests for registration capability, verification/activation,
  password boundaries, weak-password blocking, login throttling,
  auth/session version and timeout boundaries, ownership, favorite/subscription
  idempotency, reminder generation/cancellation, dispatch idempotency, and
  calendar/message shape; frontend lint/build; Playwright calendar and message
  paths across desktop/mobile; manual exploratory acceptance.
- Reports: Module report references M1 and M4; update course reports only when
  preparing deliverables.
- MkDocs navigation: This PRD is listed under Feature PRDs.

## Validation Plan

- Automated: `just api-test` for API behavior and reminder services;
  `just api-lint`; `just web-lint` and `just web-build` for frontend surfaces
  touched; the project Playwright suite for desktop/mobile calendar and message
  paths; `just docs-build` when docs change.
- Manual: Run release-sprint acceptance steps from student login/profile through
  search, favorite, subscribe, calendar, and reminder/message evidence. Record
  branch or commit, seed data, passed steps, failed steps, and linked defects.

## Risks

- Risk: Full authentication can consume more time than the Day 1 half-day
  allows; Day 1 uses a verified active seed account, while the optional email
  registration path remains independently testable and production-gated.
- Risk: Reminder behavior depends on durable time-node data from the publication
  PRD; implementation sequencing should not start reminder UI before the 赛事
  detail contract is stable.
