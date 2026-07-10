# CompeteHub API Spec

## Purpose

This document defines the initial REST API contract for CompeteHub. It is intended for frontend/backend coordination and test planning.

Implementation details may evolve, but endpoint semantics, response envelopes, auth boundaries, and error shapes should stay consistent unless an ADR or task-level API change updates this document.

## Base URL

All application APIs use:

```text
/api/v1
```

Local development:

```text
http://localhost:5000/api/v1
```

## Response Envelope

Successful response:

```json
{
  "data": {},
  "error": null
}
```

Error response:

```json
{
  "data": null,
  "error": {
    "code": "validation_error",
    "message": "请求参数不合法",
    "details": {}
  }
}
```

List response:

```json
{
  "data": {
    "items": [],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 0
    }
  },
  "error": null
}
```

## Date And Time

Datetime values are timezone-aware ISO 8601 instants. API responses normalize
them to UTC. Administrator datetime input with an explicit offset is converted
to UTC; offsetless administrator datetime input is interpreted in the
`Asia/Shanghai` product calendar time zone.

Date-only query parameters represent `Asia/Shanghai` calendar dates, not UTC or
browser-local calendar dates. Backend queries convert their local-midnight
boundaries to UTC before comparing stored instants. See
`docs/adr/0012-utc-instants-shanghai-calendar.md`.

## Common Errors

| HTTP Status | Code | Meaning |
|---|---|---|
| 400 | `validation_error` | Request parameters or body are invalid. |
| 401 | `unauthorized` | Login is required. |
| 403 | `forbidden` | Current user does not have permission. |
| 404 | `not_found` | Resource does not exist or is not visible. |
| 409 | `conflict` | Request conflicts with current resource state. |
| 429 | `rate_limited` | Too many attempts; retry after the indicated delay. |
| 500 | `internal_server_error` | Unexpected server error. |
| 503 | `registration_unavailable` | Public registration is disabled because no production verification sender is configured. |

## Authentication

The API uses Flask Cookie Session authentication. Frontend code must not store
long-lived tokens in `localStorage`; authenticated requests rely on the browser
session cookie. State-changing APIs must use POST, PATCH, or DELETE rather than
GET.

Each signed session contains only `user_id`, the account `session_version`,
`issued_at`, and `last_activity_at`. Login clears any prior session before
issuing these values. Every protected request reloads the account and accepts
the session only when the account is `active`, the version matches, and neither
timeout has elapsed. Invalid sessions are cleared and return the generic
`unauthorized` response before route behavior executes.

Student sessions have a 24-hour idle timeout and a seven-day absolute timeout.
Administrator sessions have a 30-minute idle timeout and an eight-hour absolute
timeout. Authenticated activity refreshes only the idle timestamp and never the
absolute deadline. P1 allows concurrent sessions and has no user-selectable
remember-me mode. Logout clears only the current browser; disabling an account,
confirming credential compromise, or explicitly terminating all sessions
increments the account version and invalidates every device on its next
request.

P1 assumes one configured部署高校 per deployment. `student_no` and `college`
are interpreted in that boundary; the API does not accept a user-selected tenant
or institution identifier.

Initial roles:

- `student`
- `admin`

Administrator capabilities include `competition_editor` and
`competition_reviewer`. They do not create new formal product roles. One account
may hold both capabilities, but it cannot review a competition revision it
submitted.

Future candidate roles, not current formal product roles:

- `teacher`
- `organizer`

### Password Policy

P1 passwords are a single authentication factor and therefore contain 15 to
128 Unicode code points after NFC normalization. Spaces, paste, browser
autofill, and password managers are supported. The API does not require a mix
of upper case, lower case, numbers, or symbols and never trims or silently
truncates a submitted password.

New passwords are rejected when the complete normalized value matches the
local common/compromised-password blocklist or an obvious context-specific weak
value derived from CompeteHub or the account identity. This check does not call
an online breach service. Password hashes use explicit adaptive-algorithm
parameters, preferring Argon2id and allowing only a security-baseline scrypt
configuration as fallback. Passwords are changed on evidence of compromise or
an explicit security action, not on a periodic schedule.

