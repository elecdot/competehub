from __future__ import annotations

from datetime import UTC, datetime

import pytest

from competehub_api.extensions import db
from competehub_api.models import (
    AuditLog,
    Competition,
    CompetitionRevision,
    Message,
    Reminder,
    ReminderSetting,
    ReviewRecord,
    Subscription,
    User,
)
from competehub_api.models.enums import ReminderStatus, UserRole
from competehub_api.services.auth import start_session


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
    with client.application.app_context():
        user = db.session.get(User, user_id)
        assert user is not None
        with client.session_transaction() as session:
            start_session(session, user)


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
        "registration_applicability": "applicable",
        "participant_forms": ["individual", "team"],
        "team_size": "1-5",
        "major_scope": "selected",
        "grade_scope": "selected",
        "suitable_majors": ["Computer Science"],
        "suitable_grades": ["Year 2", "Year 3"],
        "tags": [
            {
                "code": "ai",
                "name": "Artificial Intelligence",
                "tag_type": "topic",
            }
        ],
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


def create_published_edition(
    client,
    editor_id: int,
    reviewer_id: int,
    *,
    elapsed_nodes: bool = False,
) -> dict:
    series_id = create_series(client)
    payload = complete_edition_payload(series_id)
    if elapsed_nodes:
        payload["stages"][0]["time_nodes"][0]["occurs_at"] = "2020-07-01T16:00:00Z"
        payload["stages"][0]["time_nodes"][1]["occurs_at"] = "2020-07-15T16:00:00Z"
    response = client.post("/api/v1/admin/competitions", json=payload)
    assert response.status_code == 201
    edition = response.get_json()["data"]
    revision_id = edition["revision"]["id"]
    assert (
        client.post(f"/api/v1/admin/competition_revisions/{revision_id}/submit_review").status_code
        == 200
    )
    login(client, reviewer_id)
    assert (
        client.post(
            f"/api/v1/admin/competition_revisions/{revision_id}/review",
            json={"action": "approve", "comment": "Initial publication verified."},
        ).status_code
        == 200
    )
    login(client, editor_id)
    return edition


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
    assert created["revision"]["stages"][0]["time_nodes"][1]["prominence"] == "primary"
    assert created["revision"]["major_scope"] == "selected"
    assert created["revision"]["grade_scope"] == "selected"
    assert created["revision"]["tags"][0]["code"] == "ai"

    update_payload = complete_edition_payload(series_id)
    update_payload.pop("series_id")
    update_payload.pop("edition_label")
    update_payload["stages"].append(
        {
            "stage_key": "submission",
            "stage_type": "submission",
            "label": "Submission",
            "order": 2,
            "time_nodes": [
                {
                    "logical_node_key": "submission-note",
                    "node_type": "other",
                    "occurs_at": "2026-08-20T16:00:00Z",
                    "description": "Submission instructions published",
                }
            ],
        }
    )
    updated = client.patch(
        f"/api/v1/admin/competition_revisions/{created['revision']['id']}",
        json=update_payload,
    )
    assert updated.status_code == 200
    assert [stage["stage_key"] for stage in updated.get_json()["data"]["stages"]] == [
        "registration",
        "submission",
    ]

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


def test_completeness_requires_explicit_scopes_and_reports_pair_warnings(client, app) -> None:
    with app.app_context():
        editor_id = create_user(
            19, UserRole.ADMIN, "editor-scope@example.edu", ["competition_editor"]
        )
    login(client, editor_id)
    series_id = create_series(client)
    payload = complete_edition_payload(series_id)
    payload.pop("major_scope")
    payload["stages"][0]["time_nodes"] = payload["stages"][0]["time_nodes"][:1]

    created_response = client.post("/api/v1/admin/competitions", json=payload)
    assert created_response.status_code == 201
    revision_id = created_response.get_json()["data"]["revision"]["id"]
    detail = client.get(f"/api/v1/admin/competition_revisions/{revision_id}").get_json()["data"]

    assert "major_scope" in detail["completeness"]["missing_fields"]
    assert {
        "code": "missing_pair",
        "stage_key": "registration",
        "missing_node_type": "registration_deadline",
    } in detail["completeness"]["warnings"]
    submit = client.post(f"/api/v1/admin/competition_revisions/{revision_id}/submit_review")
    assert submit.status_code == 400


