from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

from sqlalchemy import select

from competehub_api.extensions import db
from competehub_api.models import (
    AuditLog,
    Competition,
    CompetitionRevision,
    CompetitionSeries,
    CompetitionStage,
    CompetitionTimeNode,
    ReviewRecord,
    User,
)
from competehub_api.models.enums import (
    CompetitionRevisionStatus,
    CompetitionStatus,
    ReviewStatus,
)
from competehub_api.repositories.competitions import (
    get_competition_series,
    get_competition_series_by_name,
)
from competehub_api.services.errors import ServiceError

REVISION_FIELDS = (
    "title",
    "short_title",
    "category",
    "organizer",
    "host",
    "source_name",
    "source_url",
    "official_url",
    "attachment_url",
    "summary",
    "detail",
    "eligibility",
    "team_size",
    "participant_forms",
    "suitable_majors",
    "suitable_grades",
    "value_notes",
)
REQUIRED_PUBLICATION_FIELDS = (
    "title",
    "category",
    "organizer",
    "source_name",
    "source_url",
    "summary",
    "eligibility",
    "participant_forms",
    "suitable_majors",
    "suitable_grades",
)
CORE_NODE_TYPES = {
    "registration_start",
    "registration_deadline",
    "submission_deadline",
    "competition_start",
    "competition_end",
    "defense_or_review",
    "result_announcement",
}


def create_series(payload: dict[str, Any], actor: User) -> CompetitionSeries:
    name = payload["canonical_name"]
    if get_competition_series_by_name(name) is not None:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "competition series already exists",
            {"canonical_name": name},
        )
    series = CompetitionSeries(canonical_name=name, created_by_id=actor.id)
    db.session.add(series)
    db.session.flush()
    _write_audit(actor, "competition_series.create", "competition_series", series.id)
    db.session.commit()
    return series


def create_edition_with_revision(payload: dict[str, Any], actor: User) -> Competition:
    payload = payload.copy()
    series_id = payload.pop("series_id")
    edition_label = payload.pop("edition_label")
    stages = payload.pop("stages", []) or []
    series = get_competition_series(series_id)
    if series is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "competition series not found")
    existing = db.session.scalar(
        select(Competition).where(
            Competition.series_id == series_id,
            Competition.edition_label == edition_label,
        )
    )
    if existing is not None:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "competition edition already exists",
            {"competition_id": existing.id},
        )

    edition = Competition(
        series=series,
        edition_label=edition_label,
        status=CompetitionStatus.UNPUBLISHED,
        created_by_id=actor.id,
        **_projection_fields(payload),
    )
    revision = CompetitionRevision(
        competition=edition,
        revision_number=1,
        revision_status=CompetitionRevisionStatus.DRAFT,
        created_by_id=actor.id,
        **{field: payload.get(field) for field in REVISION_FIELDS},
    )
    db.session.add(edition)
    _replace_stages(revision, edition, stages)
    db.session.flush()
    _write_audit(
        actor,
        "competition_revision.create",
        "competition_revision",
        revision.id,
        {"competition_id": edition.id, "revision_number": 1},
    )
    db.session.commit()
    return edition


def update_revision(
    revision: CompetitionRevision,
    payload: dict[str, Any],
    actor: User,
) -> CompetitionRevision:
    if revision.revision_status != CompetitionRevisionStatus.DRAFT:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "only draft revisions are editable",
            {"revision_status": revision.revision_status.value},
        )
    payload = payload.copy()
    stages = payload.pop("stages", None)
    for field, value in payload.items():
        setattr(revision, field, value)
    if stages is not None:
        _replace_stages(revision, revision.competition, stages or [])
    changed_fields = sorted([*payload, *(["stages"] if stages is not None else [])])
    _write_audit(
        actor,
        "competition_revision.update",
        "competition_revision",
        revision.id,
        {"fields": changed_fields},
    )
    db.session.commit()
    return revision


