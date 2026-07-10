from __future__ import annotations

import pytest

from competehub_api.extensions import db
from competehub_api.models import AuditLog, Competition, ReviewRecord, User
from competehub_api.models.enums import CompetitionStatus, ReviewStatus, UserRole
from competehub_api.repositories.competitions import PUBLIC_COMPETITION_STATUSES


def create_admin_user(user_id: int = 1) -> int:
    user = User(
        id=user_id,
        email=f"admin-{user_id}@example.edu",
        password_hash="not-used",
        display_name="Admin",
        role=UserRole.ADMIN,
    )
    db.session.add(user)
    db.session.commit()
    return user_id


def create_student_user(user_id: int = 2) -> int:
    user = User(
        id=user_id,
        email=f"student-{user_id}@example.edu",
        password_hash="not-used",
        display_name="Student",
        role=UserRole.STUDENT,
    )
    db.session.add(user)
    db.session.commit()
    return user_id


def login(client, user_id: int) -> None:
    with client.session_transaction() as session:
        session["user_id"] = user_id


def test_create_draft_competition_records_source_and_audit(client, app) -> None:
    with app.app_context():
        admin = create_admin_user()
    login(client, admin)

    response = client.post(
        "/api/v1/admin/competitions",
        json={
            "title": "Innovation Challenge",
            "source_name": "School Notice",
            "source_url": "https://example.edu/notice",
            "category": "innovation",
            "organizer": "Example University",
            "time_nodes": [
                {
                    "node_type": "registration_deadline",
                    "due_at": "2026-08-15T16:00:00Z",
                    "description": "Registration closes",
                }
            ],
            "tags": [
                {
                    "code": "innovation",
                    "name": "创新创业",
                    "tag_type": "category",
                }
            ],
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["error"] is None
    assert body["data"]["status"] == "draft"
    assert body["data"]["source_name"] == "School Notice"
    assert body["data"]["source_url"] == "https://example.edu/notice"
    assert body["data"]["time_nodes"][0]["node_type"] == "registration_deadline"
    assert body["data"]["tags"] == [
        {
            "code": "innovation",
            "description": None,
            "name": "创新创业",
            "tag_type": "category",
        }
    ]

    with app.app_context():
        competition = db.session.get(Competition, body["data"]["id"])
        assert competition is not None
        assert competition.status == CompetitionStatus.DRAFT
        assert competition.status not in PUBLIC_COMPETITION_STATUSES
        assert competition.time_nodes[0].description == "Registration closes"
        assert competition.tag_links[0].tag.code == "innovation"
        audit = AuditLog.query.one()
        assert audit.action == "competition.create"
        assert audit.actor_id == admin
        assert audit.target_id == competition.id
        assert audit.result == "success"


def test_admin_competition_write_requires_admin_role(client, app) -> None:
    anonymous_response = client.post(
        "/api/v1/admin/competitions",
        json={
            "title": "Unauthorized Challenge",
            "source_name": "School Notice",
            "source_url": "https://example.edu/notice",
        },
    )
    with app.app_context():
        student = create_student_user()
    login(client, student)
    student_response = client.post(
        "/api/v1/admin/competitions",
        json={
            "title": "Forbidden Challenge",
            "source_name": "School Notice",
            "source_url": "https://example.edu/notice",
        },
    )

    assert anonymous_response.status_code == 401
    assert anonymous_response.get_json()["error"]["code"] == "unauthorized"
    assert student_response.status_code == 403
    assert student_response.get_json()["error"]["code"] == "forbidden"


def test_create_draft_rejects_invalid_list_items(client, app) -> None:
    with app.app_context():
        admin = create_admin_user()
    login(client, admin)

    response = client.post(
        "/api/v1/admin/competitions",
        json={
            "title": "Invalid Challenge",
            "source_name": "School Notice",
            "source_url": "https://example.edu/notice",
            "suitable_majors": ["软件工程", 42],
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_update_editable_competition_records_audit_evidence(client, app) -> None:
    with app.app_context():
        admin = create_admin_user()
        competition = Competition(
            id=106,
            title="Editable Challenge",
            source_name="School Notice",
            source_url="https://example.edu/editable",
            status=CompetitionStatus.DRAFT,
            created_by_id=admin,
        )
        db.session.add(competition)
        db.session.commit()
    login(client, admin)

    response = client.patch(
        "/api/v1/admin/competitions/106",
        json={
            "summary": "Updated publication summary.",
            "suitable_majors": ["软件工程"],
            "time_nodes": [
                {
                    "node_type": "submission_deadline",
                    "due_at": "2026-09-10T16:00:00Z",
                }
            ],
            "tags": [
                {
                    "code": "ai",
                    "name": "人工智能",
                    "tag_type": "topic",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["summary"] == "Updated publication summary."
    with app.app_context():
        competition = db.session.get(Competition, 106)
        assert competition.summary == "Updated publication summary."
        assert competition.suitable_majors == ["软件工程"]
        assert [node.node_type for node in competition.time_nodes] == ["submission_deadline"]
        assert [link.tag.code for link in competition.tag_links] == ["ai"]
        audit = AuditLog.query.filter_by(action="competition.update").one()
        assert audit.actor_id == admin
        assert set(audit.detail["fields"]) == {
            "summary",
            "suitable_majors",
            "tags",
            "time_nodes",
        }


def test_update_non_editable_competition_is_rejected(client, app) -> None:
    with app.app_context():
        admin = create_admin_user()
        competition = Competition(
            id=107,
            title="Published Challenge",
            source_name="School Notice",
            source_url="https://example.edu/published",
            summary="Already published.",
            status=CompetitionStatus.PUBLISHED,
            created_by_id=admin,
        )
        db.session.add(competition)
        db.session.commit()
    login(client, admin)

    response = client.patch(
        "/api/v1/admin/competitions/107",
        json={"summary": "Unreviewed replacement."},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "conflict"


@pytest.mark.parametrize("field", ["title", "source_name", "source_url"])
def test_update_rejects_clearing_required_competition_fields(client, app, field) -> None:
    with app.app_context():
        admin = create_admin_user()
        competition = Competition(
            id=110,
            title="Editable Challenge",
            source_name="School Notice",
            source_url="https://example.edu/editable",
            status=CompetitionStatus.DRAFT,
            created_by_id=admin,
        )
        db.session.add(competition)
        db.session.commit()
    login(client, admin)

    response = client.patch(
        "/api/v1/admin/competitions/110",
        json={field: None},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


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
        assert audit.detail == {
            "from_status": "published",
            "reason": "status maintenance",
            "to_status": target_status,
        }


def test_status_maintenance_rejects_invalid_transition(client, app) -> None:
    with app.app_context():
        admin = create_admin_user()
        competition = Competition(
            id=109,
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
        "/api/v1/admin/competitions/109/status",
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


def test_submit_review_rejects_missing_publication_fields(client, app) -> None:
    with app.app_context():
        admin = create_admin_user()
        competition = Competition(
            id=101,
            title="Incomplete Challenge",
            source_name="School Notice",
            source_url="https://example.edu/notice",
            created_by_id=admin,
        )
        db.session.add(competition)
        db.session.commit()
    login(client, admin)

    response = client.post("/api/v1/admin/competitions/101/submit_review")

    assert response.status_code == 400
    body = response.get_json()
    assert body["data"] is None
    assert body["error"]["code"] == "validation_error"
    assert "missing_fields" in body["error"]["details"]
    assert "summary" in body["error"]["details"]["missing_fields"]


def test_submit_review_moves_draft_to_pending_and_records_evidence(client, app) -> None:
    with app.app_context():
        admin = create_admin_user()
        competition = Competition(
            id=102,
            title="Complete Challenge",
            source_name="School Notice",
            source_url="https://example.edu/notice",
            summary="A complete competition summary.",
            organizer="Example University",
            category="innovation",
            created_by_id=admin,
        )
        db.session.add(competition)
        db.session.commit()
    login(client, admin)

    response = client.post("/api/v1/admin/competitions/102/submit_review")

    assert response.status_code == 200
    assert response.get_json()["data"]["status"] == "pending_review"
    with app.app_context():
        competition = db.session.get(Competition, 102)
        assert competition.status == CompetitionStatus.PENDING_REVIEW
        review = ReviewRecord.query.one()
        assert review.target_type == "competition"
        assert review.target_id == 102
        assert review.submitted_by_id == admin
        assert review.status == ReviewStatus.PENDING
        audit = AuditLog.query.filter_by(action="competition.submit_review").one()
        assert audit.result == "success"


def test_review_approve_publishes_competition_and_records_review(client, app) -> None:
    with app.app_context():
        admin = create_admin_user()
        competition = Competition(
            id=103,
            title="Pending Challenge",
            source_name="School Notice",
            source_url="https://example.edu/notice",
            summary="Ready for review.",
            status=CompetitionStatus.PENDING_REVIEW,
            created_by_id=admin,
        )
        db.session.add(competition)
        db.session.commit()
    login(client, admin)

    response = client.post(
        "/api/v1/admin/competitions/103/review",
        json={"action": "approve", "comment": "source checked"},
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["status"] == "published"
    with app.app_context():
        competition = db.session.get(Competition, 103)
        assert competition.status == CompetitionStatus.PUBLISHED
        assert competition.status in PUBLIC_COMPETITION_STATUSES
        review = ReviewRecord.query.one()
        assert review.status == ReviewStatus.APPROVED
        assert review.reviewed_by_id == admin
        assert review.comment == "source checked"
        audit = AuditLog.query.filter_by(action="competition.approve").one()
        assert audit.target_id == 103


def test_review_requires_comment(client, app) -> None:
    with app.app_context():
        admin = create_admin_user()
        competition = Competition(
            id=111,
            title="Pending Challenge",
            source_name="School Notice",
            source_url="https://example.edu/notice",
            summary="Ready for review.",
            status=CompetitionStatus.PENDING_REVIEW,
            created_by_id=admin,
        )
        db.session.add(competition)
        db.session.commit()
    login(client, admin)

    response = client.post(
        "/api/v1/admin/competitions/111/review",
        json={"action": "approve"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_review_reject_and_return_keep_competitions_non_public(client, app) -> None:
    with app.app_context():
        admin = create_admin_user()
        rejected = Competition(
            id=104,
            title="Rejected Challenge",
            source_name="School Notice",
            source_url="https://example.edu/rejected",
            summary="Ready for review.",
            status=CompetitionStatus.PENDING_REVIEW,
            created_by_id=admin,
        )
        returned = Competition(
            id=105,
            title="Returned Challenge",
            source_name="School Notice",
            source_url="https://example.edu/returned",
            summary="Ready for review.",
            status=CompetitionStatus.PENDING_REVIEW,
            created_by_id=admin,
        )
        db.session.add_all([rejected, returned])
        db.session.commit()
    login(client, admin)

    reject_response = client.post(
        "/api/v1/admin/competitions/104/review",
        json={"action": "reject", "comment": "source is not official"},
    )
    return_response = client.post(
        "/api/v1/admin/competitions/105/review",
        json={"action": "return", "comment": "missing deadline"},
    )

    assert reject_response.status_code == 200
    assert reject_response.get_json()["data"]["status"] == "rejected"
    assert return_response.status_code == 200
    assert return_response.get_json()["data"]["status"] == "draft"

    with app.app_context():
        rejected = db.session.get(Competition, 104)
        returned = db.session.get(Competition, 105)
        assert rejected.status not in PUBLIC_COMPETITION_STATUSES
        assert returned.status not in PUBLIC_COMPETITION_STATUSES
        statuses = {record.status for record in ReviewRecord.query.all()}
        assert statuses == {ReviewStatus.REJECTED, ReviewStatus.RETURNED}
        actions = {audit.action for audit in AuditLog.query.all()}
        assert {"competition.reject", "competition.return"} <= actions
