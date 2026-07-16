from __future__ import annotations

from datetime import UTC, datetime

import pytest

from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionRevision,
    CompetitionStage,
    CompetitionTimeNode,
    Favorite,
    Subscription,
    User,
)
from competehub_api.models.enums import (
    CompetitionRevisionStatus,
    CompetitionStatus,
    SubscriptionStatus,
    UserRole,
)


def test_calendar_includes_selected_nodes_when_subscription_reminders_are_disabled(
    client, app
) -> None:
    with app.app_context():
        publisher = User(
            id=1,
            email="calendar-publisher@example.edu",
            password_hash="not-used",
            role=UserRole.ADMIN,
        )
        student = User(
            id=2,
            email="calendar-student@example.edu",
            password_hash="not-used",
            role=UserRole.STUDENT,
        )
        competition = Competition(
            id=10,
            title="Calendar fixture",
            source_name="Fixture source",
            source_url="https://example.edu/calendar-fixture",
            status=CompetitionStatus.PUBLISHED,
        )
        revision = CompetitionRevision(
            id=20,
            competition=competition,
            revision_number=1,
            revision_status=CompetitionRevisionStatus.APPROVED,
            title="Current calendar title",
            source_name="Fixture source",
            source_url="https://example.edu/calendar-fixture",
            created_by_id=publisher.id,
        )
        stage = CompetitionStage(
            id=30,
            revision=revision,
            stage_key="registration",
            stage_type="registration",
            label="报名阶段",
            stage_order=1,
        )
        selected_node = CompetitionTimeNode(
            id=40,
            competition=competition,
            revision=revision,
            stage=stage,
            logical_node_key="registration-main-deadline",
            node_revision=2,
            node_type="registration_deadline",
            occurs_at=datetime(2026, 8, 15, 16, 0, tzinfo=UTC),
            prominence="primary",
            description="报名截止",
        )
        unselected_node = CompetitionTimeNode(
            id=41,
            competition=competition,
            revision=revision,
            stage=stage,
            logical_node_key="submission-main-deadline",
            node_revision=1,
            node_type="submission_deadline",
            occurs_at=datetime(2026, 8, 16, 8, 0, tzinfo=UTC),
            prominence="secondary",
            description="作品提交截止",
        )
        next_day_selected_node = CompetitionTimeNode(
            id=42,
            competition=competition,
            revision=revision,
            stage=stage,
            logical_node_key="registration-next-day-deadline",
            node_revision=1,
            node_type="registration_deadline",
            occurs_at=datetime(2026, 8, 16, 16, 0, tzinfo=UTC),
            prominence="primary",
            description="下一个上海日历日",
        )
        subscription = Subscription(
            id=50,
            user_id=student.id,
            competition_id=competition.id,
            status=SubscriptionStatus.ACTIVE,
            reminder_enabled=False,
            remind_days=3,
            node_types=["registration_deadline"],
            reminder_confirmed_at=datetime(2026, 7, 16, tzinfo=UTC),
        )
        db.session.add_all(
            [
                publisher,
                student,
                competition,
                revision,
                stage,
                selected_node,
                unselected_node,
                next_day_selected_node,
                subscription,
            ]
        )
        db.session.flush()
        competition.published_revision_id = revision.id
        db.session.commit()
        session_version = student.session_version
        expected_item = {
            "competition_id": competition.id,
            "competition_title": revision.title,
            "detail_url": f"/competitions/{competition.id}",
            "lifecycle_status": "published",
            "target_available": True,
            "stage_id": stage.id,
            "stage_label": stage.label,
            "stage_order": stage.stage_order,
            "stage_type": stage.stage_type,
            "is_current_stage": True,
            "node_snapshot_id": selected_node.id,
            "logical_node_key": selected_node.logical_node_key,
            "node_revision": selected_node.node_revision,
            "node_type": selected_node.node_type,
            "description": selected_node.description,
            "occurs_at": "2026-08-15T16:00:00+00:00",
            "prominence": "primary",
            "pair_kind": "registration",
            "pair_role": "deadline",
        }

    _sign_in(client, student.id, session_version)

    response = client.get("/api/v1/me/calendar?from=2026-08-16&to=2026-08-16&view=month")

    assert response.status_code == 200
    body = response.get_json()
    assert body["error"] is None
    assert body["data"]["range"] == {
        "from": "2026-08-16",
        "to": "2026-08-16",
        "time_zone": "Asia/Shanghai",
        "view": "month",
    }
    assert body["data"]["items"] == [expected_item]


