# Day 1 Demo Acceptance Runbook

This runbook is the working Day 1 validation artifact for issue #25. It keeps
the team aligned on the smallest acceptance path, canonical example seed data,
and evidence format needed for the release-sprint demo.

This is a demo runbook, not the project-wide testing model. The durable testing
model stays in [Testing Model](../testing.md). This runbook also does not
implement seed scripts, replace issue acceptance criteria, or expand course
reports.

## Status

- Roadmap phase: P1 core business workflow, with P2 thin recommendation and
  governance checks after the P1 contracts are stable.
- Owner: member f.
- Source issue: #25, `test(project): add Day 1 demo acceptance and seed plan`.
- Related implementation issues: #22, #23, #24, #26, and #27.
- Related PRs at the time this runbook was written: #28 for #23, #29 for #22.
- Source PRDs:
  - [Competition Publication And Discovery](../prds/features/competition-publication-discovery.md)
  - [Student Following And Reminders](../prds/features/student-following-reminders.md)
  - [Rule Recommendation And Governance Thin Slice](../prds/features/rule-recommendation-governance-thin.md)

## How To Use This Runbook

Use the checklist as a shared demo script and evidence map. Each implementation
PR should name the checklist steps it validates, the seed data it uses, and any
skipped steps with a blocker or linked follow-up.

The first Day 1 target is a reliable admin-to-student P1 path:

1. Student identity and profile are available.
2. Admin creates, reviews, and publishes a source-backed 赛事.
3. Student finds the published 赛事 in public list and detail.
4. Student can 收藏 or 订阅 the 赛事 once the follow-up slice starts.

The P2 recommendation and governance steps are included so the team can shape
seed data early. They should not block #22, #23, or #24.

## Current Executable Meaning

The isolated browser harness now runs `seed-e2e --reset` through
`just web-e2e`. For the actors and records it provisions, that command is the
canonical executable fixture. The broader symbolic catalog below remains the
acceptance contract for records not yet materialized by that focused E2E seed:

- API tests may build the remaining logical records as fixtures.
- Manual setup may create equivalent records through API calls or admin tools.
- PR evidence should name which example records were used or where it deviated.

Any future expansion of `seed-e2e --reset` should preserve these logical facts
or document why the executable fixture intentionally differs.

## Acceptance Checklist

