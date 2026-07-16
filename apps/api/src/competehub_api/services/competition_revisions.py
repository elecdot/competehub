from __future__ import annotations

from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import Any

from sqlalchemy.exc import IntegrityError

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
    Reminder,
    ReviewRecord,
    Subscription,
    User,
)
from competehub_api.models.enums import (
    CompetitionRevisionStatus,
    CompetitionStatus,
    ReminderStatus,
    ReviewStatus,
)
from competehub_api.repositories import engagement as engagement_repository
from competehub_api.repositories.competitions import (
    get_active_competition_revision,
    get_competition_by_series_edition,
    get_competition_for_update,
    get_competition_revision_for_update,
    get_competition_series,
    get_competition_series_by_name,
    get_competition_tag_by_code,
    get_latest_terminal_competition_revision,
    get_max_approved_node_revisions,
)
from competehub_api.services.errors import ServiceError
from competehub_api.services.notifications import bounded_title, create_competition_event_message
from competehub_api.services.reminder_state import revoke_pending_reminder

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
NODE_BEHAVIOR_CHANGE_FIELDS = (
    "stage_key",
    "stage_type",
    "stage_label",
    "stage_order",
    "node_type",
    "occurs_at",
    "prominence",
    "description",
)
REVISION_WORKFLOW_LIFECYCLE_STATUSES = frozenset(
    {
        CompetitionStatus.UNPUBLISHED,
        CompetitionStatus.PUBLISHED,
        CompetitionStatus.OFFLINE,
    }
)


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
    existing = get_competition_by_series_edition(series_id, edition_label)
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


def create_successor_revision(
    edition: Competition,
    actor: User,
    reason: str,
) -> CompetitionRevision:
    edition_id = edition.id
    _require_revision_workflow_lifecycle(edition)
    # Avoid taking the edition lock for a known conflict, then re-check after
    # locking so concurrent creation and lifecycle changes cannot stale this decision.
    _require_no_active_revision(edition_id)

    edition = get_competition_for_update(edition_id)
    if edition is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "competition edition not found")
    _require_revision_workflow_lifecycle(edition)
    _require_no_active_revision(edition_id)

    public_base = (
        db.session.get(CompetitionRevision, edition.published_revision_id)
        if edition.published_revision_id is not None
        else None
    )
    terminal = get_latest_terminal_competition_revision(edition.id)
    source = public_base
    if terminal is not None and (
        source is None or terminal.revision_number > source.revision_number
    ):
        source = terminal
    if source is None:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "a successor revision requires a published or decided source revision",
        )
    # Relationship loads while cloning can otherwise autoflush the new revision before
    # the explicit flush below, bypassing the unique-conflict translation.
    with db.session.no_autoflush:
        revision = CompetitionRevision(
            competition=edition,
            revision_number=max(item.revision_number for item in edition.revisions) + 1,
            base_revision_id=public_base.id if public_base is not None else None,
            change_reason=reason,
            revision_status=CompetitionRevisionStatus.DRAFT,
            created_by_id=actor.id,
            **{field: getattr(source, field) for field in REVISION_FIELDS},
        )
        db.session.add(revision)
        for base_stage in source.stages:
            stage = CompetitionStage(
                stage_key=base_stage.stage_key,
                stage_type=base_stage.stage_type,
                label=base_stage.label,
                stage_order=base_stage.stage_order,
            )
            for base_node in base_stage.time_nodes:
                stage.time_nodes.append(
                    CompetitionTimeNode(
                        revision=revision,
                        competition=edition,
                        logical_node_key=base_node.logical_node_key,
                        node_revision=base_node.node_revision,
                        node_type=base_node.node_type,
                        occurs_at=base_node.occurs_at,
                        prominence=base_node.prominence,
                        prominence_override_reason=base_node.prominence_override_reason,
                        description=base_node.description,
                    )
                )
            revision.stages.append(stage)
        for base_link in source.tag_links:
            revision.tag_links.append(CompetitionTagLink(tag=base_link.tag))
    try:
        db.session.flush()
        _write_audit(
            actor,
            "competition_revision.create_successor",
            "competition_revision",
            revision.id,
            {
                "competition_id": edition_id,
                "base_revision_id": public_base.id if public_base is not None else None,
                "source_revision_id": source.id,
                "revision_number": revision.revision_number,
                "reason": reason,
            },
        )
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        if not any(
            _is_unique_constraint(error, constraint)
            for constraint in ("uq_active_competition_revision", "uq_competition_revision")
        ):
            raise
        active = get_active_competition_revision(edition_id)
        if active is None:
            raise
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "active_revision_exists",
            "the edition already has an active revision",
            {"revision_id": active.id, "revision_status": active.revision_status.value},
        ) from error
    return revision


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

    _freeze_node_revisions(revision)

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