def test_calendar_requires_a_student_session(client, app) -> None:
    query = "/api/v1/me/calendar?from=2026-08-01&to=2026-08-31&view=month"

    unauthenticated = client.get(query)

    assert unauthenticated.status_code == 401
    assert unauthenticated.get_json()["error"]["code"] == "unauthorized"

    with app.app_context():
        teacher = User(
            id=10,
            email="calendar-teacher@example.edu",
            password_hash="not-used",
            role=UserRole.TEACHER,
        )
        db.session.add(teacher)
        db.session.commit()
        teacher_id = teacher.id
        session_version = teacher.session_version

    _sign_in(client, teacher_id, session_version)
    forbidden = client.get(query)

    assert forbidden.status_code == 403
    assert forbidden.get_json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize(
    ("query", "field"),
    [
        ("to=2026-08-31&view=month", "from"),
        ("from=not-a-date&to=2026-08-31&view=month", "from"),
        ("from=2026-08-01&to=2026-08-31&view=agenda", "view"),
        ("from=2026-09-01&to=2026-08-31&view=month", "to"),
    ],
)
def test_calendar_rejects_invalid_query(client, app, query: str, field: str) -> None:
    with app.app_context():
        student = User(
            id=20,
            email="calendar-query-student@example.edu",
            password_hash="not-used",
            role=UserRole.STUDENT,
        )
        db.session.add(student)
        db.session.commit()
        student_id = student.id
        session_version = student.session_version

    _sign_in(client, student_id, session_version)

    response = client.get(f"/api/v1/me/calendar?{query}")

    assert response.status_code == 400
    assert response.get_json()["error"] == {
        "code": "validation_error",
        "details": {"field": field},
        "message": "calendar query is invalid",
    }