def submit_revision(revision: CompetitionRevision, actor: User) -> CompetitionRevision:
    if revision.revision_status != CompetitionRevisionStatus.DRAFT:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "only draft revisions can be submitted",
        )
    missing_fields = [
        field for field in REQUIRED_PUBLICATION_FIELDS if not getattr(revision, field)
    ]
    if not revision.stages:
        missing_fields.append("stages")
    primary_core_nodes = [
        node
        for stage in revision.stages
        for node in stage.time_nodes
        if node.prominence == "primary" and node.node_type in CORE_NODE_TYPES
    ]
    if not primary_core_nodes:
        missing_fields.append("primary_core_time_node")
    if "team" in revision.participant_forms and not revision.team_size:
        missing_fields.append("team_size")
    if missing_fields:
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "competition revision is incomplete",
            {"missing_fields": sorted(set(missing_fields))},
        )

    now = datetime.now(UTC)
    revision.revision_status = CompetitionRevisionStatus.PENDING_REVIEW
    revision.submitted_by_id = actor.id
    revision.submitted_at = now
    differences = revision_differences(revision)
    impact = revision_impact(revision)
    db.session.add(
        ReviewRecord(
            target_type="competition_revision",
            target_id=revision.id,
            submitted_by_id=actor.id,
            status=ReviewStatus.PENDING,
            differences=differences,
            impact=impact,
        )
    )
    _write_audit(
        actor,
        "competition_revision.submit_review",
        "competition_revision",
        revision.id,
        {"revision_number": revision.revision_number},
    )
    db.session.commit()
    return revision


def review_revision(
    revision: CompetitionRevision,
    actor: User,
    action: str,
    comment: str,
) -> CompetitionRevision:
    revision = db.session.scalar(
        select(CompetitionRevision)
        .where(CompetitionRevision.id == revision.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if revision is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "competition revision not found")
    if revision.revision_status != CompetitionRevisionStatus.PENDING_REVIEW:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "only pending revisions can be reviewed",
        )
    if revision.submitted_by_id == actor.id:
        raise ServiceError(
            HTTPStatus.FORBIDDEN,
            "forbidden",
            "the submitter cannot review the same revision",
        )
    review = db.session.scalar(
        select(ReviewRecord)
        .where(
            ReviewRecord.target_type == "competition_revision",
            ReviewRecord.target_id == revision.id,
            ReviewRecord.status == ReviewStatus.PENDING,
        )
        .with_for_update()
    )
    if review is None:
        raise ServiceError(HTTPStatus.CONFLICT, "conflict", "pending review evidence is missing")

    now = datetime.now(UTC)
    status_by_action = {
        "approve": (CompetitionRevisionStatus.APPROVED, ReviewStatus.APPROVED),
        "reject": (CompetitionRevisionStatus.REJECTED, ReviewStatus.REJECTED),
        "return": (CompetitionRevisionStatus.RETURNED, ReviewStatus.RETURNED),
    }
    revision_status, review_status = status_by_action[action]
    edition = db.session.scalar(
        select(Competition).where(Competition.id == revision.competition_id).with_for_update()
    )
    if edition is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "competition edition not found")
    if action == "approve":
        if revision.base_revision_id != edition.published_revision_id:
            raise ServiceError(
                HTTPStatus.CONFLICT,
                "stale_revision",
                "the public revision changed after this candidate was created",
                {"published_revision_id": edition.published_revision_id},
            )
        edition.published_revision_id = revision.id
        edition.status = CompetitionStatus.PUBLISHED
        revision.published_at = now
        _sync_projection(edition, revision)

    revision.revision_status = revision_status
    revision.decided_at = now
    review.status = review_status
    review.reviewed_by_id = actor.id
    review.comment = comment
    review.decided_at = now
    _write_audit(
        actor,
        f"competition_revision.{action}",
        "competition_revision",
        revision.id,
        {"competition_id": edition.id, "revision_number": revision.revision_number},
    )
    db.session.commit()
    return revision


