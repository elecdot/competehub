from __future__ import annotations

from competehub_api.models import Competition, ReviewRecord
from competehub_api.models.enums import ReviewStatus


def latest_pending_competition_review(competition: Competition) -> ReviewRecord | None:
    return (
        ReviewRecord.query.filter_by(
            target_type="competition",
            target_id=competition.id,
            status=ReviewStatus.PENDING,
        )
        .order_by(ReviewRecord.id.desc())
        .first()
    )