def withdraw_revision(revision: CompetitionRevision, actor: User) -> CompetitionRevision:
    revision = get_competition_revision_for_update(revision.id)
    if revision is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "competition revision not found")
    if revision.revision_status != CompetitionRevisionStatus.PENDING_REVIEW:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "only pending revisions can be withdrawn",
        )
    submitted_by_id = revision.submitted_by_id
    submitted_at = revision.submitted_at
    revision.revision_status = CompetitionRevisionStatus.DRAFT
    revision.submitted_by_id = None
    revision.submitted_at = None
    revision.decided_at = None
    _write_audit(
        actor,
        "competition_revision.withdraw",
        "competition_revision",
        revision.id,
        {
            "competition_id": revision.competition_id,
            "revision_number": revision.revision_number,
            "submitted_by_id": submitted_by_id,
            "submitted_at": _utc_iso(submitted_at),
        },
    )
    db.session.commit()
    return revision


def review_revision(
    revision: CompetitionRevision,
    actor: User,
    action: str,
    comment: str,
) -> CompetitionRevision:
    revision_id = revision.id
    competition_id = revision.competition_id
    edition = get_competition_for_update(competition_id)
    if edition is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "competition edition not found")
    revision = get_competition_revision_for_update(revision_id)
    if revision is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "competition revision not found")
    if revision.competition_id != edition.id:
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
    if action == "approve":
        _require_revision_workflow_lifecycle(edition)
    now = datetime.now(UTC)
    comparison = revision_comparison(revision)
    differences = [
        *comparison["field_changes"],
        *comparison["stage_changes"],
        *comparison["time_node_changes"],
    ]
    impact = revision_impact(revision)
    status_by_action = {
        "approve": (CompetitionRevisionStatus.APPROVED, ReviewStatus.APPROVED),
        "reject": (CompetitionRevisionStatus.REJECTED, ReviewStatus.REJECTED),
        "return": (CompetitionRevisionStatus.RETURNED, ReviewStatus.RETURNED),
    }
    revision_status, review_status = status_by_action[action]
    if action == "approve":
        if edition.status == CompetitionStatus.OFFLINE and (
            revision.submitted_at is None
            or edition.lifecycle_changed_at is None
            or _aware_utc(revision.submitted_at) <= _aware_utc(edition.lifecycle_changed_at)
        ):
            raise ServiceError(
                HTTPStatus.CONFLICT,
                "offline_restoration_requires_corrected_revision",
                "offline restoration requires a corrected revision submitted after withdrawal",
                {
                    "offline_changed_at": (
                        _aware_utc(edition.lifecycle_changed_at).isoformat()
                        if edition.lifecycle_changed_at is not None
                        else None
                    ),
                    "submitted_at": (
                        _aware_utc(revision.submitted_at).isoformat()
                        if revision.submitted_at is not None
                        else None
                    ),
                },
            )
        if edition.status == CompetitionStatus.OFFLINE and not differences:
            raise ServiceError(
                HTTPStatus.CONFLICT,
                "offline_restoration_requires_corrected_revision",
                "offline restoration requires a corrected revision with changed facts",
                {"correction_required": True},
            )
        if revision.base_revision_id != edition.published_revision_id:
            raise ServiceError(
                HTTPStatus.CONFLICT,
                "stale_revision",
                "the public revision changed after this candidate was created",
                {"published_revision_id": edition.published_revision_id},
            )
        edition.published_revision_id = revision.id
        if edition.status in {
            CompetitionStatus.UNPUBLISHED,
            CompetitionStatus.PUBLISHED,
            CompetitionStatus.OFFLINE,
        }:
            edition.status = CompetitionStatus.PUBLISHED
            edition.lifecycle_reason = None
            edition.lifecycle_changed_at = now
        revision.published_at = now
        _sync_projection(edition, revision)
        if revision.base_revision_id is not None:
            impact.update(_reconcile_subscriber_state(revision, comparison, now))
            _write_reconciliation_event(actor, revision, comment, comparison)

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
            differences=differences,
            impact=impact,
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
    base = (
        db.session.get(CompetitionRevision, revision.base_revision_id)
        if revision.base_revision_id
        else None
    )
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
    comparison = revision_comparison(revision)
    schedule_changes = _schedule_changes(comparison)
    replacement_keys = _reminder_replacement_keys(comparison)
    subscriptions = engagement_repository.list_active_subscriptions_for_competition(
        revision.competition_id
    )
    reminder_settings = _required_reminder_settings(subscriptions)
    affected_subscriptions = [
        subscription
        for subscription in subscriptions
        if _subscription_affected(subscription, schedule_changes)
    ]
    base_node_ids = set()
    if revision.base_revision_id is not None:
        base = db.session.get(CompetitionRevision, revision.base_revision_id)
        base_node_ids = {
            node.id
            for node in (base.time_nodes if base is not None else [])
            if node.logical_node_key in replacement_keys
        }
    pending_to_supersede = engagement_repository.list_pending_reminders_for_competition(
        revision.competition_id,
        snapshot_ids=base_node_ids,
    )
    now = datetime.now(UTC)
    future_to_create = sum(
        1
        for subscription in subscriptions
        for node in revision.time_nodes
        if node.logical_node_key in replacement_keys
        and node.node_type in (subscription.node_types or [])
        and node.occurs_at is not None
        and _aware_utc(node.occurs_at) - timedelta(days=subscription.remind_days) > now
        and subscription.reminder_enabled
        and subscription.reminder_confirmed_at is not None
        and reminder_settings[subscription.user_id].enabled
    )
    return {
        "public_visibility": visibility,
        "public_visibility_change": (
            "publish_initial_revision"
            if revision.base_revision_id is None
            else "replace_public_revision"
        ),
        "search_reindex_required": True,
        "recommendation_refresh_required": True,
        "active_subscriptions": len(subscriptions),
        "affected_active_subscriptions": len(affected_subscriptions),
        "pending_reminders_to_supersede": len(pending_to_supersede),
        "future_reminders_to_create": future_to_create,
        "schedule_change_messages_estimate": len(affected_subscriptions),
        "schedule_semantic_changes": len(schedule_changes),
        "as_of": now.isoformat(),
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
        "stage_type": stage.stage_type,
        "stage_label": stage.label,
        "stage_order": stage.stage_order,
        "node_type": node.node_type,
        "occurs_at": _utc_iso(node.occurs_at),
        "description": node.description,
        "prominence": node.prominence,
        "prominence_override_reason": node.prominence_override_reason,
        "node_revision": node.node_revision,
    }


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


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


