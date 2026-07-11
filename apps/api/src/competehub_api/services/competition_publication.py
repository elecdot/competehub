from __future__ import annotations

from http import HTTPStatus

from competehub_api.extensions import db
from competehub_api.models import AuditLog, Competition, User
from competehub_api.models.enums import CompetitionStatus
from competehub_api.services.errors import ServiceError

POST_PUBLICATION_TARGET_STATUSES = {
    CompetitionStatus.OFFLINE,
    CompetitionStatus.ARCHIVED,
    CompetitionStatus.CANCELLED,
    CompetitionStatus.EXPIRED,
}


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
    db.session.add(
        AuditLog(
            actor_id=actor.id,
            action=f"competition.{status.value}",
            target_type="competition",
            target_id=competition.id,
            result="success",
            detail={
                "from_status": previous_status.value,
                "to_status": status.value,
                "reason": reason,
            },
        )
    )
    db.session.commit()
    return competition
