from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

from flask import Blueprint, jsonify, request
from sqlalchemy import select

from competehub_api.errors import error_response
from competehub_api.extensions import db
from competehub_api.models import Competition, CompetitionTimeNode
from competehub_api.models.enums import CompetitionStatus

competitions_bp = Blueprint("competitions", __name__)

PUBLIC_COMPETITION_STATUSES = frozenset({CompetitionStatus.PUBLISHED})
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@competitions_bp.get("/competitions")
def list_competitions():
    page_result = _positive_int_arg("page", 1)
    if isinstance(page_result, tuple):
        return page_result
    page = page_result

    page_size_result = _positive_int_arg("page_size", DEFAULT_PAGE_SIZE, max_value=MAX_PAGE_SIZE)
    if isinstance(page_size_result, tuple):
        return page_size_result
    page_size = page_size_result

    competitions = list(db.session.scalars(select(Competition)))
    public_matches = [
        competition for competition in competitions if _matches_public_filters(competition)
    ]
    public_matches.sort(key=_competition_sort_key)

    total = len(public_matches)
    start = (page - 1) * page_size
    end = start + page_size

    return jsonify(
        {
            "data": {
                "items": [
                    _serialize_competition_summary(item) for item in public_matches[start:end]
                ],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                },
            },
            "error": None,
        }
    )


@competitions_bp.get("/competitions/<int:competition_id>")
def get_competition_detail(competition_id: int):
    competition = db.session.get(Competition, competition_id)
    if competition is None or competition.status not in PUBLIC_COMPETITION_STATUSES:
        return error_response(
            HTTPStatus.NOT_FOUND,
            "not_found",
            "competition not found",
        )

    return jsonify({"data": _serialize_competition_detail(competition), "error": None})


def _positive_int_arg(name: str, default: int, max_value: int | None = None):
    raw_value = request.args.get(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return error_response(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            f"{name} must be an integer",
            {"field": name},
        )

    if value < 1:
        return error_response(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            f"{name} must be greater than zero",
            {"field": name},
        )

    if max_value is not None:
        return min(value, max_value)
    return value


def _matches_public_filters(competition: Competition) -> bool:
    if competition.status not in PUBLIC_COMPETITION_STATUSES:
        return False

    status = _query_text("status")
    if status is not None and status != CompetitionStatus.PUBLISHED.value:
        return False

    keyword = _query_text("keyword")
    if keyword is not None:
        haystack = " ".join(
            value or ""
            for value in (
                competition.title,
                competition.short_title,
                competition.organizer,
                competition.category,
                competition.summary,
            )
        ).lower()
        if keyword.lower() not in haystack:
            return False

    category = _query_text("category")
    if category is not None and competition.category != category:
        return False

    participant_form = _query_text("participant_form")
    if participant_form is not None and competition.participant_form != participant_form:
        return False

    major = _query_text("major")
    if major is not None and major not in (competition.suitable_majors or []):
        return False

    grade = _query_text("grade")
    if grade is not None and grade not in (competition.suitable_grades or []):
        return False

    tag = _query_text("tag")
    if tag is not None and tag not in _tag_names(competition):
        return False

    return True


def _query_text(name: str) -> str | None:
    value = request.args.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _competition_sort_key(competition: Competition) -> tuple[datetime, str]:
    next_node = _next_node(competition)
    return (_sortable_node_time(next_node), competition.title)


def _serialize_competition_summary(competition: Competition) -> dict[str, Any]:
    next_node = _next_node(competition)
    return {
        "id": competition.id,
        "title": competition.title,
        "short_title": competition.short_title,
        "category": competition.category,
        "organizer": competition.organizer,
        "status": competition.status.value,
        "source_name": competition.source_name,
        "source_url": competition.source_url,
        "official_url": competition.official_url,
        "tags": _tag_names(competition),
        "suitable_majors": competition.suitable_majors or [],
        "suitable_grades": competition.suitable_grades or [],
        "value_notes": competition.value_notes,
        "next_node": _serialize_time_node(next_node) if next_node is not None else None,
        "is_favorited": False,
        "is_subscribed": False,
    }


def _serialize_competition_detail(competition: Competition) -> dict[str, Any]:
    data = _serialize_competition_summary(competition)
    data.update(
        {
            "host": competition.host,
            "attachment_url": competition.attachment_url,
            "summary": competition.summary,
            "detail": competition.detail,
            "eligibility": competition.eligibility,
            "team_size": competition.team_size,
            "participant_form": competition.participant_form,
            "time_nodes": [
                _serialize_time_node(node)
                for node in sorted(competition.time_nodes, key=_time_node_sort_key)
            ],
        }
    )
    return data


def _next_node(competition: Competition) -> CompetitionTimeNode | None:
    nodes = sorted(competition.time_nodes, key=_time_node_sort_key)
    return nodes[0] if nodes else None


def _time_node_sort_key(node: CompetitionTimeNode) -> tuple[datetime, int]:
    return (_sortable_node_time(node), node.id or 0)


def _node_time(node: CompetitionTimeNode | None) -> datetime | None:
    if node is None:
        return None
    return node.due_at or node.starts_at


def _sortable_node_time(node: CompetitionTimeNode | None) -> datetime:
    value = _node_time(node)
    if value is None:
        return datetime.max.replace(tzinfo=UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _serialize_time_node(node: CompetitionTimeNode) -> dict[str, Any]:
    return {
        "id": node.id,
        "node_type": node.node_type,
        "starts_at": _isoformat(node.starts_at),
        "due_at": _isoformat(node.due_at),
        "description": node.description,
    }


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _tag_names(competition: Competition) -> list[str]:
    return sorted({link.tag.name for link in competition.tag_links if link.tag is not None})
