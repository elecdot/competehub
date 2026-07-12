from __future__ import annotations

from sqlalchemy import select

from competehub_api.extensions import db
from competehub_api.models import Competition, CompetitionRevision, ReviewRecord
from competehub_api.models.enums import CompetitionRevisionStatus, ReviewStatus
from competehub_api.schemas.competition_admin import (
    competition_revision_schema,
    edition_workspace_schema,
)
from competehub_api.services.competition_publication import lifecycle_impact
from competehub_api.services.competition_revisions import (
    revision_comparison,
    revision_completeness,
    revision_impact,
)


def revision_read_model(
    revision: CompetitionRevision,
    review: ReviewRecord | None = None,
) -> dict:
    comparison = revision_comparison(revision)
    differences = [
        *comparison["field_changes"],
        *comparison["stage_changes"],
        *comparison["time_node_changes"],
    ]
    impact = revision_impact(revision)
    if review is None and revision.revision_status not in {
        CompetitionRevisionStatus.DRAFT,
        CompetitionRevisionStatus.PENDING_REVIEW,
    }:
        review = _latest_terminal_reviews([revision.id]).get(revision.id)
    if review is not None:
        differences = review.differences or []
        comparison = _comparison_from_differences(differences)
        impact = review.impact or {}

    payload = competition_revision_schema.dump(revision)
    payload.update(
        {
            "differences": differences,
            "comparison": comparison,
            "impact": impact,
            "completeness": revision_completeness(revision),
            "published_revision_id": revision.competition.published_revision_id,
            "current_published_revision_id": revision.competition.published_revision_id,
            "is_stale": (
                revision.base_revision_id != revision.competition.published_revision_id
                and revision.revision_status == CompetitionRevisionStatus.PENDING_REVIEW
            ),
        }
    )
    return payload


def revision_read_models(revisions: list[CompetitionRevision]) -> list[dict]:
    terminal_ids = [
        revision.id
        for revision in revisions
        if revision.revision_status
        not in {CompetitionRevisionStatus.DRAFT, CompetitionRevisionStatus.PENDING_REVIEW}
    ]
    reviews = _latest_terminal_reviews(terminal_ids)
    return [revision_read_model(revision, reviews.get(revision.id)) for revision in revisions]


def edition_workspace_read_model(
    edition: Competition,
    review: ReviewRecord | None = None,
) -> dict:
    payload = edition_workspace_schema.dump(edition)
    active = next(
        (
            revision
            for revision in reversed(edition.revisions)
            if revision.revision_status
            in {CompetitionRevisionStatus.DRAFT, CompetitionRevisionStatus.PENDING_REVIEW}
        ),
        edition.published_revision,
    )
    revision_payload = revision_read_model(active, review) if active is not None else None
    payload["revision"] = revision_payload
    payload["active_revision"] = revision_payload
    payload["lifecycle_impact"] = lifecycle_impact(edition)
    return payload


def edition_workspace_read_models(editions: list[Competition]) -> list[dict]:
    active_revisions = [
        next(
            (
                revision
                for revision in reversed(edition.revisions)
                if revision.revision_status
                in {CompetitionRevisionStatus.DRAFT, CompetitionRevisionStatus.PENDING_REVIEW}
            ),
            edition.published_revision,
        )
        for edition in editions
    ]
    terminal_ids = [
        revision.id
        for revision in active_revisions
        if revision is not None
        and revision.revision_status
        not in {CompetitionRevisionStatus.DRAFT, CompetitionRevisionStatus.PENDING_REVIEW}
    ]
    reviews = _latest_terminal_reviews(terminal_ids)
    return [
        edition_workspace_read_model(
            edition,
            reviews.get(revision.id) if revision is not None else None,
        )
        for edition, revision in zip(editions, active_revisions, strict=True)
    ]


def _latest_terminal_reviews(revision_ids: list[int]) -> dict[int, ReviewRecord]:
    if not revision_ids:
        return {}
    reviews = db.session.scalars(
        select(ReviewRecord)
        .where(
            ReviewRecord.target_type == "competition_revision",
            ReviewRecord.target_id.in_(revision_ids),
            ReviewRecord.status != ReviewStatus.PENDING,
        )
        .order_by(ReviewRecord.id.desc())
    )
    result = {}
    for review in reviews:
        result.setdefault(review.target_id, review)
    return result


def _comparison_from_differences(differences: list[dict]) -> dict[str, list[dict]]:
    return {
        "field_changes": [item for item in differences if item.get("kind") == "field"],
        "stage_changes": [item for item in differences if item.get("kind") == "stage"],
        "time_node_changes": [item for item in differences if item.get("kind") == "time_node"],
    }