def _freeze_node_revisions(revision: CompetitionRevision) -> None:
    if revision.base_revision_id is None:
        for node in revision.time_nodes:
            node.node_revision = 1
        return
    base = db.session.get(CompetitionRevision, revision.base_revision_id)
    if base is None:
        raise ServiceError(HTTPStatus.CONFLICT, "conflict", "base revision is missing")
    base_nodes = {
        node.logical_node_key: (stage, node) for stage in base.stages for node in stage.time_nodes
    }
    logical_keys = {
        node.logical_node_key for node in revision.time_nodes if node.logical_node_key is not None
    }
    approved_revision_maxima = get_max_approved_node_revisions(
        revision.competition_id,
        logical_keys,
    )
    for stage in revision.stages:
        for node in stage.time_nodes:
            prior_entry = base_nodes.get(node.logical_node_key)
            if prior_entry is None:
                # Approved removal keeps historical reminder identities. Re-adding
                # the same logical milestone must allocate a fresh identity.
                prior_maximum = approved_revision_maxima.get(node.logical_node_key)
                node.node_revision = prior_maximum + 1 if prior_maximum is not None else 1
                continue
            prior_stage, prior = prior_entry
            changed = _node_behavior_facts(prior_stage, prior) != _node_behavior_facts(stage, node)
            if changed:
                prior_maximum = approved_revision_maxima.get(
                    node.logical_node_key,
                    prior.node_revision,
                )
                node.node_revision = prior_maximum + 1
            else:
                node.node_revision = prior.node_revision