def test_calendar_uses_active_subscriptions_and_the_current_public_revision(client, app) -> None:
    with app.app_context():
        publisher = User(
            id=100,
            email="calendar-current-publisher@example.edu",
            password_hash="not-used",
            role=UserRole.ADMIN,
        )
        student = User(
            id=101,
            email="calendar-current-student@example.edu",
            password_hash="not-used",
            role=UserRole.STUDENT,
        )
        db.session.add_all([publisher, student])

        current_competition, old_revision, old_node = _add_calendar_competition(
            competition_id=110,
            revision_id=120,
            stage_id=130,
            node_id=140,
            publisher_id=publisher.id,
            title="Old revision title",
            occurs_at=datetime(2026, 8, 15, 16, 0, tzinfo=UTC),
        )
        current_revision = CompetitionRevision(
            id=121,
            competition=current_competition,
            revision_number=2,
            revision_status=CompetitionRevisionStatus.APPROVED,
            title="Current revision title",
            source_name="Fixture source",
            source_url="https://example.edu/current-revision",
            created_by_id=publisher.id,
        )
        current_stage = CompetitionStage(
            id=131,
            revision=current_revision,
            stage_key="registration-current",
            stage_type="registration",
            label="当前报名阶段",
            stage_order=1,
        )
        current_node = CompetitionTimeNode(
            id=141,
            competition=current_competition,
            revision=current_revision,
            stage=current_stage,
            logical_node_key=old_node.logical_node_key,
            node_revision=2,
            node_type="registration_deadline",
            occurs_at=datetime(2026, 8, 16, 16, 0, tzinfo=UTC),
            prominence="primary",
            description="改期后的报名截止",
        )
        db.session.add_all([current_revision, current_stage, current_node])
        favorite_only, _, _ = _add_calendar_competition(
            competition_id=111,
            revision_id=122,
            stage_id=132,
            node_id=142,
            publisher_id=publisher.id,
            title="Favorite only",
            occurs_at=datetime(2026, 8, 16, 8, 0, tzinfo=UTC),
        )
        cancelled_subscription, _, _ = _add_calendar_competition(
            competition_id=112,
            revision_id=123,
            stage_id=133,
            node_id=143,
            publisher_id=publisher.id,
            title="Cancelled subscription",
            occurs_at=datetime(2026, 8, 16, 9, 0, tzinfo=UTC),
        )
        db.session.flush()
        current_competition.published_revision_id = current_revision.id
        db.session.add_all(
            [
                Subscription(
                    id=150,
                    user_id=student.id,
                    competition_id=current_competition.id,
                    status=SubscriptionStatus.ACTIVE,
                    reminder_enabled=True,
                    remind_days=3,
                    node_types=["registration_deadline"],
                ),
                Subscription(
                    id=151,
                    user_id=student.id,
                    competition_id=cancelled_subscription.id,
                    status=SubscriptionStatus.CANCELLED,
                    reminder_enabled=True,
                    remind_days=3,
                    node_types=["registration_deadline"],
                ),
                Favorite(
                    id=152,
                    user_id=student.id,
                    competition_id=favorite_only.id,
                    is_active=True,
                ),
            ]
        )
        db.session.commit()
        student_id = student.id
        session_version = student.session_version
        current_node_id = current_node.id
        old_revision_id = old_revision.id
        current_revision_id = current_revision.id

    _sign_in(client, student_id, session_version)

    items_by_view = {}
    for view in ("month", "week", "list"):
        response = client.get(f"/api/v1/me/calendar?from=2026-08-16&to=2026-08-17&view={view}")
        assert response.status_code == 200
        items_by_view[view] = response.get_json()["data"]["items"]

    assert items_by_view["month"] == items_by_view["week"] == items_by_view["list"]
    assert [item["node_snapshot_id"] for item in items_by_view["month"]] == [current_node_id]
    assert items_by_view["month"][0]["competition_title"] == "Current revision title"
    assert old_revision_id != current_revision_id