| ID | Step | Minimum evidence | Seed data needed | Source |
|---|---|---|---|---|
| D1-01 | Student logs in with a verified active provisioned account and current-user returns identity, role, and an empty capability list; administrator sessions return their controlled capabilities. Registration never creates a session before verification when that capability is configured. | API response or UI screenshot showing the standard response envelope, role, and capability discovery, plus API tests for registration capability, password boundaries, weak-password blocking, login throttling, disabled-account revocation, and role-specific session deadlines. | `student.day1@example.edu`; `admin.day1@example.edu`. | Student Following And Reminders |
| D1-02 | Student profile can be fetched and updated with dictionary-backed college, major, grade, interests, and reminder settings; readiness and missing fields are derived without blocking follow-up actions. | API response or UI screenshot showing saved fields and `recommendation_ready`, plus an incomplete-profile fallback check. | `profile.student-day1`. | Student Following And Reminders |
| D1-03 | Editor admin uses searchable series/edition workbench reads to create an unpublished赛事届次 and its single active draft revision from a可信来源, then edits structured stages and paired nodes. | UI and API evidence shows series/edition selection, workspace and revision reads, `unpublished` lifecycle, `draft` revision status, source facts, completeness feedback, stage/node controls, and saved revision data. | `admin.day1@example.edu`; `competition.ai-challenge-published`; `revision.ai-challenge-v1`. | Competition Publication And Discovery |
| D1-04 | Admin cannot submit a draft revision with missing publication fields or no valid recognized primary core node for review. | Failed request with validation error, unchanged `draft` revision, and unchanged `unpublished` edition. | `competition.incomplete-draft`; `revision.incomplete-v1`. | Competition Publication And Discovery |
| D1-05 | Editor submits a complete revision, a distinct reviewer finds it in the pending queue, inspects base/current-public diff and impact, and approves it; the locked赛事届次 atomically selects it as public. | Playwright cross-role evidence plus single-active-revision conflict, base pointer, stale-approval denial, server-owned node revision, published pointer, self-review denial, and review/audit evidence. | `competition.ai-challenge-published`; `review.ai-challenge-approved`. | Competition Publication And Discovery |
| D1-06 | Editions with only draft, pending, or rejected revisions and editions whose lifecycle is offline are inaccessible publicly; cancelled, expired, and archived editions are absent from default discovery but retain current approved detail with a status warning. Archive/expiry rejects any future-node edition and, after all nodes elapse, retains history without creating a message. | Public API or UI checks distinguish revision status from edition lifecycle and inaccessible records from historical-viewable detail; status API evidence covers the future-node conflict and no-message historical transition. | `competition.incomplete-draft`, `competition.ai-challenge-pending`, `competition.robotics-rejected`, `competition.math-offline`, and `competition.cancelled-history`; a test-created elapsed-node edition may be used for archive/expiry transition evidence. | Competition Publication And Discovery |
| D1-07 | Student searches, filters, and sorts public 赛事 by actionability or explicit order, opens detail, then follows a direct external channel without tracking becoming a navigation dependency. | List/detail evidence shows stable pagination, registration status, deterministic sorting, stage-grouped nodes and source facts; external target opens when tracking succeeds or fails, while accepted events contain only controlled privacy-minimized dimensions. | `competition.ai-challenge-published`; `outbound-click.ai-official`. | Competition Publication And Discovery |
| D1-08 | Logged-in student 收藏s a published or historical-viewable 赛事 without creating reminder obligations, and can remove owned engagement after its target becomes offline. | List/detail shows `is_favorited`; lifecycle matrix API evidence covers allowed historical favorite, denied new/updated subscription, and owner DELETE independent of public detail; no reminder is created by 收藏 alone. | `favorite.student-ai-challenge`; `competition.cancelled-history`; `competition.math-offline`. | Student Following And Reminders |
| D1-09 | Logged-in student explicitly confirms one subscription reminder configuration; the edition remains followed in month/week/list calendar views whether reminders are enabled or disabled. | Confirmation evidence shows enabled state, one 0–30 day offset and controlled nodes; Playwright covers desktop/month, mobile/list, view switching, paired/same-day nodes, and favorite-versus-subscription calendar behavior. | `subscription.student-ai-challenge`; `reminder.ai-registration`. | Student Following And Reminders |
| D1-10 | Reminder dispatch and competition-side schedule-semantic changes create idempotent durable messages; presentation-only revisions refresh pending content without a reschedule message. Calendar views refresh the current revision while the global badge and message center preserve unread/history state. | Calendar/reminder state before and after cancellation, offline, occurrence/selected-node changes, and description/prominence-only changes; Playwright proves consolidated-message idempotency, current-node refresh and unavailable targets; read and retention actions have API boundary evidence. | `subscription.student-ai-challenge`; `reminder.ai-registration`; `message.ai-registration-due`; `message.ai-time-changed`. | Student Following And Reminders |
| D1-11 | Recommendation returns published 赛事 with traceable 推荐理由, immutable active rule-set version, and no public score; rendered items and detail navigation produce privacy-minimized idempotent exposure/click evidence. | API/UI shows rule version and reasons or explicit fallback; tracking failure does not block rendering/navigation, and forged or repeated events cannot alter server dimensions or duplicate counts. | `rule-set.p2-v1`; `recommendation.student-ai-challenge`; `recommendation.fallback-innovation`; `recommendation-request.day1`. | Rule Recommendation And Governance Thin Slice |
| D1-12 | Admin uses the required Review, Audit, and Statistics tabs to inspect independent publication and recommendation-rule decisions, key operation events, and bounded operational counts; the user owner proves bounded account-governance authority. | Playwright and API evidence covers stable filters/pagination, immutable review diff/impact/comment, allowlisted audit detail, current and 7/30-day metrics with definitions/`as_of`/best-effort caveats, non-additive reason attribution, no user drill-down, student `403`, user-owner self-target denial, and last-active-owner protection. | `owner.day1@example.edu`; `review.ai-challenge-approved`; `audit.publish-ai-challenge`; `audit.user-capability-change`; `rule-set.p2-v1`; `review.rule-set-p2-v1`; `outbound-click-daily.ai-official`; `recommendation-daily-total.day1`; `recommendation-reason-daily.day1`. | Competition Publication And Discovery; Rule Recommendation And Governance Thin Slice |

