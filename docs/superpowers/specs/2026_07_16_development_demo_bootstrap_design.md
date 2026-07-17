# Development Demo Bootstrap Design

## Goal

Provide a safe, reproducible development-only bootstrap for the final
CompeteHub student and administrator demo. The bootstrap must coexist with
member-created development data, remain idempotent, and never expose the
destructive isolated E2E reset through the normal development application.

## Scope

The slice adds:

- A Flask CLI command named `bootstrap-development-demo`.
- A root `just bootstrap-development-demo` recipe.
- An explicit `--reset-demo` mode for replacing only records proven to be
  owned by the development-demo bootstrap.
- Four documented development actors and the representative P1/P2 facts needed
  by the Day 1 acceptance path.
- Tests for environment safety, idempotency, conflict handling, scoped reset,
  preservation of non-demo data, and E2E seed isolation.
- Setup, testing, API package, and Day 1 runbook documentation.

The slice does not add production initialization, product roles, API behavior,
database schema, or a general-purpose fixture framework.

## Command And Environment Boundary

The command is:

```text
bootstrap-development-demo [--reset-demo]
```

The root recipe invokes the command through the normal development app:

```text
just bootstrap-development-demo
```

The command permits mutation only when all of the following are true:

- `COMPETEHUB_ENV` resolves to `development`.
- Flask `TESTING` is false.
- Flask `E2E_TESTING` is false.
- The configured database contains the complete application table set known to
  SQLAlchemy metadata.

Production, testing, E2E, and unsupported environments fail before any write.
The command never calls `db.create_all()`, `db.drop_all()`, or Alembic. Schema
upgrade remains the separate `just api-db-upgrade` responsibility.

All validation and mutation for one invocation occur in one database
transaction. Any conflict or unexpected reference rolls back the complete
operation.

`seed-e2e --reset` keeps its current isolated-app guard and destructive
rebuild behavior. The development command reuses deterministic value
definitions or focused builders only where that does not weaken the two
commands' different safety semantics.

PostgreSQL bootstrap rows use database-generated primary keys so every
`BIGSERIAL` sequence advances through normal inserts. SQLite keeps an explicit
`max(id) + 1` fallback because its `BIGINT` primary keys do not provide the
same automatic rowid behavior.

## Ownership Registry

The bootstrap uses the existing `system_configs` table as an ownership
registry, without adding a migration or seed-specific columns to business
tables.

The fixed registry key is:

```text
development_demo.bootstrap.v1
```

Its JSON value stores:

- Registry schema version.
- Bootstrap dataset version.
- Creation and last-verification timestamps.
- Stable business identifiers for each owned logical record.
- The actual database IDs assigned to owned users, identities, profiles,
  reminder settings, series, editions, revisions, stages, nodes, tags, links,
  favorites, subscriptions, reminders, messages, review records, and audit
  records.
- A SHA-256 ownership fingerprint for every entry, derived from its immutable
  natural or relational identity and creation instant.

The registry is the only deletion authority. Matching an email address, title,
source URL, or other reserved value is not enough to authorize deletion when
the record is not listed in the registry. Before reset, the command compares
every registered row with its stored ownership fingerprint. A missing
fingerprint or a mismatch, including a deleted row whose ID was reused by an
unrelated record, fails closed before any deletion. A normal default run may
enrich an otherwise valid legacy registry entry with its fingerprint after the
deterministic record checks succeed.

## Default Bootstrap Semantics

When the registry does not exist, the command first checks that every reserved
business identity is unused. It then creates the full dataset and registry in
one transaction.

When the registry exists, the command validates every registered record and
relationship against the deterministic template:

- An exact match is retained unchanged.
- A missing owned record may be recreated when its stable identity is free and
  no conflicting external record occupies the intended relationship.
- An existing reserved identity with different content fails closed.
- A changed registered record fails closed instead of being overwritten.
- A malformed registry, an ID reused by another logical record, or a
  relationship outside the registered graph fails closed.

The failure output identifies the conflicting logical record and recommends
reviewing the data or using `--reset-demo` when a scoped replacement is
appropriate.

## Scoped Reset Semantics

`--reset-demo` performs these steps in the same transaction:

1. Load and validate the registry.
2. Resolve every registered record and verify its ownership fingerprint and
   stable identity. A registered row that is missing fails closed; only the
   default bootstrap path may recreate a missing owned row.
3. Detect references from records outside the registered ownership graph.
4. Fail and roll back when an external reference exists, reporting its type.
5. Delete registered records in dependency-safe order.
6. Delete the registry.
7. Recreate the complete deterministic dataset and a new valid registry.

The dependency-safe deletion order is:

1. Messages and reminders.
2. Favorites, subscriptions, profiles, reminder settings, and identities.
3. Review records and audit logs.
4. Tag links, time nodes, stages, revisions, editions, tags, and series.
5. Demo users.
6. Registry.

The reproducible recommendation rule-set v1 is shared application seed data,
not owned development-demo data. The bootstrap verifies that exact v1 exists
or creates it through its existing reproducible seed behavior. `--reset-demo`
never deletes, reactivates, or rewrites it; a conflicting v1 fails closed.

## Deterministic Demo Actors

The command provisions these public development-only credentials:

| Actor | Role and capabilities | Purpose |
| --- | --- | --- |
| `student.day1@example.edu` | Student with a complete recommendation-ready profile | Login, discovery, engagement, messages, calendar, and recommendations |
| `admin.day1@example.edu` | `Day 1 Admin` with competition editor plus recommendation editor/reviewer capabilities | Create and submit competition and recommendation candidates; prove same-submitter recommendation review rejection |
| `reviewer.day1@example.edu` | Admin with competition reviewer/maintainer and recommendation reviewer capabilities | Independent review and lifecycle validation |
| `owner.day1@example.edu` | Admin with only `user_administrator` | User-governance boundary checks |

Passwords are fixed public demonstration values, documented next to the command
and explicitly described as unsuitable for production.

Each account has a verified email identity. The student has a complete profile
and reminder settings. Administrator capability combinations follow the
existing student/administrator role model and do not introduce new roles.

## Deterministic Competition And Governance Facts

One reserved Day 1 competition series contains:

- A published edition with complete source-backed content, one approved
  revision, an immutable approval record, audit evidence, ordered stages, and
  three future primary time nodes.
- A pending-review edition submitted by the editor for independent reviewer
  demonstration, with a real submission timestamp and no decision timestamp.
- An incomplete draft edition for validation and recovery demonstration.
- A cancelled historical edition that is hidden from default discovery but
  remains detail-readable with its lifecycle warning.
- An offline edition that is unavailable publicly.

The published edition includes controlled tags and values aligned with the
student profile so recommendation reasons can be demonstrated.

The seed records review and audit evidence as deterministic snapshots. These
fixtures support viewing governance state but do not replace executing the
real editor-submit-review flow during acceptance.

## Engagement, Reminder, Message, And Calendar Facts

The student owns:

- An active favorite for the published edition.
- A historical cancelled subscription retaining its explicit 30-day reminder
  consent and node preferences.
- A sent reminder with immutable node lineage and its unread `reminder_due`
  snapshot.
- Read `competition_time_changed` and unread `competition_offline` snapshots,
  each with deterministic idempotency and a 365-day retention deadline.

The personal calendar remains derived from active subscriptions and the
published revision's current time nodes. Because the bootstrap relation is
historically cancelled, the Day 1 UI starts unsubscribed with no active
calendar items; D1-09 records fresh consent and creates the active relation.
The bootstrap does not invent a separate calendar persistence model.

The command creates only facts supported by the current merged schema. Future
integrated message or calendar changes may extend the deterministic builders,
but this slice does not copy unmerged PR implementation into the bootstrap.

## Recommendation Facts

The command invokes the existing reproducible recommendation-rule seed:

- Exact v1 is reused whether active or normally retired.
- Missing v1 is created.
- A conflicting v1 causes the entire bootstrap to fail and roll back.

The published competition and student profile provide the facts needed for
profile-aware recommendation reasons. The bootstrap does not create hidden
scores or a second recommendation rule dataset.

## Error Handling

Expected command failures use concise `ClickException` messages and leave the
database unchanged. Error categories include:

- Unsupported environment.
- Any missing application table, including a partially migrated schema.
- Reserved identity conflict.
- Registered record drift.
- Invalid or incomplete registry.
- External reference blocking reset.
- Conflicting recommendation rule-set v1.

Errors must identify the affected logical record or reference class without
printing passwords, password hashes, session data, or other secrets.

## Test Strategy

The public seam is the Flask CLI command running against a disposable migrated
application database.

TDD proceeds one behavior at a time:

1. Unsupported environments fail before mutation.
2. First bootstrap creates the expected actors, capabilities, states, and
   relationships.
3. Repeated bootstrap preserves stable identities and row counts.
4. Non-demo users and competition data survive normal bootstrap and reset.
5. Registered-record drift causes a full rollback.
6. An external record referencing demo data blocks reset and preserves all
   rows, including identity-verification delivery and outbound analytics
   cascades.
7. Safe reset recreates the demo graph without changing non-demo data.
8. Student, editor, reviewer, and owner credentials authenticate and expose the
   expected role/capability boundaries.
9. Existing `seed-e2e --reset` tests continue to prove isolated destructive
   behavior.
10. A real migrated PostgreSQL database accepts normal database-generated
    writes before and after bootstrap reset, with member-owned rows preserved
    and generated IDs continuing beyond prior values.
11. Reset rejects a missing registered row, and a partially migrated schema
    fails before any registry write.

Development uses focused CLI tests first. Handoff validation includes API
tests, API lint/format, browser E2E, documentation strict build, and the broad
local gate when available. A disposable migrated development database is
bootstrapped twice and inspected for stable logical identities and counts.

## Documentation Impact

The implementation updates:

- `justfile`
- `docs/setup.md`
- `docs/testing.md`
- `docs/demo/day1-acceptance.md`
- `apps/api/README.md`

The stale Day 1 statement that no seed CLI exists is replaced by the explicit
two-path contract:

- `seed-e2e --reset` is destructive and isolated to browser tests.
- `bootstrap-development-demo` is guarded, idempotent, and non-destructive by
  default for migrated development databases.

No API specification, product PRD, glossary, ADR, or migration update is
required because the slice adds development tooling rather than product
behavior or persistent domain concepts.

## Residual Integration Risk

This implementation is reconciled with the merged #64 reminder/message
contract. Open PRs for calendar and administrator navigation still overlap
seed actors, E2E fixtures, and some demo surfaces. Builders remain focused so
later reconciliation can extend facts without weakening the safety and
ownership rules defined here.