def test_calendar_hides_future_cancelled_and_offline_nodes_and_marks_unavailable_targets(
    client, app
) -> None:
    with app.app_context():
        publisher = User(
            id=200,
            email="calendar-lifecycle-publisher@example.edu",
            password_hash="not-used",
            role=UserRole.ADMIN,
        )
        student = User(
            id=201,
            email="calendar-lifecycle-student@example.edu",
            password_hash="not-used",
            role=UserRole.STUDENT,
        )
        db.session.add_all([publisher, student])
        cancelled, cancelled_revision, cancelled_past = _add_calendar_competition(
            competition_id=210,
            revision_id=220,
            stage_id=230,
            node_id=240,
            publisher_id=publisher.id,
            title="Cancelled calendar target",
            occurs_at=datetime(2000, 1, 1, 4, 0, tzinfo=UTC),
            status=CompetitionStatus.CANCELLED,
        )
        offline, offline_revision, offline_past = _add_calendar_competition(
            competition_id=211,
            revision_id=221,
            stage_id=231,
            node_id=241,
            publisher_id=publisher.id,
            title="Offline calendar target",
            occurs_at=datetime(2000, 1, 1, 5, 0, tzinfo=UTC),
            status=CompetitionStatus.OFFLINE,
        )
        archived, _, archived_past = _add_calendar_competition(
            competition_id=212,
            revision_id=222,
            stage_id=232,
            node_id=244,
            publisher_id=publisher.id,
            title="Archived calendar target",
            occurs_at=datetime(2000, 1, 1, 6, 0, tzinfo=UTC),
            status=CompetitionStatus.ARCHIVED,
        )
        expired, _, expired_past = _add_calendar_competition(
            competition_id=213,
            revision_id=223,
            stage_id=233,
            node_id=245,
            publisher_id=publisher.id,
            title="Expired calendar target",
            occurs_at=datetime(2000, 1, 1, 7, 0, tzinfo=UTC),
            status=CompetitionStatus.EXPIRED,
        )
        cancelled_future = CompetitionTimeNode(
            id=242,
            competition=cancelled,
            revision=cancelled_revision,
            stage=cancelled_past.stage,
            logical_node_key="registration-future-deadline",
            node_revision=1,
            node_type="registration_deadline",
            occurs_at=datetime(2099, 1, 1, 4, 0, tzinfo=UTC),
            prominence="primary",
            description="Cancelled future node",
        )
        offline_future = CompetitionTimeNode(
            id=243,
            competition=offline,
            revision=offline_revision,
            stage=offline_past.stage,
            logical_node_key="registration-future-deadline",
            node_revision=1,
            node_type="registration_deadline",
            occurs_at=datetime(2099, 1, 1, 5, 0, tzinfo=UTC),
            prominence="primary",
            description="Offline future node",
        )
        db.session.add_all(
            [
                cancelled_future,
                offline_future,
                Subscription(
                    id=250,
                    user_id=student.id,
                    competition_id=cancelled.id,
                    status=SubscriptionStatus.ACTIVE,
                    reminder_enabled=False,
                    remind_days=3,
                    node_types=["registration_deadline"],
                ),
                Subscription(
                    id=251,
                    user_id=student.id,
                    competition_id=offline.id,
                    status=SubscriptionStatus.ACTIVE,
                    reminder_enabled=False,
                    remind_days=3,
                    node_types=["registration_deadline"],
                ),
                Subscription(
                    id=252,
                    user_id=student.id,
                    competition_id=archived.id,
                    status=SubscriptionStatus.ACTIVE,
                    reminder_enabled=False,
                    remind_days=3,
                    node_types=["registration_deadline"],
                ),
                Subscription(
                    id=253,
                    user_id=student.id,
                    competition_id=expired.id,
                    status=SubscriptionStatus.ACTIVE,
                    reminder_enabled=False,
                    remind_days=3,
                    node_types=["registration_deadline"],
                ),
            ]
        )
        db.session.commit()
        student_id = student.id
        session_version = student.session_version
        expected_past_ids = [
            cancelled_past.id,
            offline_past.id,
            archived_past.id,
            expired_past.id,
        ]

    _sign_in(client, student_id, session_version)

    response = client.get("/api/v1/me/calendar?from=2000-01-01&to=2099-01-02&view=list")

    assert response.status_code == 200
    items = response.get_json()["data"]["items"]
    assert [item["node_snapshot_id"] for item in items] == expected_past_ids
    assert items[0]["lifecycle_status"] == "cancelled"
    assert items[0]["target_available"] is True
    assert items[0]["detail_url"] == "/competitions/210"
    assert items[1]["lifecycle_status"] == "offline"
    assert items[1]["target_available"] is False
    assert items[1]["detail_url"] is None
    assert [item["lifecycle_status"] for item in items[2:]] == ["archived", "expired"]
    assert all(item["target_available"] is True for item in items[2:])