## Example Day 1 Seed

Use these symbolic IDs in PR evidence even if the test database uses generated
numeric primary keys.

### Actors

| Symbolic ID | Role | Required fields | Purpose |
|---|---|---|---|
| `student.day1@example.edu` | `student` | Provisioned `active` account with a verified typed email identity; display name `Day 1 Student`; policy-compliant test passphrase or test login path. Seed provisioning must not imply that public registration bypasses verification. | Login, profile, public engagement, recommendation, calendar, and message checks. |
| `admin.day1@example.edu` | `admin` | Display name `Day 1 Admin`; `competition_editor`, `recommendation_editor`, `recommendation_reviewer`; policy-compliant test passphrase or test login path. | Creates and submits赛事 revisions and recommendation rule-set candidates; the dual recommendation capabilities prove that same-account rule-set review is rejected by submitter identity rather than a missing capability. |
| `reviewer.day1@example.edu` | `admin` | Display name `Day 1 Reviewer`; `competition_reviewer`, `competition_maintainer`, `recommendation_reviewer`; policy-compliant test passphrase or test login path; distinct from each submitted target's author. | Reviews赛事/rule-set candidates, maintains published赛事 status, and inspects governance evidence. |
| `owner.day1@example.edu` | `admin` | Display name `Day 1 Owner`; `user_administrator` only; active and distinct from governed targets. | Lists governed accounts, changes another account's controlled capabilities, and proves self-target and last-active-owner protection without participating in content review. |

### Student Profile

```json
{
  "id": "profile.student-day1",
  "user": "student.day1@example.edu",
  "college": "计算机学院",
  "major": "软件工程",
  "grade": "大二",
  "interest_tags": ["人工智能", "创新创业", "程序设计"],
  "competition_experience": "参加过校级程序设计竞赛",
  "goal_preferences": ["能力提升", "保研"],
  "blocked_tags": ["数学建模"]
}
```

### Reminder Settings

```json
{
  "id": "reminder-settings.student-day1",
  "user": "student.day1@example.edu",
  "enabled": true,
  "default_remind_days": 3,
  "node_types": [
    "registration_deadline",
    "submission_deadline",
    "competition_start"
  ]
}
```

These are displayed defaults only. The subscription record below still owns the
student's explicit reminder consent and selected calendar node types.

### Competition Series

| Symbolic ID | Canonical name | Purpose |
|---|---|---|
| `series.ai-challenge` | 全国大学生人工智能创新挑战赛 | Groups the 2026 published edition and 2027 pending edition without overwriting either. |
| `series.incomplete` | 材料不完整的赛事 | Submission-gate failure fixture. |
| `series.robotics` | 机器人挑战赛 | Rejected-review fixture. |
| `series.math` | 数学建模竞赛 | Emergency-offline fixture. |
| `series.cancelled` | 已取消赛事 | Historical-detail fixture. |
| `series.innovation` | 大学生创新创业训练计划 | General recommendation fallback fixture. |

### Competition Editions

Dates are intentionally future-dated for the Day 1 run on July 9, 2026. If the
demo runs after these dates, shift them forward while preserving relative order.

The table records the realized state after each scenario. The cross-role D1-03
through D1-05 path starts `competition.ai-challenge-published` as `unpublished`
with `revision.ai-challenge-v1` as `draft`, then performs submission and approval
to reach the shown `published`/`approved` state. Downstream isolated scenarios
may load that realized state directly; they must not create a duplicate edition.

