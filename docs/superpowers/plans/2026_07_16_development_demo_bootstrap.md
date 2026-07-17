# Development Demo Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a guarded, idempotent development-demo bootstrap and scoped reset that provisions the Day 1 actors and representative P1/P2 data without touching unrelated development records.

**Architecture:** A new seed module owns deterministic development-demo templates, registry validation, transactional provisioning, and registry-scoped reset. The Flask CLI exposes that service only in the development environment; the existing E2E seed retains its isolated destructive behavior. Ownership is recorded in `system_configs` under `development_demo.bootstrap.v1`, while reusable actor values remain plain immutable definitions.

**Tech Stack:** Python 3.12, Flask CLI/Click, Flask-SQLAlchemy, pytest, existing CompeteHub models and seed helpers, Just, MkDocs.

## Global Constraints

- Permit mutation only for `COMPETEHUB_ENV=development` with `TESTING` and `E2E_TESTING` false.
- Never call `db.create_all()`, `db.drop_all()`, or Alembic from the bootstrap.
- Require the complete application table set before reading or writing seed
  data; reject partially migrated databases.
- Keep one invocation atomic; any conflict or external reference rolls back all writes.
- Default execution creates missing owned facts, accepts exact facts, and fails on drift.
- `--reset-demo` deletes only records proven by registry IDs and ownership
  fingerprints, and fails on identity reuse or external references.
- Use database-generated IDs on PostgreSQL so normal `BIGSERIAL` sequences
  remain valid; keep explicit ID allocation only as the SQLite compatibility
  fallback.
- Never delete, overwrite, or reactivate recommendation rule-set v1.
- Preserve `seed-e2e --reset` behavior and isolation.
- Do not add migrations, production business fields, APIs, product roles, or dependencies.

---

### Task 1: Guarded CLI And Empty Bootstrap Registry

**Files:**
- Create: `apps/api/src/competehub_api/seeds/development_demo.py`
- Modify: `apps/api/src/competehub_api/cli.py`
- Create: `apps/api/tests/test_development_demo_seed.py`

**Interfaces:**
- Produces: `DEVELOPMENT_DEMO_REGISTRY_KEY: str`
- Produces: `bootstrap_development_demo(*, reset_demo: bool = False) -> DemoBootstrapResult`
- Produces: Flask command `bootstrap-development-demo --reset-demo`

- [ ] **Step 1: Write failing environment and registry tests**

Add tests that invoke the CLI with explicit app configurations and assert:

```python
def test_development_demo_bootstrap_refuses_testing_environment():
    app = create_app(
        {
            "TESTING": True,
            "COMPETEHUB_ENV": "development",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )
    result = app.test_cli_runner().invoke(args=["bootstrap-development-demo"])
    assert result.exit_code != 0
    assert "development environment" in result.output


def test_development_demo_bootstrap_creates_registry_in_development_app(development_app):
    result = development_app.test_cli_runner().invoke(
        args=["bootstrap-development-demo"]
    )
    assert result.exit_code == 0
    with development_app.app_context():
        registry = SystemConfig.query.filter_by(
            key=DEVELOPMENT_DEMO_REGISTRY_KEY
        ).one()
        assert registry.value["schema_version"] == 1
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
uv run --project apps/api pytest apps/api/tests/test_development_demo_seed.py -q
```

Expected: collection/import failure because the development demo module and CLI command do not exist.

- [ ] **Step 3: Implement the minimal guard and registry service**

Create:

```python
DEVELOPMENT_DEMO_REGISTRY_KEY = "development_demo.bootstrap.v1"


@dataclass(frozen=True)
class DemoBootstrapResult:
    created: bool
    reset: bool


def bootstrap_development_demo(*, reset_demo: bool = False) -> DemoBootstrapResult:
    _require_development_environment()
    registry = SystemConfig.query.filter_by(
        key=DEVELOPMENT_DEMO_REGISTRY_KEY
    ).one_or_none()
    if registry is None:
        registry = SystemConfig(
            key=DEVELOPMENT_DEMO_REGISTRY_KEY,
            value={"schema_version": 1, "dataset_version": 1, "records": {}},
            description="Owned records for the development-only Day 1 demo bootstrap.",
        )
        db.session.add(registry)
        db.session.commit()
        return DemoBootstrapResult(created=True, reset=False)
    db.session.rollback()
    return DemoBootstrapResult(created=False, reset=reset_demo)
```

Register a Click command that translates domain conflicts into
`click.ClickException` and prints whether the dataset was created, verified, or
reset.

- [ ] **Step 4: Run tests and verify GREEN**

