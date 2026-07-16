from __future__ import annotations

import os
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from flask_migrate import upgrade
from test_public_competitions import seed_day1_competitions

from competehub_api import create_app
from competehub_api.extensions import db
from competehub_api.models import OutboundClickDailyStat, OutboundClickEvent
from competehub_api.services import outbound_clicks

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "migrations")


@pytest.fixture()
def postgresql_app(postgresql_database_uri):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "issue39-postgresql-concurrency",
            "SQLALCHEMY_DATABASE_URI": postgresql_database_uri,
            "AUTH_RATE_LIMIT_ENABLED": False,
            "OUTBOUND_RATE_LIMIT_ENABLED": False,
        }
    )
    with app.app_context():
        upgrade(directory=MIGRATIONS_DIR)
        seed_day1_competitions()
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
        thread.join(timeout=20)
        assert not thread.is_alive(), "concurrent aggregation worker did not complete"
    assert failures == [None] * len(operations), failures
    return [result for result in results]


def test_postgresql_simultaneous_outbound_aggregation_counts_each_event_once(
    postgresql_app, monkeypatch
) -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    with postgresql_app.app_context():
        db.session.add_all(
            [
                OutboundClickEvent(
                    competition_id=101,
                    competition_revision_id=1,
                    target_type="official_url",
                    source_surface="competition_detail",
                    actor_kind="anonymous",
                    occurred_at=now - timedelta(minutes=index),
                )
                for index in range(20)
            ]
        )
        db.session.commit()

    original_lock = outbound_clicks._acquire_aggregation_lock
    start_lock = threading.Barrier(2)

    def synchronized_lock() -> None:
        start_lock.wait(timeout=10)
        original_lock()

    monkeypatch.setattr(outbound_clicks, "_acquire_aggregation_lock", synchronized_lock)

    def aggregate() -> None:
        with postgresql_app.app_context():
            outbound_clicks.aggregate_outbound_clicks(now=now)

    _run_together(aggregate, aggregate)

    with postgresql_app.app_context():
        stats = db.session.query(OutboundClickDailyStat).all()
        assert len(stats) == 1
        assert stats[0].click_count == 20
        assert db.session.query(OutboundClickEvent).filter_by(aggregated_at=None).count() == 0