Failed authentication is rate-limited by normalized typed-identity key and
request source. Unknown, incorrect-password, pending, and disabled account cases
return a generic authentication error; the API does not permanently lock an
account in response to remote failures.

## Pagination And Filtering

Common list query parameters:

| Parameter | Type | Meaning |
|---|---|---|
| `page` | integer | Page number, starting from 1. |
| `page_size` | integer | Items per page, from 1 to 100. |
| `sort` | string | `actionable` (default), `registration_deadline`, or `published_at`. |

Competition filters:

| Parameter | Type | Meaning |
|---|---|---|
| `keyword` | string | Search in title, short title, organizer, category, and summary. |
| `category` | string | Competition category. |
| `major` | string | Suitable major. |
| `grade` | string | Suitable grade. |
| `tag` | string | Reference or fit tag. |
| `registration_status` | string | Computed `open`, `upcoming`, `closed`, `unknown`, or `not_applicable` registration state. |
| `deadline_from` | string | Inclusive `Asia/Shanghai` date lower bound for the registration deadline. |
| `deadline_to` | string | Inclusive `Asia/Shanghai` date upper bound for the registration deadline. |
| `participant_form` | string | Match editions whose `participant_forms` contains `individual` or `team`. |

## Auth APIs

### `POST /auth/register`

Request creation of a student account. P1 accepts only `email`, and only when a
real email verification sender is configured. Supporting `phone` and
`student_no` in the identity model does not make them public registration
options. Privileged accounts and student-number identities use a controlled
administrative, institution-roster, invitation, or seed-data path.

Request:

```json
{
  "identity_type": "email",
  "identifier": "student@example.edu",
  "password": "correct horse battery staple",
  "display_name": "student a"
}
```

Response:

```json
{
  "data": {
    "accepted": true
  },
  "error": null
}
```

The successful response is `202 Accepted`, is intentionally the same whether a
pending or existing identity received a message, and does not create a session.
When public registration is disabled, the endpoint returns
`registration_unavailable`; the frontend must not show the registration entry.

### `POST /auth/verify`

Verify a pending email identity using a single-use, time-limited code. Success
atomically marks the identity verified and changes its account from
`pending_activation` to `active`; it does not create a session. The student must
then use the normal login endpoint.

Request:

```json
{
  "identity_type": "email",
  "identifier": "student@example.edu",
  "code": "123456"
}
```

### `POST /auth/verification/resend`

Request another verification message. The response is generic, rate-limited,
and does not reveal whether the identity exists, is pending, or is already
verified.

### `POST /auth/login`

Login with an explicitly typed account identity. The API never searches one
identifier across unrelated identity types. Pending, disabled, unknown, and
incorrect-password cases use a non-enumerating authentication failure and do
not create a session.

Request:

```json
{
  "identity_type": "email",
  "identifier": "student@example.edu",
  "password": "correct horse battery staple"
}
```

### `POST /auth/logout`

Logout the current browser session. It does not increment the account session
version or terminate other devices.

### `GET /me`

Return current user and role without bound email, phone, or student-number
identities.

Requires authentication.

## Profile APIs

### `GET /me/profile`

Return current student's profile plus its dynamically derived readiness state.
`profile_status` is `incomplete` or `recommendation_ready`; `missing_fields`
contains any of `college`, `major`, `grade`, or `interest_tags`. The readiness
state is not stored independently.

Response data example:

```json
{
  "college": "计算机学院",
  "major": "软件工程",
  "grade": "大二",
  "interest_tags": ["人工智能", "创新创业"],
  "competition_experience": null,
  "goal_preferences": [],
  "blocked_tags": [],
  "profile_status": "recommendation_ready",
  "missing_fields": []
}
```

Requires `student`.

### `PATCH /me/profile`

Update current student's profile.

`college`, `major`, `grade`, and `interest_tags` use deployment-controlled
dictionaries. The selected major must belong to the selected college, and
`interest_tags` contains at most 10 unique values. Partial updates are allowed
and may leave the profile `incomplete`; the response uses the same readiness
fields as `GET /me/profile`.

Request:

