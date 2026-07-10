from __future__ import annotations

from http import HTTPStatus
from typing import Any

from competehub_api.extensions import db
from competehub_api.models import (
    AuditLog,
    Competition,
    CompetitionTag,
    CompetitionTagLink,
    CompetitionTimeNode,
    ReviewRecord,
    User,
)
from competehub_api.models.enums import CompetitionStatus, ReviewStatus
from competehub_api.repositories.competitions import get_competition_tag_by_code
from competehub_api.repositories.reviews import latest_pending_competition_review
from competehub_api.services.errors import ServiceError

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
EDITABLE_STATUSES = {CompetitionStatus.DRAFT, CompetitionStatus.REJECTED}
REVIEWABLE_STATUSES = {CompetitionStatus.PENDING_REVIEW}
POST_PUBLICATION_TARGET_STATUSES = {
    CompetitionStatus.OFFLINE,
    CompetitionStatus.ARCHIVED,
    CompetitionStatus.CANCELLED,
    CompetitionStatus.EXPIRED,
}
PUBLICATION_REQUIRED_FIELDS = ("title", "source_name", "source_url", "summary")


def create_draft_competition(payload: dict[str, Any], actor: User) -> Competition:
    payload = payload.copy()
    time_nodes = payload.pop("time_nodes", [])
    tags = _resolve_tags(payload.pop("tags", []))
    competition = Competition(
        **payload,
        status=CompetitionStatus.DRAFT,
        created_by_id=actor.id,
    )
    _replace_time_nodes(competition, time_nodes)
    _replace_tags(competition, tags)
    db.session.add(competition)
    db.session.flush()
    _write_audit(actor, "competition.create", competition, {"status": competition.status.value})
    db.session.commit()
    return competition


def update_competition(
    competition: Competition,
    payload: dict[str, Any],
    actor: User,
) -> Competition:
    if competition.status not in EDITABLE_STATUSES:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "competition cannot be updated from its current status",
            {"status": competition.status.value},
        )

    payload = payload.copy()
    changed_fields = sorted(payload)
    time_nodes = payload.pop("time_nodes", None)
    tag_payloads = payload.pop("tags", None)
    tags = _resolve_tags(tag_payloads) if tag_payloads is not None else None

    for field, value in payload.items():
        setattr(competition, field, value)
    if time_nodes is not None:
        _replace_time_nodes(competition, time_nodes)
    if tags is not None:
        _replace_tags(competition, tags)
    _write_audit(
        actor,
        "competition.update",
        competition,
        {"fields": changed_fields},
    )
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
    comment: str,
) -> Competition:
    if competition.status not in REVIEWABLE_STATUSES:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "competition cannot be reviewed from its current status",
            {"status": competition.status.value},
        )
    if not comment.strip():
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "review comment is required",
            {"field": "comment"},
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
    review = latest_pending_competition_review(competition)
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


def maintain_competition_status(
    competition: Competition,
    actor: User,
    target_status: str,
    reason: str,
) -> Competition:
    status = CompetitionStatus(target_status)
    if (
        competition.status != CompetitionStatus.PUBLISHED
        or status not in POST_PUBLICATION_TARGET_STATUSES
    ):
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "competition cannot change to the requested status",
            {"from_status": competition.status.value, "to_status": status.value},
        )

    previous_status = competition.status
    competition.status = status
    _write_audit(
        actor,
        f"competition.{status.value}",
        competition,
        {
            "from_status": previous_status.value,
            "to_status": status.value,
            "reason": reason,
        },
    )
    db.session.commit()
    return competition


def _resolve_tags(tag_payloads: list[dict[str, Any]]) -> list[CompetitionTag]:
    tags = []
    for payload in tag_payloads:
        tag = get_competition_tag_by_code(payload["code"])
        if tag is not None and (tag.name != payload["name"] or tag.tag_type != payload["tag_type"]):
            raise ServiceError(
                HTTPStatus.CONFLICT,
                "conflict",
                "tag code already exists with different facts",
                {"code": payload["code"]},
            )
        if tag is None:
            tag = CompetitionTag(**payload)
        tags.append(tag)
    return tags


def _replace_time_nodes(competition: Competition, payloads: list[dict[str, Any]]) -> None:
    competition.time_nodes = [CompetitionTimeNode(**payload) for payload in payloads]


def _replace_tags(competition: Competition, tags: list[CompetitionTag]) -> None:
    competition.tag_links = [CompetitionTagLink(tag=tag) for tag in tags]


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
