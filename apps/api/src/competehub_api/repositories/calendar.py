from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionRevision,
    CompetitionStage,
    CompetitionTimeNode,
    Subscription,
)
from competehub_api.models.enums import SubscriptionStatus


@dataclass(frozen=True)
class SubscribedCalendarNode:
    subscription: Subscription
    competition: Competition
    revision: CompetitionRevision
    stage: CompetitionStage | None
    node: CompetitionTimeNode


@dataclass(frozen=True)
class RevisionStageNode:
    revision_id: int
    stage_id: int
    stage_order: int
    occurs_at: datetime | None


def list_subscribed_calendar_nodes(
    user_id: int,
    range_start: datetime,
    range_end: datetime,
) -> list[SubscribedCalendarNode]:
    statement = (
        select(
            Subscription,
            Competition,
            CompetitionRevision,
            CompetitionStage,
            CompetitionTimeNode,
        )
        .join(Competition, Competition.id == Subscription.competition_id)
        .join(
            CompetitionRevision,
            CompetitionRevision.id == Competition.published_revision_id,
        )
        .join(
            CompetitionTimeNode,
            CompetitionTimeNode.competition_revision_id == CompetitionRevision.id,
        )
        .outerjoin(CompetitionStage, CompetitionStage.id == CompetitionTimeNode.stage_id)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            CompetitionTimeNode.occurs_at.is_not(None),
            CompetitionTimeNode.occurs_at >= range_start,
            CompetitionTimeNode.occurs_at < range_end,
        )
    )
    return [
        SubscribedCalendarNode(
            subscription=subscription,
            competition=competition,
            revision=revision,
            stage=stage,
            node=node,
        )
        for subscription, competition, revision, stage, node in db.session.execute(statement)
    ]


def list_revision_stage_nodes(revision_ids: set[int]) -> list[RevisionStageNode]:
    if not revision_ids:
        return []
    statement = (
        select(
            CompetitionStage.competition_revision_id,
            CompetitionStage.id,
            CompetitionStage.stage_order,
            CompetitionTimeNode.occurs_at,
        )
        .outerjoin(CompetitionTimeNode, CompetitionTimeNode.stage_id == CompetitionStage.id)
        .where(CompetitionStage.competition_revision_id.in_(revision_ids))
    )
    return [
        RevisionStageNode(
            revision_id=revision_id,
            stage_id=stage_id,
            stage_order=stage_order,
            occurs_at=occurs_at,
        )
        for revision_id, stage_id, stage_order, occurs_at in db.session.execute(statement)
    ]