| Symbolic ID | Series | Edition label | `lifecycle_status` | `published_revision_id` | Purpose |
|---|---|---|---|---|---|
| `competition.ai-challenge-published` | `series.ai-challenge` | `2026` | `published` | `revision.ai-challenge-v1` | Main publication, discovery, follow-up, and recommendation path. |
| `competition.incomplete-draft` | `series.incomplete` | `2026` | `unpublished` | `null` | Submission validation failure. |
| `competition.ai-challenge-pending` | `series.ai-challenge` | `2027` | `unpublished` | `null` | New-edition pending-review and public-exclusion fixture. |
| `competition.robotics-rejected` | `series.robotics` | `2026` | `unpublished` | `null` | Rejected review and governance evidence. |
| `competition.math-offline` | `series.math` | `2026` | `offline` | `revision.math-v1` | Previously approved but immediately unavailable publicly. |
| `competition.cancelled-history` | `series.cancelled` | `2026` | `cancelled` | `revision.cancelled-v1` | Previously published historical warning detail. |
| `competition.innovation-fallback` | `series.innovation` | `2026` | `published` | `revision.innovation-v1` | General recommendation fallback. |

### Competition Revisions

Every non-draft fixture below that reached review contains the required source,
category, organizer, summary, eligibility, participant form, explicit major and
grade scopes, stage, and primary core node facts. Stage and node identities are
listed separately so the seed can be created without inferring nested state.
All listed fixtures are initial revisions with `base_revision_id = null`.
Replacement, single-active-revision, and stale-baseline tests create their
candidate and current-public facts explicitly from these seeds.

| Symbolic ID | Edition | `revision_status` | Required content facts | Purpose |
|---|---|---|---|---|
| `revision.ai-challenge-v1` | `competition.ai-challenge-published` | `approved` | Title `全国大学生人工智能创新挑战赛`; category `创新创业`; organizer `示例高校创新中心`; source name `示例高校竞赛通知`; source URL `https://example.edu/notices/ai-challenge-2026`; official URL `https://example.org/ai-challenge`; summary and eligibility; team form with `1-5` members; selected major/grade scopes with majors `["软件工程", "计算机科学与技术"]` and grades `["大二", "大三"]`; value notes `校级推荐，适合有项目实践基础的学生`. | Current public snapshot. |
| `revision.incomplete-v1` | `competition.incomplete-draft` | `draft` | Title and source facts only; deliberately missing summary, eligibility, explicit scopes, stage, and core node. | Publication-gate rejection. |
| `revision.ai-challenge-2027-v1` | `competition.ai-challenge-pending` | `pending_review` | Complete source-backed individual-entry content with explicit scopes and the pending registration stage/node below. | Immutable submitted candidate that remains non-public. |
| `revision.robotics-v1` | `competition.robotics-rejected` | `rejected` | Complete source-backed team-entry content with explicit scopes and registration stage/node; review comment identifies unconfirmed official facts. | Immutable rejected candidate. |
| `revision.math-v1` | `competition.math-offline` | `approved` | Complete source-backed individual-entry content with explicit scopes and registration stage/node. | Retained approved snapshot while lifecycle is offline. |
| `revision.cancelled-v1` | `competition.cancelled-history` | `approved` | Complete source-backed individual-entry content with explicit scopes and registration stage/node. | Retained approved snapshot while lifecycle is cancelled. |
| `revision.innovation-v1` | `competition.innovation-fallback` | `approved` | Category `创新创业`; complete source, organizer, summary, eligibility, individual form, explicit all-major/all-grade scopes, registration stage/node, and general value notes. | Current public fallback snapshot. |

### Competition Stages

| Symbolic ID | Revision | Stage type | Label | Order |
|---|---|---|---|---|
| `stage.ai-registration` | `revision.ai-challenge-v1` | `registration` | 报名 | 1 |
| `stage.ai-submission` | `revision.ai-challenge-v1` | `submission` | 作品提交 | 2 |
| `stage.ai-competition` | `revision.ai-challenge-v1` | `competition` | 正式比赛 | 3 |
| `stage.ai-2027-registration` | `revision.ai-challenge-2027-v1` | `registration` | 报名 | 1 |
| `stage.robotics-registration` | `revision.robotics-v1` | `registration` | 报名 | 1 |
| `stage.math-registration` | `revision.math-v1` | `registration` | 报名 | 1 |
| `stage.cancelled-registration` | `revision.cancelled-v1` | `registration` | 报名 | 1 |
| `stage.innovation-registration` | `revision.innovation-v1` | `registration` | 报名 | 1 |

