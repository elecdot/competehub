from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
    StudentProfile,
    Subscription,
    User,
)
from competehub_api.models.enums import ReminderStatus, SubscriptionStatus, UserRole
from competehub_api.services.auth import start_session
from competehub_api.services.reminder_delivery import (
    dispatch_due_reminders,
    requeue_failed_reminders,
)
from competehub_api.timezones import stored_datetime_as_utc


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
    max_title = "T" * 255
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
        unconfirmed_student_id = create_user(
            41, UserRole.STUDENT, "successor-unconfirmed-student@example.edu"
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
                ReminderSetting(id=3, user_id=unconfirmed_student_id, enabled=True),
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
                reminder_confirmed_at=datetime(2026, 7, 1, tzinfo=UTC),
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
                reminder_confirmed_at=datetime(2026, 7, 1, tzinfo=UTC),
            )
        )
        db.session.add(
            Subscription(
                id=3,
                user_id=unconfirmed_student_id,
                competition_id=edition_id,
                reminder_enabled=True,
                remind_days=3,
                node_types=["registration_deadline"],
                reminder_confirmed_at=None,
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
                attempt_count=1,
                failed_at=datetime(2026, 8, 10, 16, tzinfo=UTC),
                last_error_code="message_persistence_unavailable",
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
        json={"title": max_title, "stages": stages},
    )
    assert updated.status_code == 200
    assert updated.get_json()["data"]["impact"]["affected_active_subscriptions"] == 3
    assert updated.get_json()["data"]["impact"]["pending_reminders_to_supersede"] == 2
    assert updated.get_json()["data"]["impact"]["future_reminders_to_create"] == 1
    assert updated.get_json()["data"]["impact"]["schedule_change_messages_estimate"] == 3
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
            ReminderStatus.FAILED,
            ReminderStatus.PENDING,
        ]
        assert reminders[0].cancel_reason == "competition_revision_superseded"
        assert reminders[1].cancel_reason == "competition_revision_superseded"
        assert reminders[1].attempt_count == 1
        assert reminders[1].failed_at is not None
        assert reminders[1].last_error_code == "message_persistence_unavailable"
        assert reminders[2].user_id == student_id
        assert reminders[2].time_node_snapshot_id == changed_deadline["id"]
        assert reminders[2].logical_node_key == changed_deadline["logical_node_key"]
        assert reminders[2].time_node_revision == changed_deadline["node_revision"]
        assert reminders[2].user_id != unconfirmed_student_id
        assert len(reminders[2].title) == 255
        assert reminders[2].title.endswith(": registration_deadline")
        messages = (
            Message.query.filter_by(
                competition_id=edition_id,
                message_type="competition_time_changed",
            )
            .order_by(Message.user_id)
            .all()
        )
        assert {message.user_id for message in messages} == {
            student_id,
            disabled_student_id,
            unconfirmed_student_id,
        }
        successor_revision = db.session.get(CompetitionRevision, successor_id)
        assert successor_revision is not None
        assert successor_revision.decided_at is not None
        assert successor_revision.published_at is not None
        expected_event_at = stored_datetime_as_utc(successor_revision.decided_at)
        assert stored_datetime_as_utc(successor_revision.published_at) == expected_event_at
        for message in messages:
            assert message.reminder_id is None
            assert message.idempotency_key == (f"competition_revision:{successor_id}:time_changed")
            assert stored_datetime_as_utc(message.event_occurred_at) == expected_event_at
            assert len(message.title_snapshot) == 255
            assert message.title_snapshot.endswith(" schedule changed")
            assert message.body_snapshot == "Review the updated competition timeline."
            assert message.target_snapshot == {
                "competition_id": edition_id,
                "competition_title": max_title,
                "node_type": None,
                "node_occurs_at": None,
                "reason_summary": "Competition timeline changed.",
            }
            assert (
                stored_datetime_as_utc(message.retained_until)
                - stored_datetime_as_utc(message.created_at)
            ) == timedelta(days=365)


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
                reminder_confirmed_at=datetime(2026, 7, 1, tzinfo=UTC),
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