```json
{
  "college": "计算机学院",
  "major": "软件工程",
  "grade": "大二",
  "interest_tags": ["人工智能", "创新创业"],
  "competition_experience": "参加过校级程序设计竞赛",
  "goal_preferences": ["保研", "能力提升"]
}
```

### `PATCH /me/preferences`

Update recommendation and reminder preferences.

Request:

```json
{
  "interest_tags": ["人工智能"],
  "blocked_tags": ["数学建模"],
  "default_remind_days": 3,
  "message_enabled": true,
  "default_reminder_node_types": ["registration_deadline", "submission_deadline", "competition_start"]
}
```

The global reminder values belong to `reminder_settings`, even though this
combined preference API returns them with recommendation preferences. Defaults
are enabled, three days, and the listed core node types, but they only prefill a
subscription confirmation. Disabling `message_enabled` cancels all pending
plans while preserving subscriptions and calendar nodes; re-enabling reconciles
future eligible plans only.

## Competition APIs

### `GET /competitions`

Search, filter, and paginate public competitions.

Visibility rules:

- Return `published` competitions by default.
- Do not return `draft`, `pending_review`, `rejected`, `offline`, `archived`,
  `cancelled`, or `expired` competitions from the default public list.

Response item:

```json
{
  "id": 1,
  "title": "大学生创新创业竞赛",
  "short_title": "创新创业竞赛",
  "category": "创新创业",
  "organizer": "示例主办方",
  "status": "published",
  "registration_status": "open",
  "registration_status_basis": {
    "stage_id": 7,
    "node_id": 11
  },
  "source_name": "示例高校竞赛通知",
  "source_url": "https://example.edu/notices/innovation",
  "official_url": "https://example.org/innovation",
  "content_updated_at": "2026-07-10T01:00:00Z",
  "tags": ["校级推荐", "适合低年级"],
  "suitable_majors": ["软件工程"],
  "suitable_grades": ["大二"],
  "major_scope": "selected",
  "grade_scope": "selected",
  "value_notes": "校级推荐，适合有项目实践基础的学生",
  "next_node": {
    "id": 11,
    "node_type": "registration_deadline",
    "occurs_at": "2026-12-15T16:00:00Z",
    "description": "报名截止"
  },
  "is_favorited": false,
  "is_subscribed": false
}
```

`next_node` is the nearest future `primary` time node. If no future primary node
exists, it falls back to the nearest future `secondary` node. Elapsed nodes
remain in the detail timeline but are not returned as `next_node`. If a public
competition has no upcoming time node, `next_node` is `null`.

Supported Day 1 filters:

- `keyword`
- `category`
- `major`
- `grade`
- `tag`
- `registration_status`
- `participant_form`
- `deadline_from`
- `deadline_to`

Deadline bounds are inclusive `Asia/Shanghai` calendar dates and match only
`registration_deadline` time nodes with an `occurs_at` inside the requested
interval. Other milestones, including `submission_deadline`, remain visible in
the detail timeline but do not make a competition match this discovery filter.

P1 time-node types are controlled:

- `registration_start`
- `registration_deadline`
- `submission_deadline`
- `competition_start`
- `competition_end`
- `defense_or_review`
- `result_announcement`
- `other`

`other` requires a non-empty user-facing `description`. It is returned for
display but does not satisfy the core-node publication gate or participate in
default deadline filters and reminders. Unknown node-type strings are rejected.

Time-node responses include their赛事阶段 identity, stage label and order, and
`primary` or `secondary` prominence. Detail clients group nodes by stage and
must not infer pairing or importance from free-text descriptions.

`registration_status` is computed from current registration stages and nodes;
it is not stored. Multiple rounds aggregate with `open` first, then `upcoming`,
then `closed`, otherwise `unknown`. `not_applicable` requires an explicit admin
fact. `registration_status_basis` identifies the stage and node facts that
explain the result. Public publication-lifecycle `status` filtering is not
supported.

Default `sort=actionable` orders registration status as open, upcoming, unknown,
not applicable, then closed. Open results use future registration deadline,
upcoming results use registration start, and remaining groups use next primary
node, all ascending with missing time facts last. `published_at DESC` and
`competition_id DESC` are final stable tie-breakers. Changing sort resets page
to one while preserving filters.

