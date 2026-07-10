# CompeteHub Data Model

## Purpose

This document describes the initial domain data model for CompeteHub. It complements `docs/api_spec.md` and `docs/tech_spec.zh.md` by explaining tables, relationships, states, and ownership rules.

PostgreSQL is the system of record. Redis must not be the only storage location for any business fact described here.

## Date And Time Convention

Datetime fields represent timezone-aware instants and are normalized to UTC for
storage and API output. User-facing dates, date-only filters, and offsetless
administrator datetime input use the `Asia/Shanghai` product calendar time
zone. See `docs/adr/0012-utc-instants-shanghai-calendar.md`.

## Entity Overview

```text
User
  |-- UserIdentity
  |     |-- IdentityVerificationChallenge
  |-- StudentProfile
  |-- Favorite
  |-- Subscription
  |-- ReminderSetting
  |-- Reminder
  |-- Message

CompetitionSeries
  |-- Competition (edition)
        |-- CompetitionRevision
        |     |-- CompetitionStage -- CompetitionTimeNode snapshot
        |-- CompetitionTagLink -- CompetitionTag
        |-- Favorite
        |-- Subscription
        |-- Reminder
        |-- OutboundClickEvent
        |-- RecommendationRequestItem

ReviewRecord
AuditLog
RecommendationRuleSet -- RecommendationRule
SystemConfig
OutboundClickDailyStat
RecommendationDailyStat
```

## Core Tables

### `users`

Stores account identity and role.

Key fields:

- `id`
- `password_hash`
- `session_version`
- `display_name`
- `role`
- `status`
- `created_at`
- `updated_at`

Constraints:

- `role` must be one of the controlled role values.
- `status` is `pending_activation`, `active`, or `disabled`.
- Pending accounts cannot authenticate or create personal product state.
- Disabled users cannot log in.
- `password_hash` contains an adaptive hash with its algorithm and explicit work
  parameters, never plaintext or reversible ciphertext. P1 prefers Argon2id;
  an OWASP-baseline scrypt configuration is the permitted fallback.
- New passwords contain 15 to 128 Unicode code points after NFC normalization,
  are checked against a local weak-password blocklist, and are never silently
  truncated.
- `session_version` is a monotonically increasing integer copied into signed
  cookie sessions. Account disablement, confirmed credential compromise, or an
  explicit terminate-all action increments it atomically.
- A protected request accepts a session only when its version matches the
  current account and the account is active; deleting a client cookie is not the
  revocation mechanism for other devices.

### `user_identities`

Stores typed identifiers bound to user accounts.

Key fields:

- `id`
- `user_id`
- `identity_type`: `student_no`, `email`, or `phone`
- `normalized_value`
- `display_value`
- `verification_status`: `pending` or `verified`
- `verification_method`: for example `email_code`, `institution_roster`, or
  `institution_sso`
- `verified_at`

Constraints:

- `(identity_type, normalized_value)` is unique inside the single deployment.
- Login always supplies `identity_type`; cross-type matching is forbidden.
- Email, phone, and student number use their documented normalization rules
  before uniqueness checks.
- Identity type support is separate from public registration availability. P1
  public registration can create only pending email identities when a real
  sender is configured; phone registration is not available, and student
  numbers come from an institution-managed path.

### `identity_verification_challenges`

Stores short-lived challenges for account identity verification.

Key fields:

- `id`
- `user_identity_id`
- `secret_hash`
- `expires_at`
- `attempt_count`
- `consumed_at`
- `created_at`

Rules:

- Plain verification codes are never stored, returned by the API, or written to
  production logs.
- A challenge is single-use, expires after a configured short lifetime, and is
  rejected after the attempt limit.
- Successful verification and account activation occur atomically and do not
  create an authenticated session.
- Registration and resend responses do not reveal whether an identity exists or
  is already verified.

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

Rules:

- One profile belongs to one user.
- Student competition experience is self-entered unless used for certification or permission granting.
- Interest and blocked tags feed rule-based recommendation.
- Account activation creates an editable profile that may remain incomplete;
  profile completion does not gate search, detail, favorite, subscription, or
  reminder behavior.
- `college`, `major`, `grade`, and `interest_tags` reference deployment-controlled
  dictionaries. The major must belong to the selected college, and interest
  tags contain 1 to 10 unique values when the profile is recommendation-ready.
- `profile_status` and `missing_fields` are derived at read/recommendation time.
  A profile is `recommendation_ready` only when college, major, grade, and at
  least one interest tag are valid; no completion boolean is persisted.