def test_override_reason_only_revision_refreshes_pending_reminder_in_place(client, app) -> None:
    with app.app_context():
        editor_id = create_user(
            137,
            UserRole.ADMIN,
            "override-reason-editor@example.edu",
            ["competition_editor"],
        )
        reviewer_id = create_user(
            138,
            UserRole.ADMIN,
            "override-reason-reviewer@example.edu",
            ["competition_reviewer"],
        )
        student_id = create_user(
            139,
            UserRole.STUDENT,
            "override-reason-student@example.edu",
        )

    login(client, editor_id)
    payload = complete_edition_payload(create_series(client))
    opening_payload = next(
        node
        for stage in payload["stages"]
        for node in stage["time_nodes"]
        if node["logical_node_key"] == "registration-open"
    )
    opening_payload["prominence"] = "primary"
    opening_payload["prominence_override_reason"] = (
        "Official source presents registration opening as a primary milestone."
    )
    deadline_payload = next(
        node
        for stage in payload["stages"]
        for node in stage["time_nodes"]
        if node["logical_node_key"] == "registration-deadline"
    )
    deadline_payload["prominence"] = "secondary"
    deadline_payload["prominence_override_reason"] = (
        "Official source initially presents this deadline as secondary."
    )
    created = client.post("/api/v1/admin/competitions", json=payload).get_json()["data"]
    edition_id = created["id"]
    initial_revision_id = created["revision"]["id"]
    submitted = client.post(
        f"/api/v1/admin/competition_revisions/{initial_revision_id}/submit_review"
    )
    assert submitted.status_code == 200, submitted.get_json()
    login(client, reviewer_id)
    assert (
        client.post(
            f"/api/v1/admin/competition_revisions/{initial_revision_id}/review",
            json={"action": "approve", "comment": "Initial source verified."},
        ).status_code
        == 200
    )

    with app.app_context():
        initial = db.session.get(CompetitionRevision, initial_revision_id)
        assert initial is not None
        deadline = next(
            node for node in initial.time_nodes if node.logical_node_key == "registration-deadline"
        )
        original_snapshot_id = deadline.id
        original_node_revision = deadline.node_revision
        original_due_at = datetime(2026, 8, 12, 16, tzinfo=UTC)
        db.session.add_all(
            [
                ReminderSetting(id=137, user_id=student_id, enabled=True),
                Subscription(
                    id=137,
                    user_id=student_id,
                    competition_id=edition_id,
                    reminder_enabled=True,
                    remind_days=3,
                    node_types=["registration_deadline"],
                    reminder_confirmed_at=datetime(2026, 7, 1, tzinfo=UTC),
                ),
                Reminder(
                    id=137,
                    user_id=student_id,
                    competition_id=edition_id,
                    time_node_snapshot_id=deadline.id,
                    logical_node_key=deadline.logical_node_key,
                    time_node_revision=deadline.node_revision,
                    node_type=deadline.node_type,
                    due_at=original_due_at,
                    title="Original registration reminder",
                    status=ReminderStatus.PENDING,
                ),
            ]
        )
        db.session.commit()

    login(client, editor_id)
    successor = client.post(
        f"/api/v1/admin/competitions/{edition_id}/revisions",
        json={"reason": "Clarify the prominence override evidence."},
    ).get_json()["data"]
    successor_id = successor["id"]
    stages = successor["stages"]
    successor_deadline = next(
        node
        for stage in stages
        for node in stage["time_nodes"]
        if node["logical_node_key"] == "registration-deadline"
    )
    successor_deadline["prominence_override_reason"] = (
        "Official source clarification still presents this deadline as secondary."
    )
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
    reason_change = next(
        change
        for change in updated_data["comparison"]["time_node_changes"]
        if change["logical_node_key"] == "registration-deadline"
    )
    assert reason_change["before"]["node_revision"] == original_node_revision
    assert reason_change["after"]["node_revision"] == original_node_revision
    assert updated_data["impact"]["pending_reminders_to_supersede"] == 0
    assert updated_data["impact"]["future_reminders_to_create"] == 0
    assert updated_data["impact"]["schedule_change_messages_estimate"] == 0
    assert (
        client.post(f"/api/v1/admin/competition_revisions/{successor_id}/submit_review").status_code
        == 200
    )

    login(client, reviewer_id)
    approved = client.post(
        f"/api/v1/admin/competition_revisions/{successor_id}/review",
        json={"action": "approve", "comment": "Override evidence verified."},
    )
    assert approved.status_code == 200

    with app.app_context():
        revision = db.session.get(CompetitionRevision, successor_id)
        assert revision is not None
        current_deadline = next(
            node for node in revision.time_nodes if node.logical_node_key == "registration-deadline"
        )
        assert current_deadline.id != original_snapshot_id
        assert current_deadline.node_revision == original_node_revision
        reminders = Reminder.query.filter_by(
            user_id=student_id,
            competition_id=edition_id,
        ).all()
        assert len(reminders) == 1
        reminder = reminders[0]
        assert reminder.id == 137
        assert reminder.status == ReminderStatus.PENDING
        assert reminder.cancel_reason is None
        assert reminder.time_node_snapshot_id == current_deadline.id
        assert reminder.time_node_revision == original_node_revision
        assert stored_datetime_as_utc(reminder.due_at) == original_due_at
        review = ReviewRecord.query.filter_by(target_id=successor_id).one()
        assert review.impact["pending_reminders_to_supersede"] == 0
        assert review.impact["future_reminders_to_create"] == 0
        assert (
            Message.query.filter_by(
                competition_id=edition_id,
                message_type="competition_time_changed",
            ).count()
            == 0
        )


