from __future__ import annotations

import pytest

from competehub_api.extensions import db
from competehub_api.models import AuditLog, Competition, User
from competehub_api.models.enums import CompetitionStatus, UserRole
from competehub_api.repositories.competitions import PUBLIC_COMPETITION_STATUSES
from competehub_api.services.auth import start_session


def create_admin_user(user_id: int = 1) -> int:
    db.session.add(
        User(
            id=user_id,
            email=f"admin-{user_id}@example.edu",
            password_hash="not-used",
            display_name="Admin",
            role=UserRole.ADMIN,
            capabilities=["competition_editor", "competition_maintainer"],
        )
    )
    db.session.commit()
    return user_id


def create_student_user(user_id: int = 2) -> int:
    db.session.add(
        User(
            id=user_id,
            email=f"student-{user_id}@example.edu",
            password_hash="not-used",
            display_name="Student",
            role=UserRole.STUDENT,
        )
    )
    db.session.commit()
    return user_id


def login(client, user_id: int) -> None:
    with client.application.app_context():
        user = db.session.get(User, user_id)
    with client.session_transaction() as session:
        start_session(session, user)


def test_legacy_mutable_create_payload_is_rejected(client, app) -> None:
    with app.app_context():
        admin = create_admin_user()
    login(client, admin)

    response = client.post(
        "/api/v1/admin/competitions",
        json={
            "title": "Legacy Challenge",
            "source_name": "School Notice",
            "source_url": "https://example.edu/notice",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"
    with app.app_context():
        assert Competition.query.count() == 0


def test_legacy_mutation_and_review_routes_are_not_available(client, app) -> None:
    with app.app_context():
        admin = create_admin_user()
        competition = Competition(
            id=106,
            title="Legacy Draft",
            source_name="School Notice",
            source_url="https://example.edu/legacy",
            status=CompetitionStatus.DRAFT,
            created_by_id=admin,
        )
        db.session.add(competition)
        db.session.commit()
    login(client, admin)

    assert (
        client.patch("/api/v1/admin/competitions/106", json={"title": "Changed"}).status_code == 405
    )
    assert client.post("/api/v1/admin/competitions/106/submit_review").status_code == 404
    assert (
        client.post(
            "/api/v1/admin/competitions/106/review",
            json={"action": "approve", "comment": "bypass"},
        ).status_code
        == 404
    )


def test_admin_competition_write_requires_admin_role(client, app) -> None:
    anonymous_response = client.post("/api/v1/admin/competitions", json={})
    with app.app_context():
        student = create_student_user()
    login(client, student)
    student_response = client.post("/api/v1/admin/competitions", json={})

    assert anonymous_response.status_code == 401
    assert anonymous_response.get_json()["error"]["code"] == "unauthorized"
    assert student_response.status_code == 403
    assert student_response.get_json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize("target_status", ["offline", "archived", "cancelled", "expired"])
def test_status_maintenance_hides_published_competition_and_records_audit(
    client,
    app,
    target_status,
) -> None:
    with app.app_context():
        admin = create_admin_user()
        competition = Competition(
            id=108,
            title="Published Challenge",
            source_name="School Notice",
            source_url="https://example.edu/published",
            summary="Ready to go offline.",
            status=CompetitionStatus.PUBLISHED,
            created_by_id=admin,
        )
        db.session.add(competition)
        db.session.commit()
    login(client, admin)

    response = client.patch(
        "/api/v1/admin/competitions/108/status",
        json={"status": target_status, "reason": "status maintenance"},
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["status"] == target_status
    with app.app_context():
        competition = db.session.get(Competition, 108)
        assert competition.status == CompetitionStatus(target_status)
        assert competition.status not in PUBLIC_COMPETITION_STATUSES
        audit = AuditLog.query.filter_by(action=f"competition.{target_status}").one()
        expected_detail = {
            "from_status": "published",
            "reason": "status maintenance",
            "to_status": target_status,
        }
        assert audit.detail | expected_detail == audit.detail
        assert "impact" in audit.detail


def test_status_maintenance_requires_maintainer_capability(client, app) -> None:
    with app.app_context():
        admin = create_admin_user()
        user = db.session.get(User, admin)
        user.capabilities = ["competition_editor"]
        competition = Competition(
            id=109,
            title="Published Challenge",
            source_name="School Notice",
            source_url="https://example.edu/published",
            status=CompetitionStatus.PUBLISHED,
            created_by_id=admin,
        )
        db.session.add(competition)
        db.session.commit()
    login(client, admin)

    response = client.patch(
        "/api/v1/admin/competitions/109/status",
        json={"status": "offline", "reason": "not authorized"},
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "forbidden"


def test_status_maintenance_rejects_invalid_transition(client, app) -> None:
    with app.app_context():
        admin = create_admin_user()
        competition = Competition(
            id=110,
            title="Draft Challenge",
            source_name="School Notice",
            source_url="https://example.edu/draft",
            status=CompetitionStatus.DRAFT,
            created_by_id=admin,
        )
        db.session.add(competition)
        db.session.commit()
    login(client, admin)

    response = client.patch(
        "/api/v1/admin/competitions/110/status",
        json={"status": "offline", "reason": "not published"},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "conflict"


def test_status_maintenance_returns_conflict_for_review_workflow_target(client, app) -> None:
    with app.app_context():
        admin = create_admin_user()
        competition = Competition(
            id=112,
            title="Published Challenge",
            source_name="School Notice",
            source_url="https://example.edu/published",
            status=CompetitionStatus.PUBLISHED,
            created_by_id=admin,
        )
        db.session.add(competition)
        db.session.commit()
    login(client, admin)

    response = client.patch(
        "/api/v1/admin/competitions/112/status",
        json={"status": "pending_review", "reason": "must use review workflow"},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "conflict"
