from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime, timedelta
from http import HTTPStatus

from flask import current_app
from sqlalchemy import delete, func, select

from competehub_api.extensions import db
from competehub_api.models import Competition, OutboundClickDailyStat, OutboundClickEvent
from competehub_api.services.errors import ServiceError
from competehub_api.services.rate_limits import increment_rate_limit, request_source
from competehub_api.timezones import PRODUCT_TIMEZONE, stored_datetime_as_utc

OUTBOUND_TARGET_FIELDS = frozenset({"source_url", "official_url", "attachment_url"})
OUTBOUND_SOURCE_SURFACES = frozenset({"competition_list", "competition_detail", "recommendation"})
OUTBOUND_AGGREGATION_LOCK_ID = 3_900_039


def record_outbound_click(
    competition: Competition,
    *,
    target_type: str,
    source_surface: str,
    actor_kind: str,
) -> None:
    _check_rate_limit()
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
    _acquire_aggregation_lock()
    events = list(
        db.session.scalars(
            select(OutboundClickEvent)
            .where(OutboundClickEvent.aggregated_at.is_(None))
            .order_by(OutboundClickEvent.id)
            .with_for_update()
        )
    )
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
            stat.click_count += click_count

    for event in events:
        event.aggregated_at = now
    db.session.flush()
    db.session.execute(
        delete(OutboundClickEvent)
        .where(OutboundClickEvent.occurred_at < now - timedelta(days=90))
        .execution_options(synchronize_session=False)
    )
    db.session.commit()


def _acquire_aggregation_lock() -> None:
    if db.session.get_bind().dialect.name == "postgresql":
        db.session.execute(select(func.pg_advisory_xact_lock(OUTBOUND_AGGREGATION_LOCK_ID)))


def _check_rate_limit() -> None:
    if not current_app.config.get("OUTBOUND_RATE_LIMIT_ENABLED", True):
        return
    max_attempts = current_app.config.get("OUTBOUND_RATE_LIMIT_MAX_ATTEMPTS", 60)
    window_seconds = current_app.config.get("OUTBOUND_RATE_LIMIT_WINDOW_SECONDS", 60)
    source = request_source(
        trust_proxy_headers=current_app.config.get("AUTH_TRUST_PROXY_HEADERS", False)
    )
    count = increment_rate_limit(
        f"outbound-rate:source:{source}",
        window_seconds,
        store_config_key="OUTBOUND_RATE_LIMIT_STORE",
        extension_key="outbound_rate_limit_redis",
    )
    if count > max_attempts:
        raise ServiceError(
            HTTPStatus.TOO_MANY_REQUESTS,
            "rate_limited",
            "too many outbound click attempts",
            {"retry_after_seconds": window_seconds},
        )


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