def test_unchanged_node_moves_retryable_failed_snapshot_and_preserves_retry_evidence(
    client, app
) -> None:
    with app.app_context():
        editor_id = create_user(
            134, UserRole.ADMIN, "failed-move-editor@example.edu", ["competition_editor"]
        )
        reviewer_id = create_user(
            135,
            UserRole.ADMIN,
            "failed-move-reviewer@example.edu",
            ["competition_reviewer"],
        )
        student_id = create_user(136, UserRole.STUDENT, "failed-move-student@example.edu")
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
        deadline = next(
            node for node in initial.time_nodes if node.logical_node_key == "registration-deadline"
        )
        original_snapshot_id = deadline.id
        retry_at = datetime(2026, 8, 12, 16, tzinfo=UTC)
        failed_at = datetime(2026, 8, 12, 15, 59, tzinfo=UTC)
        db.session.add_all(
            [
                Subscription(
                    id=136,
                    user_id=student_id,
                    competition_id=edition_id,
                    status=SubscriptionStatus.ACTIVE,
                    reminder_enabled=True,
                    remind_days=3,
                    node_types=["registration_deadline"],
                    reminder_confirmed_at=datetime(2026, 7, 1, tzinfo=UTC),
                ),
                ReminderSetting(id=136, user_id=student_id, enabled=True),
                Reminder(
                    id=136,
                    user_id=student_id,
                    competition_id=edition_id,
                    time_node_snapshot_id=deadline.id,
                    logical_node_key=deadline.logical_node_key,
                    time_node_revision=deadline.node_revision,
                    node_type=deadline.node_type,
                    due_at=retry_at,
                    title="Original failed reminder",
                    body="Original body",
                    status=ReminderStatus.FAILED,
                    attempt_count=1,
                    next_attempt_at=retry_at,
                    last_error_code="message_persistence_unavailable",
                    failed_at=failed_at,
                ),
            ]
        )
        db.session.commit()

    login(client, reviewer_id)
    assert (
        client.post(
            f"/api/v1/admin/competition_revisions/{initial_revision_id}/review",
            json={"action": "approve", "comment": "Initial facts verified."},
        ).status_code
        == 200
    )
    login(client, editor_id)
    successor = client.post(
        f"/api/v1/admin/competitions/{edition_id}/revisions",
        json={"reason": "Clarify the competition title only."},
    ).get_json()["data"]
    successor_id = successor["id"]
    assert (
        client.patch(
            f"/api/v1/admin/competition_revisions/{successor_id}",
            json={"title": "National AI Innovation Challenge — clarified"},
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
            json={"action": "approve", "comment": "Title clarification verified."},
        ).status_code
        == 200
    )

    with app.app_context():
        successor_revision = db.session.get(CompetitionRevision, successor_id)
        current_deadline = next(
            node
            for stage in successor_revision.stages
            for node in stage.time_nodes
            if node.logical_node_key == "registration-deadline"
        )
        reminder = db.session.get(Reminder, 136)
        assert current_deadline.id != original_snapshot_id
        assert reminder.status == ReminderStatus.FAILED
        assert reminder.time_node_snapshot_id == current_deadline.id
        assert reminder.attempt_count == 1
        assert reminder.last_error_code == "message_persistence_unavailable"
        assert reminder.failed_at is not None
        assert reminder.next_attempt_at is not None
        assert reminder.title == f"{successor_revision.title}: {current_deadline.node_type}"

        assert requeue_failed_reminders(now=retry_at) == {"requeued": 1, "suppressed": 0}
        assert dispatch_due_reminders(now=retry_at) == {
            "dispatched": 1,
            "cancelled": 0,
            "failed": 0,
        }
        assert db.session.get(Reminder, 136).status == ReminderStatus.SENT
        assert Message.query.filter_by(reminder_id=136).count() == 1


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
    max_title = "L" * 255
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
        client.patch(
            f"/api/v1/admin/competition_revisions/{revision_id}",
            json={"title": max_title},
        ).status_code
        == 200
    )
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
        message = messages[0]
        competition = db.session.get(Competition, edition_id)
        assert competition is not None
        assert competition.lifecycle_changed_at is not None
        assert message.user_id == student_id
        assert message.reminder_id is None
        assert message.idempotency_key == (
            f"competition:{edition_id}:published_revision:{revision_id}:cancelled"
        )
        assert stored_datetime_as_utc(message.event_occurred_at) == (
            stored_datetime_as_utc(competition.lifecycle_changed_at)
        )
        assert len(message.title_snapshot) == 255
        assert message.title_snapshot.endswith(" is cancelled")
        assert message.body_snapshot == "Organizer cancelled the 2026 edition."
        assert message.target_snapshot == {
            "competition_id": edition_id,
            "competition_title": max_title,
            "node_type": None,
            "node_occurs_at": None,
            "reason_summary": "Organizer cancelled the 2026 edition.",
        }
        assert (
            stored_datetime_as_utc(message.retained_until)
            - stored_datetime_as_utc(message.created_at)
        ) == timedelta(days=365)


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
        student_id = create_user(53, UserRole.STUDENT, "offline-student@example.edu")
    login(client, editor_id)
    edition = create_published_edition(client, editor_id, reviewer_id)
    edition_id = edition["id"]
    initial_revision_id = edition["revision"]["id"]
    with app.app_context():
        initial_revision = db.session.get(CompetitionRevision, initial_revision_id)
        assert initial_revision is not None
        initial_deadline = next(
            node
            for node in initial_revision.time_nodes
            if node.logical_node_key == "registration-deadline"
        )
        initial_open = next(
            node
            for node in initial_revision.time_nodes
            if node.logical_node_key == "registration-open"
        )
        db.session.add_all(
            [
                StudentProfile(
                    id=53,
                    user_id=student_id,
                    interest_tags=[],
                    goal_preferences=[],
                    blocked_tags=[],
                ),
                ReminderSetting(id=53, user_id=student_id, enabled=True),
            ]
        )
        db.session.add(
            Subscription(
                id=53,
                user_id=student_id,
                competition_id=edition_id,
                status=SubscriptionStatus.ACTIVE,
                reminder_enabled=True,
                remind_days=3,
                node_types=["registration_deadline"],
                reminder_confirmed_at=datetime.now(UTC),
            )
        )
        db.session.add(
            Reminder(
                id=53,
                user_id=student_id,
                competition_id=edition_id,
                time_node_snapshot_id=initial_deadline.id,
                logical_node_key=initial_deadline.logical_node_key,
                time_node_revision=initial_deadline.node_revision,
                node_type=initial_deadline.node_type,
                due_at=stored_datetime_as_utc(initial_deadline.occurs_at) - timedelta(days=3),
                title="Offline-sensitive reminder",
                status=ReminderStatus.PENDING,
            )
        )
        db.session.add(
            Reminder(
                id=54,
                user_id=student_id,
                competition_id=edition_id,
                time_node_snapshot_id=initial_open.id,
                logical_node_key=initial_open.logical_node_key,
                time_node_revision=initial_open.node_revision,
                node_type=initial_open.node_type,
                due_at=stored_datetime_as_utc(initial_open.occurs_at) - timedelta(days=3),
                title="Requeued offline-sensitive reminder",
                status=ReminderStatus.PENDING,
                attempt_count=1,
                failed_at=datetime.now(UTC) - timedelta(minutes=1),
                last_error_code="message_persistence_unavailable",
            )
        )
        db.session.commit()
        initial_deadline_id = initial_deadline.id
        initial_node_revision = initial_deadline.node_revision
    login(client, student_id)
    assert (
        client.patch("/api/v1/me/preferences", json={"message_enabled": False}).status_code == 200
    )
    with app.app_context():
        globally_cancelled = db.session.get(Reminder, 53)
        assert globally_cancelled.status == ReminderStatus.CANCELLED
        assert globally_cancelled.cancel_reason == "global_reminder_disabled"
        requeued = db.session.get(Reminder, 54)
        assert requeued.status == ReminderStatus.FAILED
        assert requeued.attempt_count == 1
        assert requeued.last_error_code == "message_persistence_unavailable"
        assert requeued.cancel_reason == "global_reminder_disabled"
        # Reproduce the retry worker's FAILED -> PENDING window before lifecycle
        # authority changes. The retained failure fields distinguish this from a
        # never-attempted pending plan.
        requeued.status = ReminderStatus.PENDING
        requeued.cancel_reason = None
        db.session.commit()
    login(client, editor_id)
    assert (
        client.patch(
            f"/api/v1/admin/competitions/{edition_id}/status",
            json={"status": "offline", "reason": "Official link was hijacked."},
        ).status_code
        == 200
    )
    with app.app_context():
        first_offline_competition = db.session.get(Competition, edition_id)
        assert first_offline_competition is not None
        assert first_offline_competition.lifecycle_changed_at is not None
        first_offline_changed_at = stored_datetime_as_utc(
            first_offline_competition.lifecycle_changed_at
        )
    assert client.get(f"/api/v1/competitions/{edition_id}").status_code == 404
    direct_restore = client.patch(
        f"/api/v1/admin/competitions/{edition_id}/status",
        json={"status": "published", "reason": "Unsafe direct restoration."},
    )
    assert direct_restore.status_code == 409

    unchanged_response = client.post(
        f"/api/v1/admin/competitions/{edition_id}/revisions",
        json={"reason": "Recheck the withdrawn public facts."},
    )
    assert unchanged_response.status_code == 201, unchanged_response.get_json()
    unchanged = unchanged_response.get_json()["data"]
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

    with app.app_context():
        successor_revision = db.session.get(CompetitionRevision, successor_id)
        successor_deadline = next(
            node
            for node in successor_revision.time_nodes
            if node.logical_node_key == "registration-deadline"
        )
        assert successor_deadline.id != initial_deadline_id
        assert successor_deadline.node_revision == initial_node_revision
        terminal = db.session.get(Reminder, 53)
        assert terminal.status == ReminderStatus.CANCELLED
        assert terminal.cancel_reason == "competition_offline"
        requeued = db.session.get(Reminder, 54)
        assert requeued.status == ReminderStatus.FAILED
        assert requeued.attempt_count == 1
        assert requeued.failed_at is not None
        assert requeued.last_error_code == "message_persistence_unavailable"
        assert requeued.next_attempt_at is None
        assert requeued.cancel_reason == "competition_offline"

    login(client, student_id)
    assert client.patch("/api/v1/me/preferences", json={"message_enabled": True}).status_code == 200
    with app.app_context():
        terminal = db.session.get(Reminder, 53)
        assert terminal.status == ReminderStatus.CANCELLED
        assert terminal.cancel_reason == "competition_offline"
        requeued = db.session.get(Reminder, 54)
        assert requeued.status == ReminderStatus.FAILED
        assert requeued.cancel_reason == "competition_offline"
        assert requeued.attempt_count == 1
        assert requeued.last_error_code == "message_persistence_unavailable"
        assert (
            Reminder.query.filter_by(
                user_id=student_id,
                competition_id=edition_id,
                status=ReminderStatus.PENDING,
            ).count()
            == 0
        )

    login(client, editor_id)
    assert (
        client.patch(
            f"/api/v1/admin/competitions/{edition_id}/status",
            json={"status": "offline", "reason": "Replacement link was also withdrawn."},
        ).status_code
        == 200
    )
    with app.app_context():
        messages = (
            Message.query.filter_by(
                user_id=student_id,
                competition_id=edition_id,
                message_type="competition_offline",
            )
            .order_by(Message.id)
            .all()
        )
        assert len(messages) == 2
        assert [message.idempotency_key for message in messages] == [
            f"competition:{edition_id}:published_revision:{initial_revision_id}:offline",
            f"competition:{edition_id}:published_revision:{successor_id}:offline",
        ]
        competition = db.session.get(Competition, edition_id)
        assert competition is not None
        assert competition.lifecycle_changed_at is not None
        assert [message.reminder_id for message in messages] == [None, None]
        assert [stored_datetime_as_utc(message.event_occurred_at) for message in messages] == [
            first_offline_changed_at,
            stored_datetime_as_utc(competition.lifecycle_changed_at),
        ]
        assert [message.title_snapshot for message in messages] == [
            "National AI Innovation Challenge is offline",
            "National AI Innovation Challenge is offline",
        ]
        assert [message.body_snapshot for message in messages] == [
            "Official link was hijacked.",
            "Replacement link was also withdrawn.",
        ]
        assert [message.target_snapshot for message in messages] == [
            {
                "competition_id": edition_id,
                "competition_title": "National AI Innovation Challenge",
                "node_type": None,
                "node_occurs_at": None,
                "reason_summary": "Official link was hijacked.",
            },
            {
                "competition_id": edition_id,
                "competition_title": "National AI Innovation Challenge",
                "node_type": None,
                "node_occurs_at": None,
                "reason_summary": "Replacement link was also withdrawn.",
            },
        ]
        assert all(
            stored_datetime_as_utc(message.retained_until)
            - stored_datetime_as_utc(message.created_at)
            == timedelta(days=365)
            for message in messages
        )


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