The list response uses the common list envelope with `items` and `pagination`.

### `GET /competitions/{id}`

Return public competition detail. `published` competitions are available from
default discovery and detail. Previously published `cancelled`, `expired`, and
`archived` competitions remain available by detail URL with their current
status so the frontend can show a warning, but they are excluded from default
list and recommendation results. Missing, `draft`, `pending_review`, `rejected`,
and `offline` competitions return `404 not_found`.

Response data extends the list item with detail fields:

```json
{
  "id": 1,
  "title": "大学生创新创业竞赛",
  "status": "published",
  "source_name": "示例高校竞赛通知",
  "source_url": "https://example.edu/notices/innovation",
  "official_url": "https://example.org/innovation",
  "attachment_url": "https://example.edu/notices/innovation.pdf",
  "content_updated_at": "2026-07-10T01:00:00Z",
  "summary": "面向大学生的创新项目竞赛。",
  "detail": "提交项目方案、作品材料和现场答辩。",
  "eligibility": "在校本科生可报名。",
  "team_size": "1-5人",
  "participant_forms": ["team"],
  "suitable_majors": ["软件工程"],
  "suitable_grades": ["大二"],
  "major_scope": "selected",
  "grade_scope": "selected",
  "tags": ["校级推荐", "适合低年级"],
  "value_notes": "校级推荐，适合有项目实践基础的学生",
  "next_node": {
    "id": 11,
    "node_type": "registration_deadline",
    "occurs_at": "2026-12-15T16:00:00Z"
  },
  "time_nodes": [
    {
      "id": 11,
      "stage_id": 7,
      "stage_label": "报名阶段",
      "stage_order": 1,
      "node_type": "registration_deadline",
      "occurs_at": "2026-12-15T16:00:00Z",
      "description": "报名截止",
      "prominence": "primary"
    }
  ],
  "is_favorited": false,
  "is_subscribed": false
}
```

Every P1 public revision passed publication with at least one valid `primary`
core time node, so `time_nodes` is not empty. `next_node` may still be `null`
after all current nodes have elapsed. Detail clients display
`content_updated_at`, source facts, and a notice that selection guidance is for
reference and official or school notices remain authoritative.

`content_updated_at` is the approval time of the current public revision. It
changes only when a later approved revision replaces the prior public snapshot;
editing or submitting a non-public candidate does not change the public value.

For anonymous requests, `is_favorited` and `is_subscribed` are `false`. For an
authenticated student, they reflect that student's persisted edition-bound
favorite and subscription state.

### `POST /competitions/{id}/outbound_clicks`

Best-effort record an official, source, or attachment link activation. The
external link is opened directly by the browser; this endpoint never proxies or
redirects it and tracking failure must not block navigation.

Request:

```json
{
  "target_type": "official_url",
  "source_surface": "competition_detail"
}
```

Controlled target types are `source_url`, `official_url`, and `attachment_url`.
Controlled source surfaces initially include `competition_list`,
`competition_detail`, and `recommendation`. The server resolves the target from
the edition's currently viewable public revision and rejects a missing or
inaccessible target; clients cannot submit an arbitrary URL. Accepted events
return `202` and use server time.

The event stores edition id, public revision id, target type, source surface,
`actor_kind` (`authenticated` or `anonymous`), and occurrence time. It does not
store user id, account identifiers, IP address, User-Agent, or a cross-day
visitor identifier. Request-source data may be used ephemerally for rate
limiting but is not persisted in analytics records.

Raw events are retained for 90 days. Daily aggregation uses the
`Asia/Shanghai` product date and dimensions of edition, target type, source
surface, and actor kind. Statistics describe recorded clicks, not unique people
or registration conversion, and may undercount when best-effort delivery fails.

## Favorite And Subscription APIs

The `{id}` in these endpoints identifies one赛事届次. Favorite and subscription
state does not carry to another届次 in the same赛事系列. A future series-following
API, if added, is a separate capability and cannot create an edition
subscription without a new student action.

### `POST /competitions/{id}/favorite`

Favorite a competition.

Requires `student`.

### `DELETE /competitions/{id}/favorite`