def test_calendar_uses_stable_same_day_order(client, app) -> None:
    with app.app_context():
        publisher = User(
            id=300,
            email="calendar-order-publisher@example.edu",
            password_hash="not-used",
            role=UserRole.ADMIN,
        )
        student = User(
            id=301,
            email="calendar-order-student@example.edu",
            password_hash="not-used",
            role=UserRole.STUDENT,
        )
        competition = Competition(
            id=310,
            title="Calendar order fixture",
            source_name="Fixture source",
            source_url="https://example.edu/calendar-order",
            status=CompetitionStatus.PUBLISHED,
        )
        revision = CompetitionRevision(
            id=320,
            competition=competition,
            revision_number=1,
            revision_status=CompetitionRevisionStatus.APPROVED,
            title="Calendar order fixture",
            source_name="Fixture source",
            source_url="https://example.edu/calendar-order",
            created_by_id=publisher.id,
        )
        first_stage = CompetitionStage(
            id=330,
            revision=revision,
            stage_key="first",
            stage_type="registration",
            label="First stage",
            stage_order=1,
        )
        second_stage = CompetitionStage(
            id=331,
            revision=revision,
            stage_key="second",
            stage_type="competition",
            label="Second stage",
            stage_order=2,
        )
        nodes = [
            CompetitionTimeNode(
                id=340,
                competition=competition,
                revision=revision,
                stage=second_stage,
                logical_node_key="competition-start",
                node_type="competition_start",
                occurs_at=datetime(2026, 8, 15, 1, 0, tzinfo=UTC),
                prominence="primary",
            ),
            CompetitionTimeNode(
                id=343,
                competition=competition,
                revision=revision,
                stage=first_stage,
                logical_node_key="registration-later",
                node_type="registration_deadline",
                occurs_at=datetime(2026, 8, 15, 15, 0, tzinfo=UTC),
                prominence="primary",
            ),
            CompetitionTimeNode(
                id=342,
                competition=competition,
                revision=revision,
                stage=first_stage,
                logical_node_key="submission-secondary",
                node_type="submission_deadline",
                occurs_at=datetime(2026, 8, 15, 8, 0, tzinfo=UTC),
                prominence="secondary",
            ),
            CompetitionTimeNode(
                id=341,
                competition=competition,
                revision=revision,
                stage=first_stage,
                logical_node_key="registration-primary",
                node_type="registration_deadline",
                occurs_at=datetime(2026, 8, 15, 8, 0, tzinfo=UTC),
                prominence="primary",
            ),
        ]
        db.session.add_all(
            [
                publisher,
                student,
                competition,
                revision,
                first_stage,
                second_stage,
                *nodes,
            ]
        )
        db.session.flush()
        competition.published_revision_id = revision.id
        db.session.add(
            Subscription(
                id=350,
                user_id=student.id,
                competition_id=competition.id,
                status=SubscriptionStatus.ACTIVE,
                reminder_enabled=True,
                remind_days=3,
                node_types=[
                    "registration_deadline",
                    "submission_deadline",
                    "competition_start",
                ],
            )
        )
        db.session.commit()
        student_id = student.id
        session_version = student.session_version

    _sign_in(client, student_id, session_version)

    response = client.get("/api/v1/me/calendar?from=2026-08-15&to=2026-08-15&view=week")

    assert response.status_code == 200
    items = response.get_json()["data"]["items"]
    assert [item["node_snapshot_id"] for item in items] == [341, 342, 343, 340]


def test_calendar_current_stage_uses_all_current_revision_nodes(client, app) -> None:
    with app.app_context():
        publisher = User(
            id=400,
            email="calendar-stage-publisher@example.edu",
            password_hash="not-used",
            role=UserRole.ADMIN,
        )
        student = User(
            id=401,
            email="calendar-stage-student@example.edu",
            password_hash="not-used",
            role=UserRole.STUDENT,
        )
        db.session.add_all([publisher, student])
        competition, revision, first_stage, second_stage = _add_two_stage_competition(
            competition_id=410,
            revision_id=420,
            first_stage_id=430,
            second_stage_id=431,
            publisher_id=publisher.id,
            title="Current stage fixture",
        )
        nearest_unselected = CompetitionTimeNode(
            id=440,
            competition=competition,
            revision=revision,
            stage=first_stage,
            logical_node_key="unselected-nearest-node",
            node_type="competition_end",
            occurs_at=datetime(2098, 1, 1, 4, 0, tzinfo=UTC),
            prominence="secondary",
        )
        selected_in_range = CompetitionTimeNode(
            id=441,
            competition=competition,
            revision=revision,
            stage=second_stage,
            logical_node_key="selected-later-node",
            node_type="registration_deadline",
            occurs_at=datetime(2099, 1, 1, 4, 0, tzinfo=UTC),
            prominence="primary",
        )
        db.session.add_all(
            [
                nearest_unselected,
                selected_in_range,
                Subscription(
                    id=450,
                    user_id=student.id,
                    competition_id=competition.id,
                    status=SubscriptionStatus.ACTIVE,
                    reminder_enabled=False,
                    remind_days=3,
                    node_types=["registration_deadline"],
                ),
            ]
        )
        db.session.commit()
        student_id = student.id
        session_version = student.session_version

    _sign_in(client, student_id, session_version)

    response = client.get("/api/v1/me/calendar?from=2099-01-01&to=2099-01-01&view=month")

    assert response.status_code == 200
    assert response.get_json()["data"]["items"][0]["is_current_stage"] is False