Run the focused test file and confirm the guard and registry tests pass.

### Task 2: Deterministic Actor Provisioning And Idempotency

**Files:**
- Modify: `apps/api/src/competehub_api/seeds/development_demo.py`
- Modify: `apps/api/tests/test_development_demo_seed.py`

**Interfaces:**
- Produces: immutable `DemoActor` templates for student, editor, reviewer, and owner.
- Produces registry groups `users`, `identities`, `profiles`, and `reminder_settings`.

- [ ] **Step 1: Write failing actor and repeated-run tests**

Assert the exact emails, roles, capabilities, verified identities, student
profile, and reminder settings. Capture user IDs and total row counts, invoke
the command again, and assert IDs/counts remain unchanged.

The editor fixture is `Day 1 Admin` with `competition_editor`,
`recommendation_editor`, and `recommendation_reviewer`; it intentionally does
not have `competition_maintainer`.

- [ ] **Step 2: Run tests and verify RED**

Expected: registry exists but no users are provisioned.

- [ ] **Step 3: Implement actor creation and exact-match validation**

Use stable business identity by email, database-assigned IDs, public fixed
passwords, verified `UserIdentity` rows, and exact field comparison. Store the
created IDs, stable email values, and immutable ownership fingerprints in the
registry. On repeated invocation, accept exact facts, recreate an owned missing
dependent row, and raise `DevelopmentDemoConflict` when a reserved account or
registered record drifts.

- [ ] **Step 4: Run tests and verify GREEN**

Confirm first-run and repeated-run tests pass.

### Task 3: Competition, Review, Audit, And Rule-Set Facts

**Files:**
- Modify: `apps/api/src/competehub_api/seeds/development_demo.py`
- Modify: `apps/api/tests/test_development_demo_seed.py`

**Interfaces:**
- Produces registry groups for series, editions, revisions, stages, nodes, tags,
  tag links, review records, and audit logs.
- Consumes: `seed_initial_recommendation_rule_set()`.

- [ ] **Step 1: Write failing fixture-state tests**

Assert one reserved series contains published, pending-review, incomplete draft,
cancelled, and offline editions. Verify the published revision has three future
primary nodes, tags, an approval record, and an audit event. Verify the pending
revision belongs to the editor and has no public pointer. Verify exact
recommendation v1 exists. Assert that the pending revision has a submission
timestamp but no decision timestamp.

- [ ] **Step 2: Run tests and verify RED**

Expected: actor tests pass but competition facts are missing.

- [ ] **Step 3: Implement deterministic competition graph**

Create the complete graph with stable canonical names, edition labels, source
URLs, logical node keys, review target identity, and audit action/detail. Use
fixed future UTC instants from the Day 1 contract. Validate exact facts on
repeat. Invoke the existing recommendation seed before committing; translate a
v1 conflict into a full bootstrap conflict.

- [ ] **Step 4: Run tests and verify GREEN**

Confirm the graph and rule-set assertions pass.

### Task 4: Engagement, Reminder, Message, And Login Smoke

**Files:**
- Modify: `apps/api/src/competehub_api/seeds/development_demo.py`
- Modify: `apps/api/tests/test_development_demo_seed.py`

**Interfaces:**
- Produces registry groups for favorites, subscriptions, reminders, and messages.

- [ ] **Step 1: Write failing engagement and authentication tests**

Assert the student owns an active favorite, a historical cancelled
subscription retaining explicit 30-day reminder consent, one terminal sent
reminder, and retained `reminder_due`,
`competition_time_changed`, and `competition_offline` message snapshots with
the expected read state and 365-day retention. Log in as all four actors
through `/api/v1/auth/login`, then assert `/api/v1/me` returns the exact role
and capabilities.

- [ ] **Step 2: Run tests and verify RED**

Expected: competition graph exists but engagement facts are absent.

- [ ] **Step 3: Implement deterministic engagement graph**

Create engagement facts through existing model contracts and stable
idempotency/logical keys. Use the published time-node snapshot and retained
historical consent. Keep the initial UI unsubscribed so D1-09 creates a fresh
active subscription and calendar projection. Register every owned row.

- [ ] **Step 4: Run tests and verify GREEN**

Confirm engagement and login smoke tests pass.

### Task 5: Conflict Detection, External References, And Scoped Reset

**Files:**
- Modify: `apps/api/src/competehub_api/seeds/development_demo.py`
- Modify: `apps/api/tests/test_development_demo_seed.py`

**Interfaces:**
- Produces: registry graph validation and `reset_development_demo()` behavior.

- [ ] **Step 1: Write failing preservation and rollback tests**

