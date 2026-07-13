from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from flask_migrate import check, downgrade, upgrade
from psycopg import connect, sql
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from werkzeug.security import generate_password_hash

from competehub_api import create_app
from competehub_api.extensions import db
from competehub_api.models import CompetitionRevision, User
from competehub_api.services.competition_revisions import review_revision
from competehub_api.services.errors import ServiceError
from competehub_api.timezones import product_datetime_as_utc, stored_datetime_as_utc

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"

LEGACY_BUSINESS_TABLES = {
    "audit_logs",
    "competition_tag_links",
    "competition_tags",
    "competition_time_nodes",
    "competitions",
    "favorites",
    "messages",
    "recommendation_rules",
    "reminder_settings",
    "reminders",
    "review_records",
    "student_profiles",
    "subscriptions",
    "system_configs",
    "users",
}


def test_fresh_upgrade_downgrade_and_reupgrade_is_repeatable(tmp_path) -> None:
    app = _migration_app(tmp_path / "fresh.db")
    _assert_fresh_upgrade_and_downgrade(app)


def test_legacy_create_all_upgrade_and_downgrade_preserves_existing_tables(tmp_path) -> None:
    app = _migration_app(tmp_path / "legacy.db")
    _assert_legacy_upgrade_and_downgrade(app)


def test_populated_predecessor_upgrade_preserves_public_competition(tmp_path) -> None:
    app = _migration_app(tmp_path / "populated-predecessor.db")
    _assert_populated_predecessor_upgrade(app)


def test_predecessor_upgrade_preserves_submitter_and_removes_pending_review(tmp_path) -> None:
    app = _migration_app(tmp_path / "predecessor-review.db")
    _assert_predecessor_review_actor_upgrade(app)


def test_issue38_empty_engagement_upgrade_backfills_reminder_settings(tmp_path) -> None:
    app = _migration_app(tmp_path / "issue38-settings.db")
    _assert_issue38_settings_upgrade_and_round_trip(app)


def test_issue38_legacy_engagement_blocks_before_schema_mutation(tmp_path, capsys) -> None:
    app = _migration_app(tmp_path / "issue38-legacy-engagement.db")
    _assert_issue38_legacy_engagement_upgrade_is_blocked(app, capsys)


def test_issue38_new_engagement_blocks_unsafe_downgrade(tmp_path, capsys) -> None:
    app = _migration_app(tmp_path / "issue38-unsafe-downgrade.db")
    _assert_issue38_unsafe_downgrade_is_blocked(app, capsys)


def test_unowned_predecessor_competition_blocks_before_schema_mutation(tmp_path) -> None:
    app = _migration_app(tmp_path / "unowned-predecessor.db")
    with app.app_context():
        upgrade(directory=str(MIGRATIONS_DIR), revision="61f2c8e4a9bd")
        competitions = sa.Table("competitions", sa.MetaData(), autoload_with=db.engine)
        now = datetime(2026, 7, 12, 8, 0)
        db.session.execute(
            competitions.insert().values(
                id=1,
                title="Unowned Competition",
                source_name="Existing Source",
                source_url="https://example.edu/unowned-source",
                status="draft",
                created_at=now,
                updated_at=now,
            )
        )
        db.session.commit()

        with pytest.raises(SystemExit) as error:
            upgrade(directory=str(MIGRATIONS_DIR))

        assert error.value.code == 1
        assert "competition_revisions" not in _tables()
        assert db.session.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "61f2c8e4a9bd"
        )


def test_postgresql_fresh_upgrade_downgrade_and_reupgrade(postgresql_database_uri) -> None:
    app = _migration_app(database_uri=postgresql_database_uri)
    _assert_fresh_upgrade_and_downgrade(app)


def test_postgresql_legacy_upgrade_and_downgrade(postgresql_database_uri) -> None:
    app = _migration_app(database_uri=postgresql_database_uri)
    _assert_legacy_upgrade_and_downgrade(app)


def test_postgresql_populated_predecessor_upgrade_preserves_public_competition(
    postgresql_database_uri,
) -> None:
    app = _migration_app(database_uri=postgresql_database_uri)
    _assert_populated_predecessor_upgrade(app)