def _node_behavior_facts(stage: CompetitionStage, node: CompetitionTimeNode) -> tuple:
    facts = _node_facts(stage, node)
    return tuple(facts[field] for field in NODE_BEHAVIOR_CHANGE_FIELDS)


def _write_reconciliation_event(
    actor: User,
    revision: CompetitionRevision,
    reason: str,
    comparison: dict[str, list[dict[str, Any]]],
) -> None:
    _write_audit(
        actor,
        "competition_revision.reconcile",
        "competition_revision",
        revision.id,
        {
            "competition_id": revision.competition_id,
            "base_revision_id": revision.base_revision_id,
            "reason": reason,
            "time_node_changes": comparison["time_node_changes"],
        },
    )


def _schedule_changes(
    comparison: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    result = []
    for change in comparison["time_node_changes"]:
        before = change.get("before") or {}
        after = change.get("after") or {}
        if change.get("change") in {"added", "removed"} or (
            before.get("occurs_at") != after.get("occurs_at")
            or before.get("node_type") != after.get("node_type")
        ):
            result.append(change)
    return result


def _reminder_replacement_keys(
    comparison: dict[str, list[dict[str, Any]]],
) -> set[str]:
    """Return nodes whose behavior requires a new ordinary reminder identity."""
    replacement_keys = set()
    for change in comparison["time_node_changes"]:
        before = change.get("before") or {}
        after = change.get("after") or {}
        if change.get("change") in {"added", "removed"} or any(
            before.get(field) != after.get(field) for field in NODE_BEHAVIOR_CHANGE_FIELDS
        ):
            replacement_keys.add(change["logical_node_key"])
    return replacement_keys


def _subscription_affected(
    subscription: Subscription,
    schedule_changes: list[dict[str, Any]],
) -> bool:
    selected_types = set(subscription.node_types or [])
    return any(
        selected_types.intersection(
            {
                value.get("node_type")
                for value in (change.get("before") or {}, change.get("after") or {})
                if value.get("node_type") is not None
            }
        )
        for change in schedule_changes
    )


def _reconcile_subscriber_state(
    revision: CompetitionRevision,
    comparison: dict[str, list[dict[str, Any]]],
    now: datetime,
) -> dict[str, Any]:
    schedule_changes = _schedule_changes(comparison)
    replacement_keys = _reminder_replacement_keys(comparison)
    base = db.session.get(CompetitionRevision, revision.base_revision_id)
    base_nodes_by_key = {
        node.logical_node_key: node for node in (base.time_nodes if base is not None else [])
    }
    new_nodes_by_key = {node.logical_node_key: node for node in revision.time_nodes}
    subscription_snapshot = engagement_repository.list_active_subscriptions_for_competition(
        revision.competition_id
    )
    reminder_settings = _required_reminder_settings(subscription_snapshot, for_update=True)
    subscriptions = engagement_repository.list_active_subscriptions_for_competition(
        revision.competition_id, for_update=True
    )
    reminders = engagement_repository.list_reconcilable_reminders_for_competition_for_update(
        revision.competition_id
    )
    reconciled_at = datetime.now(UTC)
    affected_subscriptions = [
        subscription
        for subscription in subscriptions
        if _subscription_affected(subscription, schedule_changes)
    ]
    impact = {
        "active_subscriptions": len(subscriptions),
        "affected_active_subscriptions": len(affected_subscriptions),
        "pending_reminders_to_supersede": 0,
        "future_reminders_to_create": 0,
        "schedule_change_messages_estimate": len(affected_subscriptions),
        "as_of": reconciled_at.isoformat(),
    }
    in_place_keys = (base_nodes_by_key.keys() & new_nodes_by_key.keys()) - replacement_keys
    in_place_base_ids = {base_nodes_by_key[key].id for key in in_place_keys}
    in_place_base_nodes = {
        base_nodes_by_key[key].id: base_nodes_by_key[key] for key in in_place_keys
    }
    if in_place_base_ids:
        for reminder in reminders:
            if reminder.time_node_snapshot_id not in in_place_base_ids:
                continue
            base_node = in_place_base_nodes[reminder.time_node_snapshot_id]
            new_node = new_nodes_by_key[base_node.logical_node_key]
            _move_reminder_to_current_snapshot(reminder, revision, new_node)

    if not replacement_keys:
        return impact
    changed_base_nodes = {
        node.id: node for key, node in base_nodes_by_key.items() if key in replacement_keys
    }
    changed_base_ids = set(changed_base_nodes)
    for reminder in reminders:
        if reminder.time_node_snapshot_id not in changed_base_ids:
            continue
        if reminder.status == ReminderStatus.PENDING:
            impact["pending_reminders_to_supersede"] += 1
            revoke_pending_reminder(reminder, "competition_revision_superseded")
        else:
            reminder.next_attempt_at = None
        reminder.cancel_reason = "competition_revision_superseded"

    changed_new_nodes = {
        key: node for key, node in new_nodes_by_key.items() if key in replacement_keys
    }
    for subscription in subscriptions:
        if (
            subscription.reminder_enabled
            and subscription.reminder_confirmed_at is not None
            and reminder_settings[subscription.user_id].enabled
        ):
            for node in changed_new_nodes.values():
                if node.node_type not in (subscription.node_types or []) or node.occurs_at is None:
                    continue
                due_at = _aware_utc(node.occurs_at) - timedelta(days=subscription.remind_days)
                if due_at <= reconciled_at:
                    continue
                db.session.add(
                    Reminder(
                        id=engagement_repository.next_sqlite_id(Reminder),
                        user_id=subscription.user_id,
                        competition_id=revision.competition_id,
                        time_node_snapshot_id=node.id,
                        logical_node_key=node.logical_node_key,
                        time_node_revision=node.node_revision,
                        node_type=node.node_type,
                        due_at=due_at,
                        title=bounded_title(revision.title, f": {node.node_type}"),
                        body=node.description,
                        status=ReminderStatus.PENDING,
                    )
                )
                impact["future_reminders_to_create"] += 1
        if not _subscription_affected(subscription, schedule_changes):
            continue
        idempotency_key = f"competition_revision:{revision.id}:time_changed"
        create_competition_event_message(
            user_id=subscription.user_id,
            competition=revision.competition,
            message_type="competition_time_changed",
            idempotency_key=idempotency_key,
            event_occurred_at=now,
            title_snapshot=bounded_title(revision.title, " schedule changed"),
            body_snapshot="Review the updated competition timeline.",
            reason_summary="Competition timeline changed.",
        )
    return impact


def _required_reminder_settings(
    subscriptions: list[Subscription],
    *,
    for_update: bool = False,
) -> dict[int, Any]:
    settings = {}
    for subscription in subscriptions:
        getter = (
            engagement_repository.get_reminder_setting_for_update
            if for_update
            else engagement_repository.get_reminder_setting
        )
        setting = getter(subscription.user_id)
        if setting is None:
            raise ServiceError(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "internal_server_error",
                "student-owned profile data is missing",
            )
        settings[subscription.user_id] = setting
    return settings


def _move_reminder_to_current_snapshot(
    reminder: Reminder,
    revision: CompetitionRevision,
    node: CompetitionTimeNode,
) -> None:
    reminder.time_node_snapshot_id = node.id
    reminder.logical_node_key = node.logical_node_key
    reminder.time_node_revision = node.node_revision
    reminder.node_type = node.node_type
    reminder.title = bounded_title(revision.title, f": {node.node_type}")
    reminder.body = node.description


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _require_revision_workflow_lifecycle(edition: Competition) -> None:
    if edition.status in REVISION_WORKFLOW_LIFECYCLE_STATUSES:
        return
    raise ServiceError(
        HTTPStatus.CONFLICT,
        "conflict",
        "competition lifecycle does not allow revision workflow",
        {"lifecycle_status": edition.status.value},
    )


def _require_no_active_revision(competition_id: int) -> None:
    active = get_active_competition_revision(competition_id)
    if active is None:
        return
    raise ServiceError(
        HTTPStatus.CONFLICT,
        "active_revision_exists",
        "the edition already has an active revision",
        {"revision_id": active.id, "revision_status": active.revision_status.value},
    )


def _is_unique_constraint(error: IntegrityError, name: str) -> bool:
    constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    return constraint_name == name or name in str(error.orig)


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