Cancel favorite.

Requires `student`.

### `POST /competitions/{id}/subscribe`

Subscribe to a competition and, only after explicit configuration, create
eligible pending reminders. The first subscription UI must show a confirmation
surface. User defaults may prefill it, but the API does not infer consent from
omitted fields.

Requires `student`.

Request:

```json
{
  "reminder_enabled": true,
  "remind_days": 3,
  "node_types": ["registration_deadline", "submission_deadline", "competition_start"]
}
```

`reminder_enabled` is required. When true, `remind_days` is one integer from 0
to 30 and `node_types` is a non-empty subset of controlled primary core node
types present in the edition. P1 creates at most one ordinary reminder per time
node. When false, the subscription remains valid for the follow list and
calendar without reminder plans.

The response includes the effective configuration, `scheduled_reminder_count`,
`next_reminder_at`, and `unscheduled_reason` when no future plan is eligible.
Trigger times already in the past are not backfilled as immediate due reminders.

### `PATCH /competitions/{id}/subscription`

Update reminder settings for an existing subscription using the same explicit
fields as subscription creation. Turning reminders off cancels pending plans but
does not cancel the subscription or remove its calendar nodes. Turning them on
reconciles only future eligible plans.

### `DELETE /competitions/{id}/subscribe`

Cancel subscription and future pending reminders.

Requires `student`.

## Calendar And Message APIs

### `GET /me/calendar`

Return time nodes from active edition subscriptions. Favorites are not calendar
inputs, and subscriptions remain calendar inputs when their reminders are
disabled.

Query parameters:

- `from`
- `to`
- `view`: `month`, `week`, or `list`

`from` and `to` are `Asia/Shanghai` product-calendar dates. All views resolve
the same underlying nodes; `view` selects range/grouping metadata rather than a
different source of truth. Items include edition and stage identifiers, stage
label/order, node id/type/description, `occurs_at`, `prominence`, pair metadata,
current-stage state, current lifecycle visibility, and a target-availability
flag.

The API returns every node type selected by the subscription, not only nodes
with pending reminders. Cancellation or emergency offline excludes future
nodes. A target that became unavailable has no detail URL. Same-day items use
stable stage order, node occurrence, prominence, and node id ordering.

Requires `student`.

### `GET /me/messages`

Return retained in-app messages newest first, with `created_at DESC, id DESC` as
the stable order.

Query parameters:

- `page`, `page_size`
- `read_status`: `all` (default) or `unread`
- `message_type`: `reminder_due`, `competition_time_changed`,
  `competition_cancelled`, or `competition_offline`

Response items contain immutable `title_snapshot`, `body_snapshot`,
`event_occurred_at`, `created_at`, `retained_until`, `message_type`, mutable
`is_read` and `read_at`, and a competition target snapshot. If the current
target is unavailable, `target_available` is false and no public target URL is
returned; the historical message remains readable.

Requires authentication.

### `GET /me/messages/unread_count`

Return the current user's retained unread count for the global navigation badge.

Requires authentication.

### `POST /me/messages/{id}/read`

Mark one message as read.

Requires authentication and message ownership.

The operation is idempotent. It changes only `is_read` and `read_at`; message
content and event snapshots remain immutable.

### `POST /me/messages/read_all`

Idempotently mark all retained messages owned by the current user as read and
return the updated unread count.

P1 exposes no message delete endpoint. Messages expire 365 days after creation
and are removed by the retention task or with account data deletion.

## Recommendation APIs

### `GET /recommendations`

Return rule-based recommendations and reasons.

Requires optional authentication:

- Authenticated students with a `recommendation_ready` profile receive
  profile-based recommendations.
- Anonymous or profile-incomplete users receive general actionable
  recommendations.

Response metadata includes `recommendation_mode` (`personalized` or `general`),
`profile_status` for an authenticated student, and `missing_fields` when the
profile is incomplete. General results use an explicit fallback reason rather
than implying a personal match. Personalized results also include the immutable
`rule_set_version`; general results set it to `null` and include
`fallback_reason`, including `no_active_rule_set` when configuration is missing.

