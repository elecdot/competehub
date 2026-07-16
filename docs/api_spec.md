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
| 409 | `active_revision_exists` | The edition already has its one active draft or pending revision. |
| 409 | `stale_revision` | A submitted replacement was reviewed against a public revision that is no longer current. |
| 409 | `offline_restoration_requires_corrected_revision` | An offline edition can be restored only by a changed candidate submitted after the current withdrawal. |
| 409 | `engagement_unavailable` | The current edition lifecycle does not permit the requested favorite/subscription mutation. |
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
absolute deadline. Idle timestamp Cookie writes are coalesced within a one-minute
window so concurrent page requests do not race to overwrite the signed session;
status, version, and timeout validation still runs on every request. P1 allows concurrent sessions and has no user-selectable
remember-me mode. Logout clears only the current browser; disabling an account,
changing its role or capabilities, confirming credential compromise, or
explicitly terminating all sessions increments the account version and
invalidates every device on its next request.

P1 assumes one configured部署高校 per deployment. `student_no` and `college`
are interpreted in that boundary; the API does not accept a user-selected tenant
or institution identifier.

Initial roles:

- `student`
- `admin`

Administrator capabilities include `competition_editor`,
`competition_reviewer`, `competition_maintainer`, `recommendation_editor`, and
`recommendation_reviewer`, and `user_administrator`. They do not create new
formal product roles. One account may hold multiple capabilities, but it cannot
review a competition revision or recommendation rule-set version it submitted.

`competition_maintainer` authorizes cancellation, expiry, archival, and
emergency offline with a required reason and impact context. It does not
authorize revision editing or approval, and restoring public availability still
requires an independently reviewed corrected revision.

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

### `GET /auth/capabilities`

Return public authentication capabilities that the frontend may use before a
browser session exists.

Response:

```json
{
  "data": {
    "public_email_registration_enabled": true
  },
  "error": null
}
```

`public_email_registration_enabled` is true only when public registration is
enabled and a real email verification sender is configured. The frontend must
hide public registration entry points when this value is false.

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

The successful response is `202 Accepted` and does not create a session. If the
typed email identity is already pending activation or is already verified on an
`active` account, the response remains generic and no additional account,
challenge, or delivery outbox row is created. SMTP delivery is asynchronous
through a transactional outbox; the HTTP request never contacts SMTP, and
acceptance does not claim delivery.
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
verified. Issuing a replacement consumes every older unconsumed challenge for
the identity and commits the new challenge and delivery-outbox row atomically;
only a pending identity on a `pending_activation` account can be verified. The
HTTP request does not execute SMTP.

### `POST /auth/login`

Login with an explicitly typed account identity. The API never searches one
identifier across unrelated identity types. Pending, disabled, unknown, and
incorrect-password cases use a non-enumerating authentication failure and do
not create a session. Every one of these cases performs one adaptive password
verification; unknown identities use a fixed dummy Argon2id hash before the
account and identity state is evaluated.

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

Return current user, role, and controlled capability set without bound email,
phone, or student-number identities. Student `capabilities` is always an empty
array. Administrator capabilities let the frontend discover eligible workbench
surfaces, but every backend endpoint still performs its own authoritative role
and capability check.

Response data example:

```json
{
  "id": 3,
  "display_name": "Day 1 Admin",
  "role": "admin",
  "capabilities": [
    "competition_editor",
    "recommendation_editor",
    "recommendation_reviewer"
  ]
}
```

Requires authentication.

## Profile APIs

### `GET /me/profile`

Return current student's profile plus its dynamically derived readiness state.
`profile_status` is `incomplete` or `recommendation_ready`; `missing_fields`
contains any of `college`, `major`, `grade`, or `interest_tags`. The readiness
state is not stored independently. Student profile and global reminder-setting
rows are provisioned when a student account becomes active or is governed into
the student role; these read and update routes do not create missing rows
lazily.

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

### `GET /me/profile/options`

Return the deployment-controlled values accepted by `PATCH /me/profile`. The
response keeps majors grouped by college so the client can prevent invalid
college-major combinations.

Response data example:

```json
{
  "colleges": ["计算机学院", "经济管理学院"],
  "majors_by_college": {
    "计算机学院": ["软件工程", "计算机科学与技术"],
    "经济管理学院": ["金融学", "工商管理"]
  },
  "grades": ["大一", "大二", "大三", "大四"],
  "interest_tags": ["人工智能", "创新创业", "程序设计"]
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
plans while preserving subscriptions and calendar nodes. Re-enabling changes
only the global setting in #38. In Issue #40, the false-to-true coordinator may
return the exact unattempted `global_reminder_disabled` ordinary plan to
`pending` only when its active subscription, confirmed reminder choice, current
published node revision, and recalculated trigger are still eligible and future.
It creates a current-revision plan when none exists, but does not backfill or
restore attempted, sent, failed, elapsed, prior-revision, lifecycle-cancelled,
or otherwise terminal work.

`reminder_settings` is authoritative when a row exists; the combined API shape
remains stable across its storage migration. Persistence invariants are owned by
the [data model](data_model.md#reminder_settings), transaction and
reconciliation behavior by the [technical specification](tech_spec.zh.md), and
operator migration/backfill/downgrade procedures by
`apps/api/migrations/README`.

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
    "snapshot_id": 11,
    "logical_node_key": "registration-main-deadline",
    "node_revision": 1,
    "node_type": "registration_deadline",
    "occurs_at": "2026-12-15T16:00:00Z"
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
    "snapshot_id": 11,
    "logical_node_key": "registration-main-deadline",
    "node_revision": 1,
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

`snapshot_id` identifies one immutable time-node row in the selected
competition revision. `logical_node_key` is the stable opaque identity for the
same milestone across revisions of one赛事届次, and `node_revision` increases as
approved behavior-bearing node facts or the key's approved presence change. A
node copied unchanged into a new competition revision has a new snapshot id but
keeps its node revision. Clients use the snapshot id for exact response
references and the logical key for cross-revision reconciliation; they must not
treat either value as globally meaningful outside the edition.

Tags and fit/value fields belong to the selected public revision. Candidate
revision tag changes do not appear in list, detail, outbound-link context, or
recommendations before approval switches `published_revision_id`.

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

### `GET /competitions/filter-options`

Return the exact values that a visitor can use with the public discovery
`category`, `major`, `grade`, and `tag` filters. Authentication is not required.

```json
{
  "data": {
    "categories": ["创新创业"],
    "majors": ["计算机科学与技术", "软件工程"],
    "grades": ["大一", "大二"],
    "tags": ["人工智能", "创新创业"]
  },
  "error": null
}
```

Values are deduplicated and sorted. They are derived only from the revision
selected by `published_revision_id` for editions eligible for the default public
list. Draft, pending, rejected, offline, cancelled, and archived values are never
exposed as filter options. Candidate revision values do not appear before approval
switches the public revision pointer. An empty public catalogue returns four empty
arrays.

### `GET /competitions/{id}`

Return public competition detail. `published` competitions are available from
default discovery and detail. Previously published `cancelled`, `expired`, and
`archived` competitions remain available by detail URL with their current
status so the frontend can show a warning, but they are excluded from default
list and recommendation results. Missing, `draft`, `pending_review`, `rejected`,
and `offline` competitions return `404 not_found`.

Historical detail includes `lifecycle_warning` with the current lifecycle
`status`, the required maintenance `reason`, and `changed_at`. Published detail
returns `lifecycle_warning: null`. The reason is current warning context; the
append-only audit event remains the durable transition evidence.
Clients render `changed_at` in the `Asia/Shanghai` product timezone. Historical
detail does not offer create or update subscription actions; an authenticated
student may still cancel their own existing subscription.

Response data extends the list item with detail fields:

```json
{
  "id": 1,
  "title": "大学生创新创业竞赛",
  "status": "published",
  "edition_label": "2026",
  "current_revision": {
    "id": 11,
    "revision_number": 2
  },
  "lifecycle_warning": null,
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
    "snapshot_id": 11,
    "logical_node_key": "registration-main-deadline",
    "node_revision": 1,
    "node_type": "registration_deadline",
    "occurs_at": "2026-12-15T16:00:00Z"
  },
  "time_nodes": [
    {
      "snapshot_id": 11,
      "logical_node_key": "registration-main-deadline",
      "node_revision": 1,
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
  "is_subscribed": false,
  "subscription_summary": null
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
`current_revision` identifies that selected immutable snapshot, while
`edition_label` identifies the concrete participation cycle. Clients display
these values with source facts and the time-node stage metadata, formatting
user-facing timestamps in `Asia/Shanghai`, instead of inferring currentness
from an editable candidate.

For anonymous requests, `is_favorited` and `is_subscribed` are `false`. For an
authenticated student, they reflect that student's persisted edition-bound
favorite and subscription state. Detail responses also include
`subscription_summary`: `null` when the student has no relation, otherwise the
same student-facing consent summary returned by subscription POST/PATCH. It
contains the persisted `reminder_enabled`, `remind_days`, and `node_types` used
to prefill an explicit later confirmation; it exposes no internal relation ID.

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
return `202` and use server time. The endpoint applies an ephemeral
request-source rate limit through the shared Redis-backed limiter. Exceeding
the configured window returns `429 rate_limited` and does not create another
event; the response details include `retry_after_seconds`.

The browser opens the HTTP(S) target directly with `noopener noreferrer`, then
may send this request as a best-effort action. A failed, delayed, or blocked
recording request never changes the link target or prevents navigation.

The event stores edition id, public revision id, target type, source surface,
`actor_kind` (`authenticated` or `anonymous`), and occurrence time. It does not
store user id, account identifiers, IP address, User-Agent, or a cross-day
visitor identifier. Request-source data may be used ephemerally for rate
limiting but is not persisted in analytics records.

Raw events are retained against the exact event-time cutoff: rows with
`occurred_at < now - 90 days` expire, while a row exactly on the boundary is
retained. A transactionally stored aggregation marker makes repeated jobs
idempotent, and PostgreSQL workers serialize aggregation with a transaction
advisory lock before incrementing durable counts and deleting expired rows.
Daily aggregation uses the `Asia/Shanghai` product date and dimensions of
edition, target type, source surface, and actor kind. Statistics describe
recorded clicks, not unique people or registration conversion, and may
undercount when best-effort delivery fails.

## Favorite And Subscription APIs

The `{id}` in these endpoints identifies one赛事届次. Favorite and subscription
state does not carry to another届次 in the same赛事系列. A future series-following
API, if added, is a separate capability and cannot create an edition
subscription without a new student action.

Lifecycle mutation policy:

| Edition lifecycle | Create favorite | Delete owned favorite | Create subscription | Update owned subscription settings | Delete owned subscription |
|---|---|---|---|---|---|
| `published` | allowed | allowed | allowed | allowed | allowed |
| `cancelled` | allowed | allowed | rejected | rejected | allowed |
| `archived` | allowed | allowed | rejected | rejected | allowed |
| `expired` | allowed | allowed | rejected | rejected | allowed |
| `offline` | rejected | allowed | rejected | rejected | allowed |
| `unpublished` | rejected | allowed if an owned historical relation exists | rejected | rejected | allowed if an owned historical relation exists |

Historical-viewable detail may therefore be saved as a favorite, but only a
currently published edition accepts a new subscription or reminder-setting
change. Owned DELETE operations resolve the personal relation independently of
current public visibility, remain idempotent, and are always available so an
offline target cannot trap engagement state. Rejected mutations return
`409 engagement_unavailable` without altering existing relations.

### `POST /competitions/{id}/favorite`

Favorite a published or historical-viewable competition.

Requires `student`.

### `DELETE /competitions/{id}/favorite`

Cancel favorite.

Requires `student`.

### `POST /competitions/{id}/subscription`

Subscribe to a competition and, only after explicit configuration, create
eligible pending reminders. The first subscription UI must show a confirmation
surface. User defaults may prefill it, but the API does not infer consent from
omitted fields.

`reminder_settings` is required authoritative student-owned data for subscription
creation, re-subscription, semantic updates, plan reconciliation, and summary
reads. If it is missing, the request returns `500 internal_server_error` in the
normal error envelope and rolls back without creating or changing a subscription
or reminder plan.

Requires `student`.

Request:

```json
{
  "reminder_enabled": true,
  "remind_days": 3,
  "node_types": ["registration_deadline", "submission_deadline", "competition_start"]
}
```

`reminder_enabled`, `remind_days`, and `node_types` are all required regardless
of reminder state. `remind_days` is one integer from 0 to 30 and `node_types` is
a non-empty subset of controlled primary core node types present in the edition.
The selected types define calendar projection as well as potential reminder
plans. When reminders are enabled, P1 creates at most one ordinary reminder per
selected time node. When disabled, the subscription retains the confirmed
offset and node selection for the follow list and calendar but creates no
reminder plans.

The response includes the effective configuration, `scheduled_reminder_count`,
`next_reminder_at`, and `unscheduled_reason` when no future plan is eligible.
`unscheduled_reason` is `null` when any pending plan is scheduled. Otherwise it
is exactly `reminder_disabled` when the subscription choice or global reminder
switch is disabled, or `no_future_eligible_nodes` when reminders are effectively
enabled but every matching trigger is non-future. Trigger times already in the
past are not backfilled as immediate due reminders.

Successful POST and PATCH responses use the normal envelope and expose only the
student-facing subscription summary:

```json
{
  "data": {
    "competition_id": 1,
    "status": "active",
    "is_subscribed": true,
    "reminder_enabled": true,
    "remind_days": 3,
    "node_types": ["registration_deadline"],
    "reminder_confirmed_at": "2026-07-13T00:00:00+00:00",
    "scheduled_reminder_count": 1,
    "next_reminder_at": "2026-08-15T16:00:00+00:00",
    "unscheduled_reason": null
  },
  "error": null
}
```

The first POST that creates the edition-bound relation returns `201 Created`.
POST against an active relation returns `200 OK` without replacing its existing
consent, even when the repeated payload differs. POST against a cancelled
relation is an explicit re-subscription and also returns `200 OK`: it requires a
fresh complete payload, reuses the relation, replaces its current configuration
and `reminder_confirmed_at`, and reconciles plans under the rules below. The
subscription stores only the latest consent, not immutable consent generations.

With newly confirmed consent and current eligible future nodes, explicit
re-subscription and a semantic PATCH may restore an unsent cancelled ordinary
plan only when its reason is `subscription_cancelled`, `reminder_disabled`,
`node_type_removed`, or `subscription_offset_not_future`. They retain all other
cancellation evidence. Sent, failed, elapsed, prior-revision, offline, deletion,
lifecycle, supersession, global-setting, and other system-owned evidence, plus
delivered messages, are terminal: they are never restored, rewritten, or
replayed by re-subscription or semantic PATCH. The separate Issue #40 global
false-to-true coordinator is the sole exception for an exact unattempted
`global_reminder_disabled` row whose current trigger remains future.

### `PATCH /competitions/{id}/subscription`

Update reminder settings for an existing subscription using the same explicit
fields as subscription creation. Turning reminders off cancels pending plans but
does not cancel the subscription or remove its calendar nodes. A semantic change
that turns reminders on, restores a node type, or makes the offset future may
restore only the controlled eligible plans listed above. New and restored plans
require both the confirmed subscription switch and the current global reminder
switch to be enabled. The edition must still be `published`; historical or
offline relations can be removed but not reconfigured.

### `DELETE /competitions/{id}/subscription`

Cancel subscription and future pending reminders with
`cancel_reason=subscription_cancelled`. First and repeated DELETE return
`200 OK` with the final cancelled state and never alter sent evidence.
Deleting a nonexistent edition returns `404 not_found` with `competition not found`;
an existing edition without an owned relation remains idempotent.

Its response data is `{ "competition_id": 1, "status": "cancelled",
"is_subscribed": false }`; cancellation reasons and reminder internals are not
public response fields.

Requires `student`.

## Calendar And Message APIs

### `GET /me/calendar`

Return time nodes from active edition subscriptions. Favorites are not calendar
inputs, and subscriptions remain calendar inputs when their reminders are
disabled.

Query parameters:

- `from` (required)
- `to` (required)
- `view` (required): `month`, `week`, or `list`

`from` and `to` are `Asia/Shanghai` product-calendar dates. All views resolve
the same underlying nodes; `view` selects range/grouping metadata rather than a
different source of truth. Items include edition and stage identifiers, stage
label/order, node snapshot id/logical key/revision/type/description,
`occurs_at`, `prominence`, pair metadata, current-stage state, current lifecycle
visibility, and a target-availability flag.

To keep Shanghai-midnight conversion and the exclusive end boundary within the
supported UTC datetime range, both dates must be from `0001-01-02` through
`9999-12-30`, inclusive.

Example response:

```json
{
  "data": {
    "range": {
      "from": "2026-08-01",
      "to": "2026-08-31",
      "view": "month",
      "time_zone": "Asia/Shanghai"
    },
    "items": [
      {
        "competition_id": 101,
        "competition_title": "全国大学生人工智能创新挑战赛",
        "detail_url": "/competitions/101",
        "lifecycle_status": "published",
        "target_available": true,
        "stage_id": 301,
        "stage_label": "报名阶段",
        "stage_order": 1,
        "stage_type": "registration",
        "is_current_stage": true,
        "node_snapshot_id": 401,
        "logical_node_key": "registration-main-deadline",
        "node_revision": 2,
        "node_type": "registration_deadline",
        "description": "报名截止",
        "occurs_at": "2026-08-15T16:00:00+00:00",
        "prominence": "primary",
        "pair_kind": "registration",
        "pair_role": "deadline"
      }
    ]
  },
  "error": null
}
```

`pair_kind`/`pair_role` are derived from controlled types only:
registration start/deadline and competition start/end. Other node types return
both fields as `null`. `is_current_stage` is edition-level metadata derived from
all nodes in the current public revision at the current server instant, not from
the requested range or the subscription's selected node types. The nearest
non-elapsed node determines the stage; equal instants use stage order, and after
all nodes elapse the final ordered stage is current.

Missing or malformed dates, an end before the start, an unsupported view, or an
unknown query field returns `400 validation_error`. The error `details.field`
identifies `from`, `to`, `view`, or the unknown field.

Archived or expired editions retain past selected nodes when they fall inside
the requested range, with their historical lifecycle status. Their transition
is permitted only after every node has elapsed, so they cannot contribute a
future calendar item. Existing subscriptions remain historical relations;
creating a new subscription requires a currently published edition.

The API returns every node type selected by the subscription, not only nodes
with pending reminders. Cancellation or emergency offline excludes future
nodes. A target that became unavailable has no detail URL. Same-day items use
stable stage order, node occurrence, prominence, and node snapshot id ordering.

Requires `student`.

### `GET /me/messages`

Return retained in-app messages newest first, with `created_at DESC, id DESC` as
the stable order.

Query parameters:

- `page`, `page_size`
- `read_status`: `all` (default) or `unread`
- `message_type`: `reminder_due`, `competition_time_changed`,
  `competition_cancelled`, or `competition_offline`

The response uses the common list envelope. Each item has this stable shape:

```json
{
  "id": 123,
  "message_type": "reminder_due",
  "title_snapshot": "报名截止提醒",
  "body_snapshot": "示例赛事即将截止报名。",
  "target_snapshot": {
    "competition_id": 42,
    "competition_title": "示例赛事",
    "node_type": "registration_deadline",
    "node_occurs_at": "2026-08-20T08:00:00Z",
    "reason_summary": null
  },
  "event_occurred_at": "2026-08-17T08:00:00Z",
  "created_at": "2026-08-17T08:00:01Z",
  "retained_until": "2027-08-17T08:00:01Z",
  "is_read": false,
  "read_at": null,
  "target_available": true,
  "target_url": "/competitions/42"
}
```

`title_snapshot`, `body_snapshot`, `target_snapshot`, `event_occurred_at`,
`created_at`, `retained_until`, and `message_type` are immutable. Within
`target_snapshot`, `node_type`, `node_occurs_at`, and `reason_summary` are
nullable: ordinary due reminders snapshot their one node, while consolidated
or lifecycle events may instead carry a reason summary without inventing a
single node. For `reminder_due`, `event_occurred_at` equals the reminder's
`due_at`; for the other message types it is the domain-event time.

`is_read` and `read_at` are mutable. `target_available` and `target_url` are
derived from current visibility rather than stored in the immutable snapshot.
If the target is unavailable, `target_available` is false and `target_url` is
null; the historical message remains readable.

An approved replacement revision emits at most one consolidated
`competition_time_changed` message per affected active subscriber. It is
emitted only for an `occurs_at` change, selected controlled node-type change, or
selected node addition/removal. Stage, prominence, description, title, and
other presentation-only changes update calendar data and current pending
reminder snapshots without emitting this message. Idempotency is scoped to user
and approved revision event, not to every changed node row.

Requires `student`; list results contain only that student's retained messages.

### `GET /me/messages/unread_count`

Return the current user's retained unread count for the global navigation badge:

```json
{
  "data": {"unread_count": 3},
  "error": null
}
```

Requires `student`.

### `POST /me/messages/{id}/read`

Mark one retained message as read.

Requires `student` and message ownership. A missing, expired, or other user's
message returns the same `404 not_found` response and does not reveal whether a
row exists.

The operation is idempotent. It changes only `is_read` and `read_at`; message
content and event snapshots remain immutable. It returns the updated message in
the same item shape as the list plus the current retained unread count:

```json
{
  "data": {
    "message": {},
    "unread_count": 2
  },
  "error": null
}
```

### `POST /me/messages/read_all`

Idempotently mark all retained messages owned by the current user as read and
return both the number changed by this operation and the resulting unread count:

```json
{
  "data": {
    "updated_count": 3,
    "unread_count": 0
  },
  "error": null
}
```

Requires `student`.

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
`fallback_reason`. The controlled public values are:

- `anonymous`: no authenticated student context is available, including for an
  unauthenticated request or an authenticated non-student caller.
- `profile_incomplete`: the authenticated student is missing one or more
  dynamically derived profile fields listed in `missing_fields`.
- `no_active_rule_set`: a recommendation-ready student cannot use
  personalization because no valid active rule set exists.

The fallback precedence is caller state first: `anonymous`, then
`profile_incomplete`, then `no_active_rule_set` only for a recommendation-ready
student. Configuration availability does not replace the first two causes.

General items use the controlled `general_fallback` item reason code. When an
active rule set exists, its general-fallback template supplies the display
reason. With no valid active rule set, the API uses a fixed, explicitly general
actionable-order explanation; `fallback_reason` still follows the caller-state
precedence above, so the fixed copy accompanies `no_active_rule_set` only for a
recommendation-ready student. It is never presented as an active configured
rule or personal match.

The serving slice returns at most 20 items. Personalized matches use private
governed weights from every enabled matched rule, then unmatched published
candidates supplement the result in general actionable order. General mode uses
actionable order directly. Each public item exposes at most the three strongest
controlled reasons; that display cap does not remove other matches from private
ranking. Governance preview preserves all matched rule codes and reasons.

Response data example:

```json
{
  "recommendation_mode": "general",
  "profile_status": "incomplete",
  "missing_fields": ["major", "grade", "interest_tags"],
  "fallback_reason": "profile_incomplete",
  "rule_set_version": null,
  "items": []
}
```

Each item includes server-assigned `position` and controlled `reason_codes`
alongside the display reasons. The FR-014 interaction-measurement slice extends
this response with an opaque random `recommendation_request_id` and creates a
90-day raw request-item snapshot containing mode, rule-set version, actor kind,
and server time but no user id or profile fields. Until that separately scoped
slice is implemented, clients must not assume the request id or
`POST /recommendation_events` is available.

Response item:

```json
{
  "position": 1,
  "reason_codes": ["major_match", "deadline_urgency"],
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

This is the FR-014 follow-up contract and is not registered by the Issue #42
recommendation-serving slice.

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
profile fields, IP address, User-Agent, or a cross-request visitor id.

Daily aggregation writes item-level totals by `Asia/Shanghai` date, edition,
position, mode, rule-set version, and actor kind, counting each request item
once regardless of reason count. A separate reason-attribution aggregate uses
the same dimensions plus one deduplicated `reason_code`; a multi-reason item can
contribute to several attribution rows. Overall impressions, clicks, and ratio
come only from item-level totals. Reason rows are never summed as totals and are
labeled attribution rather than cause. Neither aggregate represents people,
quality, or registration conversion.

Daily dates follow event time. An impression contributes to the
`Asia/Shanghai` date of `impressed_at`, while a click contributes to the date of
`clicked_at`; one request item may therefore affect different daily rows. The
7-day and 30-day displayed ratio divides click events in the selected period by
impression events in that period. It is labeled an event-period interaction
ratio, not an impression-cohort conversion.

## Admin APIs

Admin APIs require `admin`.

Competition create/update/submit operations require `competition_editor`;
approve/reject/return operations require `competition_reviewer`; post-publication
status maintenance requires `competition_maintainer`.

The competition workbench read endpoints require at least one of those three
capabilities. They use the common list envelope, stable pagination, and
controlled filters; possessing read access never authorizes a corresponding
write action.

### `GET /admin/competition_series`

Search and select赛事系列. Query parameters are `keyword`, `page`, and
`page_size`. Items include series id, canonical name, edition count, latest
edition summary, and whether any edition has an active workflow revision.

### `GET /admin/competitions`

List赛事届次 for editing, review, and status maintenance. Controlled filters are
`series_id`, `keyword`, `lifecycle_status`, `revision_status`,
`has_active_revision`, `page`, and `page_size`. Items include edition identity,
series identity, lifecycle status, current `published_revision_id`, public title
summary, active draft/pending revision summary, and last-updated time.

Filtering `revision_status=pending_review` supplies the workbench review queue;
terminal decisions remain in `GET /admin/reviews` and are not synthesized as
mutable pending review records.

### `GET /admin/competitions/{id}`

Load one edition workspace. The response includes series/edition identity,
lifecycle status, current public revision summary, the single active workflow
revision when present, revision history summaries, status-transition
availability, and aggregate engagement/reminder impact counts without student
identities.

### `GET /admin/competition_revisions`

List revision summaries. Controlled filters are `competition_id`,
`revision_status`, `submitted_by`, `page`, and `page_size`. Items include
revision id/number/status, `base_revision_id`, submitter, submitted/updated
times, completeness state, current-public relation, and stale state. This
endpoint supports both edition history and a global pending-review queue.

### `GET /admin/competition_revisions/{revision_id}`

Load the exact editable or immutable revision read model. It includes all
source-backed fields, revision-scoped tags, ordered stages and time-node
snapshots, workflow actor/times, and:

```json
{
  "id": 42,
  "competition_id": 7,
  "revision_number": 2,
  "revision_status": "pending_review",
  "base_revision_id": 40,
  "current_published_revision_id": 40,
  "is_stale": false,
  "submitted_by": {"id": 3, "display_name": "Day 1 Admin"},
  "completeness": {
    "is_complete": true,
    "missing_fields": [],
    "warnings": []
  },
  "comparison": {
    "field_changes": [],
    "stage_changes": [],
    "time_node_changes": []
  },
  "impact": {
    "as_of": "2026-07-10T08:00:00Z",
    "public_visibility_change": "replace_public_revision",
    "search_reindex_required": true,
    "recommendation_refresh_required": true,
    "affected_active_subscriptions": 12,
    "pending_reminders_to_supersede": 4,
    "future_reminders_to_create": 4,
    "schedule_change_messages_estimate": 3
  }
}
```

Differences are derived against immutable `base_revision_id`; the response also
reports the current public pointer so a stale baseline cannot be hidden. Draft
completeness and impact are live previews. Submission freezes the content and
server-derived node revisions, while engagement counts in impact remain an
`as_of` preview until the approval transaction.

Each `time_node_changes` item classifies `change_kind` and
`schedule_semantic`. `occurs_at` changes, controlled node-type changes, and node
addition/removal are schedule-semantic; stage, prominence, and description-only
changes are not. Message estimates include only affected active subscriptions
whose selected old or new node types intersect a schedule-semantic change.
Future-reminder estimates additionally require both the subscription reminder
switch and the student's current global `reminder_settings.enabled` switch.

For an initial revision, `base_revision_id` and
`current_published_revision_id` are both `null` until approval. Its comparison
is derived against an empty baseline, and its impact reports an initial public
visibility change with zero existing-subscription effects. Approval returns the
new `published_revision_id`; rejection or return leaves that pointer unchanged.
The response keeps the submitted comparison and impact evidence available after
the terminal decision instead of recomputing it from mutable edition state.

### `POST /admin/competition_series`

Create a赛事系列 with a canonical name. Requires `competition_editor`. The
response may include non-blocking similar-series suggestions, but similarity
never auto-merges identities; an exact controlled duplicate returns a
validation conflict.

Request:

```json
{
  "canonical_name": "全国大学生人工智能创新挑战赛"
}
```

### `POST /admin/competitions`

Create a赛事届次 and its initial draft revision atomically. The response returns
both identifiers; the initial revision has `base_revision_id = null`.
`series_id` and source-backed `edition_label` are required. Reusing an edition
identity already present in that series returns `409 conflict` with the existing
edition id rather than creating a duplicate.

Time-node datetime values follow the common date and time convention above.
Offsetless values are treated as `Asia/Shanghai`; responses are normalized to
UTC.

Structured draft fields may include time nodes and controlled tags:

```json
{
  "series_id": 5,
  "edition_label": "2026",
  "title": "全国大学生人工智能创新挑战赛",
  "source_name": "示例高校竞赛通知",
  "source_url": "https://example.edu/notices/ai-challenge-2026",
  "category": "创新创业",
  "organizer": "示例高校创新中心",
  "summary": "面向大学生的人工智能创新项目竞赛。",
  "eligibility": "在校本科生可报名。",
  "registration_applicability": "applicable",
  "participant_forms": ["individual", "team"],
  "team_size": "1-5",
  "major_scope": "selected",
  "grade_scope": "selected",
  "suitable_majors": ["软件工程"],
  "suitable_grades": ["大二"],
  "stages": [
    {
      "stage_key": "registration",
      "stage_type": "registration",
      "label": "报名阶段",
      "order": 1,
      "time_nodes": [
        {
          "logical_node_key": "registration-deadline",
          "node_type": "registration_deadline",
          "occurs_at": "2026-08-15T16:00:00Z",
          "description": "报名截止"
        }
      ]
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

`stages`, their `time_nodes`, and `tags` are revision-scoped. They are accepted
on initial edition creation and draft revision updates; top-level legacy
`time_nodes` are rejected as unknown fields. Node prominence defaults by
controlled type. A value different from that default requires
`prominence_override_reason`.

### `POST /admin/competitions/{id}/revisions`

Create a draft revision, copying the current public revision when one exists.
The current public revision remains selected while this draft is edited or
reviewed. P1 permits only one active `draft` or `pending_review` revision for an
edition. If one exists, return `409 active_revision_exists` with its revision id
instead of creating a parallel candidate. A replacement stores the exact copied
public revision as `base_revision_id`.

Successor creation is available only while the edition lifecycle is
`unpublished`, `published`, or `offline`. `cancelled`, `archived`, and `expired`
editions return `409 conflict`; those terminal lifecycle states cannot start a
new publication workflow.

If the latest candidate is `rejected` or `returned`, this endpoint copies that
immutable terminal candidate so editing can continue in a new draft. The new
draft still records the current public revision as `base_revision_id`; before
initial publication that value remains `null`.

The request requires the source-backed reason for preparing the replacement:

```json
{
  "reason": "Official notice postponed the registration deadline"
}
```

The response is the complete draft revision read model, including
`change_reason`, base/current public identifiers, comparison, completeness, and
live subscriber/reminder impact. Approval records the reviewer comment as the
reason on the single revision-scoped reconciliation audit event.

### `PATCH /admin/competition_revisions/{revision_id}`

Update one draft revision. A `pending_review` revision is content-frozen until
it is explicitly withdrawn to `draft`; decided revisions are immutable. Stage
and time-node editing is identity-aware and must not use blind list replacement
after reminder-dependent state exists.

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

Submission derives and freezes each time node's effective `node_revision`
against the immutable base revision and the edition's approved node history.
An unchanged node in the base keeps its revision, a changed node advances from
the approved historical maximum, a logical key never approved before starts at
one, and a previously approved key re-added after absence advances from its
historical maximum. Clients may submit logical keys and node facts but cannot
assign authoritative node-revision numbers.

### `POST /admin/competition_revisions/{revision_id}/withdraw`

Withdraw a `pending_review` revision back to editable `draft`. The endpoint
requires `competition_editor`, clears the prior submission actor and instant,
and appends a `competition_revision.withdraw` audit event. Decided revisions
remain immutable; withdrawing any state other than `pending_review` returns
`409 conflict`.

### `POST /admin/competition_revisions/{revision_id}/review`

Approve, reject, or return a competition.

A non-empty review comment is required so every decision retains review
context. The API rejects review when the current account submitted the target
revision, even if that account also has reviewer permission. Approval atomically
selects the revision for public reads; an existing approved revision remains
public until that decision.

Approval locks the edition and submitted revision and verifies that the
candidate's `base_revision_id` still equals the edition's
`published_revision_id`; initial publication requires both to be null. A
mismatch returns `409 stale_revision`, changes no public pointer, and appends no
terminal review decision. The reviewer must reload the comparison and an editor
must create a successor from the current public revision.

Approval is rejected with `409 conflict` when the edition is already
`cancelled`, `archived`, or `expired`, including when the candidate was
submitted before the terminal lifecycle transition. The candidate remains
pending and the public pointer and engagement state remain unchanged; a
reviewer may still reject or return it, or an editor may explicitly withdraw
it to draft.

Replacement approval locks and requires each affected subscriber's global
reminder setting before changing the public pointer. Missing student-owned
settings fail the transaction with `500 internal_server_error`; a disabled
global switch prevents new ordinary reminder plans without suppressing the
schedule-change message.

When the edition is `offline`, approval restores publication only if the
candidate was submitted after the current `lifecycle_changed_at` withdrawal
instant and differs from the selected public baseline. Otherwise the API
returns `409 offline_restoration_requires_corrected_revision`, keeps the public
pointer and lifecycle state unchanged, and appends no terminal review decision.

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

`archived` and `expired` require the current public revision to contain no
future time node. If any `occurs_at` is later than the decision instant, the API
returns `409 conflict` with the blocking node facts. A successful transition
retains favorites and subscriptions as historical relations and past calendar
nodes, cancels any stale pending reminders with a status-specific reason, and
creates no message. Cancellation or emergency offline remains the path when a
future schedule must stop and subscribers need a durable event message.

Emergency `offline` is immediate for an administrator with
`competition_maintainer`. Returning an offline edition to `published` is not
accepted through this endpoint; it requires approval of a corrected revision.

Request:

```json
{
  "status": "offline",
  "reason": "官方链接失效，待确认"
}
```

### `GET /admin/users`

List users for account governance. Requires `user_administrator`.

### `PATCH /admin/users/{id}`

Update another user's role, account status, or complete controlled capability
set. Requires `user_administrator`; a user administrator cannot target their own
account through this endpoint.

Request:

```json
{
  "role": "admin",
  "status": "active",
  "capabilities": ["competition_editor"],
  "reason": "Assign competition content maintenance"
}
```

At least one of `role`, `status`, or `capabilities` is required, together with a
non-empty reason. Student accounts must have an empty capability set; admin
capabilities come only from the controlled list. Every successful role, status,
or capability change atomically increments the target's `session_version`, so
existing sessions re-authorize on their next request.

The service rejects with `409 conflict` any change that would leave no active
admin holding `user_administrator`, including disabling or demoting that last
account or removing its capability. Successful changes write an audit event
with target id, reason, and allowlisted old/new role, status, and capability
codes; passwords, sessions, and full account identifiers are excluded.
Self-targeting returns `403 forbidden`; unknown roles, statuses, or capabilities
return the standard validation error without changing the target.

### `GET /admin/configs`

List system configs and base dictionaries. Recommendation rule sets use their
own versioned endpoints and cannot be updated through generic config APIs.

### `PATCH /admin/configs/{key}`

Update one config value.

### `GET /admin/recommendation_rule_sets`

List recommendation rule-set versions, states, submitter/reviewer facts, and the
single active version. Items include `cloned_from_rule_set_id`,
`cloned_from_version`, `base_rule_set_id`, `base_version`,
`active_rule_set_id`, `active_version`, `is_stale`, rules, and frozen or
deterministically generated `difference_snapshot` and `impact_summary` when
applicable. Every item also returns labeled governance evidence:
`created_by`, `submitted_by`, `reviewed_by`, `created_at`, `submitted_at`,
`decided_at`, `activated_at`, `retired_at`, `review_comment`, and
`terminal_review_status`. Pending candidates derive difference and impact from
their immutable base; terminal candidates read the frozen snapshots and actors
from their immutable `review_record`.

Requires `recommendation_editor` or `recommendation_reviewer`.

### `POST /admin/recommendation_rule_sets`

Create a draft by cloning an existing persisted rule-set version.

Request:

```json
{
  "source_rule_set_id": 7
}
```

The request accepts only `source_rule_set_id`. The client cannot provide
`version`, `base_rule_set_id`, `cloned_from_rule_set_id`, owner, status,
review/activation fields, or rule overrides. Clone sources are limited to the
current `active` version and immutable `rejected` or `returned` versions; `draft`,
`pending_review`, and `retired` sources return `409 conflict` in this thin
slice. The response returns the new `draft` id, integer version, creator,
clone provenance, governance base, current active version, stale state, and
rules. The reproducible v1 seed is not a hidden runtime clone template.

Requires `recommendation_editor`.

### `PATCH /admin/recommendation_rule_sets/{id}`

Update a draft rule set. Submitted, decided, active, and retired versions are
immutable. Only the draft owner with a current `recommendation_editor`
capability can modify a draft; another editor receives `403 forbidden`, and the
owner editing a non-draft snapshot receives `409 conflict`.

Rules use the controlled codes `major_match`, `grade_match`, `interest_match`,
`deadline_urgency`, and `general_fallback`. `weight` is an integer `1..100`.
Conditions are strict tagged unions tied to the rule code:
`{"operator": "overlap"}`, `{"operator": "within_days", "min_days": 0,
"max_days": N}`, or `{"operator": "always"}`. Reason templates are single-line
plain text, 1 to 200 Unicode code points after trimming, with only the
allowlisted placeholders for the rule code.

Requires `recommendation_editor` and draft ownership.

### `POST /admin/recommendation_rule_sets/{id}/preview`

Preview ordering and reasons against a synthetic profile and selected public
competition fixtures without persisting a recommendation. The endpoint computes
the rule-set version in the URL and never falls back to the current active
version or service constants.

Request:

```json
{
  "scenario": "personalized",
  "synthetic_profile": {
    "college": "计算机学院",
    "major": "软件工程",
    "grade": "大二",
    "interest_tags": ["人工智能"]
  },
  "competition_ids": [201, 305]
}
```

`scenario` is `personalized` or `general`. Personalized preview requires the
complete synthetic profile; general preview must omit it. The synthetic profile
accepts only `college`, `major`, `grade`, and 1 to 10 unique controlled
`interest_tags`; user ids, profile ids, arbitrary field paths, expressions, and
scripts are rejected. The same profile dictionary and college-major relation
used by real profile update/readiness validation govern these values; preview
never loads a real student's profile. `competition_ids` contains 1 to 20 unique public
competition fixture ids. Any duplicate, missing, or non-recommendable fixture
returns one `400 validation_error` with stable `duplicate`, `not_found`, and
`not_recommendable` id lists.

The response returns `rule_set_id`, integer `version`, `scenario`, fixture ids,
and deterministic results with server-assigned `position`, `competition_id`,
current-revision competition identity, `matched_rule_codes`, `reason_codes`,
and rendered plain-text reasons. Every recommendation fact—major and grade
scope/values, tags, registration deadline, and time nodes—comes only from the
immutable `CompetitionRevision` referenced by `competition.published_revision_id`.
Legacy flattened fields and non-current historical revisions are never fallback
facts. It does
not return internal score, probability, percentage, weight contribution, or
competition value rating. Preview is read-only: it writes no review record,
recommendation event, analytics row, production recommendation snapshot, or
business audit event.

Requires `recommendation_editor` or `recommendation_reviewer`.

### `POST /admin/recommendation_rule_sets/{id}/submit_review`

Freeze and submit a complete changed draft for independent review. The caller
must be the draft owner with a current `recommendation_editor` capability.
Submission requires enabled `general_fallback`, at least one enabled
personalized rule, valid controlled rules, and a normalized structural change
against the immutable `base_rule_set_id`; an unchanged candidate returns
`400 validation_error` with detail code `no_changes`.

Requires `recommendation_editor`.

### `POST /admin/recommendation_rule_sets/{id}/review`

Approve and activate, reject, or return a submitted rule set with a required
comment. The reviewer must differ from the submitter. Approval atomically
activates the candidate and retires the prior active version. Before approval,
the service verifies that the candidate `base_rule_set_id` still equals the
current active rule set; a stale base returns `409 stale_rule_set`, creates no
terminal review decision, does not activate the candidate, and does not retire
the active version. Successful `approve`, `reject`, or `return` creates one
immutable terminal `review_record` for `target_type =
"recommendation_rule_set"`, `target_id` as the candidate id, and
`target_revision` as the integer version.

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
- Seven-day and 30-day reason-attribution counts, explicitly non-additive and
  separate from overall recommendation totals.

P2 thin includes current published and pending-review counts, active favorite
and subscription counts, message delivery state counts, outbound click daily
counts, and recommendation recorded impression/click counts and ratio. It does
not expose named-user drill-down, real-time streaming, BI export, or claims of
unique people, recommendation quality, or registration conversion.

Recommendation totals and ratio read only item-level daily totals. Optional
reason breakdown reads the separate attribution aggregate; clients must not sum
reason rows into an overall count.

All review, audit, and statistics endpoints require `admin`; a student receives
`403 forbidden`. Stable pagination and filters are part of the contract.

## Internal Task Interfaces

Internal Celery task names:

- `competehub.reminders.dispatch_due`
- `competehub.reminders.requeue_failed`
- `competehub.messages.purge_expired`

Task behavior:

- Query due `pending` reminders and revalidate their current delivery
  eligibility before message creation.
- Create messages idempotently.
- Mark successful reminders as `sent`. An ineligible never-attempted `pending`
  plan becomes `cancelled`; a temporarily requeued attempted plan returns to
  `failed`, preserving `attempt_count`, `last_error_code`, and `failed_at`, and
  records the controlled retry-stop reason.
- On every attempted delivery, increment `attempt_count`. A transient failure
  sets `failed`, a sanitized controlled `last_error_code`, `failed_at`, and
  `next_attempt_at` from bounded retry configuration; permanent or exhausted
  failures set `next_attempt_at` to `null`.
- `requeue_failed` selects only due retryable `failed` rows with a non-null
  `next_attempt_at`, revalidates current delivery eligibility, and moves an
  eligible row back to `pending` while clearing `next_attempt_at` and any prior
  retry-stop reason. When eligibility has been revoked, the row remains
  `failed`; `attempt_count`, `last_error_code`, and `failed_at` remain intact,
  `next_attempt_at` is cleared, and `cancel_reason` records the controlled
  eligibility reason that stopped retry.
- Preference enablement and re-subscription never restore an attempted
  `failed` row. `dispatch_due` revalidates eligibility immediately before its
  idempotent message write and never sends directly from `failed`.

These are not public HTTP APIs.
