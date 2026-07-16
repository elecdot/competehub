from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import event

from competehub_api.extensions import db
from competehub_api.models import Competition, CompetitionRevision, Message, User
from competehub_api.models.enums import (
    CompetitionRevisionStatus,
    CompetitionStatus,
    UserRole,
)
from competehub_api.services.messages import purge_expired_messages
from competehub_api.services.profiles import provision_student_owned_rows


def test_student_can_list_empty_retained_message_center(client, app) -> None:
    _sign_in_student(client, app)

    response = client.get("/api/v1/me/messages")

    assert response.status_code == 200
    assert response.get_json() == {
        "data": {
            "items": [],
            "pagination": {"page": 1, "page_size": 20, "total": 0},
        },
        "error": None,
    }


def test_message_list_uses_retained_snapshots_and_hides_expired_or_foreign_rows(
    client, app
) -> None:
    student_id = _sign_in_student(client, app)
    now = datetime.now(UTC)
    with app.app_context():
        other = User(password_hash="not-used", role=UserRole.STUDENT)
        competition = Competition(
            id=10,
            title="Current mutable title",
            source_name="Fixture",
            source_url="https://example.edu/messages",
            status=CompetitionStatus.DRAFT,
        )
        db.session.add_all([other, competition])
        db.session.flush()
        snapshot = {
            "competition_id": competition.id,
            "competition_title": "Original snapshot title",
            "node_type": "registration_deadline",
            "node_occurs_at": "2026-08-01T04:00:00+00:00",
            "reason_summary": None,
        }
        db.session.add_all(
            [
                Message(
                    id=101,
                    user_id=student_id,
                    competition_id=competition.id,
                    message_type="reminder_due",
                    idempotency_key="reminder_due:101",
                    event_occurred_at=now - timedelta(hours=2),
                    title_snapshot="Original message title",
                    body_snapshot="Original message body",
                    target_snapshot=snapshot,
                    retained_until=now + timedelta(days=1),
                    created_at=now - timedelta(hours=1),
                ),
                Message(
                    id=102,
                    user_id=student_id,
                    competition_id=competition.id,
                    message_type="competition_offline",
                    idempotency_key="offline:expired",
                    event_occurred_at=now - timedelta(days=2),
                    title_snapshot="Expired",
                    body_snapshot=None,
                    target_snapshot=snapshot,
                    retained_until=now - timedelta(seconds=1),
                    created_at=now,
                ),
                Message(
                    id=103,
                    user_id=other.id,
                    competition_id=competition.id,
                    message_type="competition_cancelled",
                    idempotency_key="foreign",
                    event_occurred_at=now,
                    title_snapshot="Foreign",
                    body_snapshot=None,
                    target_snapshot=snapshot,
                    retained_until=now + timedelta(days=1),
                    created_at=now,
                ),
            ]
        )
        db.session.commit()

    response = client.get("/api/v1/me/messages")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["pagination"] == {"page": 1, "page_size": 20, "total": 1}
    assert payload["items"] == [
        {
            "id": 101,
            "message_type": "reminder_due",
            "title_snapshot": "Original message title",
            "body_snapshot": "Original message body",
            "target_snapshot": snapshot,
            "event_occurred_at": (now - timedelta(hours=2)).isoformat(),
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "retained_until": (now + timedelta(days=1)).isoformat(),
            "is_read": False,
            "read_at": None,
            "target_available": False,
            "target_url": None,
        }
    ]


def test_unread_count_includes_only_owned_retained_unread_messages(client, app) -> None:
    student_id = _sign_in_student(client, app)
    now = datetime.now(UTC)
    with app.app_context():
        competition = Competition(
            id=11,
            title="Unread count fixture",
            source_name="Fixture",
            source_url="https://example.edu/unread",
            status=CompetitionStatus.DRAFT,
        )
        db.session.add(competition)
        db.session.add_all(
            [
                _message(
                    message_id=111,
                    user_id=student_id,
                    competition_id=competition.id,
                    retained_until=now + timedelta(days=1),
                    created_at=now,
                ),
                _message(
                    message_id=112,
                    user_id=student_id,
                    competition_id=competition.id,
                    retained_until=now - timedelta(seconds=1),
                    created_at=now - timedelta(days=2),
                ),
            ]
        )
        db.session.commit()

    response = client.get("/api/v1/me/messages/unread_count")

    assert response.status_code == 200
    assert response.get_json() == {"data": {"unread_count": 1}, "error": None}


