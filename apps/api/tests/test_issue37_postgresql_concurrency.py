from __future__ import annotations

import os
import threading
from collections.abc import Callable

import pytest
from flask_migrate import upgrade
from sqlalchemy.orm import Session
from test_competition_revisions import (
    create_edition,
    create_series,
    create_user,
    login,
)

from competehub_api import create_app
from competehub_api.extensions import db
from competehub_api.models import CompetitionRevision
from competehub_api.models.enums import CompetitionRevisionStatus, UserRole

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "migrations")


@pytest.fixture()
def postgresql_app(postgresql_database_uri):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "issue37-postgresql-concurrency",
            "SQLALCHEMY_DATABASE_URI": postgresql_database_uri,
            "AUTH_RATE_LIMIT_ENABLED": False,
        }
    )
    with app.app_context():
        upgrade(directory=MIGRATIONS_DIR)
    yield app
    with app.app_context():
        db.session.remove()


def _run_together(*operations: Callable[[], object]) -> list[object]:
    start = threading.Barrier(len(operations))
    results: list[object | None] = [None] * len(operations)
    failures: list[BaseException | None] = [None] * len(operations)

    def worker(index: int, operation: Callable[[], object]) -> None:
        try:
            start.wait(timeout=10)
            results[index] = operation()
        except BaseException as error:  # surfaced in the test thread below
            failures[index] = error

    threads = [
        threading.Thread(target=worker, args=(index, operation))
        for index, operation in enumerate(operations)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)
        assert not thread.is_alive(), "concurrent request worker did not complete"
    assert failures == [None] * len(operations), failures
    return [result for result in results]


def _barrier_after_absent_active_revision(monkeypatch) -> None:
    barrier = threading.Barrier(2)
    original_scalar = Session.scalar
    worker_state = threading.local()

    def scalar(session, statement, *args, **kwargs):
        result = original_scalar(session, statement, *args, **kwargs)
        descriptions = getattr(statement, "column_descriptions", ())
        is_revision_query = descriptions and descriptions[0].get("entity") is CompetitionRevision
        is_active_query = "revision_status" in str(statement)
        if (
            result is None
            and is_revision_query
            and is_active_query
            and not getattr(worker_state, "waited", False)
        ):
            worker_state.waited = True
            barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(Session, "scalar", scalar)


def test_postgresql_simultaneous_successor_creation_returns_one_conflict(
    postgresql_app, monkeypatch
) -> None:
    first = postgresql_app.test_client()
    second = postgresql_app.test_client()
    reviewer = postgresql_app.test_client()
    with postgresql_app.app_context():
        editor_id = create_user(
            501,
            UserRole.ADMIN,
            "issue37-concurrent-editor@example.edu",
            ["competition_editor"],
        )
        reviewer_id = create_user(
            502,
            UserRole.ADMIN,
            "issue37-concurrent-reviewer@example.edu",
            ["competition_reviewer"],
        )
    login(first, editor_id)
    with (
        first.session_transaction() as first_session,
        second.session_transaction() as second_session,
    ):
        second_session.update(first_session)

    created = create_edition(first, create_series(first))
    edition_id = created["id"]
    revision_id = created["revision"]["id"]
    assert (
        first.post(f"/api/v1/admin/competition_revisions/{revision_id}/submit_review").status_code
        == 200
    )
    login(reviewer, reviewer_id)
    assert (
        reviewer.post(
            f"/api/v1/admin/competition_revisions/{revision_id}/review",
            json={"action": "approve", "comment": "Initial source verified."},
        ).status_code
        == 200
    )

    _barrier_after_absent_active_revision(monkeypatch)
    responses = _run_together(
        lambda: first.post(
            f"/api/v1/admin/competitions/{edition_id}/revisions",
            json={"reason": "Official source correction A."},
        ),
        lambda: second.post(
            f"/api/v1/admin/competitions/{edition_id}/revisions",
            json={"reason": "Official source correction B."},
        ),
    )

    assert sorted(response.status_code for response in responses) == [201, 409]
    conflict = next(response for response in responses if response.status_code == 409)
    assert conflict.get_json()["error"]["code"] == "active_revision_exists"
    with postgresql_app.app_context():
        active = CompetitionRevision.query.filter(
            CompetitionRevision.competition_id == edition_id,
            CompetitionRevision.revision_status.in_(
                [CompetitionRevisionStatus.DRAFT, CompetitionRevisionStatus.PENDING_REVIEW]
            ),
        ).all()
        assert len(active) == 1
        assert active[0].revision_number == 2
