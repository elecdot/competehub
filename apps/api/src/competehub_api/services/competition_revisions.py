from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

from sqlalchemy import select

from competehub_api.extensions import db
from competehub_api.models import (
    AuditLog,
    Competition,
    CompetitionRevision,
    CompetitionSeries,
    CompetitionStage,
    CompetitionTag,
    CompetitionTagLink,
    CompetitionTimeNode,
    ReviewRecord,
    User,
)
from competehub_api.models.enums import (
    CompetitionRevisionStatus,
    CompetitionStatus,
    ReviewStatus,
)
from competehub_api.repositories.competitions import (
    get_competition_series,
    get_competition_series_by_name,
    get_competition_tag_by_code,
)
from competehub_api.services.errors import ServiceError

REVISION_FIELDS = (
    "title",
    "short_title",
    "category",
    "organizer",
    "host",
    "source_name",
    "source_url",
    "official_url",
    "attachment_url",
    "summary",
    "detail",
    "eligibility",
    "registration_applicability",
    "team_size",
    "participant_forms",
    "major_scope",
    "grade_scope",
    "suitable_majors",
    "suitable_grades",
    "value_notes",
)
REQUIRED_PUBLICATION_FIELDS = (
    "title",
    "category",
    "organizer",
    "source_name",
    "source_url",
    "summary",
    "eligibility",
    "registration_applicability",
    "participant_forms",
    "major_scope",
    "grade_scope",
)
CORE_NODE_TYPES = {
    "registration_start",
    "registration_deadline",
    "submission_deadline",
    "competition_start",
    "competition_end",
    "defense_or_review",
    "result_announcement",
}
PRIMARY_NODE_TYPES = {
    "registration_deadline",
    "submission_deadline",
    "competition_start",
}


def create_series(payload: dict[str, Any], actor: User) -> CompetitionSeries:
    name = payload["canonical_name"]
    if get_competition_series_by_name(name) is not None:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "competition series already exists",
            {"canonical_name": name},
        )
    series = CompetitionSeries(canonical_name=name, created_by_id=actor.id)
    db.session.add(series)
    db.session.flush()
    _write_audit(actor, "competition_series.create", "competition_series", series.id)
    db.session.commit()
    return series


def create_edition_with_revision(payload: dict[str, Any], actor: User) -> Competition:
    payload = payload.copy()
    series_id = payload.pop("series_id")
    edition_label = payload.pop("edition_label")
    stages = payload.pop("stages", []) or []
    tags = payload.pop("tags", []) or []
    series = get_competition_series(series_id)
    if series is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "competition series not found")
    existing = db.session.scalar(
        select(Competition).where(
            Competition.series_id == series_id,
            Competition.edition_label == edition_label,
        )
    )
    if existing is not None:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "competition edition already exists",
            {"competition_id": existing.id},
        )

    edition = Competition(
        series=series,
        edition_label=edition_label,
        status=CompetitionStatus.UNPUBLISHED,
        created_by_id=actor.id,
        **_projection_fields(payload),
    )
    revision = CompetitionRevision(
        competition=edition,
        revision_number=1,
        revision_status=CompetitionRevisionStatus.DRAFT,
        created_by_id=actor.id,
        **{field: payload.get(field) for field in REVISION_FIELDS},
    )
    db.session.add(edition)
    _replace_stages(revision, edition, stages)
    _replace_tags(revision, tags)
    db.session.flush()
    _write_audit(
        actor,
        "competition_revision.create",
        "competition_revision",
        revision.id,
        {
            "competition_id": edition.id,
            "revision_number": 1,
            "prominence_overrides": _prominence_overrides(revision),
        },
    )
    db.session.commit()
    return edition


def update_revision(
    revision: CompetitionRevision,
    payload: dict[str, Any],
    actor: User,
) -> CompetitionRevision:
    if revision.revision_status != CompetitionRevisionStatus.DRAFT:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "only draft revisions are editable",
            {"revision_status": revision.revision_status.value},
        )
    payload = payload.copy()
    stages = payload.pop("stages", None)
    tags = payload.pop("tags", None)
    for field, value in payload.items():
        setattr(revision, field, value)
    if stages is not None:
        _replace_stages(revision, revision.competition, stages or [])
    if tags is not None:
        _replace_tags(revision, tags or [])
    changed_fields = sorted(
        [
            *payload,
            *(["stages"] if stages is not None else []),
            *(["tags"] if tags is not None else []),
        ]
    )
    _write_audit(
        actor,
        "competition_revision.update",
        "competition_revision",
        revision.id,
        {
            "fields": changed_fields,
            "prominence_overrides": _prominence_overrides(revision),
        },
    )
    db.session.commit()
    return revision


def submit_revision(revision: CompetitionRevision, actor: User) -> CompetitionRevision:
    if revision.revision_status != CompetitionRevisionStatus.DRAFT:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "only draft revisions can be submitted",
        )
    completeness = revision_completeness(revision)
    if not completeness["is_complete"]:
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "competition revision is incomplete",
            completeness,
        )

    now = datetime.now(UTC)
    revision.revision_status = CompetitionRevisionStatus.PENDING_REVIEW
    revision.submitted_by_id = actor.id
    revision.submitted_at = now
    _write_audit(
        actor,
        "competition_revision.submit_review",
        "competition_revision",
        revision.id,
        {"revision_number": revision.revision_number},
    )
    db.session.commit()
    return revision