def test_selected_scope_requires_values_and_prominence_override_requires_reason(
    client, app
) -> None:
    with app.app_context():
        editor_id = create_user(
            20, UserRole.ADMIN, "editor-values@example.edu", ["competition_editor"]
        )
    login(client, editor_id)
    series_id = create_series(client)
    payload = complete_edition_payload(series_id)
    payload["suitable_majors"] = []
    payload["stages"][0]["time_nodes"][1]["prominence"] = "secondary"

    response = client.post("/api/v1/admin/competitions", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"

    payload["suitable_majors"] = ["Computer Science"]
    payload["stages"][0]["time_nodes"][1]["prominence_override_reason"] = (
        "Official source marks this deadline as secondary."
    )
    accepted = client.post("/api/v1/admin/competitions", json=payload)
    assert accepted.status_code == 201
    with app.app_context():
        audit = AuditLog.query.filter_by(action="competition_revision.create").one()
        assert audit.detail["prominence_overrides"] == [
            {
                "logical_node_key": "registration-deadline",
                "default": "primary",
                "selected": "secondary",
                "reason": "Official source marks this deadline as secondary.",
            }
        ]


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
    with app.app_context():
        assert ReviewRecord.query.count() == 0

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
    comparison = pending.get_json()["data"]["items"][0]["comparison"]
    assert comparison["stage_changes"][0]["change"] == "added"
    assert {item["logical_node_key"] for item in comparison["time_node_changes"]} == {
        "registration-open",
        "registration-deadline",
    }

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

    with app.app_context():
        edition = db.session.get(Competition, edition_id)
        edition.title = "Tampered mutable projection"
        edition.participant_forms = ["team"]
        db.session.commit()

    public_detail = client.get(f"/api/v1/competitions/{edition_id}")
    assert public_detail.status_code == 200
    assert public_detail.get_json()["data"]["title"] == "National AI Innovation Challenge"
    assert public_detail.get_json()["data"]["revision_id"] == revision_id
    assert public_detail.get_json()["data"]["participant_forms"] == ["individual", "team"]
    assert public_detail.get_json()["data"]["major_scope"] == "selected"
    assert public_detail.get_json()["data"]["grade_scope"] == "selected"
    assert public_detail.get_json()["data"]["tags"] == ["Artificial Intelligence"]
    assert public_detail.get_json()["data"]["content_updated_at"] is not None
    public_node = public_detail.get_json()["data"]["time_nodes"][0]
    assert public_node["snapshot_id"] == public_node["id"]
    assert public_node["stage_label"] == "Registration"
    assert public_node["stage_order"] == 1

    with app.app_context():
        review = ReviewRecord.query.one()
        assert review.target_type == "competition_revision"
        assert review.target_id == revision_id
        assert review.submitted_by_id == editor_id
        assert review.reviewed_by_id == reviewer_id
        assert review.comment == "Source and chronology verified."
        assert review.submitted_at is not None
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


def test_successor_revision_keeps_public_snapshot_until_approval_and_reconciles_nodes(
    client, app
) -> None:
    with app.app_context():
        editor_id = create_user(
            31, UserRole.ADMIN, "successor-editor@example.edu", ["competition_editor"]
        )
        reviewer_id = create_user(
            32, UserRole.ADMIN, "successor-reviewer@example.edu", ["competition_reviewer"]
        )
        student_id = create_user(33, UserRole.STUDENT, "successor-student@example.edu")
        disabled_student_id = create_user(
            37, UserRole.STUDENT, "successor-disabled-student@example.edu"
        )
    login(client, editor_id)
    series_id = create_series(client)
    created = create_edition(client, series_id)
    edition_id = created["id"]
    initial_revision_id = created["revision"]["id"]
    assert (
        client.post(
            f"/api/v1/admin/competition_revisions/{initial_revision_id}/submit_review"
        ).status_code
        == 200
    )

    with app.app_context():
        initial = db.session.get(CompetitionRevision, initial_revision_id)
        assert initial is not None
        deadline = next(
            node for node in initial.time_nodes if node.logical_node_key == "registration-deadline"
        )
        db.session.add_all(
            [
                ReminderSetting(id=1, user_id=student_id, enabled=True),
                ReminderSetting(id=2, user_id=disabled_student_id, enabled=False),
            ]
        )
        db.session.add(
            Subscription(
                id=1,
                user_id=student_id,
                competition_id=edition_id,
                reminder_enabled=True,
                remind_days=3,
                node_types=["registration_deadline"],
            )
        )
        db.session.add(
            Subscription(
                id=2,
                user_id=disabled_student_id,
                competition_id=edition_id,
                reminder_enabled=True,
                remind_days=3,
                node_types=["registration_deadline"],
            )
        )
        db.session.add(
            Reminder(
                id=1,
                user_id=student_id,
                competition_id=edition_id,
                time_node_snapshot_id=deadline.id,
                logical_node_key=deadline.logical_node_key,
                time_node_revision=deadline.node_revision,
                node_type="registration_deadline",
                due_at=datetime(2026, 8, 12, 16, tzinfo=UTC),
                title="Old deadline reminder",
                status=ReminderStatus.PENDING,
            )
        )
        db.session.add(
            Reminder(
                id=2,
                user_id=disabled_student_id,
                competition_id=edition_id,
                time_node_snapshot_id=deadline.id,
                logical_node_key=deadline.logical_node_key,
                time_node_revision=deadline.node_revision,
                node_type="registration_deadline",
                due_at=datetime(2026, 8, 12, 16, tzinfo=UTC),
                title="Globally disabled old deadline reminder",
                status=ReminderStatus.PENDING,
            )
        )
        db.session.commit()
    login(client, reviewer_id)
    assert (
        client.post(
            f"/api/v1/admin/competition_revisions/{initial_revision_id}/review",
            json={"action": "approve", "comment": "Initial source verified."},
        ).status_code
        == 200
    )

    login(client, editor_id)
    successor_response = client.post(
        f"/api/v1/admin/competitions/{edition_id}/revisions",
        json={"reason": "Official registration deadline was postponed."},
    )
    assert successor_response.status_code == 201
    successor = successor_response.get_json()["data"]
    successor_id = successor["id"]
    assert successor["revision_number"] == 2
    assert successor["base_revision_id"] == initial_revision_id
    assert successor["revision_status"] == "draft"

    parallel = client.post(
        f"/api/v1/admin/competitions/{edition_id}/revisions",
        json={"reason": "A second concurrent correction."},
    )
    assert parallel.status_code == 409
    assert parallel.get_json()["error"]["code"] == "active_revision_exists"
    assert parallel.get_json()["error"]["details"]["revision_id"] == successor_id

    before_public = client.get(f"/api/v1/competitions/{edition_id}").get_json()["data"]
    old_deadline = next(
        node
        for node in before_public["time_nodes"]
        if node["logical_node_key"] == "registration-deadline"
    )
    stages = successor["stages"]
    successor_deadline = next(
        node
        for stage in stages
        for node in stage["time_nodes"]
        if node["logical_node_key"] == "registration-deadline"
    )
    assert successor_deadline["id"] != old_deadline["id"]
    assert successor_deadline["node_revision"] == old_deadline["node_revision"]
    successor_deadline["occurs_at"] = "2026-08-20T16:00:00Z"
    for stage in stages:
        for node in stage["time_nodes"]:
            node.pop("id", None)
            node.pop("node_revision", None)
        stage.pop("id", None)

    updated = client.patch(
        f"/api/v1/admin/competition_revisions/{successor_id}",
        json={"stages": stages},
    )
    assert updated.status_code == 200
    assert updated.get_json()["data"]["impact"]["affected_active_subscriptions"] == 2
    assert updated.get_json()["data"]["impact"]["pending_reminders_to_supersede"] == 2
    assert updated.get_json()["data"]["impact"]["future_reminders_to_create"] == 1
    assert updated.get_json()["data"]["impact"]["schedule_change_messages_estimate"] == 2
    assert (
        client.post(f"/api/v1/admin/competition_revisions/{successor_id}/submit_review").status_code
        == 200
    )

    while_pending = client.get(f"/api/v1/competitions/{edition_id}").get_json()["data"]
    assert while_pending["revision_id"] == initial_revision_id
    assert (
        next(
            node
            for node in while_pending["time_nodes"]
            if node["logical_node_key"] == "registration-deadline"
        )["occurs_at"]
        == old_deadline["occurs_at"]
    )

    login(client, reviewer_id)
    approved = client.post(
        f"/api/v1/admin/competition_revisions/{successor_id}/review",
        json={"action": "approve", "comment": "Corrected deadline matches the source."},
    )
    assert approved.status_code == 200
    after_public = client.get(f"/api/v1/competitions/{edition_id}").get_json()["data"]
    assert after_public["revision_id"] == successor_id
    changed_deadline = next(
        node
        for node in after_public["time_nodes"]
        if node["logical_node_key"] == "registration-deadline"
    )
    assert changed_deadline["node_revision"] == old_deadline["node_revision"] + 1
    assert changed_deadline["occurs_at"] == "2026-08-20T16:00:00+00:00"

    with app.app_context():
        initial = db.session.get(CompetitionRevision, initial_revision_id)
        assert initial is not None
        original = next(
            node for node in initial.time_nodes if node.logical_node_key == "registration-deadline"
        )
        assert original.id == old_deadline["id"]
        assert original.occurs_at.replace(tzinfo=UTC).isoformat() == old_deadline["occurs_at"]
        events = AuditLog.query.filter_by(action="competition_revision.reconcile").all()
        assert len(events) == 1
        assert events[0].target_id == successor_id
        assert events[0].detail["reason"] == "Corrected deadline matches the source."
        assert len(events[0].detail["time_node_changes"]) == 1
        audit_change = events[0].detail["time_node_changes"][0]
        assert audit_change["logical_node_key"] == "registration-deadline"
        assert audit_change["change"] == "changed"
        assert audit_change["before"] == {
            "stage_key": "registration",
            "stage_type": "registration",
            "stage_label": "Registration",
            "stage_order": 1,
            "node_type": "registration_deadline",
            "occurs_at": old_deadline["occurs_at"],
            "description": "Registration closes",
            "prominence": "primary",
            "prominence_override_reason": None,
            "node_revision": old_deadline["node_revision"],
        }
        assert audit_change["after"] == {
            **audit_change["before"],
            "occurs_at": "2026-08-20T16:00:00+00:00",
            "node_revision": old_deadline["node_revision"] + 1,
        }
        reminders = Reminder.query.filter_by(competition_id=edition_id).order_by(Reminder.id).all()
        assert [reminder.status for reminder in reminders] == [
            ReminderStatus.CANCELLED,
            ReminderStatus.CANCELLED,
            ReminderStatus.PENDING,
        ]
        assert reminders[0].cancel_reason == "competition_revision_superseded"
        assert reminders[1].cancel_reason == "competition_revision_superseded"
        assert reminders[2].user_id == student_id
        assert reminders[2].time_node_snapshot_id == changed_deadline["id"]
        assert reminders[2].logical_node_key == changed_deadline["logical_node_key"]
        assert reminders[2].time_node_revision == changed_deadline["node_revision"]
        messages = Message.query.filter_by(
            competition_id=edition_id,
            message_type="competition_time_changed",
        ).all()
        assert {message.user_id for message in messages} == {student_id, disabled_student_id}


@pytest.mark.parametrize("presentation_change", ["stage_metadata", "description"])
def test_presentation_only_revision_moves_pending_reminder_without_schedule_message(
    client, app, presentation_change: str
) -> None:
    with app.app_context():
        editor_id = create_user(
            34, UserRole.ADMIN, "presentation-editor@example.edu", ["competition_editor"]
        )
        reviewer_id = create_user(
            35, UserRole.ADMIN, "presentation-reviewer@example.edu", ["competition_reviewer"]
        )
        student_id = create_user(36, UserRole.STUDENT, "presentation-student@example.edu")
    login(client, editor_id)
    created = create_edition(client, create_series(client))
    edition_id = created["id"]
    initial_revision_id = created["revision"]["id"]
    assert (
        client.post(
            f"/api/v1/admin/competition_revisions/{initial_revision_id}/submit_review"
        ).status_code
        == 200
    )

    with app.app_context():
        initial = db.session.get(CompetitionRevision, initial_revision_id)
        assert initial is not None
        deadline = next(
            node for node in initial.time_nodes if node.logical_node_key == "registration-deadline"
        )
        old_deadline_id = deadline.id
        old_node_revision = deadline.node_revision
        db.session.add(
            Subscription(
                id=3,
                user_id=student_id,
                competition_id=edition_id,
                reminder_enabled=True,
                remind_days=3,
                node_types=["registration_deadline"],
            )
        )
        db.session.add(ReminderSetting(id=3, user_id=student_id, enabled=True))
        db.session.add(
            Reminder(
                id=3,
                user_id=student_id,
                competition_id=edition_id,
                time_node_snapshot_id=deadline.id,
                logical_node_key=deadline.logical_node_key,
                time_node_revision=deadline.node_revision,
                node_type="registration_deadline",
                due_at=datetime(2026, 8, 12, 16, tzinfo=UTC),
                title="Original registration reminder",
                status=ReminderStatus.PENDING,
            )
        )
        db.session.commit()

    login(client, reviewer_id)
    assert (
        client.post(
            f"/api/v1/admin/competition_revisions/{initial_revision_id}/review",
            json={"action": "approve", "comment": "Initial source verified."},
        ).status_code
        == 200
    )
    login(client, editor_id)
    successor = client.post(
        f"/api/v1/admin/competitions/{edition_id}/revisions",
        json={"reason": "Clarify the registration stage presentation."},
    ).get_json()["data"]
    successor_id = successor["id"]
    stages = successor["stages"]
    deadline_payload = next(
        node
        for stage in stages
        for node in stage["time_nodes"]
        if node["logical_node_key"] == "registration-deadline"
    )
    if presentation_change == "stage_metadata":
        stages[0]["stage_type"] = "submission"
        stages[0]["label"] = "Main registration round"
        stages[0]["order"] = 2
    else:
        deadline_payload["description"] = "Registration closes at the published instant"
    for stage in stages:
        stage.pop("id", None)
        for node in stage["time_nodes"]:
            node.pop("id", None)
            node.pop("node_revision", None)

    updated = client.patch(
        f"/api/v1/admin/competition_revisions/{successor_id}",
        json={"stages": stages},
    )
    assert updated.status_code == 200
    updated_data = updated.get_json()["data"]
    preview_change = next(
        change
        for change in updated_data["comparison"]["time_node_changes"]
        if change["logical_node_key"] == "registration-deadline"
    )
    assert preview_change["before"]["stage_type"] == "registration"
    assert preview_change["before"]["stage_label"] == "Registration"
    assert preview_change["before"]["stage_order"] == 1
    assert preview_change["before"]["node_revision"] == old_node_revision
    assert preview_change["after"]["node_revision"] == old_node_revision
    if presentation_change == "stage_metadata":
        assert preview_change["after"]["stage_type"] == "submission"
        assert preview_change["after"]["stage_label"] == "Main registration round"
        assert preview_change["after"]["stage_order"] == 2
    else:
        assert preview_change["after"]["description"] == (
            "Registration closes at the published instant"
        )
    assert updated_data["impact"]["pending_reminders_to_supersede"] == 1
    assert updated_data["impact"]["future_reminders_to_create"] == 1
    assert updated_data["impact"]["schedule_change_messages_estimate"] == 0
    assert (
        client.post(f"/api/v1/admin/competition_revisions/{successor_id}/submit_review").status_code
        == 200
    )
    login(client, reviewer_id)
    assert (
        client.post(
            f"/api/v1/admin/competition_revisions/{successor_id}/review",
            json={"action": "approve", "comment": "Presentation clarification verified."},
        ).status_code
        == 200
    )

    with app.app_context():
        successor_revision = db.session.get(CompetitionRevision, successor_id)
        assert successor_revision is not None
        new_deadline = next(
            node
            for node in successor_revision.time_nodes
            if node.logical_node_key == "registration-deadline"
        )
        assert new_deadline.id != old_deadline_id
        assert new_deadline.node_revision == old_node_revision + 1
        reminders = Reminder.query.filter_by(competition_id=edition_id).order_by(Reminder.id).all()
        assert [reminder.status for reminder in reminders] == [
            ReminderStatus.CANCELLED,
            ReminderStatus.PENDING,
        ]
        assert reminders[0].cancel_reason == "competition_revision_superseded"
        assert reminders[1].time_node_snapshot_id == new_deadline.id
        assert reminders[1].logical_node_key == new_deadline.logical_node_key
        assert reminders[1].time_node_revision == new_deadline.node_revision
        assert reminders[1].title == f"{successor_revision.title}: {new_deadline.node_type}"
        assert reminders[1].body == new_deadline.description
        event = AuditLog.query.filter_by(
            action="competition_revision.reconcile", target_id=successor_id
        ).one()
        deadline_change = next(
            change
            for change in event.detail["time_node_changes"]
            if change["logical_node_key"] == "registration-deadline"
        )
        assert deadline_change["before"] == {
            "stage_key": "registration",
            "stage_type": "registration",
            "stage_label": "Registration",
            "stage_order": 1,
            "node_type": "registration_deadline",
            "occurs_at": "2026-08-15T16:00:00+00:00",
            "description": "Registration closes",
            "prominence": "primary",
            "prominence_override_reason": None,
            "node_revision": old_node_revision,
        }
        expected_after = {
            **deadline_change["before"],
            "node_revision": old_node_revision + 1,
        }
        if presentation_change == "stage_metadata":
            expected_after.update(
                {
                    "stage_type": "submission",
                    "stage_label": "Main registration round",
                    "stage_order": 2,
                }
            )
        else:
            expected_after["description"] = "Registration closes at the published instant"
        assert deadline_change["after"] == expected_after
        review = ReviewRecord.query.filter_by(target_id=successor_id).one()
        review_change = next(
            change
            for change in review.differences
            if change.get("logical_node_key") == "registration-deadline"
        )
        assert review_change == deadline_change
        assert (
            Message.query.filter_by(
                competition_id=edition_id,
                message_type="competition_time_changed",
            ).count()
            == 0
        )


def test_replacement_approval_is_atomic_when_reminder_setting_is_missing(client, app) -> None:
    with app.app_context():
        editor_id = create_user(
            38, UserRole.ADMIN, "missing-setting-editor@example.edu", ["competition_editor"]
        )
        reviewer_id = create_user(
            39, UserRole.ADMIN, "missing-setting-reviewer@example.edu", ["competition_reviewer"]
        )
        student_id = create_user(40, UserRole.STUDENT, "missing-setting-student@example.edu")
    login(client, editor_id)
    edition = create_published_edition(client, editor_id, reviewer_id)
    edition_id = edition["id"]
    initial_revision_id = edition["revision"]["id"]
    with app.app_context():
        db.session.add(
            Subscription(
                id=4,
                user_id=student_id,
                competition_id=edition_id,
                reminder_enabled=True,
                remind_days=3,
                node_types=["registration_deadline"],
            )
        )
        db.session.add(ReminderSetting(id=4, user_id=student_id, enabled=True))
        db.session.commit()

    successor = client.post(
        f"/api/v1/admin/competitions/{edition_id}/revisions",
        json={"reason": "Clarify source-backed summary."},
    ).get_json()["data"]
    successor_id = successor["id"]
    assert (
        client.patch(
            f"/api/v1/admin/competition_revisions/{successor_id}",
            json={"summary": "Clarified source-backed summary."},
        ).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/admin/competition_revisions/{successor_id}/submit_review").status_code
        == 200
    )
    with app.app_context():
        setting = ReminderSetting.query.filter_by(user_id=student_id).one()
        db.session.delete(setting)
        db.session.commit()

    login(client, reviewer_id)
    response = client.post(
        f"/api/v1/admin/competition_revisions/{successor_id}/review",
        json={"action": "approve", "comment": "Attempt approval with corrupt profile state."},
    )

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "internal_server_error"
    with app.app_context():
        competition = db.session.get(Competition, edition_id)
        candidate = db.session.get(CompetitionRevision, successor_id)
        assert competition.published_revision_id == initial_revision_id
        assert candidate.revision_status.value == "pending_review"
        assert ReviewRecord.query.filter_by(target_id=successor_id).count() == 0


def test_historical_lifecycle_detail_keeps_warning_while_offline_returns_404(client, app) -> None:
    with app.app_context():
        editor_id = create_user(
            41,
            UserRole.ADMIN,
            "lifecycle-editor@example.edu",
            ["competition_editor", "competition_maintainer"],
        )
        reviewer_id = create_user(
            42, UserRole.ADMIN, "lifecycle-reviewer@example.edu", ["competition_reviewer"]
        )
        student_id = create_user(43, UserRole.STUDENT, "lifecycle-student@example.edu")
    login(client, editor_id)
    edition = create_edition(client, create_series(client))
    edition_id = edition["id"]
    revision_id = edition["revision"]["id"]
    assert (
        client.post(f"/api/v1/admin/competition_revisions/{revision_id}/submit_review").status_code
        == 200
    )

    with app.app_context():
        published = db.session.get(CompetitionRevision, revision_id)
        deadline = next(
            node
            for node in published.time_nodes
            if node.logical_node_key == "registration-deadline"
        )
        db.session.add(
            Subscription(
                id=2,
                user_id=student_id,
                competition_id=edition_id,
                reminder_enabled=True,
                remind_days=3,
                node_types=["registration_deadline"],
            )
        )
        db.session.add(ReminderSetting(id=5, user_id=student_id, enabled=True))
        db.session.add(
            Reminder(
                id=2,
                user_id=student_id,
                competition_id=edition_id,
                time_node_snapshot_id=deadline.id,
                logical_node_key=deadline.logical_node_key,
                time_node_revision=deadline.node_revision,
                node_type="registration_deadline",
                due_at=datetime(2026, 8, 12, 16, tzinfo=UTC),
                title="Cancellation-sensitive reminder",
                status=ReminderStatus.PENDING,
            )
        )
        db.session.commit()
    login(client, reviewer_id)
    assert (
        client.post(
            f"/api/v1/admin/competition_revisions/{revision_id}/review",
            json={"action": "approve", "comment": "Initial publication verified."},
        ).status_code
        == 200
    )

    login(client, editor_id)
    cancelled = client.patch(
        f"/api/v1/admin/competitions/{edition_id}/status",
        json={"status": "cancelled", "reason": "Organizer cancelled the 2026 edition."},
    )
    assert cancelled.status_code == 200
    historical_detail = client.get(f"/api/v1/competitions/{edition_id}")
    assert historical_detail.status_code == 200
    detail_data = historical_detail.get_json()["data"]
    assert detail_data["status"] == "cancelled"
    assert detail_data["lifecycle_warning"]["status"] == "cancelled"
    assert detail_data["lifecycle_warning"]["reason"] == ("Organizer cancelled the 2026 edition.")
    assert detail_data["lifecycle_warning"]["changed_at"] is not None
    listed_ids = {
        item["id"] for item in client.get("/api/v1/competitions").get_json()["data"]["items"]
    }
    assert edition_id not in listed_ids
    with app.app_context():
        reminder = db.session.get(Reminder, 2)
        assert reminder.status == ReminderStatus.CANCELLED
        assert reminder.cancel_reason == "competition_cancelled"
        messages = Message.query.filter_by(
            competition_id=edition_id,
            message_type="competition_cancelled",
        ).all()
        assert len(messages) == 1
        assert messages[0].user_id == student_id


def test_emergency_offline_cannot_flip_back_but_approved_successor_restores_publication(
    client, app
) -> None:
    with app.app_context():
        editor_id = create_user(
            51,
            UserRole.ADMIN,
            "offline-editor@example.edu",
            ["competition_editor", "competition_maintainer"],
        )
        reviewer_id = create_user(
            52, UserRole.ADMIN, "offline-reviewer@example.edu", ["competition_reviewer"]
        )
    login(client, editor_id)
    edition = create_published_edition(client, editor_id, reviewer_id)
    edition_id = edition["id"]
    assert (
        client.patch(
            f"/api/v1/admin/competitions/{edition_id}/status",
            json={"status": "offline", "reason": "Official link was hijacked."},
        ).status_code
        == 200
    )
    assert client.get(f"/api/v1/competitions/{edition_id}").status_code == 404
    direct_restore = client.patch(
        f"/api/v1/admin/competitions/{edition_id}/status",
        json={"status": "published", "reason": "Unsafe direct restoration."},
    )
    assert direct_restore.status_code == 409

    unchanged = client.post(
        f"/api/v1/admin/competitions/{edition_id}/revisions",
        json={"reason": "Recheck the withdrawn public facts."},
    ).get_json()["data"]
    unchanged_id = unchanged["id"]
    assert (
        client.post(f"/api/v1/admin/competition_revisions/{unchanged_id}/submit_review").status_code
        == 200
    )
    login(client, reviewer_id)
    unchanged_approval = client.post(
        f"/api/v1/admin/competition_revisions/{unchanged_id}/review",
        json={"action": "approve", "comment": "No correction was supplied."},
    )
    assert unchanged_approval.status_code == 409
    assert unchanged_approval.get_json()["error"]["code"] == (
        "offline_restoration_requires_corrected_revision"
    )
    assert (
        client.post(
            f"/api/v1/admin/competition_revisions/{unchanged_id}/review",
            json={"action": "reject", "comment": "A corrected fact is required."},
        ).status_code
        == 200
    )

    login(client, editor_id)
    successor = client.post(
        f"/api/v1/admin/competitions/{edition_id}/revisions",
        json={"reason": "Replace the compromised official link."},
    ).get_json()["data"]
    successor_id = successor["id"]
    assert (
        client.patch(
            f"/api/v1/admin/competition_revisions/{successor_id}",
            json={"official_url": "https://safe.example.org/ai-2026"},
        ).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/admin/competition_revisions/{successor_id}/submit_review").status_code
        == 200
    )
    login(client, reviewer_id)
    assert (
        client.post(
            f"/api/v1/admin/competition_revisions/{successor_id}/review",
            json={"action": "approve", "comment": "Replacement link verified."},
        ).status_code
        == 200
    )
    restored = client.get(f"/api/v1/competitions/{edition_id}")
    assert restored.status_code == 200
    assert restored.get_json()["data"]["revision_id"] == successor_id
    assert restored.get_json()["data"]["status"] == "published"
    assert restored.get_json()["data"]["official_url"] == "https://safe.example.org/ai-2026"


def test_emergency_offline_rejects_candidate_submitted_before_withdrawal(client, app) -> None:
    with app.app_context():
        editor_id = create_user(
            55,
            UserRole.ADMIN,
            "offline-stale-editor@example.edu",
            ["competition_editor", "competition_maintainer"],
        )
        reviewer_id = create_user(
            56,
            UserRole.ADMIN,
            "offline-stale-reviewer@example.edu",
            ["competition_reviewer"],
        )
    login(client, editor_id)
    edition = create_published_edition(client, editor_id, reviewer_id)
    edition_id = edition["id"]
    initial_revision_id = edition["revision"]["id"]
    successor = client.post(
        f"/api/v1/admin/competitions/{edition_id}/revisions",
        json={"reason": "Prepare a replacement official link."},
    ).get_json()["data"]
    successor_id = successor["id"]
    assert (
        client.patch(
            f"/api/v1/admin/competition_revisions/{successor_id}",
            json={"official_url": "https://candidate.example.org/ai-2026"},
        ).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/admin/competition_revisions/{successor_id}/submit_review").status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/admin/competitions/{edition_id}/status",
            json={"status": "offline", "reason": "A later source-integrity incident."},
        ).status_code
        == 200
    )

    login(client, reviewer_id)
    response = client.post(
        f"/api/v1/admin/competition_revisions/{successor_id}/review",
        json={"action": "approve", "comment": "The older candidate looked valid."},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == (
        "offline_restoration_requires_corrected_revision"
    )
    with app.app_context():
        competition = db.session.get(Competition, edition_id)
        candidate = db.session.get(CompetitionRevision, successor_id)
        assert competition.status.value == "offline"
        assert competition.published_revision_id == initial_revision_id
        assert candidate.revision_status.value == "pending_review"
        assert ReviewRecord.query.filter_by(target_id=successor_id).count() == 0


def test_archive_and_expire_reject_current_public_future_nodes(client, app) -> None:
    with app.app_context():
        editor_id = create_user(
            61,
            UserRole.ADMIN,
            "history-editor@example.edu",
            ["competition_editor", "competition_maintainer"],
        )
        reviewer_id = create_user(
            62, UserRole.ADMIN, "history-reviewer@example.edu", ["competition_reviewer"]
        )
    login(client, editor_id)
    edition = create_edition(client, create_series(client))
    edition_id = edition["id"]
    revision_id = edition["revision"]["id"]
    assert (
        client.post(f"/api/v1/admin/competition_revisions/{revision_id}/submit_review").status_code
        == 200
    )
    login(client, reviewer_id)
    assert (
        client.post(
            f"/api/v1/admin/competition_revisions/{revision_id}/review",
            json={"action": "approve", "comment": "Initial publication verified."},
        ).status_code
        == 200
    )

    login(client, editor_id)
    for target_status in ("archived", "expired"):
        response = client.patch(
            f"/api/v1/admin/competitions/{edition_id}/status",
            json={"status": target_status, "reason": "Routine history maintenance."},
        )
        assert response.status_code == 409
        assert response.get_json()["error"]["code"] == "conflict"
        blocking = response.get_json()["error"]["details"]["blocking_nodes"]
        assert {node["logical_node_key"] for node in blocking} == {
            "registration-open",
            "registration-deadline",
        }


@pytest.mark.parametrize("lifecycle_status", ["cancelled", "archived", "expired"])
def test_terminal_lifecycle_rejects_successor_creation(client, app, lifecycle_status: str) -> None:
    with app.app_context():
        editor_id = create_user(
            81,
            UserRole.ADMIN,
            f"terminal-create-{lifecycle_status}-editor@example.edu",
            ["competition_editor", "competition_maintainer"],
        )
        reviewer_id = create_user(
            82,
            UserRole.ADMIN,
            f"terminal-create-{lifecycle_status}-reviewer@example.edu",
            ["competition_reviewer"],
        )
    login(client, editor_id)
    edition = create_published_edition(
        client,
        editor_id,
        reviewer_id,
        elapsed_nodes=True,
    )
    edition_id = edition["id"]
    transition = client.patch(
        f"/api/v1/admin/competitions/{edition_id}/status",
        json={
            "status": lifecycle_status,
            "reason": "The edition reached a terminal lifecycle state.",
        },
    )
    assert transition.status_code == 200

    response = client.post(
        f"/api/v1/admin/competitions/{edition_id}/revisions",
        json={"reason": "An invalid correction after terminal maintenance."},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "conflict"
    assert response.get_json()["error"]["details"]["lifecycle_status"] == lifecycle_status
    with app.app_context():
        assert CompetitionRevision.query.filter_by(competition_id=edition_id).count() == 1
        assert AuditLog.query.filter_by(action="competition_revision.create_successor").count() == 0


@pytest.mark.parametrize("lifecycle_status", ["cancelled", "archived", "expired"])
def test_candidate_submitted_before_terminal_lifecycle_cannot_be_approved(
    client, app, lifecycle_status: str
) -> None:
    with app.app_context():
        editor_id = create_user(
            83,
            UserRole.ADMIN,
            f"terminal-approve-{lifecycle_status}-editor@example.edu",
            ["competition_editor", "competition_maintainer"],
        )
        reviewer_id = create_user(
            84,
            UserRole.ADMIN,
            f"terminal-approve-{lifecycle_status}-reviewer@example.edu",
            ["competition_reviewer"],
        )
        student_id = create_user(
            85,
            UserRole.STUDENT,
            f"terminal-approve-{lifecycle_status}-student@example.edu",
        )
    login(client, editor_id)
    edition = create_published_edition(
        client,
        editor_id,
        reviewer_id,
        elapsed_nodes=True,
    )
    edition_id = edition["id"]
    initial_revision_id = edition["revision"]["id"]
    with app.app_context():
        initial = db.session.get(CompetitionRevision, initial_revision_id)
        assert initial is not None
        deadline = next(
            node for node in initial.time_nodes if node.logical_node_key == "registration-deadline"
        )
        db.session.add_all(
            [
                ReminderSetting(id=10, user_id=student_id, enabled=True),
                Subscription(
                    id=10,
                    user_id=student_id,
                    competition_id=edition_id,
                    reminder_enabled=True,
                    remind_days=3,
                    node_types=["registration_deadline"],
                ),
                Reminder(
                    id=10,
                    user_id=student_id,
                    competition_id=edition_id,
                    time_node_snapshot_id=deadline.id,
                    logical_node_key=deadline.logical_node_key,
                    time_node_revision=deadline.node_revision,
                    node_type=deadline.node_type,
                    due_at=datetime(2020, 7, 12, 16, tzinfo=UTC),
                    title="Terminal lifecycle baseline reminder",
                    status=ReminderStatus.PENDING,
                ),
            ]
        )
        db.session.commit()
    successor = client.post(
        f"/api/v1/admin/competitions/{edition_id}/revisions",
        json={"reason": "Prepare a source-backed clarification."},
    ).get_json()["data"]
    successor_id = successor["id"]
    stages = successor["stages"]
    successor_deadline = next(
        node
        for stage in stages
        for node in stage["time_nodes"]
        if node["logical_node_key"] == "registration-deadline"
    )
    successor_deadline["occurs_at"] = "2026-08-20T16:00:00Z"
    for stage in stages:
        stage.pop("id", None)
        for node in stage["time_nodes"]:
            node.pop("id", None)
            node.pop("node_revision", None)
    assert (
        client.patch(
            f"/api/v1/admin/competition_revisions/{successor_id}",
            json={"stages": stages},
        ).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/admin/competition_revisions/{successor_id}/submit_review").status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/admin/competitions/{edition_id}/status",
            json={
                "status": lifecycle_status,
                "reason": "The edition became terminal after candidate submission.",
            },
        ).status_code
        == 200
    )
    with app.app_context():
        reminders_before_approval = [
            (reminder.id, reminder.status.value, reminder.cancel_reason)
            for reminder in Reminder.query.filter_by(competition_id=edition_id)
            .order_by(Reminder.id)
            .all()
        ]
        messages_before_approval = Message.query.filter_by(competition_id=edition_id).count()

    login(client, reviewer_id)
    response = client.post(
        f"/api/v1/admin/competition_revisions/{successor_id}/review",
        json={"action": "approve", "comment": "The candidate predates terminal state."},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "conflict"
    assert response.get_json()["error"]["details"]["lifecycle_status"] == lifecycle_status
    with app.app_context():
        competition = db.session.get(Competition, edition_id)
        candidate = db.session.get(CompetitionRevision, successor_id)
        assert competition is not None
        assert candidate is not None
        assert competition.status.value == lifecycle_status
        assert competition.published_revision_id == initial_revision_id
        assert candidate.revision_status.value == "pending_review"
        assert candidate.published_at is None
        assert candidate.decided_at is None
        assert ReviewRecord.query.filter_by(target_id=successor_id).count() == 0
        assert [
            (reminder.id, reminder.status.value, reminder.cancel_reason)
            for reminder in Reminder.query.filter_by(competition_id=edition_id)
            .order_by(Reminder.id)
            .all()
        ] == reminders_before_approval
        assert (
            Message.query.filter_by(competition_id=edition_id).count() == messages_before_approval
        )
        assert (
            AuditLog.query.filter_by(
                action="competition_revision.approve", target_id=successor_id
            ).count()
            == 0
        )
        assert (
            AuditLog.query.filter_by(
                action="competition_revision.reconcile", target_id=successor_id
            ).count()
            == 0
        )


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


@pytest.mark.parametrize("action", ["reject", "return"])
def test_terminal_initial_revision_can_continue_as_successor_draft(client, app, action) -> None:
    with app.app_context():
        editor_id = create_user(
            71, UserRole.ADMIN, f"terminal-{action}-editor@example.edu", ["competition_editor"]
        )
        reviewer_id = create_user(
            72,
            UserRole.ADMIN,
            f"terminal-{action}-reviewer@example.edu",
            ["competition_reviewer"],
        )
    login(client, editor_id)
    edition = create_edition(client, create_series(client))
    edition_id = edition["id"]
    revision_id = edition["revision"]["id"]
    assert (
        client.post(f"/api/v1/admin/competition_revisions/{revision_id}/submit_review").status_code
        == 200
    )
    login(client, reviewer_id)
    assert (
        client.post(
            f"/api/v1/admin/competition_revisions/{revision_id}/review",
            json={"action": action, "comment": "More source work is required."},
        ).status_code
        == 200
    )

    login(client, editor_id)
    workspace = next(
        item
        for item in client.get("/api/v1/admin/competitions").get_json()["data"]["items"]
        if item["id"] == edition_id
    )
    assert workspace["active_revision"]["id"] == revision_id
    response = client.post(
        f"/api/v1/admin/competitions/{edition_id}/revisions",
        json={"reason": "Continue from the reviewed terminal candidate."},
    )

    assert response.status_code == 201
    successor = response.get_json()["data"]
    assert successor["revision_number"] == 2
    assert successor["revision_status"] == "draft"
    assert successor["base_revision_id"] is None
    assert successor["title"] == edition["revision"]["title"]
    assert (
        client.patch(
            f"/api/v1/admin/competition_revisions/{successor['id']}",
            json={"summary": "Corrected after review."},
        ).status_code
        == 200
    )


def test_editor_withdraws_pending_revision_back_to_editable_draft(client, app) -> None:
    with app.app_context():
        editor_id = create_user(
            73, UserRole.ADMIN, "withdraw-editor@example.edu", ["competition_editor"]
        )
    login(client, editor_id)
    edition = create_edition(client, create_series(client))
    revision_id = edition["revision"]["id"]
    submitted = client.post(f"/api/v1/admin/competition_revisions/{revision_id}/submit_review")
    assert submitted.status_code == 200
    submitted_at = datetime.fromisoformat(submitted.get_json()["data"]["submitted_at"])
    if submitted_at.tzinfo is None:
        submitted_at = submitted_at.replace(tzinfo=UTC)

    withdrawn = client.post(f"/api/v1/admin/competition_revisions/{revision_id}/withdraw")

    assert withdrawn.status_code == 200
    payload = withdrawn.get_json()["data"]
    assert payload["revision_status"] == "draft"
    assert payload["submitted_by_id"] is None
    assert payload["submitted_at"] is None
    assert (
        client.patch(
            f"/api/v1/admin/competition_revisions/{revision_id}",
            json={"summary": "Corrected before resubmission."},
        ).status_code
        == 200
    )
    with app.app_context():
        event = AuditLog.query.filter_by(
            action="competition_revision.withdraw", target_id=revision_id
        ).one()
        assert event.actor_id == editor_id
        assert event.detail["submitted_by_id"] == editor_id
        assert datetime.fromisoformat(event.detail["submitted_at"]) == submitted_at