def test_calendar_current_stage_breaks_equal_node_times_by_stage_order(client, app) -> None:
    with app.app_context():
        publisher = User(
            id=500,
            email="calendar-stage-tie-publisher@example.edu",
            password_hash="not-used",
            role=UserRole.ADMIN,
        )
        student = User(
            id=501,
            email="calendar-stage-tie-student@example.edu",
            password_hash="not-used",
            role=UserRole.STUDENT,
        )
        db.session.add_all([publisher, student])
        competition, revision, first_stage, second_stage = _add_two_stage_competition(
            competition_id=510,
            revision_id=520,
            first_stage_id=530,
            second_stage_id=531,
            publisher_id=publisher.id,
            title="Current stage tie fixture",
        )
        shared_time = datetime(2099, 2, 1, 4, 0, tzinfo=UTC)
        db.session.add_all(
            [
                CompetitionTimeNode(
                    id=540,
                    competition=competition,
                    revision=revision,
                    stage=first_stage,
                    logical_node_key="first-stage-node",
                    node_type="registration_deadline",
                    occurs_at=shared_time,
                    prominence="primary",
                ),
                CompetitionTimeNode(
                    id=541,
                    competition=competition,
                    revision=revision,
                    stage=second_stage,
                    logical_node_key="second-stage-node",
                    node_type="competition_start",
                    occurs_at=shared_time,
                    prominence="primary",
                ),
                Subscription(
                    id=550,
                    user_id=student.id,
                    competition_id=competition.id,
                    status=SubscriptionStatus.ACTIVE,
                    reminder_enabled=True,
                    remind_days=3,
                    node_types=["registration_deadline", "competition_start"],
                ),
            ]
        )
        db.session.commit()
        student_id = student.id
        session_version = student.session_version

    _sign_in(client, student_id, session_version)

    response = client.get("/api/v1/me/calendar?from=2099-02-01&to=2099-02-01&view=week")

    assert response.status_code == 200
    items = response.get_json()["data"]["items"]
    assert [item["is_current_stage"] for item in items] == [True, False]


def test_calendar_uses_final_stage_after_all_revision_nodes_elapsed(client, app) -> None:
    with app.app_context():
        publisher = User(
            id=600,
            email="calendar-stage-past-publisher@example.edu",
            password_hash="not-used",
            role=UserRole.ADMIN,
        )
        student = User(
            id=601,
            email="calendar-stage-past-student@example.edu",
            password_hash="not-used",
            role=UserRole.STUDENT,
        )
        db.session.add_all([publisher, student])
        competition, revision, first_stage, second_stage = _add_two_stage_competition(
            competition_id=610,
            revision_id=620,
            first_stage_id=630,
            second_stage_id=631,
            publisher_id=publisher.id,
            title="Elapsed stage fixture",
        )
        db.session.add_all(
            [
                CompetitionTimeNode(
                    id=640,
                    competition=competition,
                    revision=revision,
                    stage=first_stage,
                    logical_node_key="elapsed-first-stage-node",
                    node_type="registration_deadline",
                    occurs_at=datetime(2000, 2, 1, 4, 0, tzinfo=UTC),
                    prominence="primary",
                ),
                CompetitionTimeNode(
                    id=641,
                    competition=competition,
                    revision=revision,
                    stage=second_stage,
                    logical_node_key="elapsed-final-stage-node",
                    node_type="competition_start",
                    occurs_at=datetime(2000, 2, 2, 4, 0, tzinfo=UTC),
                    prominence="primary",
                ),
                Subscription(
                    id=650,
                    user_id=student.id,
                    competition_id=competition.id,
                    status=SubscriptionStatus.ACTIVE,
                    reminder_enabled=False,
                    remind_days=3,
                    node_types=["registration_deadline", "competition_start"],
                ),
            ]
        )
        db.session.commit()
        student_id = student.id
        session_version = student.session_version

    _sign_in(client, student_id, session_version)

    response = client.get("/api/v1/me/calendar?from=2000-02-01&to=2000-02-02&view=list")

    assert response.status_code == 200
    items = response.get_json()["data"]["items"]
    assert [item["is_current_stage"] for item in items] == [False, True]