def review_revision(
    revision: CompetitionRevision,
    actor: User,
    action: str,
    comment: str,
) -> CompetitionRevision:
    revision = db.session.scalar(
        select(CompetitionRevision)
        .where(CompetitionRevision.id == revision.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if revision is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "competition revision not found")
    if revision.revision_status != CompetitionRevisionStatus.PENDING_REVIEW:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "only pending revisions can be reviewed",
        )
    if revision.submitted_by_id == actor.id:
        raise ServiceError(
            HTTPStatus.FORBIDDEN,
            "forbidden",
            "the submitter cannot review the same revision",
        )
    now = datetime.now(UTC)
    status_by_action = {
        "approve": (CompetitionRevisionStatus.APPROVED, ReviewStatus.APPROVED),
        "reject": (CompetitionRevisionStatus.REJECTED, ReviewStatus.REJECTED),
        "return": (CompetitionRevisionStatus.RETURNED, ReviewStatus.RETURNED),
    }
    revision_status, review_status = status_by_action[action]
    edition = db.session.scalar(
        select(Competition).where(Competition.id == revision.competition_id).with_for_update()
    )
    if edition is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "competition edition not found")
    if action == "approve":
        if revision.base_revision_id != edition.published_revision_id:
            raise ServiceError(
                HTTPStatus.CONFLICT,
                "stale_revision",
                "the public revision changed after this candidate was created",
                {"published_revision_id": edition.published_revision_id},
            )
        edition.published_revision_id = revision.id
        edition.status = CompetitionStatus.PUBLISHED
        revision.published_at = now
        _sync_projection(edition, revision)

    revision.revision_status = revision_status
    revision.decided_at = now
    db.session.add(
        ReviewRecord(
            target_type="competition_revision",
            target_id=revision.id,
            submitted_by_id=revision.submitted_by_id,
            submitted_at=revision.submitted_at,
            reviewed_by_id=actor.id,
            status=review_status,
            comment=comment,
            differences=revision_differences(revision),
            impact=revision_impact(revision),
            decided_at=now,
        )
    )
    _write_audit(
        actor,
        f"competition_revision.{action}",
        "competition_revision",
        revision.id,
        {"competition_id": edition.id, "revision_number": revision.revision_number},
    )
    db.session.commit()
    return revision


def revision_differences(revision: CompetitionRevision) -> list[dict[str, Any]]:
    comparison = revision_comparison(revision)
    return [
        *comparison["field_changes"],
        *comparison["stage_changes"],
        *comparison["time_node_changes"],
    ]


def revision_comparison(revision: CompetitionRevision) -> dict[str, list[dict[str, Any]]]:
    base = revision.competition.published_revision if revision.base_revision_id else None
    field_changes = []
    for field in REVISION_FIELDS:
        before = getattr(base, field) if base is not None else None
        after = getattr(revision, field)
        if before != after:
            field_changes.append(
                {"kind": "field", "field": field, "before": before, "after": after}
            )
    before_tags = _tag_codes(base) if base is not None else []
    after_tags = _tag_codes(revision)
    if before_tags != after_tags:
        field_changes.append(
            {"kind": "field", "field": "tags", "before": before_tags, "after": after_tags}
        )

    stage_changes = _keyed_changes(
        "stage",
        {_stage.stage_key: _stage_facts(_stage) for _stage in base.stages} if base else {},
        {_stage.stage_key: _stage_facts(_stage) for _stage in revision.stages},
        "stage_key",
    )
    before_nodes = (
        {
            node.logical_node_key: _node_facts(stage, node)
            for stage in base.stages
            for node in stage.time_nodes
        }
        if base
        else {}
    )
    after_nodes = {
        node.logical_node_key: _node_facts(stage, node)
        for stage in revision.stages
        for node in stage.time_nodes
    }
    time_node_changes = _keyed_changes("time_node", before_nodes, after_nodes, "logical_node_key")
    return {
        "field_changes": field_changes,
        "stage_changes": stage_changes,
        "time_node_changes": time_node_changes,
    }


def revision_impact(revision: CompetitionRevision) -> dict[str, Any]:
    visibility = "publish" if revision.base_revision_id is None else "replace"
    return {
        "public_visibility": visibility,
        "public_visibility_change": (
            "publish_initial_revision"
            if revision.base_revision_id is None
            else "replace_public_revision"
        ),
        "search_reindex_required": True,
        "recommendation_refresh_required": True,
        "active_subscriptions": 0,
        "affected_active_subscriptions": 0,
        "pending_reminders_to_supersede": 0,
        "future_reminders_to_create": 0,
        "schedule_change_messages_estimate": 0,
        "schedule_semantic_changes": sum(len(stage.time_nodes) for stage in revision.stages),
        "as_of": datetime.now(UTC).isoformat(),
    }