### Time Nodes

Each row is an immutable snapshot. The logical key is stable only within its
edition and would be reused by a corrected successor snapshot with an
incremented node revision.

| Snapshot symbolic ID | Logical node key | Revision / stage | Node revision | Node type | Occurs at | Prominence | Purpose |
|---|---|---|---|---|---|---|---|
| `node-snapshot.ai-registration-v1` | `registration-deadline` | `revision.ai-challenge-v1` / `stage.ai-registration` | `1` | `registration_deadline` | E2E reset clock + 27 days (UTC) | `primary` | Public next node, calendar, and reminder creation; the relative clock keeps the executable fixture future-safe. |
| `node-snapshot.ai-submission-v1` | `submission-main-deadline` | `revision.ai-challenge-v1` / `stage.ai-submission` | `1` | `submission_deadline` | `2026-09-10T16:00:00Z` | `primary` | Subscription reminder generation. |
| `node-snapshot.ai-competition-v1` | `competition-main-start` | `revision.ai-challenge-v1` / `stage.ai-competition` | `1` | `competition_start` | `2026-10-01T01:00:00Z` | `primary` | Calendar ordering. |
| `node-snapshot.ai-2027-registration-v1` | `registration-main-deadline` | `revision.ai-challenge-2027-v1` / `stage.ai-2027-registration` | `1` | `registration_deadline` | `2027-08-15T16:00:00Z` | `primary` | Same key is valid because this is a different edition; complete pending candidate. |
| `node-snapshot.robotics-registration-v1` | `registration-main-deadline` | `revision.robotics-v1` / `stage.robotics-registration` | `1` | `registration_deadline` | `2026-08-20T16:00:00Z` | `primary` | Complete rejected candidate. |
| `node-snapshot.math-registration-v1` | `registration-main-deadline` | `revision.math-v1` / `stage.math-registration` | `1` | `registration_deadline` | `2026-08-25T16:00:00Z` | `primary` | Retained offline snapshot. |
| `node-snapshot.cancelled-registration-v1` | `registration-main-deadline` | `revision.cancelled-v1` / `stage.cancelled-registration` | `1` | `registration_deadline` | `2026-08-28T16:00:00Z` | `primary` | Retained cancelled snapshot. |
| `node-snapshot.innovation-registration-v1` | `registration-main-deadline` | `revision.innovation-v1` / `stage.innovation-registration` | `1` | `registration_deadline` | `2026-08-30T16:00:00Z` | `primary` | General recommendation fallback. |

### Controlled Tags And Revision Links

| Symbolic ID | Value | Purpose |
|---|---|---|
| `tag.ai` | `人工智能` | Profile and 赛事 tag match. |
| `tag.innovation` | `创新创业` | Category and fallback recommendation. |
| `tag.programming` | `程序设计` | Student interest overlap. |
| `tag.school-recommended` | `校级推荐` | Source-backed reference tag. |

| Symbolic link | Revision | Tag |
|---|---|---|
| `tag-link.ai-ai` | `revision.ai-challenge-v1` | `tag.ai` |
| `tag-link.ai-innovation` | `revision.ai-challenge-v1` | `tag.innovation` |
| `tag-link.ai-recommended` | `revision.ai-challenge-v1` | `tag.school-recommended` |
| `tag-link.innovation-general` | `revision.innovation-v1` | `tag.innovation` |

Candidate revisions own separate tag links; creating or editing them cannot
change tags returned from the current `published_revision_id`.

### Recommendation Rules

| Symbolic ID | Value | Purpose |
|---|---|---|
| `rule.major-match` | Reason template `与你的专业匹配` | Traceable profile-aware recommendation. |
| `rule.grade-match` | Reason template `适合当前年级` | Traceable grade-aware recommendation. |
| `rule.upcoming-deadline` | Reason template `报名截止较近` | Deadline-aware recommendation. |

### Engagement And Reminder Records