- Competition experience, goal preferences, blocked tags, and account display
  name are optional and do not affect readiness.
- Global reminder defaults are not duplicated in this table; they belong to
  `reminder_settings` and may be composed into a preference API response.

### `competition_series`

Stores the stable cross-edition identity of a赛事系列.

Key fields:

- `id`
- `canonical_name`
- `created_at`
- `updated_at`

Rules:

- Every赛事届次 belongs to one赛事系列.
- A one-off赛事 has a series with one届次.
- Similar title or organizer facts can suggest a relation but cannot
  automatically merge series or editions.

### `competitions`

Stores one赛事届次: a concrete annual or participation cycle within a赛事系列.

Key fields:

- `id`
- `series_id`
- `edition_label`
- `lifecycle_status`
- `published_revision_id`
- `created_by_id`

Rules:

- A new annual or distinct participation cycle creates a new row; prior届次 are
  not overwritten.
- Public content resolves through one approved immutable revision.
- Draft and pending replacement revisions do not replace the public revision.
- Emergency offline requires permission, reason, and audit evidence; restoration
  requires independent approval of a corrected revision.

### `competition_revisions`

Stores one numbered content version of a赛事届次.

Key fields:

- `id`
- `competition_id`
- `revision_number`
- `revision_status`
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
- `registration_applicability`: `applicable`, `not_applicable`, or `unknown`
- `participant_forms`
- `team_size`
- `major_scope`: `all`, `selected`, or `unknown`
- `grade_scope`: `all`, `selected`, or `unknown`
- `suitable_majors`
- `suitable_grades`
- `value_notes`
- `created_by_id`
- `submitted_by_id`
- `created_at`
- `published_at`

Rules:

- Source name and source URL are required.
- Publication requires series identity, edition label, title, category,
  organizer, summary, eligibility, at least one participant form, explicit major
  and grade scope, at least one stage, and at least one primary core time node.
- `participant_forms` may contain `individual`, `team`, or both. Team entry
  requires explicit team-size facts.
- `selected` major or grade scope requires a non-empty controlled-value list;
  `all` and `unknown` are explicit and are never inferred from an empty list.
- Source, official, and attachment URLs accept only valid HTTP(S) URLs when
  present.
- Draft revisions are editable. Submitted, approved, rejected, and returned
  snapshots are immutable; continued work creates a successor draft.
- Approval atomically selects the revision as `published_revision_id` and
  refreshes public search, recommendation, and detail reads.
- `published_at` records the approval time at which a revision became public and
  supplies deterministic discovery tie-breaking.
- Stages and time-node snapshots are scoped to the content revision while stable
  logical node identity links schedule revisions for reminder reconciliation.
- `registration_status` is computed from current public registration stages and
  nodes. It is not persisted. `not_applicable` requires explicit
  `registration_applicability`; missing nodes alone yield `unknown`.
- Value notes and tags are reference information only and do not replace official school recognition.

### `competition_stages`

Stores an ordered, labeled phase or round within one赛事届次.

Key fields:

- `id`
- `competition_revision_id`
- `logical_stage_key`
- `stage_type`
- `label`
- `sort_order`

Rules:

- Stage labels distinguish multiple rounds with the same stage type.
- Known start/deadline and start/end pairs belong to the same stage.
- Stage ordering is stable and explicit; clients do not infer it from labels.

### `competition_time_nodes`

Stores milestone dates for competitions.

Key fields:

- `competition_revision_id`
- `logical_node_key`
- `stage_id`
- `node_type`
- `revision`
- `prominence`: `primary` or `secondary`
- `occurs_at`
- `description`

Common `node_type` values:

- `registration_start`
- `registration_deadline`
- `submission_deadline`
- `competition_start`
- `competition_end`
- `defense_or_review`
- `result_announcement`
- `other`

Rules:

- A competition can have multiple time nodes.
- Every node belongs to one ordered赛事阶段.
- Registration deadline, submission deadline, and competition start default to
  `primary`; an administrator override requires an audited reason.
- Registration start/deadline and competition start/end pairs in one stage must
  be chronologically ordered. One-sided source facts are allowed with an
  explicit completeness warning.
- A node keeps the same identity across official schedule corrections; each
  accepted correction increments its revision and retains old/new facts in
  audit evidence.
- Each node has exactly one timezone-aware `occurs_at` instant. A source period
  is represented by separate start and end milestone nodes.
