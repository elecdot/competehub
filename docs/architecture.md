# CompeteHub Architecture

## Purpose

This document explains the long-lived architecture of CompeteHub at a high level. It is the entry point for understanding system boundaries, runtime components, data flow, and repository layout.

Detailed implementation conventions remain in `docs/tech_spec.md`. Time-bound architecture decisions and tradeoffs are recorded in `docs/adr/`.

## System Context

CompeteHub helps undergraduate students discover trustworthy competitions, judge fit, subscribe to key milestones, and receive in-app reminders. Administrators maintain competition data, review content, configure rules, and inspect operational records.

External dependencies:

- Official competition websites and school or college announcements as source links.
- Browser clients used by students and administrators.
- PostgreSQL for durable business data.
- Redis for transient runtime concerns and task queue infrastructure.

## Runtime Components

```text
Browser
  |
  | HTTP / JSON
  v
Vue SPA (apps/web)
  |
  | /api/v1
  v
Flask API (apps/api)
  |
  +--> PostgreSQL
  |
  +--> Redis
  |
  +--> Celery worker
```

Components:

- Web: Vue 3 SPA for student and admin workflows.
- API: Flask REST API under `/api/v1`.
- PostgreSQL: system of record for users, competitions, subscriptions, reminders, messages, review records, audit logs, and configuration.
- Redis: Celery broker/result backend, short-lived cache, rate limiting counters, and idempotency locks.
- Celery worker: asynchronous task runner for reminder dispatch, competition expiration jobs, and future collection candidate jobs.

## Repository Layout

```text
apps/
  api/       # Flask backend
  web/       # Vue frontend
docs/        # Stable product and engineering documents
docs/adr/    # Architecture Decision Records
infra/       # Local infrastructure
reports/     # Course reports and generated analysis documents
scripts/     # Repository helper scripts
```

Every semantic directory should include a local `README.md` that explains responsibility, commands, and local conventions.

## Backend Architecture

The backend uses a Flask application factory and Blueprints. Request handling follows this layering:

```text
routes -> schemas -> services -> repositories -> models
```

Layer responsibilities:

- Routes handle HTTP input, auth context, and response conversion.
- Schemas validate request payloads and serialize responses.
- Services own business workflows, state transitions, and cross-table consistency.
- Repositories encapsulate reusable database queries.
- Models define database structure and relationships.
- Tasks call services from asynchronous Celery entrypoints.

Initial backend domains:

- `auth`: registration, login, logout, current user.
- `users`: student profile and preferences.
- `competitions`: public competition list, filters, details, outbound link tracking.
- `admin`: competition creation, review, status management, configuration.
- `subscriptions`: favorites, subscriptions, personal calendar.
- `notifications`: in-app messages, reminder settings, read state.
- `recommendations`: rule-based recommendation and reasons.
- `audit`: operation log queries.

## Frontend Architecture

The frontend is organized around user workflows instead of backend table names.

Student workflows:

- Search and filter competitions.
- View competition details.
- See rule-based recommendations.
- Manage favorites and subscriptions.
- View personal competition calendar.
- Read in-app messages.
- Maintain personal profile.

Admin workflows:

- Create and edit competitions.
- Review pending competitions.
- Manage base configuration.
- Manage users and roles.
- View audit logs and simple statistics.

Pinia stores:

- `auth_store`: current user and role.
- `profile_store`: student profile and preferences.
- `competition_filter_store`: list query state.
- `dictionary_store`: categories, tags, majors, grades.
- `notification_store`: messages and unread state.

Frontend permission checks are only for user experience. Backend APIs must enforce authorization.

## Core Data Flow

### Competition Publication

```text
Admin creates draft
  -> submit review
  -> reviewer approves
  -> competition becomes published
  -> public list/search/recommendation can include it
```

Every review and status change writes an audit log.

### Student Subscription And Reminder

```text
Student subscribes to competition
  -> API creates subscription
  -> API creates pending reminders from competition time nodes
  -> Celery scans due reminders
  -> worker creates in-app messages idempotently
  -> student reads messages
```

Reminder data is stored in PostgreSQL. Redis must not be the only reminder source.

### Rule-Based Recommendation

```text
Student profile + competition tags + recommendation rules
  -> scoring and reason generation
  -> recommendation list
```

Recommendation reasons must be traceable to explicit rules or competition fields.

## Security Boundaries

- Unauthenticated users can only access public competition list and detail data.
- Students can only manage their own profile, favorites, subscriptions, reminders, and messages.
- Administrators can access backend management features.
- Role and permission checks must happen on the backend.
- Audit logs are required for review, status changes, config changes, role changes, and content handling.

## Extension Points

- Search: start with PostgreSQL-backed filtering; add a dedicated search service later if Chinese full-text search requires it.
- Notification channels: start with in-app messages; add email, SMS, or WeChat only through explicit ADRs and user authorization requirements.
- Recommendation: start with rules; add model-based ranking only after data volume and evaluation criteria exist.
- Content: materials, team posts, certifications, and reviews should reuse users, competitions, review records, and audit logs.