def test_mark_one_message_read_is_owned_retained_and_idempotent(client, app) -> None:
    student_id = _sign_in_student(client, app)
    now = datetime.now(UTC)
    with app.app_context():
        competition = Competition(
            id=12,
            title="Read fixture",
            source_name="Fixture",
            source_url="https://example.edu/read",
            status=CompetitionStatus.DRAFT,
        )
        db.session.add(competition)
        db.session.add(
            _message(
                message_id=121,
                user_id=student_id,
                competition_id=competition.id,
                retained_until=now + timedelta(days=1),
                created_at=now,
            )
        )
        db.session.commit()

    first = client.post("/api/v1/me/messages/121/read")

    assert first.status_code == 200
    first_data = first.get_json()["data"]
    assert first_data["message"]["id"] == 121
    assert first_data["message"]["is_read"] is True
    assert first_data["message"]["read_at"] is not None
    assert first_data["unread_count"] == 0

    second = client.post("/api/v1/me/messages/121/read")

    assert second.status_code == 200
    second_data = second.get_json()["data"]
    assert second_data["message"]["read_at"] == first_data["message"]["read_at"]
    assert second_data["unread_count"] == 0


def test_mark_all_messages_read_updates_only_owned_retained_unread_rows(client, app) -> None:
    student_id = _sign_in_student(client, app)
    now = datetime.now(UTC)
    with app.app_context():
        competition = Competition(
            id=13,
            title="Read all fixture",
            source_name="Fixture",
            source_url="https://example.edu/read-all",
            status=CompetitionStatus.DRAFT,
        )
        db.session.add(competition)
        db.session.add_all(
            [
                _message(
                    message_id=131,
                    user_id=student_id,
                    competition_id=competition.id,
                    retained_until=now + timedelta(days=1),
                    created_at=now,
                ),
                _message(
                    message_id=132,
                    user_id=student_id,
                    competition_id=competition.id,
                    retained_until=now + timedelta(days=1),
                    created_at=now - timedelta(seconds=1),
                ),
                _message(
                    message_id=133,
                    user_id=student_id,
                    competition_id=competition.id,
                    retained_until=now - timedelta(seconds=1),
                    created_at=now - timedelta(days=2),
                ),
            ]
        )
        db.session.commit()

    first = client.post("/api/v1/me/messages/read_all")

    assert first.status_code == 200
    assert first.get_json() == {
        "data": {"updated_count": 2, "unread_count": 0},
        "error": None,
    }
    second = client.post("/api/v1/me/messages/read_all")
    assert second.get_json() == {
        "data": {"updated_count": 0, "unread_count": 0},
        "error": None,
    }
    with app.app_context():
        assert db.session.get(Message, 133).is_read is False


def test_message_list_has_stable_pagination_filters_and_available_target(client, app) -> None:
    student_id = _sign_in_student(client, app)
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        competition = _published_competition(20)
        db.session.add(competition)
        db.session.add_all(
            [
                _message(
                    message_id=201,
                    user_id=student_id,
                    competition_id=competition.id,
                    retained_until=now + timedelta(days=1),
                    created_at=now - timedelta(seconds=2),
                    message_type="reminder_due",
                ),
                _message(
                    message_id=202,
                    user_id=student_id,
                    competition_id=competition.id,
                    retained_until=now + timedelta(days=1),
                    created_at=now - timedelta(seconds=1),
                    message_type="competition_cancelled",
                ),
                _message(
                    message_id=203,
                    user_id=student_id,
                    competition_id=competition.id,
                    retained_until=now + timedelta(days=1),
                    created_at=now - timedelta(seconds=1),
                    is_read=True,
                    message_type="competition_time_changed",
                ),
                _message(
                    message_id=204,
                    user_id=student_id,
                    competition_id=competition.id,
                    retained_until=now + timedelta(days=1),
                    created_at=now,
                    message_type="competition_offline",
                ),
            ]
        )
        db.session.commit()

    first_page = client.get("/api/v1/me/messages?page_size=2").get_json()["data"]
    second_page = client.get("/api/v1/me/messages?page=2&page_size=2").get_json()["data"]
    assert [item["id"] for item in first_page["items"]] == [204, 203]
    assert [item["id"] for item in second_page["items"]] == [202, 201]
    assert first_page["pagination"] == {"page": 1, "page_size": 2, "total": 4}
    assert first_page["items"][0]["target_available"] is True
    assert first_page["items"][0]["target_url"] == "/competitions/20"

    unread = client.get("/api/v1/me/messages?read_status=unread").get_json()["data"]
    assert [item["id"] for item in unread["items"]] == [204, 202, 201]
    expected_by_type = {
        "reminder_due": 201,
        "competition_time_changed": 203,
        "competition_cancelled": 202,
        "competition_offline": 204,
    }
    for message_type, expected_id in expected_by_type.items():
        filtered = client.get(f"/api/v1/me/messages?message_type={message_type}").get_json()["data"]
        assert [item["id"] for item in filtered["items"]] == [expected_id]