Every response includes an opaque random `recommendation_request_id`. Each item
includes server-assigned `position` and controlled `reason_codes` alongside the
display reasons. The server creates a raw request-item snapshot for every
returned item, including mode, rule-set version, actor kind, and server time;
the snapshot contains no user id or profile fields and expires after 90 days.

Response item:

```json
{
  "competition": {
    "id": 1,
    "title": "大学生创新创业竞赛"
  },
  "reasons": ["与你的专业匹配", "报名截止较近"]
}
```

Recommendation ranking may use internal weights, but the public API should expose
reasons and ordering rather than a raw score or competition value rating.

### `POST /recommendation_events`

Best-effort record actual rendering or detail navigation for items from one
recommendation response.

Impression request example:

```json
{
  "recommendation_request_id": "01J...",
  "event_type": "impression",
  "competition_ids": [1, 2, 3]
}
```

Click requests use `event_type: "click"` with one competition id. The service
accepts only unexpired request-item pairs created by the recommendation API and
reads position, mode, rule-set version, reason codes, and actor kind from the
server snapshot. It does not accept those dimensions from the client.

Impression and click are each idempotent per request item. A click requires a
recorded impression. Tracking failure must not block recommendation rendering or
detail navigation.

Raw request items retain random request id, edition, position, mode, rule-set
version, reason codes, actor kind, returned time, optional impressed time, and
optional clicked time for 90 days. They do not store user id, account identity,
profile fields, IP address, User-Agent, or a cross-request visitor id. Daily
aggregates use `Asia/Shanghai` date and are labeled as recorded impressions,
clicks, and best-effort click-through ratio rather than people, quality, or
registration conversion.

## Admin APIs

Admin APIs require `admin`.

Competition create/update/submit operations require `competition_editor`;
approve/reject/return operations require `competition_reviewer`.

### `POST /admin/competitions`

Create a draft competition.

Time-node datetime values follow the common date and time convention above.
Offsetless values are treated as `Asia/Shanghai`; responses are normalized to
UTC.

Structured draft fields may include time nodes and controlled tags:

```json
{
  "title": "全国大学生人工智能创新挑战赛",
  "source_name": "示例高校竞赛通知",
  "source_url": "https://example.edu/notices/ai-challenge-2026",
  "summary": "面向大学生的人工智能创新项目竞赛。",
  "time_nodes": [
    {
      "node_type": "registration_deadline",
      "occurs_at": "2026-08-15T16:00:00Z",
      "description": "报名截止"
    }
  ],
  "tags": [
    {
      "code": "ai",
      "name": "人工智能",
      "tag_type": "topic"
    }
  ]
}
```

### `POST /admin/competitions/{id}/revisions`

Create a draft revision, copying the current public revision when one exists.
The current public revision remains selected while this draft is edited or
reviewed.

### `PATCH /admin/competition_revisions/{revision_id}`

Update one draft revision. Submitted and decided revisions are immutable.
Stage and time-node editing is identity-aware and must not use blind list
replacement after reminder-dependent state exists.

### `POST /admin/competition_revisions/{revision_id}/submit_review`

Submit competition for review.

The current P1 publication gate requires at least one recognized competition
time node with a valid `occurs_at` instant. An empty time-node list
does not implicitly mean that dates are pending official announcement; such a
record remains editable and non-public.

The complete P1 gate also requires series identity, source-backed edition label,
title, source name, valid HTTP(S) source URL, category, organizer, summary,
eligibility, a non-empty `participant_forms` set, explicit major and grade
scope, at least one stage, and at least one primary core node. Team entry
requires team-size facts. Optional official and attachment URLs must also use
HTTP(S).

### `POST /admin/competition_revisions/{revision_id}/review`

Approve, reject, or return a competition.

A non-empty review comment is required so every decision retains review
context. The API rejects review when the current account submitted the target
revision, even if that account also has reviewer permission. Approval atomically
selects the revision for public reads; an existing approved revision remains
public until that decision.

Request:

```json
{
  "action": "approve",
  "comment": "信息完整，来源可信"
}
```

Allowed actions:

- `approve`
- `reject`
- `return`

### `PATCH /admin/competitions/{id}/status`