def _add_calendar_competition(
    *,
    competition_id: int,
    revision_id: int,
    stage_id: int,
    node_id: int,
    publisher_id: int,
    title: str,
    occurs_at: datetime,
    status: CompetitionStatus = CompetitionStatus.PUBLISHED,
) -> tuple[Competition, CompetitionRevision, CompetitionTimeNode]:
    competition = Competition(
        id=competition_id,
        title=title,
        source_name="Fixture source",
        source_url=f"https://example.edu/calendar/{competition_id}",
        status=status,
    )
    revision = CompetitionRevision(
        id=revision_id,
        competition=competition,
        revision_number=1,
        revision_status=CompetitionRevisionStatus.APPROVED,
        title=title,
        source_name="Fixture source",
        source_url=f"https://example.edu/calendar/{competition_id}",
        created_by_id=publisher_id,
    )
    stage = CompetitionStage(
        id=stage_id,
        revision=revision,
        stage_key="registration",
        stage_type="registration",
        label="报名阶段",
        stage_order=1,
    )
    node = CompetitionTimeNode(
        id=node_id,
        competition=competition,
        revision=revision,
        stage=stage,
        logical_node_key="registration-main-deadline",
        node_revision=1,
        node_type="registration_deadline",
        occurs_at=occurs_at,
        prominence="primary",
        description="报名截止",
    )
    db.session.add_all([competition, revision, stage, node])
    db.session.flush()
    competition.published_revision_id = revision.id
    return competition, revision, node


def _add_two_stage_competition(
    *,
    competition_id: int,
    revision_id: int,
    first_stage_id: int,
    second_stage_id: int,
    publisher_id: int,
    title: str,
) -> tuple[Competition, CompetitionRevision, CompetitionStage, CompetitionStage]:
    competition = Competition(
        id=competition_id,
        title=title,
        source_name="Fixture source",
        source_url=f"https://example.edu/calendar/{competition_id}",
        status=CompetitionStatus.PUBLISHED,
    )
    revision = CompetitionRevision(
        id=revision_id,
        competition=competition,
        revision_number=1,
        revision_status=CompetitionRevisionStatus.APPROVED,
        title=title,
        source_name="Fixture source",
        source_url=f"https://example.edu/calendar/{competition_id}",
        created_by_id=publisher_id,
    )
    first_stage = CompetitionStage(
        id=first_stage_id,
        revision=revision,
        stage_key="first",
        stage_type="registration",
        label="First stage",
        stage_order=1,
    )
    second_stage = CompetitionStage(
        id=second_stage_id,
        revision=revision,
        stage_key="second",
        stage_type="competition",
        label="Second stage",
        stage_order=2,
    )
    db.session.add_all([competition, revision, first_stage, second_stage])
    db.session.flush()
    competition.published_revision_id = revision.id
    return competition, revision, first_stage, second_stage


def _sign_in(client, user_id: int, session_version: int) -> None:
    now = datetime.now(UTC).isoformat()
    with client.session_transaction() as browser_session:
        browser_session["user_id"] = user_id
        browser_session["session_version"] = session_version
        browser_session["issued_at"] = now
        browser_session["last_activity_at"] = now