def revision_completeness(revision: CompetitionRevision) -> dict[str, Any]:
    missing_fields = [
        field for field in REQUIRED_PUBLICATION_FIELDS if not getattr(revision, field)
    ]
    if not revision.stages:
        missing_fields.append("stages")
    if not any(
        node.prominence == "primary" and node.node_type in CORE_NODE_TYPES
        for stage in revision.stages
        for node in stage.time_nodes
    ):
        missing_fields.append("primary_core_time_node")
    if "team" in (revision.participant_forms or []) and not revision.team_size:
        missing_fields.append("team_size")
    if revision.major_scope == "selected" and not revision.suitable_majors:
        missing_fields.append("suitable_majors")
    if revision.grade_scope == "selected" and not revision.suitable_grades:
        missing_fields.append("suitable_grades")
    warnings = _pair_warnings(revision)
    missing_fields = sorted(set(missing_fields))
    return {
        "is_complete": not missing_fields,
        "missing_fields": missing_fields,
        "warnings": warnings,
    }


def _keyed_changes(
    kind: str,
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    key_name: str,
) -> list[dict[str, Any]]:
    changes = []
    for key in sorted(set(before) | set(after)):
        old = before.get(key)
        new = after.get(key)
        if old == new:
            continue
        change = "added" if old is None else "removed" if new is None else "changed"
        changes.append(
            {
                "kind": kind,
                "change": change,
                key_name: key,
                "before": old,
                "after": new,
            }
        )
    return changes


def _stage_facts(stage: CompetitionStage) -> dict[str, Any]:
    return {
        "stage_type": stage.stage_type,
        "label": stage.label,
        "order": stage.stage_order,
    }


def _node_facts(stage: CompetitionStage, node: CompetitionTimeNode) -> dict[str, Any]:
    return {
        "stage_key": stage.stage_key,
        "node_type": node.node_type,
        "occurs_at": node.occurs_at.isoformat() if node.occurs_at else None,
        "description": node.description,
        "prominence": node.prominence,
        "prominence_override_reason": node.prominence_override_reason,
        "node_revision": node.node_revision,
    }


def _tag_codes(revision: CompetitionRevision | None) -> list[str]:
    if revision is None:
        return []
    return sorted(link.tag.code for link in revision.tag_links if link.tag is not None)


def _pair_warnings(revision: CompetitionRevision) -> list[dict[str, str]]:
    warnings = []
    for stage in revision.stages:
        node_types = {node.node_type for node in stage.time_nodes}
        for first, second in (
            ("registration_start", "registration_deadline"),
            ("competition_start", "competition_end"),
        ):
            if (first in node_types) == (second in node_types):
                continue
            warnings.append(
                {
                    "code": "missing_pair",
                    "stage_key": stage.stage_key,
                    "missing_node_type": second if first in node_types else first,
                }
            )
    return warnings


def _prominence_overrides(revision: CompetitionRevision) -> list[dict[str, str]]:
    overrides = []
    for stage in revision.stages:
        for node in stage.time_nodes:
            default = "primary" if node.node_type in PRIMARY_NODE_TYPES else "secondary"
            if node.prominence == default:
                continue
            overrides.append(
                {
                    "logical_node_key": node.logical_node_key,
                    "default": default,
                    "selected": node.prominence,
                    "reason": node.prominence_override_reason,
                }
            )
    return overrides


def _replace_stages(
    revision: CompetitionRevision,
    edition: Competition,
    payloads: list[dict[str, Any]],
) -> None:
    revision.stages.clear()
    if revision.id is not None:
        db.session.flush()
    for payload in payloads:
        payload = payload.copy()
        nodes = payload.pop("time_nodes", [])
        stage = CompetitionStage(**payload)
        for node_payload in nodes:
            stage.time_nodes.append(
                CompetitionTimeNode(
                    revision=revision,
                    competition=edition,
                    **node_payload,
                )
            )
        revision.stages.append(stage)


def _replace_tags(revision: CompetitionRevision, payloads: list[dict[str, Any]]) -> None:
    revision.tag_links.clear()
    if revision.id is not None:
        db.session.flush()
    for payload in payloads:
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
        revision.tag_links.append(CompetitionTagLink(tag=tag))


def _projection_fields(payload: dict[str, Any]) -> dict[str, Any]:
    fields = {field: payload.get(field) for field in REVISION_FIELDS}
    forms = payload.get("participant_forms") or []
    fields["participant_form"] = "team" if "team" in forms else next(iter(forms), None)
    return fields


def _sync_projection(edition: Competition, revision: CompetitionRevision) -> None:
    for field in REVISION_FIELDS:
        setattr(edition, field, getattr(revision, field))
    forms = revision.participant_forms or []
    edition.participant_form = "team" if "team" in forms else next(iter(forms), None)


def _write_audit(
    actor: User,
    action: str,
    target_type: str,
    target_id: int,
    detail: dict[str, Any] | None = None,
) -> None:
    db.session.add(
        AuditLog(
            actor_id=actor.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            result="success",
            detail=detail or {},
        )
    )
