from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from flask_migrate import downgrade, upgrade
from psycopg import connect, sql
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from werkzeug.security import generate_password_hash

from competehub_api import create_app
from competehub_api.extensions import db

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


def test_fresh_upgrade_and_downgrade_removes_fresh_schema(tmp_path) -> None:
    app = _migration_app(tmp_path / "fresh.db")
    _assert_fresh_upgrade_and_downgrade(app)


def test_legacy_create_all_upgrade_and_downgrade_preserves_existing_tables(tmp_path) -> None:
    app = _migration_app(tmp_path / "legacy.db")
    _assert_legacy_upgrade_and_downgrade(app)


def test_postgresql_fresh_upgrade_and_downgrade(postgresql_database_uri) -> None:
    app = _migration_app(database_uri=postgresql_database_uri)
    _assert_fresh_upgrade_and_downgrade(app)


def test_postgresql_legacy_upgrade_and_downgrade(postgresql_database_uri) -> None:
    app = _migration_app(database_uri=postgresql_database_uri)
    _assert_legacy_upgrade_and_downgrade(app)


def _assert_fresh_upgrade_and_downgrade(app) -> None:

    with app.app_context():
        upgrade(directory=str(MIGRATIONS_DIR))
        assert "users" in _tables()
        assert "user_identities" in _tables()

        downgrade(directory=str(MIGRATIONS_DIR), revision="base")

        assert "users" not in _tables()
        assert "user_identities" not in _tables()
        assert "competehub_migration_baselines" not in _tables()
        if db.engine.dialect.name == "postgresql":
            remaining_types = db.session.execute(
                text(
                    """
                    SELECT typname FROM pg_type
                    WHERE typname IN (
                        'competition_status', 'identity_verification_status',
                        'reminder_status', 'review_status', 'subscription_status',
                        'user_role', 'user_status'
                    )
                    """
                )
            ).scalars()
            assert list(remaining_types) == []


def _assert_legacy_upgrade_and_downgrade(app) -> None:
    with app.app_context():
        _create_legacy_schema()
        before_tables = _tables()

        upgrade(directory=str(MIGRATIONS_DIR))

        assert "user_identities" in _tables()
        assert "identity_verification_challenges" in _tables()
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
