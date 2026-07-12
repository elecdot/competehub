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
  |           |-- VerificationDeliveryOutbox
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
        |     |-- CompetitionTagLink -- CompetitionTag
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
RecommendationReasonDailyStat
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
- `capabilities`
- `status`
- `created_at`
- `updated_at`

Constraints:

- `role` must be one of the controlled role values.
- Student capabilities are empty. Administrator capabilities are a controlled
  set containing zero or more of `competition_editor`,
  `competition_reviewer`, `competition_maintainer`, `recommendation_editor`,
  `recommendation_reviewer`, and `user_administrator`; they are permissions
  within the `admin` role, not additional formal roles.
- `competition_maintainer` authorizes post-publication cancellation, expiry,
  archival, and emergency offline but not revision editing or review.
- `user_administrator` authorizes listing governed accounts and changing
  another account's role, status, or controlled capabilities. Self-targeting is
  rejected, and a transaction cannot remove, disable, or demote the last active
  holder of this capability.
- `status` is `pending_activation`, `active`, or `disabled`.
- Pending accounts cannot authenticate or create personal product state.
- Disabled users cannot log in.
- A role, status, or capability change increments `session_version` in the same
  transaction and writes allowlisted old/new codes plus a non-empty reason to
  the audit log.
- `password_hash` contains an adaptive hash with its algorithm and explicit work
  parameters, never plaintext or reversible ciphertext. New and upgraded hashes
  use Argon2id with the repository's current explicit parameters.
- Historical adaptive hashes remain verifiable during migration. A successful
  login upgrades a non-Argon2id hash, or an Argon2id hash whose parameters are
  stale, in the same login transaction; a failed login never changes the hash.
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
- Resend consumes every older unconsumed challenge for the identity. Successful
  verification locks the pending identity, consumes all of its outstanding
  challenges, and activates only a `pending_activation` account in one
  transaction; a code can never reactivate a disabled account.
- Successful verification and account activation occur atomically and do not
  create an authenticated session.
- Registration and resend responses do not reveal whether an identity exists or
  is already verified.

### `verification_delivery_outbox`

Stores transactional work for asynchronous verification-email delivery.

Key fields:

- `id`
- `challenge_id`
- `delivery_nonce`
- `attempt_count`
- `available_at`
- `delivered_at`
- `discarded_at`
- `last_error`
- `created_at`
- `updated_at`

Rules:

- Challenge creation and its outbox row commit atomically. HTTP registration and
  resend requests never contact SMTP directly.
- `delivery_nonce` is random input to a keyed derivation of the six-digit code;
  the plaintext code is never persisted. The nonce is cleared after delivery or
  discard and cannot produce the code without the application secret.
- A worker delivers only an unconsumed, unexpired challenge. It discards stale
  work, retries transient failures with bounded backoff, and never logs the code.
- Unknown or ineligible register/resend requests perform equivalent password or
  challenge hashing but do not create durable outbox work.

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
- `base_revision_id`: nullable FK to the public revision copied as the editing
  and review baseline
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
- `updated_at`
- `submitted_at`
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
- P1 permits at most one active workflow revision (`draft` or `pending_review`)
  per赛事届次. A partial unique constraint on `competition_id` for those states
  enforces the boundary; creating another returns the existing active revision
  rather than allowing parallel replacements.
- An initial unpublished revision has `base_revision_id = null`. A replacement
  stores the exact `published_revision_id` it copied. Draft and review read
  models compare against that baseline and separately expose the current public
  revision so stale state is visible.
- Submission freezes server-derived node revisions against `base_revision_id`.
  Unchanged logical nodes keep their prior `node_revision`; changed nodes
  increment it and new nodes start at one. Clients never assign this value.
- Approval locks the edition and submitted revision, verifies that
  `base_revision_id` still equals `published_revision_id` (or both are null for
  initial publication), then atomically selects the revision and refreshes
  public search, recommendation, and detail reads. A mismatch returns
  `409 stale_revision` and creates no terminal review decision.
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

- `id`: immutable snapshot-row identifier
- `competition_revision_id`
- `logical_node_key`
- `stage_id`
- `node_type`
- `node_revision`
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
- `id` identifies exactly one immutable node snapshot in one
  `competition_revision`; it is never reused as the cross-revision node
  identity. `competition_revision_id` is a foreign key to
  `competition_revisions`, and `stage_id` must reference a stage in that same
  revision.
