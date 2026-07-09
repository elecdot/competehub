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

The repository does not yet have a Day 1 seed CLI. Until one exists, the
canonical example seed below is the executable contract:

- API tests may build these logical records as fixtures.
- Manual setup may create equivalent records through API calls, admin tools, or
  direct local setup.
- PR evidence should name which example records were used or where it deviated.

Future seed CLI work should generate the same logical fixture set or document
why it differs.

## Acceptance Checklist

| ID | Step | Minimum evidence | Seed data needed | Source |
|---|---|---|---|---|
| D1-01 | Student registers or logs in and current-user returns identity and role. | API response or UI screenshot showing the standard response envelope and student role. | `student.day1@example.edu`. | Student Following And Reminders |
| D1-02 | Student profile can be fetched and updated with college, major, grade, interests, and reminder settings. | API response or UI screenshot showing saved profile fields. | `profile.student-day1`. | Student Following And Reminders |
| D1-03 | Admin creates a draft 赛事 from a 可信来源. | API response, database row, or admin surface showing draft status, source name, and source URL. | `admin.day1@example.edu`; `competition.ai-challenge-draft`. | Competition Publication And Discovery |
| D1-04 | Admin cannot submit an incomplete draft for review. | Failed request with validation error and unchanged non-public state. | `competition.incomplete-draft`. | Competition Publication And Discovery |
| D1-05 | Admin submits a complete draft, reviewer approves it, and the 赛事 becomes `published`. | State transition evidence plus review or audit record. | `competition.ai-challenge-published`; `review.ai-challenge-approved`. | Competition Publication And Discovery |
| D1-06 | Rejected, returned, draft, pending, offline, or cancelled 赛事 are hidden from default public list and detail. | Public API or UI check showing non-public records are absent or inaccessible. | `competition.incomplete-draft`, `competition.ai-challenge-pending`, `competition.robotics-rejected`, and `competition.math-offline`. | Competition Publication And Discovery |
| D1-07 | Student searches or filters public 赛事 and opens detail. | List response or UI shows pagination/envelope; detail shows source facts, time nodes, tags, value notes, and official link. | `competition.ai-challenge-published`. | Competition Publication And Discovery |
| D1-08 | Logged-in student 收藏s a published 赛事 without creating reminder obligations. | List/detail shows `is_favorited`; no subscription or reminder record is created by 收藏 alone. | `favorite.student-ai-challenge`. | Student Following And Reminders |
| D1-09 | Logged-in student 订阅s a published 赛事 and future reminders/calendar nodes exist. | Subscription state plus pending reminders or calendar list entries. | `subscription.student-ai-challenge`; `reminder.ai-registration`. | Student Following And Reminders |
| D1-10 | Cancelling 订阅 cancels or removes future pending reminders, and due reminder dispatch is idempotent where implemented. | Calendar/reminder state before and after cancellation; repeated dispatch creates no duplicate message. | `subscription.student-ai-challenge`; `message.ai-registration-due` if dispatch exists. | Student Following And Reminders |
| D1-11 | Recommendation returns published 赛事 with traceable 推荐理由 and no public score. | Recommendation API or UI shows reasons tied to profile, tags, grade, major, deadline, or fallback rule; no raw score is visible. | `recommendation.student-ai-challenge`; `recommendation.fallback-innovation`. | Rule Recommendation And Governance Thin Slice |
| D1-12 | Admin governance evidence shows publication decisions and useful counts where implemented. | Review/audit records or thin stats response for published, pending, favorite, subscription, or recommendation data. | `review.ai-challenge-approved`; `audit.publish-ai-challenge`; engagement counts. | Competition Publication And Discovery; Rule Recommendation And Governance Thin Slice |

## Example Day 1 Seed

Use these symbolic IDs in PR evidence even if the test database uses generated
numeric primary keys.

### Actors

