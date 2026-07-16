from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from competehub_api.models.enums import CompetitionStatus
from competehub_api.repositories.calendar import (
    RevisionStageNode,
    SubscribedCalendarNode,
    list_revision_stage_nodes,
    list_subscribed_calendar_nodes,
)
from competehub_api.timezones import (
    PRODUCT_TIMEZONE,
    PRODUCT_TIMEZONE_NAME,
    product_date_start_utc,
    stored_datetime_as_utc,
)

DETAIL_AVAILABLE_STATUSES = frozenset(
    {
        CompetitionStatus.PUBLISHED,
        CompetitionStatus.CANCELLED,
        CompetitionStatus.ARCHIVED,
        CompetitionStatus.EXPIRED,
    }
)
FUTURE_HIDDEN_STATUSES = frozenset({CompetitionStatus.CANCELLED, CompetitionStatus.OFFLINE})
PAIR_METADATA = {
    "registration_start": ("registration", "start"),
    "registration_deadline": ("registration", "deadline"),
    "competition_start": ("competition", "start"),
    "competition_end": ("competition", "end"),
}


def student_calendar(
    user_id: int,
    date_from: date,
    date_to: date,
    view: str,
    *,
    now: datetime | None = None,
) -> dict:
    range_start = product_date_start_utc(date_from)
    range_end = product_date_start_utc(date_to + timedelta(days=1))
    now = stored_datetime_as_utc(now or datetime.now(UTC))
    projections = list_subscribed_calendar_nodes(user_id, range_start, range_end)
    current_stage_ids = _current_stage_ids(projections, now)
    items = [
        _calendar_item(projection, current_stage_ids.get(projection.revision.id))
        for projection in projections
        if _is_selected(projection) and _is_lifecycle_visible(projection, now)
    ]
    items.sort(key=_calendar_item_sort_key)
    return {
        "range": {
            "from": date_from,
            "to": date_to,
            "view": view,
            "time_zone": PRODUCT_TIMEZONE_NAME,
        },
        "items": items,
    }


def _is_selected(projection: SubscribedCalendarNode) -> bool:
    return projection.node.node_type in set(projection.subscription.node_types or [])


def _is_lifecycle_visible(
    projection: SubscribedCalendarNode,
    now: datetime,
) -> bool:
    occurs_at = stored_datetime_as_utc(projection.node.occurs_at)
    return not (projection.competition.status in FUTURE_HIDDEN_STATUSES and occurs_at >= now)


def _calendar_item(
    projection: SubscribedCalendarNode,
    current_stage_id: int | None,
) -> dict:
    competition = projection.competition
    revision = projection.revision
    stage = projection.stage
    node = projection.node
    target_available = competition.status in DETAIL_AVAILABLE_STATUSES
    pair_kind, pair_role = PAIR_METADATA.get(node.node_type, (None, None))
    return {
        "competition_id": competition.id,
        "competition_title": revision.title,
        "detail_url": f"/competitions/{competition.id}" if target_available else None,
        "lifecycle_status": competition.status.value,
        "target_available": target_available,
        "stage_id": stage.id if stage else None,
        "stage_label": stage.label if stage else None,
        "stage_order": stage.stage_order if stage else None,
        "stage_type": stage.stage_type if stage else None,
        "is_current_stage": stage is not None and stage.id == current_stage_id,
        "node_snapshot_id": node.id,
        "logical_node_key": node.logical_node_key,
        "node_revision": node.node_revision,
        "node_type": node.node_type,
        "description": node.description,
        "occurs_at": node.occurs_at,
        "prominence": node.prominence,
        "pair_kind": pair_kind,
        "pair_role": pair_role,
    }


def _current_stage_ids(
    projections: list[SubscribedCalendarNode],
    now: datetime,
) -> dict[int, int]:
    revision_ids = {projection.revision.id for projection in projections}
    facts_by_revision: dict[int, list[RevisionStageNode]] = {}
    for fact in list_revision_stage_nodes(revision_ids):
        facts_by_revision.setdefault(fact.revision_id, []).append(fact)

    current_stage_ids = {}
    for revision_id, facts in facts_by_revision.items():
        future_facts = [
            fact
            for fact in facts
            if fact.occurs_at is not None and stored_datetime_as_utc(fact.occurs_at) >= now
        ]
        if future_facts:
            current = min(
                future_facts,
                key=lambda fact: (
                    stored_datetime_as_utc(fact.occurs_at),
                    fact.stage_order,
                    fact.stage_id,
                ),
            )
        else:
            current = max(facts, key=lambda fact: (fact.stage_order, fact.stage_id))
        current_stage_ids[revision_id] = current.stage_id
    return current_stage_ids


def _calendar_item_sort_key(item: dict) -> tuple:
    occurs_at = stored_datetime_as_utc(item["occurs_at"])
    return (
        occurs_at.astimezone(PRODUCT_TIMEZONE).date(),
        item["stage_order"] if item["stage_order"] is not None else 2**31 - 1,
        occurs_at,
        0 if item["prominence"] == "primary" else 1,
        item["node_snapshot_id"],
    )