- `(competition_revision_id, logical_node_key)` is unique. The opaque
  `logical_node_key` is stable within one赛事届次 across official schedule
  corrections, is never reused for a different milestone, and is interpreted
  only together with the edition reached through `competition_revision_id`.
- `node_revision` is a positive integer that increases only when an approved
  successor changes behavior-bearing facts for the same edition and
  `logical_node_key` (type, stage, occurrence, prominence, or description).
  An unchanged node copied into another competition revision receives a new
  snapshot `id` but keeps its node revision. Old snapshots remain immutable,
  and audit evidence retains old/new facts and the reason.
- Revision comparison classifies `occurs_at` change, controlled `node_type`
  change, and node addition or removal as schedule-semantic changes. Stage,
  prominence, and description-only changes are presentation/context changes;
  they can increment node revision but do not claim the schedule moved.
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

Connects immutable competition revisions and controlled tags.

Key fields:

- `competition_revision_id`
- `tag_id`

Rules:

- `(competition_revision_id, tag_id)` is unique.
- Public list, detail, recommendation, and outbound-link context resolve only
  tag links belonging to the selected `published_revision_id`.
- Editing tags on a draft or pending candidate cannot change current public
  output; approval exposes the candidate's tag snapshot with the rest of the
  revision.
- Tags shown to users must be traceable to this relation or revision fields.
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

Stores durable item-level `Asia/Shanghai` daily recorded impression and click
totals. Each request item contributes at most once to each event total,
regardless of how many reasons it displays.

Key fields:

- `stat_date`
- `competition_id`
- `rule_set_version`: nullable for general mode
- `recommendation_mode`
- `position`
- `actor_kind`
- `impression_count`
- `click_count`

Rules:

- `stat_date` is event-time based: an impression increments the Shanghai date
  of `impressed_at`, and a click increments the Shanghai date of `clicked_at`.
  One request item may therefore increment impression and click rows on
  different dates.
- Aggregation is idempotent for the dimension tuple and counts one request item
  at most once per event type; it never expands an item by `reason_codes`.
- A windowed interaction ratio is derived as clicks whose click event falls in
  the window divided by impressions whose impression event falls in the same
  window. It is an event-period ratio, not an impression-cohort conversion,
  independent-user, recommendation-quality, or registration-conversion
  measure.
- Overall impression, click, and ratio metrics in `/admin/stats` come only from
  this item-level table.

### `recommendation_reason_daily_stats`

Stores reason-level attribution for the same recorded recommendation events.
One request item contributes at most once to each distinct reason code it
displayed, so these rows explain which reasons accompanied interactions but are
not additive item totals.

Key fields:

- `stat_date`
- `competition_id`
- `rule_set_version`: nullable for general mode
- `recommendation_mode`
- `position`
- `reason_code`
- `actor_kind`
- `attributed_impression_count`
- `attributed_click_count`

Rules:

- Impression attribution uses the Shanghai date of `impressed_at`; click
  attribution uses the Shanghai date of `clicked_at`, matching item totals.
- The dimension tuple is unique and aggregation is idempotent after reason-code
  deduplication within each request item.
- A multi-reason item may increment multiple reason rows. Summing reason rows
  does not produce overall impressions or clicks and must never be presented as
  such.
- Reason-level values are labeled attribution counts, not causal effects,
  unique users, recommendation quality, or registration conversion.

### `favorites`

Stores user favorites.

Key fields:

- `user_id`
- `competition_id`
- `is_active`

Rules:

- Favorite and subscription are separate concepts.
- Cancelling favorite should not cancel subscription.
- New favorites may target `published`, `cancelled`, `archived`, or `expired`
  editions because all retain public detail. `offline` and never-published
  editions reject favorite creation.
- An owner can deactivate an existing favorite regardless of current edition
  lifecycle or public-detail availability.
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
- Only a currently `published` edition accepts a new subscription. Existing
  subscriptions remain owned relations after the edition becomes `cancelled`,
  `archived`, `expired`, or `offline`, but those lifecycle states are not
  eligible for new plans or setting changes.
- Cancelling subscription should cancel future pending reminders.
- An owner can cancel an existing subscription regardless of current edition
  lifecycle or public-detail availability.
- Subscription can exist independently from favorite.
- Favorite creation never creates a subscription or reminder plan.
- `reminder_enabled` is an explicitly confirmed per-subscription choice.
  `remind_days` is always one integer from 0 to 30 and `node_types` is always a
  non-empty controlled set, regardless of reminder state. When enabled, P1 has
  one ordinary plan per selected time node; when disabled, no plan is created.