- Current P1 publication requires at least one recognized time node with a valid
  `occurs_at`; absence of nodes is not a modeled "to be announced"
  state.
- `other` requires a user-facing description and does not satisfy the core-node
  publication gate or participate in default filtering and reminders.
- Node types are a controlled application/API vocabulary. Behavior-bearing
  additions require coordinated schema, documentation, and test changes.
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

### `outbound_click_events`

Stores privacy-minimized raw activations of current public external links.

Key fields:

- `id`
- `competition_id`
- `competition_revision_id`
- `target_type`: `source_url`, `official_url`, or `attachment_url`
- `source_surface`: `competition_list`, `competition_detail`, or
  `recommendation`
- `actor_kind`: `authenticated` or `anonymous`
- `occurred_at`

Rules:

- The server resolves the target from the currently viewable public revision;
  the event does not store a client-provided URL.
- Events do not contain user id, account identity, IP address, User-Agent, or a
  cross-day visitor identifier. Request-source values used for rate limiting are
  ephemeral and are not copied into analytics rows.
- Each accepted activation is a click count, not a unique person or completed
  registration. Best-effort delivery may undercount.
- Raw events expire after 90 days and are aggregated before deletion.

### `outbound_click_daily_stats`

Stores durable aggregate counts by `Asia/Shanghai` product date.

Key fields:

- `stat_date`
- `competition_id`
- `target_type`
- `source_surface`
- `actor_kind`
- `click_count`

Rules:

- The dimension tuple is unique and aggregation is idempotent.
- Counts are labeled as recorded outbound clicks, not people or registration
  conversion.

### `recommendation_request_items`

Stores a privacy-minimized 90-day snapshot of each item returned in one
recommendation response and its optional rendered/clicked timestamps.

Key fields:

- `id`
- `recommendation_request_id`: opaque random response identifier
- `competition_id`
- `position`
- `recommendation_mode`: `personalized` or `general`
- `rule_set_id`: nullable for general fallback
- `reason_codes`
- `actor_kind`: `authenticated` or `anonymous`
- `returned_at`
- `impressed_at`
- `clicked_at`
- `retained_until`

Rules:

- `(recommendation_request_id, competition_id)` is unique. Position, mode,
  rule-set version, reason codes, and actor kind come from server recommendation
  output and cannot be supplied or changed by event clients.
- Impression and click are each recorded at most once per request item. A click
  requires an impression; repeated event delivery is idempotent.
- API return alone is not an impression. Frontend rendering sends the
  best-effort impression, while detail navigation sends the non-blocking click.
- Rows do not contain user id, account identity, profile fields, IP address,
  User-Agent, or a cross-request/cross-day visitor identifier and do not drive
  automatic personal tuning.
- Raw request-item rows expire after 90 days and are aggregated before deletion.

### `recommendation_daily_stats`

Stores durable `Asia/Shanghai` daily recorded impression and click aggregates.

Key fields:

- `stat_date`
- `competition_id`
- `rule_set_version`: nullable for general mode
- `recommendation_mode`
- `position`
- `reason_code`
- `actor_kind`
- `impression_count`
- `click_count`

Rules:

- Aggregation is idempotent for the dimension tuple.
- Click-through ratio is derived as recorded clicks divided by recorded
  impressions. It is not an independent-user, recommendation-quality, or
  registration-conversion measure.

### `favorites`

Stores user favorites.

Key fields:

- `user_id`
- `competition_id`
- `is_active`

Rules:

- Favorite and subscription are separate concepts.
- Cancelling favorite should not cancel subscription.
- A favorite targets one赛事届次 and is not copied to a later届次 in the same
  赛事系列.

### `subscriptions`

Stores user subscriptions and reminder preference overrides.

Key fields:

- `user_id`
- `competition_id`
- `status`
- `reminder_enabled`
- `remind_days`
- `node_types`
- `reminder_confirmed_at`

Rules:

- Active subscription can generate reminders.
- Cancelling subscription should cancel future pending reminders.
- Subscription can exist independently from favorite.
- Favorite creation never creates a subscription or reminder plan.
- `reminder_enabled` is an explicitly confirmed per-subscription choice. When
  enabled, `remind_days` is one integer from 0 to 30 and `node_types` is a
  non-empty controlled set; P1 has one ordinary plan per selected time node.
- Reminder-disabled subscriptions remain in follow lists and calendars.
- Calendar projection reads active subscriptions only, never favorites, and
  includes selected nodes independently of reminder-plan state.
