from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime, timedelta
from http import HTTPStatus

from sqlalchemy import select

from competehub_api.extensions import db
from competehub_api.models import Competition, OutboundClickDailyStat, OutboundClickEvent
from competehub_api.services.errors import ServiceError
from competehub_api.timezones import PRODUCT_TIMEZONE, stored_datetime_as_utc

OUTBOUND_TARGET_FIELDS = frozenset({"source_url", "official_url", "attachment_url"})
OUTBOUND_SOURCE_SURFACES = frozenset({"competition_list", "competition_detail", "recommendation"})


def record_outbound_click(
    competition: Competition,
    *,
    target_type: str,
    source_surface: str,
    actor_kind: str,
) -> None:
    if target_type not in OUTBOUND_TARGET_FIELDS or source_surface not in OUTBOUND_SOURCE_SURFACES:
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "outbound click dimensions are invalid",
        )
    revision = competition.published_revision
    target = getattr(revision, target_type, None) if revision is not None else None
    if revision is None or not target:
        raise ServiceError(
            HTTPStatus.NOT_FOUND,
            "outbound_target_not_found",
            "outbound target is not available",
        )

    db.session.add(
        OutboundClickEvent(
            competition_id=competition.id,
            competition_revision_id=revision.id,
            target_type=target_type,
            source_surface=source_surface,
            actor_kind=actor_kind,
            occurred_at=datetime.now(UTC),
        )
    )
    db.session.commit()


def aggregate_outbound_clicks(*, now: datetime | None = None) -> None:
    now = stored_datetime_as_utc(now or datetime.now(UTC))
    events = list(db.session.scalars(select(OutboundClickEvent)))
    grouped = Counter(_stat_dimensions(event) for event in events)
    existing_stats = {
        _daily_stat_dimensions(stat): stat
        for stat in db.session.scalars(select(OutboundClickDailyStat))
    }
    for dimensions, click_count in grouped.items():
        stat = existing_stats.get(dimensions)
        if stat is None:
            stat = OutboundClickDailyStat(
                stat_date=dimensions[0],
                competition_id=dimensions[1],
                target_type=dimensions[2],
                source_surface=dimensions[3],
                actor_kind=dimensions[4],
                click_count=click_count,
            )
            db.session.add(stat)
        else:
            stat.click_count = click_count

    retention_date = now.astimezone(PRODUCT_TIMEZONE).date() - timedelta(days=90)
    for event in events:
        if _product_date(event.occurred_at) < retention_date:
            db.session.delete(event)
    db.session.commit()


def _stat_dimensions(event: OutboundClickEvent) -> tuple:
    return (
        _product_date(event.occurred_at),
        event.competition_id,
        event.target_type,
        event.source_surface,
        event.actor_kind,
    )


def _daily_stat_dimensions(stat: OutboundClickDailyStat) -> tuple:
    return (
        stat.stat_date,
        stat.competition_id,
        stat.target_type,
        stat.source_surface,
        stat.actor_kind,
    )


def _product_date(value: datetime) -> date:
    return stored_datetime_as_utc(value).astimezone(PRODUCT_TIMEZONE).date()