- Reminder-disabled subscriptions retain their confirmed offset and node
  selection and remain in follow lists and calendars.
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
- `time_node_snapshot_id`
- `logical_node_key`
- `time_node_revision`
- `node_type`
- `due_at`
- `title`
- `body`
- `status`
- `cancel_reason`
- `attempt_count`
- `next_attempt_at`
- `last_error_code`
- `failed_at`
- `sent_at`

Rules:

- PostgreSQL reminder rows are the source of truth for reminder delivery.
- `time_node_snapshot_id` is a foreign key to the exact immutable
  `competition_time_nodes.id` snapshot used to schedule the reminder.
  `logical_node_key` and `time_node_revision` are copied into the plan for
  reconciliation and idempotency; they do not change the FK target into a
  cross-revision identity.
- `(user_id, competition_id, logical_node_key, time_node_revision)` is unique
  for the P1 ordinary reminder plan. This permits the same logical key in
  another edition without duplicate delivery inside one node revision.
- Worker tasks must be idempotent.
- Competition cancellation, offline status, or time node deletion should cancel pending reminders.
- When a changed node receives a new `node_revision`, reconciliation cancels
  its prior pending plan as superseded and creates only a still-future plan from
  the new snapshot. If a node is copied unchanged and keeps its node revision,
  reconciliation updates the pending plan's snapshot FK and title/body in place
  so current public content is used without changing due time or plan identity.
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
- Approval creates at most one consolidated `competition_time_changed` message
  per active subscriber and approved competition revision, and only when the
  revision contains a schedule-semantic change affecting one of that
  subscription's selected old or new node types. The idempotency key uses the
  approved revision event rather than every node revision.
- `occurs_at` change, selected node addition/removal, and selected controlled
  node-type change are message-worthy. Stage, prominence, description, title,
  or other presentation-only corrections refresh calendar/current pending
  reminder content but do not create a misleading reschedule message.

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
- User role, account status, or capability changes.
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
- `cloned_from_rule_set_id`: nullable FK to the direct content-copy source
- `base_rule_set_id`: nullable FK to the immutable active governance baseline
- `review_comment`
- `submitted_at`
- `decided_at`
- `activated_at`
- `retired_at`

Rules:

- `version` is a positive integer unique within the current single-deployment
  institution scope. The reproducible seed creates `version = 1` once and must
  not overwrite a conflicting existing v1 snapshot. Runtime draft creation
  allocates the next version server-side in the same transaction as clone data.
- Exactly one rule-set version is active. A partial unique constraint on
  `status = active` protects the invariant. Activating an approved candidate
  and retiring the prior active version occur atomically.
- Drafts are editable only by `created_by_id` while that account still has
  `recommendation_editor`. Other editors may read or preview but cannot modify,
  submit, transfer, or take over the draft. Submitted, decided, active, and
  retired snapshots are immutable; continued work clones a successor draft.
- Creating a draft deep-copies rule rows from an allowed persisted source:
  current `active`, immutable `rejected`, or immutable `returned`. `draft`,
  `pending_review`, and `retired` sources are outside the #36 thin slice. The
  new draft stores `cloned_from_rule_set_id` as the direct copy source.
- `base_rule_set_id` is the immutable active governance baseline used for
  structural difference and stale approval checks. A normal draft cloned from
  the current active has both lineage fields pointing to active; a successor
  cloned from `rejected` or `returned` copies content from that source but
  inherits the source's original `base_rule_set_id`.
- Approval verifies that `base_rule_set_id` still equals the current active
  rule set. A stale candidate remains pending and returns `409 stale_rule_set`
  without a terminal review decision.
- The reviewer differs from the submitter. Submission, review, activation, and
  retirement write audit evidence with version and differences.
- A reproducible seed creates the initial active version. Production
  personalization does not use hidden service constants.
- Pending review read models derive `difference_snapshot` from the candidate
  and immutable base, aligning rules by controlled `code`. Added and removed
  rules include full rule snapshots; changed rules include only `name`,
  `weight`, `conditions`, `reason_template`, and `enabled` field changes.
- `impact_summary` is structural and non-user-level. It reports base/current
  active/candidate versions, enabled/added/removed/changed counts, conservative
  `ordering_may_change` and `reasons_may_change` flags, stale state, and that
  no real profile evaluation was performed. It does not store affected-student,
  quality, conversion, score, or cache-state claims.

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
- `code` is controlled and limited to `major_match`, `grade_match`,
  `interest_match`, `deadline_urgency`, and `general_fallback`. Unknown codes
  are rejected when writing a rule; changing a code is modeled as removing one
  controlled code and adding another.