def revision_differences(revision: CompetitionRevision) -> list[dict[str, Any]]:
    base = revision.competition.published_revision if revision.base_revision_id else None
    differences = []
    for field in REVISION_FIELDS:
        before = getattr(base, field) if base is not None else None
        after = getattr(revision, field)
        if before != after:
            differences.append({"field": field, "before": before, "after": after})
    if revision.stages:
        differences.append(
            {
                "field": "stages",
                "before": 0 if base is None else len(base.stages),
                "after": len(revision.stages),
            }
        )
    return differences


def revision_impact(revision: CompetitionRevision) -> dict[str, Any]:
    visibility = "publish" if revision.base_revision_id is None else "replace"
    return {
        "public_visibility": visibility,
        "public_visibility_change": (
            "publish_initial_revision"
            if revision.base_revision_id is None
            else "replace_public_revision"
        ),
        "search_reindex_required": True,
        "recommendation_refresh_required": True,
        "active_subscriptions": 0,
        "affected_active_subscriptions": 0,
        "pending_reminders_to_supersede": 0,
        "future_reminders_to_create": 0,
        "schedule_change_messages_estimate": 0,
        "schedule_semantic_changes": sum(len(stage.time_nodes) for stage in revision.stages),
        "as_of": datetime.now(UTC).isoformat(),
    }


def revision_completeness(revision: CompetitionRevision) -> dict[str, Any]:
    missing_fields = [
        field for field in REQUIRED_PUBLICATION_FIELDS if not getattr(revision, field)
    ]
    if not revision.stages:
        missing_fields.append("stages")
    if not any(
        node.prominence == "primary" and node.node_type in CORE_NODE_TYPES
        for stage in revision.stages
        for node in stage.time_nodes
    ):
        missing_fields.append("primary_core_time_node")
    if "team" in (revision.participant_forms or []) and not revision.team_size:
        missing_fields.append("team_size")
    missing_fields = sorted(set(missing_fields))
    return {"is_complete": not missing_fields, "missing_fields": missing_fields, "warnings": []}


def review_evidence(revision: CompetitionRevision) -> tuple[list, dict]:
    review = db.session.scalar(
        select(ReviewRecord)
        .where(
            ReviewRecord.target_type == "competition_revision",
            ReviewRecord.target_id == revision.id,
        )
        .order_by(ReviewRecord.id.desc())
    )
    if review is None:
        return revision_differences(revision), revision_impact(revision)
    return review.differences or [], review.impact or {}


def _replace_stages(
    revision: CompetitionRevision,
    edition: Competition,
    payloads: list[dict[str, Any]],
) -> None:
    revision.stages.clear()
    for payload in payloads:
        payload = payload.copy()
        nodes = payload.pop("time_nodes", [])
        stage = CompetitionStage(revision=revision, **payload)
        for node_payload in nodes:
            stage.time_nodes.append(
                CompetitionTimeNode(
                    revision=revision,
                    competition=edition,
                    **node_payload,
                )
            )
        revision.stages.append(stage)


def _projection_fields(payload: dict[str, Any]) -> dict[str, Any]:
    fields = {
        field: payload.get(field) for field in REVISION_FIELDS if field != "participant_forms"
    }
    forms = payload.get("participant_forms") or []
    fields["participant_form"] = "team" if "team" in forms else next(iter(forms), None)
    return fields


def _sync_projection(edition: Competition, revision: CompetitionRevision) -> None:
    for field in REVISION_FIELDS:
        if field == "participant_forms":
            forms = revision.participant_forms or []
            edition.participant_form = "team" if "team" in forms else next(iter(forms), None)
        else:
            setattr(edition, field, getattr(revision, field))


def _write_audit(
    actor: User,
    action: str,
    target_type: str,
    target_id: int,
    detail: dict[str, Any] | None = None,
) -> None:
    db.session.add(
        AuditLog(
            actor_id=actor.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            result="success",
            detail=detail or {},
        )
    )