def test_message_list_batches_availability_for_shared_and_distinct_targets(client, app) -> None:
    student_id = _sign_in_student(client, app)
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        available = _published_competition(21)
        unavailable = _published_competition(22)
        unavailable.status = CompetitionStatus.OFFLINE
        db.session.add_all([available, unavailable])
        db.session.add_all(
            [
                _message(
                    message_id=211,
                    user_id=student_id,
                    competition_id=available.id,
                    retained_until=now + timedelta(days=1),
                    created_at=now - timedelta(seconds=2),
                ),
                _message(
                    message_id=212,
                    user_id=student_id,
                    competition_id=available.id,
                    retained_until=now + timedelta(days=1),
                    created_at=now - timedelta(seconds=1),
                ),
                _message(
                    message_id=213,
                    user_id=student_id,
                    competition_id=unavailable.id,
                    retained_until=now + timedelta(days=1),
                    created_at=now,
                ),
            ]
        )
        db.session.commit()

        statements = []

        def capture_statement(
            _connection, _cursor, statement, _parameters, _context, _executemany
        ) -> None:
            statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", capture_statement)
        try:
            response = client.get("/api/v1/me/messages?page_size=100")
        finally:
            event.remove(db.engine, "before_cursor_execute", capture_statement)

    assert response.status_code == 200
    items = response.get_json()["data"]["items"]
    assert [(item["id"], item["target_available"]) for item in items] == [
        (213, False),
        (212, True),
        (211, True),
    ]
    competition_selects = [
        statement
        for statement in statements
        if statement.lstrip().upper().startswith("SELECT") and "FROM competitions" in statement
    ]
    assert len(competition_selects) == 1


def test_message_list_rejects_invalid_query_values(client, app) -> None:
    _sign_in_student(client, app)

    for query in (
        "read_status=read",
        "message_type=unknown",
        "page=0",
        "page_size=101",
    ):
        response = client.get(f"/api/v1/me/messages?{query}")
        assert response.status_code == 400
        assert response.get_json()["error"]["code"] == "validation_error"


def test_message_endpoints_require_a_student_session(client, app) -> None:
    requests = (
        ("get", "/api/v1/me/messages"),
        ("get", "/api/v1/me/messages/unread_count"),
        ("post", "/api/v1/me/messages/999/read"),
        ("post", "/api/v1/me/messages/read_all"),
    )
    for method, path in requests:
        assert getattr(client, method)(path).status_code == 401

    _sign_in_as(client, app, UserRole.ADMIN)
    for method, path in requests:
        assert getattr(client, method)(path).status_code == 403