- Calendar grouping uses `Asia/Shanghai`; current stage, prominence, and pair
  metadata come from the current public revision rather than duplicated calendar
  rows.
- A subscription targets one赛事届次 and never renews automatically for a later
  届次. Future赛事系列 following requires a separate relation.

### `reminder_settings`

Stores default reminder settings per user.

Key fields:

- `user_id`
- `enabled`
- `default_remind_days`
- `node_types`

Rules:

- This table is the single source of truth for global reminder settings; profile
  rows do not duplicate them.
- New settings default to enabled, three days, and the controlled primary core
  types `registration_deadline`, `submission_deadline`, and
  `competition_start`. These values prefill a confirmation and are not consent.
- Subscription-level settings are copied from the student's confirmed choice
  and may differ from later global defaults.
- Disabling global reminders cancels pending plans with a global-disabled
  reason while preserving subscriptions and calendar nodes. Re-enabling
  reconciles only future eligible plans.

### `reminders`

Stores reminder delivery plan and status.

Key fields:

- `user_id`
- `competition_id`
- `time_node_id`
- `time_node_revision`
- `node_type`
- `due_at`
- `title`
- `body`
- `status`
- `cancel_reason`
- `sent_at`

Rules:

- PostgreSQL reminder rows are the source of truth for reminder delivery.
- Worker tasks must be idempotent.
- Competition cancellation, offline status, or time node deletion should cancel pending reminders.
- A time-node revision cancels pending reminders for the prior revision with a
  supersession reason and creates only future plans for the current revision.
- Sent reminders are immutable and are never rewritten after a schedule change.
- Trigger instants already in the past are not backfilled as immediate ordinary
  reminders after subscription, re-enablement, or reconciliation.

### `messages`

Stores in-app messages visible to users.

Key fields:

- `id`
- `user_id`
- `reminder_id`: nullable for non-reminder events
- `competition_id`
- `message_type`: `reminder_due`, `competition_time_changed`,
  `competition_cancelled`, or `competition_offline`
- `idempotency_key`
- `title_snapshot`
- `body_snapshot`
- `target_snapshot`
- `event_occurred_at`
- `is_read`
- `read_at`
- `created_at`
- `retained_until`

Rules:

- Messages belong to one user.
- Users can only read or update their own messages.
- `(user_id, idempotency_key)` is unique so repeated workers and domain-event
  handlers cannot create duplicate messages.
- Message type and content snapshots are immutable after creation. Only
  `is_read` and `read_at` change through one-message or read-all actions.
- A target snapshot remains readable if the current competition is unavailable;
  APIs must not expose a public target URL when access is no longer allowed.
- Messages are retained for 365 days regardless of read state. P1 has no
  per-message deletion; an expiry task purges records after `retained_until`,
  and account deletion follows the account-data cleanup policy.
- User-triggered unsubscription or reminder disablement does not create a
  message. Competition cancellation or emergency offline creates one idempotent
  event message for each active subscriber before future plans are stopped.
- A time-node revision for a published赛事届次 creates at most one time-change
  message per active subscriber and revision. This message is not an ordinary
  due reminder.

### `review_records`

Stores immutable review decisions for competition revisions,
recommendation-rule-set versions, and future governed content.

Key fields:

- `target_type`
- `target_id`
- `target_revision`
- `submitted_by_id`
- `submitted_at`
- `reviewed_by_id`
- `status`
- `comment`
- `difference_snapshot`
- `impact_summary`
- `decided_at`

Rules:

- A decision appends one record for the exact submitted target snapshot. The
  pending queue is derived from target workflow state rather than by mutating a
  prior decision.
- Competition publication and recommendation-rule activation decisions must
  create a record. Rejection, return, correction, and resubmission preserve the
  earlier record and use a new target revision or version.
- The reviewer of a target snapshot must differ from its submitter.
- Decision fields, differences, impact, and comments are immutable after
  creation. There is no product update or delete operation for review records.
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
- `occurred_at`

Required audit actions:

- Competition create, update, submit review, approve, reject, return, offline, archive, cancel.
- Config changes.
- Recommendation rule-set submit, review, activation, and retirement.
- User role or account status changes.
- Content and certification review actions.

Rules:

- Audit events are append-only and have no product update or delete operation.
- `detail` uses an action-specific allowlist. It must not contain passwords,
  verification codes, session values, full account identifiers, profile
  content, or raw analytics identifiers.
- System actions use a controlled system actor instead of inventing an
  administrator identity.