def test_postgresql_predecessor_upgrade_preserves_submitter_and_removes_pending_review(
    postgresql_database_uri,
) -> None:
    app = _migration_app(database_uri=postgresql_database_uri)
    _assert_predecessor_review_actor_upgrade(app)


def test_postgresql_issue38_empty_engagement_upgrade_backfills_reminder_settings(
    postgresql_database_uri,
) -> None:
    app = _migration_app(database_uri=postgresql_database_uri)
    _assert_issue38_settings_upgrade_and_round_trip(app)


def test_postgresql_issue38_legacy_engagement_blocks_before_schema_mutation(
    postgresql_database_uri,
    capsys,
) -> None:
    app = _migration_app(database_uri=postgresql_database_uri)
    _assert_issue38_legacy_engagement_upgrade_is_blocked(app, capsys)


def test_postgresql_issue38_new_engagement_blocks_unsafe_downgrade(
    postgresql_database_uri,
    capsys,
) -> None:
    app = _migration_app(database_uri=postgresql_database_uri)
    _assert_issue38_unsafe_downgrade_is_blocked(app, capsys)


def _assert_fresh_upgrade_and_downgrade(app) -> None:

    with app.app_context():
        upgrade(directory=str(MIGRATIONS_DIR))
        assert "users" in _tables()
        assert "user_identities" in _tables()
        assert "verification_delivery_outbox" in _tables()
        assert "competition_revisions" in _tables()
        check(directory=str(MIGRATIONS_DIR))

        downgrade(directory=str(MIGRATIONS_DIR), revision="base")

        assert "users" not in _tables()
        assert "user_identities" not in _tables()
        assert "verification_delivery_outbox" not in _tables()
        assert "competehub_migration_baselines" not in _tables()
        if db.engine.dialect.name == "postgresql":
            remaining_types = db.session.execute(
                text(
                    """
                    SELECT typname FROM pg_type
                    WHERE typname IN (
                        'competition_revision_status', 'competition_status',
                        'identity_verification_status', 'reminder_status',
                        'review_status', 'subscription_status', 'user_role',
                        'user_status'
                    )
                    """
                )
            ).scalars()
            assert list(remaining_types) == []

        upgrade(directory=str(MIGRATIONS_DIR))
        assert "competition_revisions" in _tables()
        check(directory=str(MIGRATIONS_DIR))
        downgrade(directory=str(MIGRATIONS_DIR), revision="base")


def _assert_issue38_settings_upgrade_and_round_trip(app) -> None:
    with app.app_context():
        upgrade(directory=str(MIGRATIONS_DIR), revision="13eb10903bd7")
        _seed_issue38_student_settings_predecessor()

        upgrade(directory=str(MIGRATIONS_DIR))

        assert {"default_remind_days", "message_enabled"}.isdisjoint(_columns("student_profiles"))
        assert "time_node_snapshot_id" in _columns("reminders")
        assert any(
            foreign_key["constrained_columns"] == ["time_node_snapshot_id"]
            and foreign_key["referred_table"] == "competition_time_nodes"
            and foreign_key["referred_columns"] == ["id"]
            for foreign_key in inspect(db.engine).get_foreign_keys("reminders")
        )
        rows = db.session.execute(
            text(
                """
                SELECT user_id, enabled, default_remind_days, node_types
                FROM reminder_settings ORDER BY user_id
                """
            )
        ).mappings()
        assert [
            {
                **row,
                "node_types": _decoded_json(row["node_types"]),
            }
            for row in rows
        ] == [
            {
                "user_id": 1,
                "enabled": False,
                "default_remind_days": 9,
                "node_types": ["competition_start"],
            },
            {
                "user_id": 2,
                "enabled": False,
                "default_remind_days": 7,
                "node_types": [
                    "registration_deadline",
                    "submission_deadline",
                    "competition_start",
                ],
            },
            {
                "user_id": 3,
                "enabled": True,
                "default_remind_days": 3,
                "node_types": [
                    "registration_deadline",
                    "submission_deadline",
                    "competition_start",
                ],
            },
        ]

        db.session.remove()
        downgrade(directory=str(MIGRATIONS_DIR), revision="13eb10903bd7")

        assert {"default_remind_days", "message_enabled"} <= _columns("student_profiles")
        assert "time_node_id" in _columns("reminders")
        assert any(
            foreign_key["constrained_columns"] == ["time_node_id"]
            and foreign_key["referred_table"] == "competition_time_nodes"
            and foreign_key["referred_columns"] == ["id"]
            for foreign_key in inspect(db.engine).get_foreign_keys("reminders")
        )
        compatibility_rows = db.session.execute(
            text(
                """
                SELECT user_id, default_remind_days, message_enabled
                FROM student_profiles ORDER BY user_id
                """
            )
        ).mappings()
        assert list(compatibility_rows) == [
            {"user_id": 1, "default_remind_days": 9, "message_enabled": False},
            {"user_id": 2, "default_remind_days": 7, "message_enabled": False},
        ]

        db.session.remove()
        upgrade(directory=str(MIGRATIONS_DIR))
        assert {"default_remind_days", "message_enabled"}.isdisjoint(_columns("student_profiles"))
        assert db.session.execute(text("SELECT count(*) FROM reminder_settings")).scalar_one() == 3


