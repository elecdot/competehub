from __future__ import annotations

from competehub_api.extensions import db
from competehub_api.models import AuditLog, ReviewRecord, User
from competehub_api.models.enums import UserRole


def create_user(
    user_id: int,
    role: UserRole,
    email: str,
    capabilities: list[str] | None = None,
) -> int:
    db.session.add(
        User(
            id=user_id,
            email=email,
            password_hash="not-used",
            display_name=email.split("@", 1)[0],
            role=role,
            capabilities=capabilities or [],
        )
    )
    db.session.commit()
    return user_id


def login(client, user_id: int) -> None:
    with client.session_transaction() as session:
        session["user_id"] = user_id


def complete_edition_payload(series_id: int) -> dict:
    return {
        "series_id": series_id,
        "edition_label": "2026",
        "title": "National AI Innovation Challenge",
        "short_title": "AI Challenge",
        "category": "innovation",
        "organizer": "Example University",
        "source_name": "Example University Notice",
        "source_url": "https://example.edu/notices/ai-2026",
        "official_url": "https://example.org/ai-2026",
        "summary": "A source-backed national innovation competition.",
        "eligibility": "Enrolled undergraduate students.",
        "participant_forms": ["individual", "team"],
        "team_size": "1-5",
        "suitable_majors": ["Computer Science"],
        "suitable_grades": ["Year 2", "Year 3"],
        "stages": [
            {
                "stage_key": "registration",
                "stage_type": "registration",
                "label": "Registration",
                "order": 1,
                "time_nodes": [
                    {
                        "logical_node_key": "registration-open",
                        "node_type": "registration_start",
                        "occurs_at": "2026-07-31T16:00:00Z",
                        "description": "Registration opens",
                        "prominence": "secondary",
                    },
                    {
                        "logical_node_key": "registration-deadline",
                        "node_type": "registration_deadline",
                        "occurs_at": "2026-08-15T16:00:00Z",
                        "description": "Registration closes",
                        "prominence": "primary",
                    },
                ],
            }
        ],
    }


def create_series(client) -> int:
    response = client.post(
        "/api/v1/admin/competition_series",
        json={"canonical_name": "National AI Innovation Challenge"},
    )
    assert response.status_code == 201
    return response.get_json()["data"]["id"]


def create_edition(client, series_id: int) -> dict:
    response = client.post(
        "/api/v1/admin/competitions",
        json=complete_edition_payload(series_id),
    )
    assert response.status_code == 201
    return response.get_json()["data"]


def test_editor_creates_series_and_immutable_candidate_revision(client, app) -> None:
    with app.app_context():
        editor_id = create_user(10, UserRole.ADMIN, "editor@example.edu", ["competition_editor"])
    login(client, editor_id)

    series_id = create_series(client)
    created = create_edition(client, series_id)

    assert created["series_id"] == series_id
    assert created["edition_label"] == "2026"
    assert created["lifecycle_status"] == "unpublished"
    assert created["published_revision_id"] is None
    assert created["revision"]["revision_number"] == 1
    assert created["revision"]["revision_status"] == "draft"
    assert created["revision"]["base_revision_id"] is None
    assert created["revision"]["stages"][0]["order"] == 1
    assert created["revision"]["stages"][0]["time_nodes"][1]["node_revision"] == 1

    workspace = client.get(f"/api/v1/admin/competitions/{created['id']}")
    assert workspace.status_code == 200
    assert workspace.get_json()["data"]["active_revision"]["id"] == created["revision"]["id"]
    workspaces = client.get("/api/v1/admin/competitions")
    assert workspaces.status_code == 200
    assert workspaces.get_json()["data"]["items"][0]["id"] == created["id"]


def test_submit_requires_complete_http_source_and_valid_chronology(client, app) -> None:
    with app.app_context():
        editor_id = create_user(11, UserRole.ADMIN, "editor-2@example.edu", ["competition_editor"])
    login(client, editor_id)
    series_id = create_series(client)

    payload = complete_edition_payload(series_id)
    payload["source_url"] = "javascript:alert(1)"
    payload["stages"][0]["time_nodes"][0]["occurs_at"] = "2026-08-20T16:00:00Z"
    response = client.post("/api/v1/admin/competitions", json=payload)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"

    created = create_edition(client, series_id)
    revision_id = created["revision"]["id"]
    response = client.patch(
        f"/api/v1/admin/competition_revisions/{revision_id}",
        json={"summary": None},
    )
    assert response.status_code == 200

    response = client.post(f"/api/v1/admin/competition_revisions/{revision_id}/submit_review")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"
    assert "summary" in response.get_json()["error"]["details"]["missing_fields"]


def test_create_rejects_duplicate_revision_structure_keys(client, app) -> None:
    with app.app_context():
        editor_id = create_user(
            18, UserRole.ADMIN, "editor-keys@example.edu", ["competition_editor"]
        )
    login(client, editor_id)
    series_id = create_series(client)

    duplicate_stage_payload = complete_edition_payload(series_id)
    duplicate_stage_payload["stages"].append(
        {
            "stage_key": "registration",
            "stage_type": "submission",
            "label": "Submission",
            "order": 2,
            "time_nodes": [],
        }
    )
    duplicate_stage_response = client.post(
        "/api/v1/admin/competitions", json=duplicate_stage_payload
    )

    duplicate_node_payload = complete_edition_payload(series_id)
    duplicate_node_payload["edition_label"] = "2027"
    duplicate_node_payload["stages"][0]["time_nodes"][1]["logical_node_key"] = (
        duplicate_node_payload["stages"][0]["time_nodes"][0]["logical_node_key"]
    )
    duplicate_node_response = client.post("/api/v1/admin/competitions", json=duplicate_node_payload)

    assert duplicate_stage_response.status_code == 400
    assert duplicate_stage_response.get_json()["error"]["code"] == "validation_error"
    assert duplicate_node_response.status_code == 400
    assert duplicate_node_response.get_json()["error"]["code"] == "validation_error"