Cover:

```python
def test_bootstrap_preserves_non_demo_data(development_app): ...
def test_default_bootstrap_rejects_registered_record_drift_and_rolls_back(...): ...
def test_reset_rejects_external_reference_and_rolls_back(...): ...
def test_reset_rejects_external_identity_on_owned_user(...): ...
def test_reset_rejects_external_verification_delivery_on_owned_identity(...): ...
def test_reset_rejects_external_outbound_analytics_on_owned_competition(...): ...
def test_reset_rejects_missing_registered_owned_record(...): ...
def test_reset_rejects_registry_owned_audit_id_reuse(...): ...
def test_safe_reset_recreates_demo_graph_and_preserves_non_demo_data(...): ...
```

The external-reference test adds a registry-external competition owned by the
demo editor. The reset must fail because deleting that user would affect
unowned data.

- [ ] **Step 2: Run tests and verify RED**

Expected: reset is not implemented and drift is not rejected completely.

- [ ] **Step 3: Implement registry validation and reset**

Resolve rows from registry IDs and stable identities. Compare every row's
stored SHA-256 ownership fingerprint before deletion so reused IDs fail closed,
then compare deterministic fields and relationships. Before reset, query for
references from unregistered records to every registered group, including
secondary identities, verification challenge/delivery cascades, and outbound
click event/daily-stat rows. Treat a missing registered row as an ownership
failure. Delete only registered rows in dependency order, flush between cyclic
public-pointer boundaries, recreate the graph, and commit once.

- [ ] **Step 4: Run tests and verify GREEN**

Confirm all seed tests pass and all rollback assertions observe unchanged
non-demo rows.

### Task 6: Root Recipe And Documentation Contract

**Files:**
- Modify: `justfile`
- Modify: `apps/api/README.md`
- Modify: `docs/setup.md`
- Modify: `docs/testing.md`
- Modify: `docs/demo/day1-acceptance.md`

**Interfaces:**
- Produces: documented command and public development credentials.

- [ ] **Step 1: Add the root recipe**

Add:

```make
# Provision or verify the non-destructive development-only Day 1 demo dataset.
bootstrap-development-demo *args:
    ./scripts/agent-env.sh uv run --project apps/api flask --app competehub_api.app:create_app bootstrap-development-demo {{args}}
```

- [ ] **Step 2: Update documentation**

Document migration prerequisite, default idempotency, conflict behavior,
`--reset-demo`, credentials, registry ownership, and the distinction from
`seed-e2e --reset`. Replace the stale Day 1 statement that no seed CLI exists.

- [ ] **Step 3: Run docs and focused static checks**

Run:

```powershell
uv run --project apps/api --group docs mkdocs build --strict
uv run --project apps/api ruff check apps/api/src/competehub_api/seeds/development_demo.py apps/api/src/competehub_api/cli.py apps/api/tests/test_development_demo_seed.py
uv run --project apps/api ruff format --check apps/api/src/competehub_api/seeds/development_demo.py apps/api/src/competehub_api/cli.py apps/api/tests/test_development_demo_seed.py
```

Expected: all pass.

### Task 7: Full Validation And Handoff

**Files:**
- Modify only if validation exposes an issue in the scoped implementation.

**Interfaces:**
- Produces: PR-ready evidence.

- [ ] **Step 1: Run focused seed tests**

```powershell
uv run --project apps/api pytest apps/api/tests/test_development_demo_seed.py apps/api/tests/test_e2e_seed.py -q
```

- [ ] **Step 2: Run the real PostgreSQL generated-ID regression**

Against the disposable migrated PostgreSQL fixture, bootstrap the demo, perform
normal database-generated writes, reset the demo, verify the member rows
survive, and perform another set of normal writes whose IDs advance beyond the
first set.

- [ ] **Step 3: Run backend gates**

```powershell
uv run --project apps/api pytest
uv run --project apps/api ruff check .
uv run --project apps/api ruff format --check .
```

- [ ] **Step 4: Run browser and docs gates**

```powershell
npm --prefix apps/web run test:e2e
uv run --project apps/api --group docs mkdocs build --strict
```

- [ ] **Step 4: Exercise the command twice against a disposable migrated development database**

Configure `COMPETEHUB_ENV=development` and a disposable SQLite database,
upgrade it through Alembic, run the command twice, inspect stable counts, then
run `--reset-demo` and verify non-demo rows survive.

- [ ] **Step 5: Inspect the complete diff**

Run `git diff --check`, review every changed file against #57 acceptance
criteria, and record skipped checks and residual integration risk.