def _assert_issue38_legacy_engagement_upgrade_is_blocked(app, capsys) -> None:
    with app.app_context():
        upgrade(directory=str(MIGRATIONS_DIR), revision="13eb10903bd7")
        _seed_issue38_legacy_engagement()
        original_columns = {
            table_name: _columns(table_name)
            for table_name in ("favorites", "subscriptions", "reminders", "student_profiles")
        }

        with pytest.raises(SystemExit) as error:
            upgrade(directory=str(MIGRATIONS_DIR))

        assert error.value.code == 1
        output = capsys.readouterr()
        message = f"{output.out}\n{output.err}"
        assert "favorites=1" in message
        assert "subscriptions=1" in message
        assert "reminders=1" in message
        assert db.session.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "13eb10903bd7"
        )
        assert {
            table_name: _columns(table_name)
            for table_name in ("favorites", "subscriptions", "reminders", "student_profiles")
        } == original_columns


def _assert_issue38_unsafe_downgrade_is_blocked(app, capsys) -> None:
    with app.app_context():
        upgrade(directory=str(MIGRATIONS_DIR))
        head_revision = db.session.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        assert head_revision != "13eb10903bd7"
        _seed_issue38_new_favorite()
        original_columns = _columns("favorites")

        with pytest.raises(SystemExit) as error:
            downgrade(directory=str(MIGRATIONS_DIR), revision="13eb10903bd7")

        assert error.value.code == 1
        output = capsys.readouterr()
        message = f"{output.out}\n{output.err}"
        assert "favorites=1" in message
        assert db.session.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            head_revision
        )
        assert _columns("favorites") == original_columns