| Symbolic ID | Role | Required fields | Purpose |
|---|---|---|---|
| `student.day1@example.edu` | `student` | Display name `Day 1 Student`; password or test login path. | Login, profile, public engagement, recommendation, calendar, and message checks. |
| `admin.day1@example.edu` | `admin` | Display name `Day 1 Admin`; password or test login path. | Creates and submits 赛事 records from 可信来源. |
| `reviewer.day1@example.edu` | `admin` | Display name `Day 1 Reviewer`; password or test login path. | Approves, rejects, returns, or inspects review/governance evidence. One admin may cover both admin roles if role separation is not implemented. |

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
  "blocked_tags": ["数学建模"],
  "default_remind_days": 3,
  "message_enabled": true
}
```

### Competition Records

Dates are intentionally future-dated for the Day 1 run on July 9, 2026. If the
demo runs after these dates, shift them forward while preserving relative order.

| Symbolic ID | Status | Required facts | Purpose |
|---|---|---|---|
| `competition.ai-challenge-published` | `published` | Title `全国大学生人工智能创新挑战赛`; category `创新创业`; organizer `示例高校创新中心`; source name `示例高校竞赛通知`; source URL `https://example.edu/notices/ai-challenge-2026`; official URL `https://example.org/ai-challenge`; suitable majors `["软件工程", "计算机科学与技术"]`; suitable grades `["大二", "大三"]`; tags `["人工智能", "创新创业", "校级推荐"]`; value notes `校级推荐，适合有项目实践基础的学生`. | Main publication, list, detail, follow-up, and recommendation path. |
| `competition.incomplete-draft` | `draft` | Title `材料不完整的赛事草稿`; source name and source URL present; missing summary/detail; may also omit time nodes if the implementation supports time-node validation | Submission validation failure. |
| `competition.ai-challenge-pending` | `pending_review` | Same domain as the published AI challenge but not approved. | Review workflow and public visibility exclusion. |
| `competition.robotics-rejected` | `rejected` | Title `机器人挑战赛退回样例`; source facts present; review comment explains missing official confirmation. | Public visibility exclusion and governance evidence. |
| `competition.math-offline` | `offline` or `cancelled` | Title `数学建模下架样例`; source facts present; no default public visibility. | Public list/detail exclusion and reminder cancellation checks when implemented. |
| `competition.innovation-fallback` | `published` | Title `大学生创新创业训练计划`; category `创新创业`; source facts and future deadline. | Anonymous or profile-incomplete recommendation fallback. |

### Time Nodes

| Competition | Node type | Due date | Purpose |
|---|---|---|---|
| `competition.ai-challenge-published` | `registration_deadline` | `2026-08-15T16:00:00Z` | Public next node, calendar, and reminder creation. |
| `competition.ai-challenge-published` | `submission_deadline` | `2026-09-10T16:00:00Z` | Subscription reminder generation. |
| `competition.ai-challenge-published` | `competition_start` | `2026-10-01T01:00:00Z` | Calendar ordering. |
| `competition.innovation-fallback` | `registration_deadline` | `2026-08-30T16:00:00Z` | General recommendation fallback. |

### Tags And Rules

| Symbolic ID | Value | Purpose |
|---|---|---|
| `tag.ai` | `人工智能` | Profile and 赛事 tag match. |
| `tag.innovation` | `创新创业` | Category and fallback recommendation. |
| `tag.programming` | `程序设计` | Student interest overlap. |
| `rule.major-match` | Reason template `与你的专业匹配` | Traceable profile-aware recommendation. |
| `rule.grade-match` | Reason template `适合当前年级` | Traceable grade-aware recommendation. |
| `rule.upcoming-deadline` | Reason template `报名截止较近` | Deadline-aware recommendation. |

### Engagement And Reminder Records

| Symbolic ID | Required state | Purpose |
|---|---|---|
| `favorite.student-ai-challenge` | User `student.day1@example.edu`; competition `competition.ai-challenge-published`; active true. | D1-08 收藏 evidence. |
| `subscription.student-ai-challenge` | User `student.day1@example.edu`; competition `competition.ai-challenge-published`; active; reminder enabled; remind days 3; node types registration/submission/start. | D1-09 and D1-10 subscription evidence. |
| `reminder.ai-registration` | Pending reminder for registration deadline. | Calendar/reminder generation. |
| `message.ai-registration-due` | Sent or unread message linked to due reminder, only if dispatch exists. | Idempotent dispatch and message evidence. |

### Governance Records

| Symbolic ID | Required state | Purpose |
|---|---|---|
| `review.ai-challenge-approved` | Target `competition.ai-challenge-published`; status `approved`; reviewer `reviewer.day1@example.edu`; comment `信息完整，来源可信`. | D1-05 and D1-12 review evidence. |
| `review.robotics-rejected` | Target `competition.robotics-rejected`; status `rejected`; comment names missing official confirmation. | D1-06 and governance evidence. |
| `audit.publish-ai-challenge` | Actor admin or reviewer; action create/submit/approve/publish; result success. | D1-12 audit evidence when audit logs exist. |

### Expected Recommendation Reasons

For `student.day1@example.edu`, `competition.ai-challenge-published` should be
eligible for reasons such as:

- `与你的专业匹配`
- `符合你的兴趣标签`
- `适合当前年级`
- `报名截止较近`

Recommendation output must expose reasons and ordering, not a public numeric
score or 赛事 value rating.

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
| #26 subscription/reminder/calendar | D1-08, D1-09, and D1-10. | Student/profile seed from #22 plus published competition seed from #23/#24. | Start from the logged-in student and published 赛事, then record favorite/subscription/reminder/calendar evidence and skipped dispatch evidence if the worker is not implemented. |
| #27 recommendation/governance | D1-11 and D1-12. | Student profile seed from #22, published/non-public competition seed from #23/#24, and governance evidence from #23. | Start from traceable recommendation reasons and no-score output, then record governance/stat evidence only for surfaces implemented in the slice. |

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
