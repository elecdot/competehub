from __future__ import annotations

from pathlib import Path

from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect, text

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

    with app.app_context():
        upgrade(directory=str(MIGRATIONS_DIR))
        assert "users" in _tables()
        assert "user_identities" in _tables()

        downgrade(directory=str(MIGRATIONS_DIR), revision="base")

        assert "users" not in _tables()
        assert "user_identities" not in _tables()
        assert "competehub_migration_baselines" not in _tables()


def test_legacy_create_all_upgrade_and_downgrade_preserves_existing_tables(tmp_path) -> None:
    app = _migration_app(tmp_path / "legacy.db")

    with app.app_context():
        _create_legacy_schema()
        before_tables = _tables()

        upgrade(directory=str(MIGRATIONS_DIR))

        assert "user_identities" in _tables()
        assert "identity_verification_challenges" in _tables()
        assert _columns("users") >= {"session_version", "capabilities"}
        assert db.session.execute(text("SELECT COUNT(*) FROM user_identities")).scalar_one() == 1

        downgrade(directory=str(MIGRATIONS_DIR), revision="base")

        assert LEGACY_BUSINESS_TABLES <= _tables()
        assert _tables() >= before_tables
        assert "user_identities" not in _tables()
        assert "identity_verification_challenges" not in _tables()
        assert "session_version" not in _columns("users")
        assert "capabilities" not in _columns("users")


def _migration_app(database_path: Path):
    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
        }
    )


def _create_legacy_schema() -> None:
    for table_name in sorted(LEGACY_BUSINESS_TABLES - {"users"}):
        db.session.execute(text(f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY)"))
    db.session.execute(
        text(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email VARCHAR(255),
                phone VARCHAR(32),
                student_no VARCHAR(64),
                password_hash VARCHAR(255) NOT NULL,
                display_name VARCHAR(120),
                role VARCHAR(32) NOT NULL,
                status VARCHAR(32) NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )
    )
    db.session.execute(
        text(
            """
            INSERT INTO users (
                id, email, phone, student_no, password_hash, role, status, created_at, updated_at
            )
            VALUES
                (1, 'Student@Example.EDU', NULL, NULL, 'hash', 'student', 'active',
                 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                (2, ' student@example.edu ', NULL, NULL, 'hash', 'student', 'active',
                 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        )
    )
    db.session.commit()


def _tables() -> set[str]:
    return set(inspect(db.engine).get_table_names())


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(db.engine).get_columns(table_name)}
