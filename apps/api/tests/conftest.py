from __future__ import annotations

import os
import uuid

import pytest
from psycopg import connect, sql
from sqlalchemy.engine import make_url

from competehub_api import create_app
from competehub_api.extensions import db


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "OUTBOUND_RATE_LIMIT_ENABLED": False,
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture()
def postgresql_database_uri():
    admin_dsn = os.getenv("POSTGRES_TEST_ADMIN_URL")
    if not admin_dsn:
        pytest.skip("POSTGRES_TEST_ADMIN_URL is required for PostgreSQL test evidence")

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
