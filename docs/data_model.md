# CompeteHub Data Model

## Purpose

This document describes the initial domain data model for CompeteHub. It complements `docs/api_spec.md` and `docs/tech_spec.zh.md` by explaining tables, relationships, states, and ownership rules.

PostgreSQL is the system of record. Redis must not be the only storage location for any business fact described here.

## Entity Overview

```text
User
  |-- StudentProfile
  |-- Favorite
  |-- Subscription
  |-- ReminderSetting
  |-- Reminder
  |-- Message

Competition
  |-- CompetitionTimeNode
  |-- CompetitionTagLink -- CompetitionTag
  |-- Favorite
  |-- Subscription
  |-- Reminder

ReviewRecord
AuditLog
RecommendationRule
SystemConfig
```

## Core Tables

### `users`

Stores account identity and role.

Key fields:

- `id`
- `email`
- `phone`
- `student_no`
- `password_hash`
- `display_name`
- `role`
- `status`
- `created_at`
- `updated_at`

Constraints:

- `email`, `phone`, and `student_no` are independently unique when present.
- `role` must be one of the controlled role values.
- Disabled users cannot log in.

### `student_profiles`

Stores student-specific profile and recommendation preferences.

Key fields:

- `user_id`
- `college`
- `major`
- `grade`
- `interest_tags`
- `competition_experience`
- `goal_preferences`
- `blocked_tags`
- `default_remind_days`
- `message_enabled`

Rules:

- One profile belongs to one user.
- Student competition experience is self-entered unless used for certification or permission granting.
- Interest and blocked tags feed rule-based recommendation.

### `competitions`

Stores the main competition record.

Key fields:

- `title`
- `short_title`
- `category`
- `organizer`
- `host`
- `source_name`
- `source_url`
- `official_url`
- `attachment_url`
- `summary`
- `detail`
- `eligibility`
- `participant_form`
- `team_size`
- `suitable_majors`
- `suitable_grades`
- `value_notes`
- `status`
- `created_by_id`

Rules:

- Source name and source URL are required.
- Draft and pending competitions are not public.
- Value notes and tags are reference information only and do not replace official school recognition.

### `competition_time_nodes`

Stores milestone dates for competitions.

Key fields:

- `competition_id`
- `node_type`
- `starts_at`
- `due_at`
- `description`

Common `node_type` values:

- `registration_start`
- `registration_deadline`
- `submission_deadline`
- `competition_start`
- `defense_or_review`
- `result_announcement`

Rules:

- A competition can have multiple time nodes.
- Reminder generation uses future nodes and user subscription preferences.

### `competition_tags`

Stores controlled reference and fit tags.

Key fields:

- `code`
- `name`
- `tag_type`
- `description`

Common `tag_type` values:

- `level`
- `fit`
- `category`
- `recognition`
- `format`

### `competition_tag_links`

Connects competitions and tags.

Rules:

- Tags shown to users must be traceable to this relation or competition fields.
- Future college-level tags must not override system-level facts.

### `favorites`

Stores user favorites.

Key fields:

- `user_id`
- `competition_id`
- `is_active`

Rules:

- Favorite and subscription are separate concepts.
- Cancelling favorite should not cancel subscription.

### `subscriptions`

Stores user subscriptions and reminder preference overrides.

Key fields:

- `user_id`
- `competition_id`
- `status`
- `reminder_enabled`
- `remind_days`
- `node_types`

Rules:

- Active subscription can generate reminders.
- Cancelling subscription should cancel future pending reminders.
- Subscription can exist independently from favorite.

### `reminder_settings`

Stores default reminder settings per user.

Key fields:

- `user_id`
- `enabled`
- `default_remind_days`
- `node_types`

Rules:

- Subscription-level settings override user defaults.
- If reminders are disabled, no new pending reminders should be generated.

### `reminders`

Stores reminder delivery plan and status.

Key fields:

- `user_id`
- `competition_id`
- `time_node_id`
- `node_type`
- `due_at`
- `title`
- `body`
- `status`
- `sent_at`

Rules:

- PostgreSQL reminder rows are the source of truth for reminder delivery.
- Worker tasks must be idempotent.
- Competition cancellation, offline status, or time node deletion should cancel pending reminders.

### `messages`

Stores in-app messages visible to users.

Key fields:

- `user_id`
- `reminder_id`
- `title`
- `body`
- `is_read`
- `read_at`

Rules:

- Messages belong to one user.
- Users can only read or update their own messages.

### `review_records`

Stores review workflow state for competitions and future content.

Key fields:

- `target_type`
- `target_id`
- `submitted_by_id`
- `reviewed_by_id`
- `status`
- `comment`

Rules:

- Competition publish review must create or update a review record.
- Materials, certifications, and future forum content should reuse this review model.

### `audit_logs`

Stores administrator and system operation records.

Key fields:

- `actor_id`
- `action`
- `target_type`
- `target_id`
- `result`
- `detail`

Required audit actions:

- Competition create, update, submit review, approve, reject, return, offline, archive, cancel.
- Config changes.
- User role or account status changes.
- Content and certification review actions.

### `recommendation_rules`

Stores rule-based recommendation configuration.

Key fields:

- `code`
- `name`
- `weight`
- `conditions`
- `reason_template`
- `enabled`

Rules:

- Recommendation reasons must be generated from rules or explicit competition fields.
- Internal ranking score is not a public competition value score.

### `system_configs`

Stores dictionaries and configurable values.

Examples:

- Competition categories.
- Suitable majors.
- Suitable grades.
- Message templates.
- Default recommendation weights.

## State Models

### Competition Status

```text
draft
  -> pending_review
  -> published
  -> archived

pending_review
  -> rejected
  -> draft

published
  -> offline
  -> cancelled
  -> expired
```

Status meanings:

- `draft`: editable by admin, not public.
- `pending_review`: waiting for review, not public.
- `published`: visible to students.
- `rejected`: review failed, not public.
- `offline`: manually removed from public views.
- `archived`: historical record, not shown by default.
- `cancelled`: competition cancelled, visible only with clear status warning.
- `expired`: past relevant deadline or event, not shown as active.

### Reminder Status

```text
pending -> sent
pending -> cancelled
pending -> failed
sent -> read
failed -> sent
```

Rules:

- `pending` reminders are eligible for worker dispatch.
- `cancelled` reminders must not create messages.
- `failed` reminders may be retried if failure is transient.

### Review Status

```text
pending -> approved
pending -> rejected
pending -> returned
returned -> pending
```

Rules:

- `approved` can publish or unlock the target object.
- `rejected` keeps target non-public.
- `returned` means the submitter can revise and resubmit.

## Data Ownership

- Users own their profile, favorites, subscriptions, reminder settings, reminders, and messages.
- Administrators own competition publication workflow and configuration.
- The system owns reminder dispatch status and audit log creation.
- Public competition data is readable by anonymous users only after publication.

## Indexing Guidance

Initial indexes should prioritize:

- `competitions.status`
- `competitions.title`
- `competitions.short_title`
- `competitions.category`
- `competition_time_nodes.due_at`
- `favorites.user_id`
- `subscriptions.user_id`
- `reminders.status`
- `reminders.due_at`
- `messages.user_id`
- `messages.is_read`
- `audit_logs.action`
- `audit_logs.target_type`

Search can start with PostgreSQL filters and simple text matching. Add a dedicated search service only after the product requires better Chinese full-text search quality.

## Migration Rules

- Every schema change must include a migration.
- Enum changes must include a compatibility note when existing rows may be affected.
- Data backfills should be idempotent and documented in the migration or task note.
- Migrations should not depend on Redis.