| Symbolic ID | Required state | Purpose |
|---|---|---|
| `favorite.student-ai-challenge` | User `student.day1@example.edu`; competition `competition.ai-challenge-published`; active true. | D1-08 收藏 evidence. |
| `subscription.student-ai-challenge` | User `student.day1@example.edu`; competition `competition.ai-challenge-published`; historical cancelled relation after an explicitly confirmed 30-day reminder; current UI remains unsubscribed until D1-09 creates fresh consent. | D1-09 re-subscription and D1-10 historical lineage evidence. |
| `reminder.ai-registration` | Sent reminder with FK to `node-snapshot.ai-registration-v1`, copied logical key `registration-deadline`, node revision 1, trigger at reset clock - 3 days, attempt count 1, and `sent_at` equal to the linked message creation time one minute later. | Exact scheduling basis and immutable dispatch lineage. |
| `message.ai-registration-due` | Unread `reminder_due` message linked to the sent reminder, with immutable competition/node snapshots and a 365-day retention deadline. | Idempotent dispatch, unread badge, and message-center evidence. |
| `message.ai-time-changed` | Read consolidated `competition_time_changed` message keyed by student and approved revision event; immutable summary of affected occurrence/selected-node semantic changes. | Historical read state, presentation-only no-message boundary, type filtering, and repeated-event idempotency. |

### Analytics Records

| Symbolic ID | Required state | Purpose |
|---|---|---|
| `outbound-click.ai-official` | Raw best-effort click for the AI challenge current public revision; target `official_url`; source `competition_detail`; actor kind only; no user, account, IP, User-Agent, or visitor identifier. | D1-07 direct-navigation, privacy-field, and 90-day raw-retention evidence. |
| `outbound-click-daily.ai-official` | Idempotent `Asia/Shanghai` daily aggregate for the same edition, target type, source surface, and actor kind. | D1-12 recorded-click count and no-user-drill-down evidence. |

### Governance Records

| Symbolic ID | Required state | Purpose |
|---|---|---|
| `review.ai-challenge-approved` | Target `revision.ai-challenge-v1`; submitter `admin.day1@example.edu`; status `approved`; reviewer `reviewer.day1@example.edu`; comment `信息完整，来源可信`; retained diff/impact snapshot. | D1-05 and D1-12 immutable review evidence. |
| `review.robotics-rejected` | Target `revision.robotics-v1`; status `rejected`; comment names missing official confirmation. | D1-06 and governance evidence. |
| `audit.publish-ai-challenge` | Actor admin or reviewer; actions create revision/submit/approve/select public revision; target edition and exact revision; result success; only action-allowlisted detail. | Required D1-12 audit evidence and sensitive-field exclusion. |
| `audit.user-capability-change` | Actor `owner.day1@example.edu`; target another admin id; reason and allowlisted old/new role, status, and capability codes; no full account identifier or session value. | D1-12 user-governance authority, session invalidation, and audit-boundary evidence. |

### Expected Recommendation Reasons

For `student.day1@example.edu`, `competition.ai-challenge-published` should be
eligible for reasons such as:

- `与你的专业匹配`
- `符合你的兴趣标签`
- `适合当前年级`
- `报名截止较近`

Recommendation output must expose reasons and ordering, not a public numeric
score or 赛事 value rating.

### Recommendation Rule Set

| Symbolic ID | Required state | Purpose |
|---|---|---|
| `rule-set.p2-v1` | Immutable version 1; active; controlled major/grade/interest/deadline/fallback rules; seeded reproducibly; activated by a reviewer distinct from its submitter. | D1-11 personalized version/reason traceability and D1-12 governance evidence. |
| `review.rule-set-p2-v1` | Approved recommendation rule-set review with submitter, distinct reviewer, synthetic-preview summary, differences, reason, and activation time. | Self-review denial, atomic activation, and audit evidence. |
| `recommendation-request.day1` | Opaque request with returned AI challenge item, server-owned position/mode/rule version/reason codes, one impressed timestamp and one clicked timestamp; no user/profile/device identifiers. | D1-11 render/click idempotency, anti-forgery, privacy, and non-blocking behavior. |
| `recommendation-daily-total.day1` | Item-level aggregates by event-time Shanghai date and rule version/mode/position/actor kind/赛事; impression uses `impressed_at`, click uses `clicked_at`, and each event contributes once despite multiple reasons. | D1-12 overall best-effort event-period interaction ratio without double counting. |
| `recommendation-reason-daily.day1` | Separate event-time Shanghai-date attribution rows for each distinct displayed reason code on the request item. | D1-12 reason attribution evidence; rows are explicitly non-additive and non-causal. |