def _seed_issue38_student_settings_predecessor() -> None:
    metadata = sa.MetaData()
    metadata.reflect(
        bind=db.engine,
        only=["users", "student_profiles", "reminder_settings"],
    )
    users = metadata.tables["users"]
    profiles = metadata.tables["student_profiles"]
    settings = metadata.tables["reminder_settings"]
    now = datetime(2026, 7, 12, 8, 0)
    db.session.execute(
        users.insert(),
        [
            _issue38_user_row(1, "student-existing-settings@example.edu", "student", now),
            _issue38_user_row(2, "student-profile-settings@example.edu", "student", now),
            _issue38_user_row(3, "student-no-profile@example.edu", "student", now),
            _issue38_user_row(4, "admin-no-settings@example.edu", "admin", now),
        ],
    )
    db.session.execute(
        profiles.insert(),
        [
            {
                "id": 1,
                "user_id": 1,
                "interest_tags": [],
                "goal_preferences": [],
                "blocked_tags": [],
                "default_remind_days": 1,
                "message_enabled": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": 2,
                "user_id": 2,
                "interest_tags": [],
                "goal_preferences": [],
                "blocked_tags": [],
                "default_remind_days": 7,
                "message_enabled": False,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )
    db.session.execute(
        settings.insert().values(
            id=1,
            user_id=1,
            enabled=False,
            default_remind_days=9,
            node_types=["competition_start"],
            created_at=now,
            updated_at=now,
        )
    )
    db.session.commit()


def _seed_issue38_legacy_engagement() -> None:
    metadata = sa.MetaData()
    metadata.reflect(
        bind=db.engine,
        only=["users", "competitions", "favorites", "subscriptions", "reminders"],
    )
    now = datetime(2026, 7, 12, 8, 0)
    db.session.execute(
        metadata.tables["users"]
        .insert()
        .values(**_issue38_user_row(1, "legacy-engagement@example.edu", "student", now))
    )
    db.session.execute(
        metadata.tables["competitions"]
        .insert()
        .values(
            id=1,
            title="Legacy Engagement Competition",
            source_name="Legacy Source",
            source_url="https://example.edu/legacy-engagement",
            participant_forms=[],
            status="unpublished",
            created_at=now,
            updated_at=now,
        )
    )
    db.session.execute(
        metadata.tables["favorites"]
        .insert()
        .values(
            id=1,
            user_id=1,
            competition_id=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db.session.execute(
        metadata.tables["subscriptions"]
        .insert()
        .values(
            id=1,
            user_id=1,
            competition_id=1,
            status="active",
            reminder_enabled=True,
            remind_days=3,
            node_types=["registration_deadline"],
            created_at=now,
            updated_at=now,
        )
    )
    db.session.execute(
        metadata.tables["reminders"]
        .insert()
        .values(
            id=1,
            user_id=1,
            competition_id=1,
            time_node_id=None,
            node_type="registration_deadline",
            due_at=now,
            title="Legacy reminder",
            status="pending",
            created_at=now,
            updated_at=now,
        )
    )
    db.session.commit()


def _seed_issue38_new_favorite() -> None:
    metadata = sa.MetaData()
    metadata.reflect(bind=db.engine, only=["users", "competitions", "favorites"])
    now = datetime(2026, 7, 12, 8, 0)
    db.session.execute(
        metadata.tables["users"]
        .insert()
        .values(**_issue38_user_row(1, "new-engagement@example.edu", "student", now))
    )
    db.session.execute(
        metadata.tables["competitions"]
        .insert()
        .values(
            id=1,
            title="New Engagement Competition",
            source_name="New Source",
            source_url="https://example.edu/new-engagement",
            participant_forms=[],
            status="unpublished",
            created_at=now,
            updated_at=now,
        )
    )
    db.session.execute(
        metadata.tables["favorites"]
        .insert()
        .values(
            id=1,
            user_id=1,
            competition_id=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db.session.commit()


def _issue38_user_row(user_id: int, email: str, role: str, now: datetime) -> dict:
    return {
        "id": user_id,
        "email": email,
        "password_hash": "migration-test-hash",
        "display_name": email.split("@", 1)[0],
        "session_version": 1,
        "capabilities": [],
        "role": role,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }


def _assert_populated_predecessor_upgrade(app) -> None:
    with app.app_context():
        upgrade(directory=str(MIGRATIONS_DIR), revision="61f2c8e4a9bd")
        _seed_predecessor_publication()

        upgrade(directory=str(MIGRATIONS_DIR))

        edition = (
            db.session.execute(
                text(
                    """
                SELECT series_id, published_revision_id, participant_forms
                FROM competitions WHERE id = 1
                """
                )
            )
            .mappings()
            .one()
        )
        assert edition["series_id"] is not None
        assert edition["published_revision_id"] is not None
        assert _decoded_json(edition["participant_forms"]) == ["individual"]

        revision = (
            db.session.execute(
                text(
                    """
                SELECT revision_status, participant_forms, major_scope, grade_scope,
                       submitted_by_id, submitted_at, decided_at
                FROM competition_revisions WHERE id = :revision_id
                """
                ),
                {"revision_id": edition["published_revision_id"]},
            )
            .mappings()
            .one()
        )
        assert {
            **revision,
            "participant_forms": _decoded_json(revision["participant_forms"]),
            "submitted_at": _migrated_legacy_instant(revision["submitted_at"]),
            "decided_at": _migrated_legacy_instant(revision["decided_at"]),
        } == {
            "revision_status": "approved",
            "participant_forms": ["individual"],
            "major_scope": "selected",
            "grade_scope": "selected",
            "submitted_by_id": 2,
            "submitted_at": _expected_legacy_instant(datetime(2026, 7, 12, 8, 30)),
            "decided_at": _expected_legacy_instant(datetime(2026, 7, 12, 9, 0)),
        }

        migrated_review = (
            db.session.execute(
                text(
                    """
                    SELECT target_type, target_id, submitted_by_id, reviewed_by_id,
                           status, comment, submitted_at, decided_at
                    FROM review_records
                    """
                )
            )
            .mappings()
            .one()
        )
        assert {
            **migrated_review,
            "submitted_at": _migrated_legacy_instant(migrated_review["submitted_at"]),
            "decided_at": _migrated_legacy_instant(migrated_review["decided_at"]),
        } == {
            "target_type": "competition_revision",
            "target_id": edition["published_revision_id"],
            "submitted_by_id": 2,
            "reviewed_by_id": 3,
            "status": "approved",
            "comment": "Legacy approval evidence",
            "submitted_at": _expected_legacy_instant(datetime(2026, 7, 12, 8, 30)),
            "decided_at": _expected_legacy_instant(datetime(2026, 7, 12, 9, 0)),
        }

        node = (
            db.session.execute(
                text(
                    """
                SELECT competition_revision_id, stage_id, logical_node_key,
                       node_revision, occurs_at, prominence
                FROM competition_time_nodes WHERE id = 1
                """
                )
            )
            .mappings()
            .one()
        )
        assert node["competition_revision_id"] == edition["published_revision_id"]
        assert node["stage_id"] is not None
        assert node["logical_node_key"] == "legacy-node-1"
        assert node["node_revision"] == 1
        assert node["occurs_at"] is not None
        assert node["prominence"] == "primary"

        public_response = app.test_client().get("/api/v1/competitions/1")
        assert public_response.status_code == 200
        public_edition = public_response.get_json()["data"]
        assert public_edition["title"] == "Existing Published Competition"
        assert public_edition["participant_forms"] == ["individual"]
        assert public_edition["tags"] == ["Existing Tag"]
        assert public_edition["next_node"]["logical_node_key"] == "legacy-node-1"

        if db.engine.dialect.name == "postgresql":
            enum_values = db.session.execute(
                text("SELECT unnest(enum_range(NULL::competition_status))::text")
            ).scalars()
            assert "unpublished" in set(enum_values)

        db.session.remove()
        downgrade(directory=str(MIGRATIONS_DIR), revision="61f2c8e4a9bd")
        predecessor = (
            db.session.execute(
                text("SELECT title, status, participant_form FROM competitions WHERE id = 1")
            )
            .mappings()
            .one()
        )
        assert predecessor == {
            "title": "Existing Published Competition",
            "status": "published",
            "participant_form": "individual",
        }
        assert (
            db.session.execute(
                text("SELECT due_at FROM competition_time_nodes WHERE id = 1")
            ).scalar_one()
            is not None
        )

        db.session.remove()
        upgrade(directory=str(MIGRATIONS_DIR))
        assert app.test_client().get("/api/v1/competitions/1").status_code == 200
        reupgraded_revision = db.session.execute(
            text("SELECT submitted_by_id FROM competition_revisions WHERE competition_id = 1")
        ).scalar_one()
        assert reupgraded_revision == 2
        db.session.remove()
        check(directory=str(MIGRATIONS_DIR))


def _assert_predecessor_review_actor_upgrade(app) -> None:
    with app.app_context():
        upgrade(directory=str(MIGRATIONS_DIR), revision="61f2c8e4a9bd")
        _seed_predecessor_pending_review()

        upgrade(directory=str(MIGRATIONS_DIR))

        revision = db.session.scalar(sa.select(CompetitionRevision))
        assert revision is not None
        assert revision.submitted_by_id == 2
        assert _migrated_legacy_instant(revision.submitted_at) == _expected_legacy_instant(
            datetime(2026, 7, 12, 9, 0)
        )
        assert (
            db.session.execute(
                text("SELECT count(*) FROM review_records WHERE status = 'pending'")
            ).scalar_one()
            == 0
        )

        db.session.remove()
        downgrade(directory=str(MIGRATIONS_DIR), revision="61f2c8e4a9bd")
        predecessor_pending = (
            db.session.execute(
                text(
                    """
                    SELECT c.status, r.submitted_by_id
                    FROM competitions AS c
                    JOIN review_records AS r
                      ON r.target_type = 'competition' AND r.target_id = c.id
                    WHERE c.id = 1 AND r.status = 'pending'
                    """
                )
            )
            .mappings()
            .one()
        )
        assert predecessor_pending == {"status": "pending_review", "submitted_by_id": 2}

        db.session.remove()
        upgrade(directory=str(MIGRATIONS_DIR))
        revision = db.session.scalar(sa.select(CompetitionRevision))
        assert revision is not None
        assert revision.submitted_by_id == 2
        assert (
            db.session.execute(
                text("SELECT count(*) FROM review_records WHERE status = 'pending'")
            ).scalar_one()
            == 0
        )

        submitter = db.session.get(User, 2)
        reviewer = db.session.get(User, 3)
        assert submitter is not None
        assert reviewer is not None
        with pytest.raises(ServiceError) as error:
            review_revision(revision, submitter, "approve", "self review must fail")
        assert error.value.status_code == 403

        decided = review_revision(revision, reviewer, "return", "needs source clarification")
        assert decided.revision_status.value == "returned"
        decision = (
            db.session.execute(
                text(
                    """
                    SELECT target_type, target_id, submitted_by_id, reviewed_by_id, status, comment
                    FROM review_records
                    """
                )
            )
            .mappings()
            .one()
        )
        assert decision == {
            "target_type": "competition_revision",
            "target_id": revision.id,
            "submitted_by_id": 2,
            "reviewed_by_id": 3,
            "status": "returned",
            "comment": "needs source clarification",
        }


def _seed_predecessor_pending_review() -> None:
    metadata = sa.MetaData()
    metadata.reflect(bind=db.engine, only=["users", "competitions", "review_records"])
    users = metadata.tables["users"]
    competitions = metadata.tables["competitions"]
    reviews = metadata.tables["review_records"]
    created_at = datetime(2026, 7, 12, 8, 0)
    submitted_at = datetime(2026, 7, 12, 9, 0)

    db.session.execute(
        users.insert(),
        [
            {
                "id": 1,
                "email": "migration-creator@example.edu",
                "password_hash": "migration-test-hash",
                "display_name": "Migration Creator",
                "session_version": 1,
                "capabilities": ["competition_editor"],
                "role": "admin",
                "status": "active",
                "created_at": created_at,
                "updated_at": created_at,
            },
            {
                "id": 2,
                "email": "migration-submitter@example.edu",
                "password_hash": "migration-test-hash",
                "display_name": "Migration Submitter",
                "session_version": 1,
                "capabilities": ["competition_editor", "competition_reviewer"],
                "role": "admin",
                "status": "active",
                "created_at": created_at,
                "updated_at": created_at,
            },
            {
                "id": 3,
                "email": "migration-reviewer@example.edu",
                "password_hash": "migration-test-hash",
                "display_name": "Migration Reviewer",
                "session_version": 1,
                "capabilities": ["competition_reviewer"],
                "role": "admin",
                "status": "active",
                "created_at": created_at,
                "updated_at": created_at,
            },
        ],
    )
    db.session.execute(
        competitions.insert().values(
            id=1,
            title="Pending Legacy Competition",
            source_name="Existing Source",
            source_url="https://example.edu/pending-source",
            participant_form="individual",
            status="pending_review",
            created_by_id=1,
            created_at=created_at,
            updated_at=submitted_at,
        )
    )
    db.session.execute(
        reviews.insert().values(
            id=1,
            target_type="competition",
            target_id=1,
            submitted_by_id=2,
            status="pending",
            created_at=submitted_at,
            updated_at=submitted_at,
        )
    )
    db.session.commit()


def _seed_predecessor_publication() -> None:
    metadata = sa.MetaData()
    metadata.reflect(
        bind=db.engine,
        only=[
            "users",
            "competitions",
            "competition_time_nodes",
            "competition_tags",
            "competition_tag_links",
            "review_records",
        ],
    )
    now = datetime(2026, 7, 12, 8, 0)
    users = metadata.tables["users"]
    competitions = metadata.tables["competitions"]
    time_nodes = metadata.tables["competition_time_nodes"]
    tags = metadata.tables["competition_tags"]
    tag_links = metadata.tables["competition_tag_links"]
    reviews = metadata.tables["review_records"]

    db.session.execute(
        users.insert(),
        [
            {
                "id": 1,
                "email": "migration-owner@example.edu",
                "password_hash": "migration-test-hash",
                "display_name": "Migration Owner",
                "session_version": 1,
                "capabilities": ["competition_editor"],
                "role": "admin",
                "status": "active",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": 2,
                "email": "migration-submitter@example.edu",
                "password_hash": "migration-test-hash",
                "display_name": "Migration Submitter",
                "session_version": 1,
                "capabilities": ["competition_editor"],
                "role": "admin",
                "status": "active",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": 3,
                "email": "migration-reviewer@example.edu",
                "password_hash": "migration-test-hash",
                "display_name": "Migration Reviewer",
                "session_version": 1,
                "capabilities": ["competition_reviewer"],
                "role": "admin",
                "status": "active",
                "created_at": now,
                "updated_at": now,
            },
        ],
    )
    db.session.execute(
        competitions.insert().values(
            id=1,
            title="Existing Published Competition",
            short_title="Existing Competition",
            category="innovation",
            organizer="Example University",
            source_name="Existing Source",
            source_url="https://example.edu/existing-source",
            summary="Existing summary",
            eligibility="Existing eligibility",
            participant_form="individual",
            suitable_majors=["Computer Science"],
            suitable_grades=["Year 2"],
            status="published",
            created_by_id=1,
            created_at=now,
            updated_at=now,
        )
    )
    db.session.execute(
        time_nodes.insert().values(
            id=1,
            competition_id=1,
            node_type="registration_deadline",
            due_at=datetime(2099, 7, 20, 15, 59),
            description="Existing deadline",
            created_at=now,
            updated_at=now,
        )
    )
    db.session.execute(
        tags.insert().values(
            id=1,
            code="existing-tag",
            name="Existing Tag",
            tag_type="topic",
            created_at=now,
            updated_at=now,
        )
    )
    db.session.execute(
        tag_links.insert().values(
            id=1,
            competition_id=1,
            tag_id=1,
            created_at=now,
            updated_at=now,
        )
    )
    db.session.execute(
        reviews.insert().values(
            id=1,
            target_type="competition",
            target_id=1,
            submitted_by_id=2,
            reviewed_by_id=3,
            status="approved",
            comment="Legacy approval evidence",
            created_at=datetime(2026, 7, 12, 8, 30),
            updated_at=datetime(2026, 7, 12, 9, 0),
        )
    )
    db.session.commit()


def _assert_legacy_upgrade_and_downgrade(app) -> None:
    with app.app_context():
        _create_legacy_schema()
        before_tables = _tables()

        upgrade(directory=str(MIGRATIONS_DIR))

        assert "user_identities" in _tables()
        assert "identity_verification_challenges" in _tables()
        assert "verification_delivery_outbox" in _tables()
        assert _columns("users") >= {"session_version", "capabilities"}
        assert db.session.execute(text("SELECT COUNT(*) FROM user_identities")).scalar_one() == 2
        phone_login = app.test_client().post(
            "/api/v1/auth/login",
            json={
                "identity_type": "phone",
                "identity": "+86 138 0000 0000",
                "password": "correct horse battery staple",
            },
        )
        assert phone_login.status_code == 200

        users = sa.Table("users", sa.MetaData(), autoload_with=db.engine)
        db.session.execute(
            users.insert().values(
                id=4,
                password_hash="hash",
                role="student",
                status="pending_activation",
                session_version=1,
                capabilities=[],
                created_at=sa.func.current_timestamp(),
                updated_at=sa.func.current_timestamp(),
            )
        )
        db.session.commit()

        downgrade(directory=str(MIGRATIONS_DIR), revision="base")

        assert LEGACY_BUSINESS_TABLES <= _tables()
        assert _tables() >= before_tables
        assert "user_identities" not in _tables()
        assert "identity_verification_challenges" not in _tables()
        assert "verification_delivery_outbox" not in _tables()
        assert "session_version" not in _columns("users")
        assert "capabilities" not in _columns("users")
        assert (
            db.session.execute(text("SELECT status FROM users WHERE id = 4")).scalar_one()
            == "disabled"
        )


def _migration_app(database_path: Path | None = None, *, database_uri: str | None = None):
    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": database_uri or f"sqlite:///{database_path}",
            "AUTH_RATE_LIMIT_ENABLED": False,
        }
    )


def _create_legacy_schema() -> None:
    metadata = sa.MetaData()
    users = sa.Table(
        "users",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(32)),
        sa.Column("student_no", sa.String(64)),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120)),
        sa.Column(
            "role",
            sa.Enum("student", "admin", "teacher", "organizer", name="user_role"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("active", "disabled", name="user_status"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    for table_name in sorted(LEGACY_BUSINESS_TABLES - {"users"}):
        sa.Table(table_name, metadata, sa.Column("id", sa.Integer(), primary_key=True))
    metadata.create_all(db.engine)

    legacy_hash = generate_password_hash("correct horse battery staple", method="scrypt:32768:8:1")
    now = datetime.now(UTC).replace(tzinfo=None)
    db.session.execute(
        users.insert(),
        [
            {
                "id": 1,
                "email": "Student@Example.EDU",
                "phone": None,
                "student_no": None,
                "display_name": None,
                "password_hash": legacy_hash,
                "role": "student",
                "status": "active",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": 2,
                "email": " student@example.edu ",
                "phone": None,
                "student_no": None,
                "display_name": None,
                "password_hash": legacy_hash,
                "role": "student",
                "status": "active",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": 3,
                "email": None,
                "phone": "+86 138 0000 0000",
                "student_no": None,
                "display_name": None,
                "password_hash": legacy_hash,
                "role": "student",
                "status": "active",
                "created_at": now,
                "updated_at": now,
            },
        ],
    )
    db.session.commit()


@pytest.fixture()
def postgresql_database_uri():
    admin_dsn = os.getenv("POSTGRES_TEST_ADMIN_URL")
    if not admin_dsn:
        pytest.skip("POSTGRES_TEST_ADMIN_URL is required for PostgreSQL migration evidence")

    database_name = f"competehub_migration_test_{uuid.uuid4().hex}"
    with connect(admin_dsn, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))

    admin_url = make_url(admin_dsn)
    database_url = admin_url.set(
        drivername="postgresql+psycopg", database=database_name
    ).render_as_string(hide_password=False)
    try:
        yield database_url
    finally:
        with connect(admin_dsn, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name))
            )


def _tables() -> set[str]:
    return set(inspect(db.engine).get_table_names())


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(db.engine).get_columns(table_name)}


def _decoded_json(value):
    return json.loads(value) if isinstance(value, str) else value


def _decoded_datetime(value):
    decoded = datetime.fromisoformat(value) if isinstance(value, str) else value
    if decoded.tzinfo is not None:
        return decoded.astimezone(UTC).replace(tzinfo=None)
    return decoded


def _migrated_legacy_instant(value):
    return stored_datetime_as_utc(_decoded_datetime(value))


def _expected_legacy_instant(value: datetime) -> datetime:
    if db.engine.dialect.name == "postgresql":
        return product_datetime_as_utc(value)
    return stored_datetime_as_utc(value)
