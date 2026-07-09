from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from competehub_api.extensions import db
from competehub_api.models import AuditLog, Competition, ReviewRecord, User
from competehub_api.models.enums import CompetitionStatus, ReviewStatus


@dataclass(frozen=True)
class ServiceError(Exception):
    status_code: int
    code: str
    message: str
    details: dict[str, Any] | None = None


REVIEW_ACTIONS: dict[str, tuple[ReviewStatus, CompetitionStatus, str]] = {
    "approve": (
        ReviewStatus.APPROVED,
        CompetitionStatus.PUBLISHED,
        "competition.approve",
    ),
    "reject": (
        ReviewStatus.REJECTED,
        CompetitionStatus.REJECTED,
        "competition.reject",
    ),
    "return": (
        ReviewStatus.RETURNED,
        CompetitionStatus.DRAFT,
        "competition.return",
    ),
}

SUBMITTABLE_STATUSES = {CompetitionStatus.DRAFT, CompetitionStatus.REJECTED}
REVIEWABLE_STATUSES = {CompetitionStatus.PENDING_REVIEW}
PUBLICATION_REQUIRED_FIELDS = ("title", "source_name", "source_url", "summary")


def create_draft_competition(payload: dict[str, Any], actor: User) -> Competition:
    title = _required_text(payload, "title")
    source_name = _required_text(payload, "source_name")
    source_url = _required_text(payload, "source_url")

    competition = Competition(
        title=title,
        short_title=_optional_text(payload, "short_title"),
        category=_optional_text(payload, "category"),
        organizer=_optional_text(payload, "organizer"),
        host=_optional_text(payload, "host"),
        source_name=source_name,
        source_url=source_url,
        official_url=_optional_text(payload, "official_url"),
        attachment_url=_optional_text(payload, "attachment_url"),
        summary=_optional_text(payload, "summary"),
        detail=_optional_text(payload, "detail"),
        eligibility=_optional_text(payload, "eligibility"),
        team_size=_optional_text(payload, "team_size"),
        participant_form=_optional_text(payload, "participant_form"),
        suitable_majors=_optional_list(payload, "suitable_majors"),
        suitable_grades=_optional_list(payload, "suitable_grades"),
        value_notes=_optional_text(payload, "value_notes"),
        status=CompetitionStatus.DRAFT,
        created_by_id=actor.id,
    )
    db.session.add(competition)
    db.session.flush()
    _write_audit(actor, "competition.create", competition, {"status": competition.status.value})
    db.session.commit()
    return competition


def submit_competition_for_review(competition: Competition, actor: User) -> Competition:
    if competition.status not in SUBMITTABLE_STATUSES:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "competition cannot be submitted from its current status",
            {"status": competition.status.value},
        )

    missing_fields = [
        field for field in PUBLICATION_REQUIRED_FIELDS if not getattr(competition, field)
    ]
    if missing_fields:
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "competition is missing required publication fields",
            {"missing_fields": missing_fields},
        )

    competition.status = CompetitionStatus.PENDING_REVIEW
    review = ReviewRecord(
        target_type="competition",
        target_id=competition.id,
        submitted_by_id=actor.id,
        status=ReviewStatus.PENDING,
    )
    db.session.add(review)
    _write_audit(
        actor,
        "competition.submit_review",
        competition,
        {"status": competition.status.value},
    )
    db.session.commit()
    return competition


def review_competition(
    competition: Competition,
    actor: User,
    action: str,
    comment: str | None = None,
) -> Competition:
    if competition.status not in REVIEWABLE_STATUSES:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "competition cannot be reviewed from its current status",
            {"status": competition.status.value},
        )

    try:
        review_status, competition_status, audit_action = REVIEW_ACTIONS[action]
    except KeyError as error:
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "unsupported review action",
            {"allowed_actions": sorted(REVIEW_ACTIONS)},
        ) from error

    competition.status = competition_status
    review = _latest_pending_review(competition)
    if review is None:
        review = ReviewRecord(
            target_type="competition",
            target_id=competition.id,
            submitted_by_id=competition.created_by_id,
        )
        db.session.add(review)

    review.status = review_status
    review.reviewed_by_id = actor.id
    review.comment = comment
    _write_audit(
        actor,
        audit_action,
        competition,
        {"status": competition.status.value, "comment": comment},
    )
    db.session.commit()
    return competition


def serialize_competition(competition: Competition) -> dict[str, Any]:
    return {
        "id": competition.id,
        "title": competition.title,
        "short_title": competition.short_title,
        "category": competition.category,
        "organizer": competition.organizer,
        "host": competition.host,
        "source_name": competition.source_name,
        "source_url": competition.source_url,
        "official_url": competition.official_url,
        "attachment_url": competition.attachment_url,
        "summary": competition.summary,
        "detail": competition.detail,
        "eligibility": competition.eligibility,
        "team_size": competition.team_size,
        "participant_form": competition.participant_form,
        "suitable_majors": competition.suitable_majors,
        "suitable_grades": competition.suitable_grades,
        "value_notes": competition.value_notes,
        "status": competition.status.value,
        "created_by_id": competition.created_by_id,
    }


def _latest_pending_review(competition: Competition) -> ReviewRecord | None:
    return (
        ReviewRecord.query.filter_by(
            target_type="competition",
            target_id=competition.id,
            status=ReviewStatus.PENDING,
        )
        .order_by(ReviewRecord.id.desc())
        .first()
    )


def _write_audit(
    actor: User,
    action: str,
    competition: Competition,
    detail: dict[str, Any] | None = None,
) -> None:
    db.session.add(
        AuditLog(
            actor_id=actor.id,
            action=action,
            target_type="competition",
            target_id=competition.id,
            result="success",
            detail=detail or {},
        )
    )


def _required_text(payload: dict[str, Any], field: str) -> str:
    value = _optional_text(payload, field)
    if value is None:
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "request body is missing required fields",
            {"missing_fields": [field]},
        )
    return value


def _optional_text(payload: dict[str, Any], field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "request field must be a non-empty string",
            {"field": field},
        )
    return value.strip()


def _optional_list(payload: dict[str, Any], field: str) -> list | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, list):
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "request field must be a list",
            {"field": field},
        )
    return value