## Required Acceptance Addendum For Day 1 Work

This addendum is a Day 1 merge/readiness gate. It asks each PR or not-yet-started
issue to connect its own validation evidence to this runbook; it does not ask
members to re-run unrelated downstream work.

### Existing PRs

| PR | Issue | Required checklist steps | Work help |
|---|---|---|---|
| #29 | #22 | D1-01 and D1-02. | Add a short PR body update or comment naming the student/profile seed used, commands run, and downstream steps skipped because #24/#26/#27 are not ready. |
| #28 | #23 | D1-03 through D1-06, plus D1-12 if review/audit evidence is implemented. | Add a short PR body update or comment naming the published and non-public competition seed, commands run, and downstream steps skipped because #24/#26/#27 are not ready. |

### Issues Without PRs

| Issue | Required checklist steps | Seed dependencies | Work help |
|---|---|---|---|
| #24 public list/detail | D1-06 and D1-07. | Published and non-public competition records from #23. | Start implementation from the public visibility contract, then record list/detail evidence and skipped personal-state checks if #22 or #26 is not ready. |
| #26 subscription/reminder/calendar | D1-08, D1-09, and D1-10. | Student/profile and separate reminder-settings seed from #22 plus published edition/revision/stage/node seed from #23/#24. | Start from the logged-in student and current public revision, then record complete favorite/subscription/reminder/message/calendar evidence; a skipped worker or list-only calendar does not satisfy accepted P1. |
| #27 recommendation/governance | D1-11 and D1-12. | Student profile seed from #22, published/non-public competition seed from #23/#24, and governance evidence from #23. | Deliver traceable recommendation reasons and no-score output, then record Review, Audit, and Statistics evidence; all three governance surfaces are required for P2 thin. |

### Post-Push Comment Rule

Comments to PRs or issues should be sent only after this runbook is merged or
otherwise available from the pushed branch. The comment must include:

- The relevant checklist steps.
- The seed records the member should use.
- A short update note that tells the member how to get the pushed runbook before
  continuing:
  - If the runbook has been merged to `main`, run `git fetch origin` and
    `git pull --rebase origin main`.
  - If the runbook is still on a documentation PR branch, fetch that branch or
    open the pushed PR and use `docs/demo/day1-acceptance.md` from there.
- A short work help note that tells the member how to update their PR or start
  their issue.
- A reminder to record skipped steps with reasons instead of marking downstream
  work complete.

## Evidence Format

Use this format in PR summaries and standup updates when recording manual
acceptance:

```text
Validation evidence:
- Date/time:
- Branch or commit:
- Environment:
- Seed data source:
- Seed data size:
- Checklist steps run:
- Commands run:
- Manual results:
- Skipped steps and reason:
- Defects or follow-up issues:
```

For a standup row or short update, use the compact version:

```text
Issue:
Validated:
Seed:
Skipped/blocker:
Next:
```

## PRD Mapping

| PRD | Checklist coverage | Dependent issues |
|---|---|---|
| Competition Publication And Discovery | D1-03 through D1-07, plus governance evidence in D1-12. | #23, #24 |
| Student Following And Reminders | D1-01, D1-02, and D1-08 through D1-10. | #22, #26 |
| Rule Recommendation And Governance Thin Slice | D1-11 and the statistics/governance part of D1-12. | #27 |

## Skip Rules

If an upstream contract is not ready, mark the downstream step as skipped
instead of forcing a mock-only demo:

- If #22 is not ready, skip personal profile, 收藏, 订阅, calendar, and
  profile-aware recommendation evidence.
- If #23 is not ready, skip final public visibility claims and use only
  contract-prep evidence for #24, #26, and #27.
- If #24 is not ready, skip frontend public discovery evidence and record API
  contract evidence separately.
- If #26 or #27 has not started, keep D1-08 through D1-12 as seed and evidence
  preparation rather than implementation completion.

Skipped steps need a concrete reason and next action. They should not be marked
passed until the relevant implementation issue provides evidence.