Perform post-publication status maintenance. The P1 flow allows a `published`
competition to move to `offline`, `archived`, `cancelled`, or `expired`. Other
transitions use the submit/review workflow or return `409 conflict`. A non-empty
reason is required, and successful changes write status-specific audit evidence.

Emergency `offline` is immediate for an authorized status maintainer. Returning
an offline edition to `published` is not accepted through this endpoint; it
requires approval of a corrected revision.

Request:

```json
{
  "status": "offline",
  "reason": "官方链接失效，待确认"
}
```

### `GET /admin/users`

List users.

### `PATCH /admin/users/{id}`

Update user role or account status.

### `GET /admin/configs`

List system configs and base dictionaries. Recommendation rule sets use their
own versioned endpoints and cannot be updated through generic config APIs.

### `PATCH /admin/configs/{key}`

Update one config value.

### `GET /admin/recommendation_rule_sets`

List recommendation rule-set versions, states, submitter/reviewer facts, and the
single active version. Requires `recommendation_editor` or
`recommendation_reviewer`.

### `POST /admin/recommendation_rule_sets`

Create a draft by cloning an existing version or the reproducible initial seed.
Rules use controlled codes, bounded integer weights, structured conditions,
reason templates, and enabled state; executable expressions are rejected.

Requires `recommendation_editor`.

### `PATCH /admin/recommendation_rule_sets/{id}`

Update a draft rule set. Submitted, decided, active, and retired versions are
immutable.

Requires `recommendation_editor` and draft ownership or equivalent permission.

### `POST /admin/recommendation_rule_sets/{id}/preview`

Preview ordering and reasons against a synthetic profile and selected public
competition fixtures without persisting a recommendation. The endpoint does not
accept another student's user id or read arbitrary personal profiles.

Requires `recommendation_editor` or `recommendation_reviewer`.

### `POST /admin/recommendation_rule_sets/{id}/submit_review`

Freeze and submit a complete draft for independent review.

Requires `recommendation_editor`.

### `POST /admin/recommendation_rule_sets/{id}/review`

Approve and activate, reject, or return a submitted rule set with a required
comment. The reviewer must differ from the submitter. Approval atomically
activates the candidate and retires the prior active version.

Requires `recommendation_reviewer`.

### `GET /admin/reviews`

List immutable competition-revision and recommendation-rule-set review records.

Query parameters include `page`, `page_size`, controlled `target_type`, review
`status`, `submitted_by`, and date range. Items expose submitter/reviewer,
decision time, comment, target version, differences, and impact summary. The API
does not provide a review-record update endpoint.

### `GET /admin/audit_logs`

List immutable key-operation events, filterable by `page`, `page_size`, actor,
controlled action, target type/id, result, and date range. Event detail uses an
action-specific allowlist and never contains passwords, verification codes,
session values, full account identifiers, profile content, or raw analytics
identifiers. The API does not provide an audit-log update or delete endpoint.

### `GET /admin/stats`

Return read-only operational statistics with `as_of`, time-zone, metric
definitions, windows, and best-effort caveats. Query `window` is `current`,
`7d`, or `30d`; unsupported dimensions are rejected rather than approximated.

Initial metrics:

- Current published and pending-review counts.
- Current active favorite and subscription counts.
- Current message delivery-state counts.
- Seven-day and 30-day recorded outbound click counts.
- Seven-day and 30-day recorded recommendation impression and click counts,
  plus their explicitly labeled best-effort ratio.

P2 thin includes current published and pending-review counts, active favorite
and subscription counts, message delivery state counts, outbound click daily
counts, and recommendation recorded impression/click counts and ratio. It does
not expose named-user drill-down, real-time streaming, BI export, or claims of
unique people, recommendation quality, or registration conversion.

All review, audit, and statistics endpoints require `admin`; a student receives
`403 forbidden`. Stable pagination and filters are part of the contract.

## Internal Task Interfaces

Internal Celery task names:

- `competehub.reminders.dispatch_due`

Task behavior:

- Query due `pending` reminders.
- Create messages idempotently.
- Mark reminders as `sent`, `cancelled`, or `failed`.

These are not public HTTP APIs.