- `weight` is an integer in the closed range `1..100`; zero and negative
  weights are invalid. Disabling a rule uses `enabled = false`.
- Conditions are strict code-bound JSON contracts: overlap rules use
  `{"operator": "overlap"}`, deadline urgency uses
  `{"operator": "within_days", "min_days": 0, "max_days": N}`, and fallback
  uses `{"operator": "always"}`. Unknown condition fields are invalid.
- `reason_template` is a single-line plain-text template, 1 to 200 Unicode code
  points after trimming, with only the placeholders allowed for its rule code.
  It is rendered by fixed server-side field mappings rather than dynamic
  evaluation.
- Recommendation reasons must be generated from active rules or explicit
  competition fallback facts. The response identifies the active rule-set
  version.
- Internal ranking score and rule weights are not public competition value
  scores, probabilities, percentages, or "quality" scores.
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

Transition rules:

- `published -> archived` and `published -> expired` are accepted only when the
  current public revision has no future time node. If any node has
  `occurs_at > now`, the transition returns a conflict; the schedule must be
  corrected or the maintainer must use cancellation or emergency offline when
  those facts apply.
- Archival and expiry retain favorites and subscriptions as historical
  relations. Past subscribed nodes remain available to calendar ranges, while
  no future calendar node or new reminder can exist under the transition
  precondition.
- The status transaction cancels any stale `pending` reminder with
  `competition_archived` or `competition_expired`. It creates no subscriber
  message; those routine historical states are distinct from cancellation and
  emergency offline.

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
failed -> pending
```

Rules:

- `pending` reminders are eligible for worker dispatch.
- `cancelled` reminders must not create messages.
- Every dispatch attempt increments `attempt_count`. A transient failure sets
  `status = failed`, a sanitized controlled `last_error_code`, `failed_at`, and
  a future `next_attempt_at`; a retry scheduler moves a due retryable row back
  to `pending` before dispatch. Permanent or exhausted failures remain
  `failed` with `next_attempt_at = null`.
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

### Review Decision Status

```text
approved | rejected | returned
```

Rules:

- Pending work belongs to the target revision or rule-set workflow state; it is
  not an incomplete mutable review-decision row.
- A review action appends one terminal immutable decision for the exact target
  snapshot: `approved`, `rejected`, or `returned`.
- `approved` can publish or activate the target object. `rejected` keeps the
  target non-public or inactive. `returned` requires a successor draft and a
  later independent decision rather than mutation of the earlier row.

## Data Ownership

- Users own their profile, favorites, subscriptions, reminder settings, reminders, and messages.
- Administrators own competition publication workflow and configuration.
- The system owns reminder dispatch status and audit log creation.
- Public competition data is readable by anonymous users only after publication.

## Indexing Guidance

Initial indexes should prioritize:

- `competitions.lifecycle_status`
- `competitions.series_id`
- `competitions.published_revision_id`
- `competition_revisions.competition_id, revision_number`
- `competition_revisions.revision_status`
- Partial unique index on `competition_revisions.competition_id` where
  `revision_status IN ('draft', 'pending_review')`
- `competition_revisions.title`
- `competition_revisions.short_title`
- `competition_revisions.category`
- `competition_time_nodes.competition_revision_id, occurs_at`
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
- The reproducible chain starts at
  `apps/api/migrations/versions/c5e0e7e0560d_initial_schema_with_verified_identities.py`;
  `13eb10903bd7_add_immutable_competition_revisions.py` adds the series,
  edition, revision, stage, single-instant node, review, and audit relationships.
  Fresh SQLite and PostgreSQL paths support repeatable upgrade, downgrade, and
  re-upgrade. The known `61f2c8e4a9bd` predecessor backfills owned mutable
  competitions, nodes, and tags into immutable revision snapshots while
  retaining public visibility; unattributed rows block before schema mutation.
  The recorded legacy `db.create_all()` path preserves unknown business-table
  shapes and requires a dedicated publication bridge or reset.
- `seed-e2e --reset` provisions distinct student/editor/reviewer actors plus one
  approved series/edition/revision fixture with an ordered stage and immutable
  `occurs_at` node. It is isolated browser-test data, not a production backfill.
