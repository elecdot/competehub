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

## Common Errors

| HTTP Status | Code | Meaning |
|---|---|---|
| 400 | `validation_error` | Request parameters or body are invalid. |
| 401 | `unauthorized` | Login is required. |
| 403 | `forbidden` | Current user does not have permission. |
| 404 | `not_found` | Resource does not exist or is not visible. |
| 409 | `conflict` | Request conflicts with current resource state. |
| 500 | `internal_server_error` | Unexpected server error. |

## Authentication

The API uses Flask Cookie Session authentication. Frontend code must not store
long-lived tokens in `localStorage`; authenticated requests rely on the browser
session cookie. State-changing APIs must use POST, PATCH, or DELETE rather than
GET.

Initial roles:

- `student`
- `admin`

Future candidate roles, not current formal product roles:

- `teacher`
- `organizer`

## Pagination And Filtering

Common list query parameters:

| Parameter | Type | Meaning |
|---|---|---|
| `page` | integer | Page number, starting from 1. |
| `page_size` | integer | Items per page. |
| `sort` | string | Sort key, such as `deadline`, `published_at`, `recommendation`, `popularity`. |

Competition filters:

| Parameter | Type | Meaning |
|---|---|---|
| `keyword` | string | Search in title, short title, organizer, category, and summary. |
| `category` | string | Competition category. |
| `major` | string | Suitable major. |
| `grade` | string | Suitable grade. |
| `tag` | string | Reference or fit tag. |
| `status` | string | Public-facing competition state. |
| `deadline_from` | string | ISO date lower bound. |
| `deadline_to` | string | ISO date upper bound. |
| `participant_form` | string | Individual or team competition form. |

## Auth APIs

### `POST /auth/register`

Register a student user. Public registration cannot create `admin` or other
privileged roles; those accounts must be provisioned through an administrative
or seed-data path.

Request:

```json
{
  "email": "student@example.edu",
  "phone": "13800000000",
  "student_no": "20260001",
  "password": "example-password",
  "display_name": "student a",
  "role": "student"
}
```

Response:

```json
{
  "data": {
    "id": 1,
    "display_name": "student a",
    "role": "student"
  },
  "error": null
}
```

### `POST /auth/login`

Login with account credential.

Request:

```json
{
  "account": "student@example.edu",
  "password": "example-password"
}
```

### `POST /auth/logout`

Logout current user.

### `GET /me`

Return current user and role.

Requires authentication.

## Profile APIs

### `GET /me/profile`

Return current student's profile.

Requires `student`.

### `PATCH /me/profile`

Update current student's profile.

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
  "message_enabled": true
}
```

## Competition APIs

### `GET /competitions`

Search, filter, sort, and paginate public competitions.

Visibility rules:

- Return `published` competitions by default.
- Do not return `draft`, `pending_review`, `rejected`, or `offline` competitions.
- `archived`, `cancelled`, and `expired` competitions require explicit filters if exposed.

Response item:

```json
{
  "id": 1,
  "title": "大学生创新创业竞赛",
  "category": "创新创业",
  "organizer": "示例主办方",
  "status": "published",
  "tags": ["校级推荐", "适合低年级"],
  "next_node": {
    "node_type": "registration_deadline",
    "due_at": "2026-06-01T16:00:00Z"
  },
  "is_favorited": false,
  "is_subscribed": false
}
```

### `GET /competitions/{id}`

Return competition detail.

Response data includes:

- Basic competition fields.
- Source name and source URL.
- Time nodes.
- Eligibility and material requirements.
- Suitable majors and grades.
- Reference tags and value notes.
- Official and attachment links.
- Current user's favorite/subscription state when authenticated.

### `POST /competitions/{id}/outbound_clicks`

Record official link, source link, or attachment link click.

Request:

```json
{
  "target_type": "official_url"
}
```

## Favorite And Subscription APIs

### `POST /competitions/{id}/favorite`

Favorite a competition.

Requires `student`.

### `DELETE /competitions/{id}/favorite`

Cancel favorite.

Requires `student`.

### `POST /competitions/{id}/subscribe`

Subscribe to a competition and create pending reminders.

Requires `student`.

Request:

```json
{
  "reminder_enabled": true,
  "remind_days": 3,
  "node_types": ["registration_deadline", "submission_deadline", "competition_start"]
}
```

### `DELETE /competitions/{id}/subscribe`

Cancel subscription and future pending reminders.

Requires `student`.

## Calendar And Message APIs

### `GET /me/calendar`

Return subscribed competition nodes.

Query parameters:

- `from`
- `to`
- `view`: `month`, `week`, or `list`

Requires `student`.

### `GET /me/messages`

Return in-app messages.

Requires authentication.

### `POST /me/messages/{id}/read`

Mark one message as read.

Requires authentication and message ownership.

## Recommendation APIs

### `GET /recommendations`

Return rule-based recommendations and reasons.

Requires optional authentication:

- Authenticated students receive profile-based recommendations.
- Anonymous users receive general recent or popular competitions.

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

## Admin APIs

Admin APIs require `admin`.

### `POST /admin/competitions`

Create a draft competition.

### `PATCH /admin/competitions/{id}`

Update editable fields on a `draft` or `rejected` competition. Published and
pending-review records must not be edited without returning to an editable
workflow state. Successful updates write `competition.update` audit evidence.

### `POST /admin/competitions/{id}/submit_review`

Submit competition for review.

### `POST /admin/competitions/{id}/review`

Approve, reject, or return a competition.

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

List system configs, recommendation rules, and base dictionaries.

### `PATCH /admin/configs/{key}`

Update one config value.

### `GET /admin/reviews`

List review records.

### `GET /admin/audit_logs`

List operation logs.

### `GET /admin/stats`

Return operational statistics.

Initial metrics:

- Search count.
- Favorite count.
- Subscription count.
- Official outbound click count.
- Recommendation click count.

## Internal Task Interfaces

Internal Celery task names:

- `competehub.reminders.dispatch_due`

Task behavior:

- Query due `pending` reminders.
- Create messages idempotently.
- Mark reminders as `sent`, `cancelled`, or `failed`.

These are not public HTTP APIs.