### Governance statistics read model

The P2 governance statistics API is a read model, not a mutable statistics
record. Current published and pending-review counts, active favorites and
subscriptions, and message delivery states are derived from their owning
tables. Seven-day and 30-day outbound and recommendation metrics read the
privacy-minimized daily aggregate tables.

Each returned metric has a stable metric code, value, definition, window,
`as_of`, `Asia/Shanghai` time zone, and any best-effort caveat. Unsupported
dimensions are rejected rather than approximated. The read model exposes no
named-user drill-down.

### `recommendation_rule_sets`

Stores immutable versions of recommendation behavior.

Key fields:

- `id`
- `version`
- `status`: `draft`, `pending_review`, `active`, `rejected`, `returned`, or
  `retired`
- `created_by_id`
- `submitted_by_id`
- `reviewed_by_id`
- `review_comment`
- `submitted_at`
- `activated_at`
- `retired_at`

Rules:

- Exactly one rule-set version is active. Activating an approved candidate and
  retiring the prior active version occur atomically.
- Drafts are editable. Submitted, decided, active, and retired snapshots are
  immutable; continued work clones a successor draft.
- The reviewer differs from the submitter. Submission, review, activation, and
  retirement write audit evidence with version and differences.
- A reproducible seed creates the initial active version. Production
  personalization does not use hidden service constants.

### `recommendation_rules`

Stores controlled rules belonging to one recommendation rule-set version.

Key fields:

- `id`
- `rule_set_id`
- `code`
- `name`
- `weight`: bounded integer
- `conditions`: schema-validated structured JSON
- `reason_template`
- `enabled`

Rules:

- `(rule_set_id, code)` is unique.
- Rule codes are controlled, initially covering major match, grade match,
  interest match, deadline urgency, and general fallback. Conditions cannot
  contain executable expressions or arbitrary scripts.
- Recommendation reasons must be generated from active rules or explicit
  competition fallback facts. The response identifies the active rule-set
  version.
- Internal ranking score is not a public competition value score.
- Preview uses a synthetic profile and selected public competition fixtures; it
  does not read an arbitrary real student's profile or persist recommendations.

### `system_configs`

Stores dictionaries and configurable values.

Examples:

- Host institution name and code.
- Competition categories.
- Suitable majors.
- Suitable grades.
- Message templates.

## State Models

### Competition Lifecycle Status

```text
unpublished -> published
published -> offline | archived | cancelled | expired
offline -> published  # only through corrected revision approval
```

Draft, pending, rejected, and returned are revision states rather than public
lifecycle states. Post-publication maintenance requires an audit reason.

Status meanings:

- `published`: visible to students.
- `unpublished`: no approved public revision exists.
- `offline`: manually removed from public views.
- `archived`: historical record, not shown by default.
- `cancelled`: competition cancelled, visible only with clear status warning.
- `expired`: past relevant deadline or event, not shown as active.

Public visibility policy:

- `published` records are available in default public discovery and detail.
- `archived`, `cancelled`, and `expired` records are excluded from default
  discovery and recommendation but retain public detail with a status warning.
- `offline` and `unpublished` records have no public detail.

### Competition Revision Status

```text
draft -> pending_review
pending_review -> approved | rejected | returned
rejected | returned -> successor draft
```

Rules:

- Draft content may change until submission.
- Submitted and decided snapshots are immutable.
- Approved initial revisions publish an unpublished edition; approved
  replacements atomically switch the public revision.

### Reminder Status

```text
pending -> sent
pending -> cancelled
pending -> failed
failed -> sent
```

Rules:

- `pending` reminders are eligible for worker dispatch.
- `cancelled` reminders must not create messages.
- `failed` reminders may be retried if failure is transient.
- `sent` is terminal and points to the immutable delivered message; read state
  does not belong to the reminder.

### Message Read Status

```text
unread -> read
```

Rules:

- Reading one message or all messages is idempotent.
- Read state never changes message content or its 365-day retention deadline.

### Recommendation Rule-Set Status

```text
draft -> pending_review
pending_review -> active | rejected | returned
active -> retired  # atomically when a successor becomes active
rejected | returned -> successor draft
```

Rules:

- Submission freezes the candidate snapshot.
- The submitter cannot review the same version.
- Approval activates the candidate and retires the prior active version in one
  transaction.
- Rejected, returned, active, and retired versions are retained for audit and
  cannot be edited in place.

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
- `competition_time_nodes.occurs_at`
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