def test_missing_foreign_and_expired_message_reads_are_indistinguishable(client, app) -> None:
    student_id = _sign_in_student(client, app)
    now = datetime.now(UTC)
    with app.app_context():
        other = User(password_hash="not-used", role=UserRole.STUDENT)
        competition = Competition(
            id=30,
            title="Read ownership fixture",
            source_name="Fixture",
            source_url="https://example.edu/read-ownership",
            status=CompetitionStatus.DRAFT,
        )
        db.session.add_all([other, competition])
        db.session.flush()
        db.session.add_all(
            [
                _message(
                    message_id=301,
                    user_id=student_id,
                    competition_id=competition.id,
                    retained_until=now - timedelta(seconds=1),
                    created_at=now - timedelta(days=2),
                ),
                _message(
                    message_id=302,
                    user_id=other.id,
                    competition_id=competition.id,
                    retained_until=now + timedelta(days=1),
                    created_at=now,
                ),
            ]
        )
        db.session.commit()

    responses = [
        client.post(f"/api/v1/me/messages/{message_id}/read") for message_id in (301, 302, 999)
    ]
    assert [response.status_code for response in responses] == [404, 404, 404]
    assert len({str(response.get_json()) for response in responses}) == 1
    with app.app_context():
        assert db.session.get(Message, 301).is_read is False
        assert db.session.get(Message, 302).is_read is False


def test_retention_cleanup_drains_read_and_unread_batches_at_the_cutoff(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        user = User(id=401, password_hash="not-used", role=UserRole.STUDENT)
        competition = Competition(
            id=40,
            title="Retention fixture",
            source_name="Fixture",
            source_url="https://example.edu/retention",
            status=CompetitionStatus.DRAFT,
        )
        db.session.add_all([user, competition])
        db.session.add_all(
            [
                _message(
                    message_id=message_id,
                    user_id=user.id,
                    competition_id=competition.id,
                    retained_until=now if message_id == 403 else now - timedelta(seconds=1),
                    created_at=now - timedelta(days=365),
                    is_read=message_id % 2 == 0,
                )
                for message_id in (401, 402, 403)
            ]
        )
        db.session.add(
            _message(
                message_id=404,
                user_id=user.id,
                competition_id=competition.id,
                retained_until=now + timedelta(seconds=1),
                created_at=now,
            )
        )
        db.session.commit()

        assert purge_expired_messages(now=now, limit=2) == {"purged": 3}
        assert purge_expired_messages(now=now, limit=2) == {"purged": 0}
        assert [message.id for message in Message.query.all()] == [404]


def _sign_in_student(client, app) -> int:
    return _sign_in_as(client, app, UserRole.STUDENT)


def _sign_in_as(client, app, role: UserRole) -> int:
    with app.app_context():
        user = User(
            password_hash="not-used",
            display_name="Message Center Student",
            role=role,
        )
        db.session.add(user)
        db.session.flush()
        if role == UserRole.STUDENT:
            provision_student_owned_rows(user)
        db.session.commit()
        user_id = user.id
        session_version = user.session_version

    now = datetime.now(UTC).isoformat()
    with client.session_transaction() as browser_session:
        browser_session["user_id"] = user_id
        browser_session["session_version"] = session_version
        browser_session["issued_at"] = now
        browser_session["last_activity_at"] = now
    return user_id


def _published_competition(competition_id: int) -> Competition:
    publisher = User(
        id=competition_id + 1000,
        password_hash="not-used",
        role=UserRole.ADMIN,
    )
    competition = Competition(
        id=competition_id,
        title="Available competition",
        source_name="Fixture",
        source_url="https://example.edu/available",
        status=CompetitionStatus.PUBLISHED,
        created_by_id=publisher.id,
    )
    revision = CompetitionRevision(
        id=competition_id,
        competition=competition,
        revision_number=1,
        revision_status=CompetitionRevisionStatus.APPROVED,
        title=competition.title,
        source_name=competition.source_name,
        source_url=competition.source_url,
        created_by_id=publisher.id,
    )
    competition.published_revision = revision
    db.session.add(publisher)
    return competition


def _message(
    *,
    message_id: int,
    user_id: int,
    competition_id: int,
    retained_until: datetime,
    created_at: datetime,
    is_read: bool = False,
    message_type: str = "reminder_due",
) -> Message:
    return Message(
        id=message_id,
        user_id=user_id,
        competition_id=competition_id,
        message_type=message_type,
        idempotency_key=f"fixture:{message_id}",
        event_occurred_at=created_at,
        title_snapshot=f"Message {message_id}",
        body_snapshot=None,
        target_snapshot={
            "competition_id": competition_id,
            "competition_title": "Snapshot fixture",
            "node_type": None,
            "node_occurs_at": None,
            "reason_summary": None,
        },
        retained_until=retained_until,
        created_at=created_at,
        is_read=is_read,
        read_at=created_at if is_read else None,
    )