def test_distinct_reviewer_atomically_publishes_without_mutating_snapshot(client, app) -> None:
    with app.app_context():
        editor_id = create_user(12, UserRole.ADMIN, "editor-3@example.edu", ["competition_editor"])
        reviewer_id = create_user(
            13, UserRole.ADMIN, "reviewer@example.edu", ["competition_reviewer"]
        )
    login(client, editor_id)
    series_id = create_series(client)
    created = create_edition(client, series_id)
    edition_id = created["id"]
    revision_id = created["revision"]["id"]

    submitted = client.post(f"/api/v1/admin/competition_revisions/{revision_id}/submit_review")
    assert submitted.status_code == 200
    assert submitted.get_json()["data"]["revision_status"] == "pending_review"

    self_review = client.post(
        f"/api/v1/admin/competition_revisions/{revision_id}/review",
        json={"action": "approve", "comment": "I submitted this."},
    )
    assert self_review.status_code == 403
    assert self_review.get_json()["error"]["code"] == "forbidden"

    login(client, reviewer_id)
    pending = client.get("/api/v1/admin/competition_revisions?status=pending_review")
    assert pending.status_code == 200
    assert [item["id"] for item in pending.get_json()["data"]["items"]] == [revision_id]
    assert pending.get_json()["data"]["items"][0]["differences"]
    assert "public_visibility" in pending.get_json()["data"]["items"][0]["impact"]

    approved = client.post(
        f"/api/v1/admin/competition_revisions/{revision_id}/review",
        json={"action": "approve", "comment": "Source and chronology verified."},
    )
    assert approved.status_code == 200
    assert approved.get_json()["data"]["revision_status"] == "approved"
    assert approved.get_json()["data"]["published_revision_id"] == revision_id

    login(client, editor_id)
    immutable = client.patch(
        f"/api/v1/admin/competition_revisions/{revision_id}",
        json={"summary": "Mutated after review."},
    )
    assert immutable.status_code == 409

    public_detail = client.get(f"/api/v1/competitions/{edition_id}")
    assert public_detail.status_code == 200
    assert public_detail.get_json()["data"]["title"] == "National AI Innovation Challenge"
    assert public_detail.get_json()["data"]["revision_id"] == revision_id

    with app.app_context():
        review = ReviewRecord.query.one()
        assert review.target_type == "competition_revision"
        assert review.target_id == revision_id
        assert review.submitted_by_id == editor_id
        assert review.reviewed_by_id == reviewer_id
        assert review.comment == "Source and chronology verified."
        assert review.differences
        assert review.impact["public_visibility"] == "publish"
        assert review.decided_at is not None

        actions = {event.action for event in AuditLog.query.all()}
        assert {
            "competition_series.create",
            "competition_revision.create",
            "competition_revision.submit_review",
            "competition_revision.approve",
        } <= actions


def test_student_cannot_use_editor_or_reviewer_endpoints(client, app) -> None:
    with app.app_context():
        student_id = create_user(14, UserRole.STUDENT, "student@example.edu")
    login(client, student_id)

    series_response = client.post(
        "/api/v1/admin/competition_series",
        json={"canonical_name": "Forbidden Series"},
    )
    queue_response = client.get("/api/v1/admin/competition_revisions?status=pending_review")

    assert series_response.status_code == 403
    assert queue_response.status_code == 403


def test_admin_without_competition_capability_cannot_use_workbench(client, app) -> None:
    with app.app_context():
        admin_id = create_user(17, UserRole.ADMIN, "unprivileged-admin@example.edu")
    login(client, admin_id)

    assert client.get("/api/v1/admin/competition_series").status_code == 403
    assert (
        client.post(
            "/api/v1/admin/competition_series",
            json={"canonical_name": "Forbidden Admin Series"},
        ).status_code
        == 403
    )


def test_distinct_reviewer_can_reject_without_publishing(client, app) -> None:
    with app.app_context():
        editor_id = create_user(15, UserRole.ADMIN, "editor-4@example.edu", ["competition_editor"])
        reviewer_id = create_user(
            16, UserRole.ADMIN, "reviewer-2@example.edu", ["competition_reviewer"]
        )
    login(client, editor_id)
    series_id = create_series(client)
    created = create_edition(client, series_id)
    revision_id = created["revision"]["id"]
    assert (
        client.post(f"/api/v1/admin/competition_revisions/{revision_id}/submit_review").status_code
        == 200
    )

    login(client, reviewer_id)
    rejected = client.post(
        f"/api/v1/admin/competition_revisions/{revision_id}/review",
        json={"action": "reject", "comment": "The source evidence is insufficient."},
    )

    assert rejected.status_code == 200
    assert rejected.get_json()["data"]["revision_status"] == "rejected"
    assert rejected.get_json()["data"]["published_revision_id"] is None
    assert client.get(f"/api/v1/competitions/{created['id']}").status_code == 404
