from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from flask import current_app
from sqlalchemy import and_, func, inspect, or_, select

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
    Favorite,
    Message,
    RecommendationRuleSet,
    Reminder,
    ReminderSetting,
    ReviewRecord,
    StudentProfile,
    Subscription,
    SystemConfig,
    User,
    UserIdentity,
)
from competehub_api.models.enums import (
    CompetitionRevisionStatus,
    CompetitionStatus,
    IdentityVerificationStatus,
    ReminderStatus,
    ReviewStatus,
    SubscriptionStatus,
    UserRole,
    UserStatus,
)
from competehub_api.models.mixins import utc_now
from competehub_api.seeds.recommendation_rules import (
    InitialRecommendationRuleSetConflict,
    seed_initial_recommendation_rule_set,
)
from competehub_api.services.auth import hash_password, normalize_identity
from competehub_api.services.passwords import verify_password_hash
from competehub_api.services.profiles import DEFAULT_REMINDER_NODE_TYPES

DEVELOPMENT_DEMO_REGISTRY_KEY = "development_demo.bootstrap.v1"
DEMO_VERIFIED_AT = datetime(2026, 7, 16, 0, 0, tzinfo=UTC)


class DevelopmentDemoConflict(RuntimeError):
    """The development demo dataset cannot be safely created or replaced."""


@dataclass(frozen=True)
class DemoBootstrapResult:
    action: str


@dataclass(frozen=True)
class DemoActor:
    key: str
    email: str
    password: str
    display_name: str
    role: UserRole
    capabilities: tuple[str, ...]
    profile: dict[str, object] | None = None


DEVELOPMENT_DEMO_ACTORS = (
    DemoActor(
        key="student",
        email="student.day1@example.edu",
        password="violet harbor lantern orbit 47",
        display_name="Day 1 Student",
        role=UserRole.STUDENT,
        capabilities=(),
        profile={
            "college": "计算机学院",
            "major": "软件工程",
            "grade": "大二",
            "interest_tags": ["人工智能", "创新创业", "程序设计"],
            "competition_experience": "参加过校级程序设计竞赛",
            "goal_preferences": ["能力提升", "保研"],
            "blocked_tags": ["数学建模"],
        },
    ),
    DemoActor(
        key="editor",
        email="admin.day1@example.edu",
        password="copper meadow signal river 82",
        display_name="Day 1 Editor",
        role=UserRole.ADMIN,
        capabilities=(
            "competition_editor",
            "competition_maintainer",
            "recommendation_editor",
        ),
    ),
    DemoActor(
        key="reviewer",
        email="reviewer.day1@example.edu",
        password="silver orchard compass cloud 59",
        display_name="Day 1 Reviewer",
        role=UserRole.ADMIN,
        capabilities=(
            "competition_reviewer",
            "competition_maintainer",
            "recommendation_reviewer",
        ),
    ),
    DemoActor(
        key="owner",
        email="owner.day1@example.edu",
        password="indigo summit owner path 73",
        display_name="Day 1 Owner",
        role=UserRole.ADMIN,
        capabilities=("user_administrator",),
    ),
)


def bootstrap_development_demo(*, reset_demo: bool = False) -> DemoBootstrapResult:
    try:
        _require_development_environment()
        _require_migrated_database()
        registry = SystemConfig.query.filter_by(key=DEVELOPMENT_DEMO_REGISTRY_KEY).one_or_none()
        registry_existed = registry is not None
        if reset_demo:
            if registry is None:
                raise DevelopmentDemoConflict(
                    "development demo registry does not exist; run the default bootstrap first"
                )
            owned_records = _registry_records(registry)
            _validate_reset_ownership(owned_records)
            _reject_external_references(owned_records)
            _delete_owned_records(owned_records)
            db.session.delete(registry)
            db.session.flush()
            registry = None
            registry_existed = False
        if registry is None:
            registry = SystemConfig(
                id=_next_id(SystemConfig),
                key=DEVELOPMENT_DEMO_REGISTRY_KEY,
                value={
                    "schema_version": 1,
                    "dataset_version": 1,
                    "created_at": utc_now().isoformat(),
                    "records": {},
                },
                description=("Owned records for the development-only Day 1 demo bootstrap."),
            )
            db.session.add(registry)
        records = _registry_records(registry)
        _ensure_actors(records)
        _ensure_competition_graph(records)
        _ensure_engagement_graph(records)
        try:
            seed_initial_recommendation_rule_set(commit=False)
        except InitialRecommendationRuleSetConflict as exc:
            raise DevelopmentDemoConflict(str(exc)) from exc
        registry.value = {
            **registry.value,
            "schema_version": 1,
            "dataset_version": 1,
            "verified_at": utc_now().isoformat(),
            "records": records,
        }
        db.session.commit()
        return DemoBootstrapResult(
            action="reset" if reset_demo else ("verified" if registry_existed else "created")
        )
    except Exception:
        db.session.rollback()
        raise


def _require_development_environment() -> None:
    environment = str(
        current_app.config.get(
            "COMPETEHUB_ENV",
            os.getenv("COMPETEHUB_ENV", "development"),
        )
    ).casefold()
    if (
        environment != "development"
        or current_app.config.get("TESTING")
        or current_app.config.get("E2E_TESTING")
    ):
        raise DevelopmentDemoConflict(
            "bootstrap-development-demo requires the normal development environment"
        )


def _require_migrated_database() -> None:
    required_tables = {"system_configs", "users", "competitions"}
    available_tables = set(inspect(db.engine).get_table_names())
    missing = sorted(required_tables - available_tables)
    if missing:
        raise DevelopmentDemoConflict(
            "bootstrap-development-demo requires a migrated database; "
            f"missing tables: {', '.join(missing)}"
        )


def _next_id(model) -> int:
    value = db.session.execute(select(func.max(model.id))).scalar_one_or_none()
    return (value or 0) + 1


def _registry_records(registry: SystemConfig) -> dict:
    value = registry.value
    if not isinstance(value, dict):
        raise DevelopmentDemoConflict("development demo registry value is invalid")
    if value.get("schema_version") != 1 or value.get("dataset_version") != 1:
        raise DevelopmentDemoConflict("development demo registry version is unsupported")
    records = value.get("records")
    if not isinstance(records, dict):
        raise DevelopmentDemoConflict("development demo registry records are invalid")
    return records


def _ensure_actors(records: dict) -> None:
    users = records.setdefault("users", {})
    identities = records.setdefault("identities", {})
    profiles = records.setdefault("profiles", {})
    settings = records.setdefault("reminder_settings", {})

    for actor in DEVELOPMENT_DEMO_ACTORS:
        user = _ensure_actor(actor, users)
        _ensure_identity(actor, user, identities)
        if actor.profile is not None:
            _ensure_profile(actor, user, profiles)
            _ensure_reminder_settings(actor, user, settings)


def _ensure_actor(actor: DemoActor, records: dict) -> User:
    registered = records.get(actor.key)
    by_email = User.query.filter_by(email=actor.email).one_or_none()
    if registered is None:
        if by_email is not None:
            raise DevelopmentDemoConflict(
                f"reserved demo account is not registry-owned: {actor.email}"
            )
        user = User(
            id=_next_id(User),
            email=actor.email,
            password_hash=hash_password(actor.password, identity=actor.email),
            display_name=actor.display_name,
            role=actor.role,
            status=UserStatus.ACTIVE,
            capabilities=list(actor.capabilities),
        )
        db.session.add(user)
        db.session.flush()
        records[actor.key] = {"id": user.id, "email": actor.email}
        return user

    user = db.session.get(User, _registered_id(registered, f"user {actor.key}"))
    if user is None:
        if by_email is not None:
            raise DevelopmentDemoConflict(
                f"registered demo account id is missing but email is occupied: {actor.email}"
            )
        user = User(
            id=_next_id(User),
            email=actor.email,
            password_hash=hash_password(actor.password, identity=actor.email),
            display_name=actor.display_name,
            role=actor.role,
            status=UserStatus.ACTIVE,
            capabilities=list(actor.capabilities),
        )
        db.session.add(user)
        db.session.flush()
        records[actor.key] = {"id": user.id, "email": actor.email}
        return user

    expected = (
        actor.email,
        actor.display_name,
        actor.role,
        UserStatus.ACTIVE,
        list(actor.capabilities),
    )
    actual = (
        user.email,
        user.display_name,
        user.role,
        user.status,
        user.capabilities,
    )
    if actual != expected or not verify_password_hash(user.password_hash, actor.password):
        raise DevelopmentDemoConflict(f"registered demo account drifted: {actor.email}")
    if registered.get("email") != actor.email:
        raise DevelopmentDemoConflict(f"demo registry identity drifted: user {actor.key}")
    return user


def _ensure_identity(actor: DemoActor, user: User, records: dict) -> None:
    registered = records.get(actor.key)
    normalized = normalize_identity("email", actor.email)
    by_value = UserIdentity.query.filter_by(
        identity_type="email",
        normalized_value=normalized,
    ).one_or_none()
    if registered is None:
        if by_value is not None:
            raise DevelopmentDemoConflict(
                f"reserved demo identity is not registry-owned: {actor.email}"
            )
        identity = UserIdentity(
            id=_next_id(UserIdentity),
            user_id=user.id,
            identity_type="email",
            normalized_value=normalized,
            display_value=actor.email,
            verification_status=IdentityVerificationStatus.VERIFIED,
            verification_method="development_demo_seed",
            verified_at=DEMO_VERIFIED_AT,
        )
        db.session.add(identity)
        db.session.flush()
        records[actor.key] = {"id": identity.id, "email": actor.email}
        return

    identity = db.session.get(
        UserIdentity,
        _registered_id(registered, f"identity {actor.key}"),
    )
    if identity is None:
        if by_value is not None:
            raise DevelopmentDemoConflict(
                f"registered demo identity is missing but value is occupied: {actor.email}"
            )
        identity = UserIdentity(
            id=_next_id(UserIdentity),
            user_id=user.id,
            identity_type="email",
            normalized_value=normalized,
            display_value=actor.email,
            verification_status=IdentityVerificationStatus.VERIFIED,
            verification_method="development_demo_seed",
            verified_at=DEMO_VERIFIED_AT,
        )
        db.session.add(identity)
        db.session.flush()
        records[actor.key] = {"id": identity.id, "email": actor.email}
        return

    actual = (
        identity.user_id,
        identity.identity_type,
        identity.normalized_value,
        identity.display_value,
        identity.verification_status,
        identity.verification_method,
    )
    expected = (
        user.id,
        "email",
        normalized,
        actor.email,
        IdentityVerificationStatus.VERIFIED,
        "development_demo_seed",
    )
    if actual != expected or registered.get("email") != actor.email:
        raise DevelopmentDemoConflict(f"registered demo identity drifted: {actor.email}")


def _ensure_profile(actor: DemoActor, user: User, records: dict) -> None:
    registered = records.get(actor.key)
    profile = StudentProfile.query.filter_by(user_id=user.id).one_or_none()
    if registered is None:
        if profile is not None:
            raise DevelopmentDemoConflict(f"student profile is not registry-owned: {actor.email}")
        profile = StudentProfile(
            id=_next_id(StudentProfile),
            user_id=user.id,
            **actor.profile,
        )
        db.session.add(profile)
        db.session.flush()
        records[actor.key] = {"id": profile.id, "user_email": actor.email}
        return

    if profile is None:
        profile = StudentProfile(
            id=_next_id(StudentProfile),
            user_id=user.id,
            **actor.profile,
        )
        db.session.add(profile)
        db.session.flush()
        records[actor.key] = {"id": profile.id, "user_email": actor.email}
        return

    if profile.id != _registered_id(registered, f"profile {actor.key}"):
        raise DevelopmentDemoConflict(f"registered demo profile id drifted: {actor.email}")
    actual = {
        "college": profile.college,
        "major": profile.major,
        "grade": profile.grade,
        "interest_tags": profile.interest_tags,
        "competition_experience": profile.competition_experience,
        "goal_preferences": profile.goal_preferences,
        "blocked_tags": profile.blocked_tags,
    }
    if actual != actor.profile:
        raise DevelopmentDemoConflict(f"registered demo profile drifted: {actor.email}")


def _ensure_reminder_settings(actor: DemoActor, user: User, records: dict) -> None:
    registered = records.get(actor.key)
    setting = ReminderSetting.query.filter_by(user_id=user.id).one_or_none()
    if registered is None:
        if setting is not None:
            raise DevelopmentDemoConflict(
                f"reminder settings are not registry-owned: {actor.email}"
            )
        setting = ReminderSetting(
            id=_next_id(ReminderSetting),
            user_id=user.id,
            enabled=True,
            default_remind_days=3,
            node_types=list(DEFAULT_REMINDER_NODE_TYPES),
        )
        db.session.add(setting)
        db.session.flush()
        records[actor.key] = {"id": setting.id, "user_email": actor.email}
        return

    if setting is None:
        setting = ReminderSetting(
            id=_next_id(ReminderSetting),
            user_id=user.id,
            enabled=True,
            default_remind_days=3,
            node_types=list(DEFAULT_REMINDER_NODE_TYPES),
        )
        db.session.add(setting)
        db.session.flush()
        records[actor.key] = {"id": setting.id, "user_email": actor.email}
        return

    actual = (
        setting.id,
        setting.enabled,
        setting.default_remind_days,
        setting.node_types,
    )
    expected = (
        _registered_id(registered, f"reminder settings {actor.key}"),
        True,
        3,
        list(DEFAULT_REMINDER_NODE_TYPES),
    )
    if actual != expected:
        raise DevelopmentDemoConflict(f"registered demo reminder settings drifted: {actor.email}")


def _registered_id(record: dict, label: str) -> int:
    if not isinstance(record, dict) or not isinstance(record.get("id"), int):
        raise DevelopmentDemoConflict(f"development demo registry entry is invalid: {label}")
    return record["id"]


def _ensure_competition_graph(records: dict) -> None:
    editor = User.query.filter_by(email="admin.day1@example.edu").one()
    reviewer = User.query.filter_by(email="reviewer.day1@example.edu").one()
    decided_at = datetime(2026, 7, 16, 1, 0, tzinfo=UTC)

    series = _ensure_model(
        records,
        "series",
        "day1",
        CompetitionSeries,
        lambda: CompetitionSeries.query.filter_by(
            canonical_name="CompeteHub Day 1 Demo Series"
        ).one_or_none(),
        lambda record_id: CompetitionSeries(
            id=record_id,
            canonical_name="CompeteHub Day 1 Demo Series",
            created_by_id=editor.id,
        ),
        {
            "canonical_name": "CompeteHub Day 1 Demo Series",
            "created_by_id": editor.id,
        },
        {"canonical_name": "CompeteHub Day 1 Demo Series"},
    )

    editions: dict[str, Competition] = {}
    edition_specs = {
        "published": {
            "edition_label": "2026-published",
            "title": "全国大学生人工智能创新挑战赛 2026",
            "status": CompetitionStatus.PUBLISHED,
            "complete": True,
        },
        "pending": {
            "edition_label": "2027-pending",
            "title": "全国大学生人工智能创新挑战赛 2027",
            "status": CompetitionStatus.UNPUBLISHED,
            "complete": True,
        },
        "incomplete": {
            "edition_label": "2026-incomplete",
            "title": "材料待补充的创新赛事 2026",
            "status": CompetitionStatus.UNPUBLISHED,
            "complete": False,
        },
        "cancelled": {
            "edition_label": "2025-cancelled",
            "title": "全国大学生人工智能创新挑战赛 2025（已取消）",
            "status": CompetitionStatus.CANCELLED,
            "complete": True,
        },
        "offline": {
            "edition_label": "2025-offline",
            "title": "全国大学生人工智能创新挑战赛 2025（已下线）",
            "status": CompetitionStatus.OFFLINE,
            "complete": True,
        },
    }
    for key, spec in edition_specs.items():
        fields = _competition_fields(spec["title"], spec["status"], spec["complete"])
        fields.update(
            {
                "series_id": series.id,
                "edition_label": spec["edition_label"],
                "created_by_id": editor.id,
            }
        )
        editions[key] = _ensure_model(
            records,
            "competitions",
            key,
            Competition,
            lambda label=spec["edition_label"]: Competition.query.filter_by(
                series_id=series.id,
                edition_label=label,
            ).one_or_none(),
            lambda record_id, values=fields: Competition(id=record_id, **values),
            fields,
            {
                "series": "CompeteHub Day 1 Demo Series",
                "edition_label": spec["edition_label"],
            },
        )

    revisions: dict[str, CompetitionRevision] = {}
    revision_specs = {
        "published": (
            editions["published"],
            CompetitionRevisionStatus.APPROVED,
            True,
            editor.id,
            editor.id,
            decided_at,
        ),
        "pending": (
            editions["pending"],
            CompetitionRevisionStatus.PENDING_REVIEW,
            True,
            editor.id,
            editor.id,
            None,
        ),
        "incomplete": (
            editions["incomplete"],
            CompetitionRevisionStatus.DRAFT,
            False,
            editor.id,
            None,
            None,
        ),
        "cancelled": (
            editions["cancelled"],
            CompetitionRevisionStatus.APPROVED,
            True,
            editor.id,
            editor.id,
            decided_at,
        ),
        "offline": (
            editions["offline"],
            CompetitionRevisionStatus.APPROVED,
            True,
            editor.id,
            editor.id,
            decided_at,
        ),
    }
    for key, (
        edition,
        status,
        complete,
        creator_id,
        submitter_id,
        decided,
    ) in revision_specs.items():
        fields = _revision_fields(
            edition,
            status=status,
            complete=complete,
            creator_id=creator_id,
            submitter_id=submitter_id,
            decided_at=decided,
        )
        revisions[key] = _ensure_model(
            records,
            "revisions",
            key,
            CompetitionRevision,
            lambda edition_id=edition.id: CompetitionRevision.query.filter_by(
                competition_id=edition_id,
                revision_number=1,
            ).one_or_none(),
            lambda record_id, values=fields: CompetitionRevision(id=record_id, **values),
            fields,
            {"competition_id": edition.id, "revision_number": 1},
        )

    for key in ("published", "cancelled", "offline"):
        edition = editions[key]
        revision = revisions[key]
        if edition.published_revision_id is None:
            edition.published_revision = revision
        elif edition.published_revision_id != revision.id:
            raise DevelopmentDemoConflict(f"registered demo public revision pointer drifted: {key}")
    if editions["pending"].published_revision_id is not None:
        raise DevelopmentDemoConflict("pending demo edition unexpectedly became public")
    if editions["incomplete"].published_revision_id is not None:
        raise DevelopmentDemoConflict("incomplete demo edition unexpectedly became public")

    stage_specs = (
        (
            "registration",
            "registration",
            "报名",
            1,
            "registration-deadline",
            "registration_deadline",
            DEMO_VERIFIED_AT + timedelta(days=27),
        ),
        (
            "submission",
            "submission",
            "作品提交",
            2,
            "submission-deadline",
            "submission_deadline",
            datetime(2026, 9, 10, 16, 0, tzinfo=UTC),
        ),
        (
            "competition",
            "competition",
            "正式比赛",
            3,
            "competition-start",
            "competition_start",
            datetime(2026, 10, 1, 1, 0, tzinfo=UTC),
        ),
    )
    for stage_key, stage_type, label, order, node_key, node_type, occurs_at in stage_specs:
        stage = _ensure_model(
            records,
            "stages",
            f"published-{stage_key}",
            CompetitionStage,
            lambda value=stage_key: CompetitionStage.query.filter_by(
                competition_revision_id=revisions["published"].id,
                stage_key=value,
            ).one_or_none(),
            lambda record_id, value=stage_key, kind=stage_type, name=label, position=order: (
                CompetitionStage(
                    id=record_id,
                    competition_revision_id=revisions["published"].id,
                    stage_key=value,
                    stage_type=kind,
                    label=name,
                    stage_order=position,
                )
            ),
            {
                "competition_revision_id": revisions["published"].id,
                "stage_key": stage_key,
                "stage_type": stage_type,
                "label": label,
                "stage_order": order,
            },
            {"revision": "published", "stage_key": stage_key},
        )

        def build_time_node(
            record_id,
            value=node_key,
            kind=node_type,
            instant=occurs_at,
            stage_id=stage.id,
            description=label,
        ):
            return CompetitionTimeNode(
                id=record_id,
                competition_id=editions["published"].id,
                competition_revision_id=revisions["published"].id,
                stage_id=stage_id,
                logical_node_key=value,
                node_revision=1,
                node_type=kind,
                occurs_at=instant,
                prominence="primary",
                description=description,
            )

        _ensure_model(
            records,
            "time_nodes",
            f"published-{node_key}",
            CompetitionTimeNode,
            lambda value=node_key: CompetitionTimeNode.query.filter_by(
                competition_revision_id=revisions["published"].id,
                logical_node_key=value,
            ).one_or_none(),
            build_time_node,
            {
                "competition_id": editions["published"].id,
                "competition_revision_id": revisions["published"].id,
                "stage_id": stage.id,
                "logical_node_key": node_key,
                "node_revision": 1,
                "node_type": node_type,
                "occurs_at": occurs_at,
                "prominence": "primary",
                "description": label,
            },
            {"revision": "published", "logical_node_key": node_key},
        )

    tags = {}
    for key, code, name in (
        ("ai", "demo-ai", "人工智能"),
        ("innovation", "demo-innovation", "创新创业"),
    ):
        tags[key] = _ensure_model(
            records,
            "tags",
            key,
            CompetitionTag,
            lambda value=code: CompetitionTag.query.filter_by(code=value).one_or_none(),
            lambda record_id, value=code, label=name: CompetitionTag(
                id=record_id,
                code=value,
                name=label,
                tag_type="topic",
                description="Development demo tag.",
            ),
            {
                "code": code,
                "name": name,
                "tag_type": "topic",
                "description": "Development demo tag.",
            },
            {"code": code},
        )
        _ensure_model(
            records,
            "tag_links",
            f"published-{key}",
            CompetitionTagLink,
            lambda tag_id=tags[key].id: CompetitionTagLink.query.filter_by(
                competition_revision_id=revisions["published"].id,
                tag_id=tag_id,
            ).one_or_none(),
            lambda record_id, tag_id=tags[key].id: CompetitionTagLink(
                id=record_id,
                competition_id=editions["published"].id,
                competition_revision_id=revisions["published"].id,
                tag_id=tag_id,
            ),
            {
                "competition_id": editions["published"].id,
                "competition_revision_id": revisions["published"].id,
                "tag_id": tags[key].id,
            },
            {"revision": "published", "tag": code},
        )

    _ensure_model(
        records,
        "review_records",
        "published-approval",
        ReviewRecord,
        lambda: ReviewRecord.query.filter_by(
            target_type="competition_revision",
            target_id=revisions["published"].id,
            target_revision=1,
        ).one_or_none(),
        lambda record_id: ReviewRecord(
            id=record_id,
            target_type="competition_revision",
            target_id=revisions["published"].id,
            target_revision=1,
            submitted_by_id=editor.id,
            submitted_at=decided_at,
            reviewed_by_id=reviewer.id,
            status=ReviewStatus.APPROVED,
            comment="Development demo source facts verified.",
            differences=[
                {
                    "kind": "field",
                    "field": "title",
                    "before": None,
                    "after": revisions["published"].title,
                }
            ],
            impact={"public_visibility": "publish", "active_subscriptions": 1},
            decided_at=decided_at,
        ),
        {
            "target_type": "competition_revision",
            "target_id": revisions["published"].id,
            "target_revision": 1,
            "submitted_by_id": editor.id,
            "submitted_at": decided_at,
            "reviewed_by_id": reviewer.id,
            "status": ReviewStatus.APPROVED,
            "comment": "Development demo source facts verified.",
            "differences": [
                {
                    "kind": "field",
                    "field": "title",
                    "before": None,
                    "after": revisions["published"].title,
                }
            ],
            "impact": {"public_visibility": "publish", "active_subscriptions": 1},
            "decided_at": decided_at,
        },
        {"target": "published revision approval"},
    )
    _ensure_model(
        records,
        "audit_logs",
        "published",
        AuditLog,
        lambda: AuditLog.query.filter_by(
            action="development_demo.competition_published",
            target_type="competition",
            target_id=editions["published"].id,
        ).one_or_none(),
        lambda record_id: AuditLog(
            id=record_id,
            actor_id=reviewer.id,
            action="development_demo.competition_published",
            target_type="competition",
            target_id=editions["published"].id,
            result="success",
            detail={
                "revision_id": revisions["published"].id,
                "reason": "development demo fixture",
            },
        ),
        {
            "actor_id": reviewer.id,
            "action": "development_demo.competition_published",
            "target_type": "competition",
            "target_id": editions["published"].id,
            "result": "success",
            "detail": {
                "revision_id": revisions["published"].id,
                "reason": "development demo fixture",
            },
        },
        {"action": "development_demo.competition_published"},
    )


def _competition_fields(
    title: str,
    status: CompetitionStatus,
    complete: bool,
) -> dict:
    return {
        "title": title,
        "short_title": "Day 1 AI Challenge" if complete else None,
        "category": "innovation" if complete else None,
        "organizer": "Example University Innovation Center" if complete else None,
        "host": "Example University" if complete else None,
        "source_name": "Example University Official Notice",
        "source_url": (
            "https://example.edu/notices/competehub-day1/" + title.encode("utf-8").hex()[:24]
        ),
        "official_url": "https://example.org/competehub-day1" if complete else None,
        "summary": "A source-backed development demo competition." if complete else None,
        "eligibility": "Currently enrolled university students." if complete else None,
        "registration_applicability": "applicable" if complete else None,
        "participant_form": "team" if complete else None,
        "participant_forms": ["individual", "team"] if complete else [],
        "major_scope": "selected" if complete else None,
        "grade_scope": "selected" if complete else None,
        "suitable_majors": ["软件工程", "计算机科学与技术"] if complete else None,
        "suitable_grades": ["大二", "大三"] if complete else None,
        "value_notes": "校级推荐，适合有项目实践基础的学生。" if complete else None,
        "status": status,
    }


def _ensure_engagement_graph(records: dict) -> None:
    student = User.query.filter_by(email="student.day1@example.edu").one()
    published = Competition.query.filter_by(edition_label="2026-published").one()
    offline = Competition.query.filter_by(edition_label="2025-offline").one()
    registration_node = CompetitionTimeNode.query.filter_by(
        competition_revision_id=published.published_revision_id,
        logical_node_key="registration-deadline",
    ).one()
    submission_node = CompetitionTimeNode.query.filter_by(
        competition_revision_id=published.published_revision_id,
        logical_node_key="submission-deadline",
    ).one()
    remind_days = 30
    sent_due_at = registration_node.occurs_at - timedelta(days=remind_days)
    confirmed_at = sent_due_at - timedelta(days=1)
    sent_at = sent_due_at + timedelta(minutes=1)

    _ensure_model(
        records,
        "favorites",
        "student-published",
        Favorite,
        lambda: Favorite.query.filter_by(
            user_id=student.id,
            competition_id=published.id,
        ).one_or_none(),
        lambda record_id: Favorite(
            id=record_id,
            user_id=student.id,
            competition_id=published.id,
            is_active=True,
        ),
        {
            "user_id": student.id,
            "competition_id": published.id,
            "is_active": True,
        },
        {"user_email": student.email, "edition_label": published.edition_label},
    )
    _ensure_model(
        records,
        "subscriptions",
        "student-published",
        Subscription,
        lambda: Subscription.query.filter_by(
            user_id=student.id,
            competition_id=published.id,
        ).one_or_none(),
        lambda record_id: Subscription(
            id=record_id,
            user_id=student.id,
            competition_id=published.id,
            status=SubscriptionStatus.ACTIVE,
            reminder_enabled=True,
            remind_days=remind_days,
            node_types=[
                "registration_deadline",
                "submission_deadline",
                "competition_start",
            ],
            reminder_confirmed_at=confirmed_at,
        ),
        {
            "user_id": student.id,
            "competition_id": published.id,
            "status": SubscriptionStatus.ACTIVE,
            "reminder_enabled": True,
            "remind_days": remind_days,
            "node_types": [
                "registration_deadline",
                "submission_deadline",
                "competition_start",
            ],
            "reminder_confirmed_at": confirmed_at,
        },
        {"user_email": student.email, "edition_label": published.edition_label},
    )
    sent_reminder = _ensure_reminder(
        records,
        "registration-sent",
        student,
        published,
        registration_node,
        ReminderStatus.SENT,
        sent_at,
        remind_days,
    )
    _ensure_reminder(
        records,
        "submission-pending",
        student,
        published,
        submission_node,
        ReminderStatus.PENDING,
        None,
        remind_days,
    )
    _ensure_message(
        records=records,
        key="registration-unread",
        student=student,
        competition=published,
        reminder=sent_reminder,
        message_type="reminder_due",
        idempotency_key="development-demo:reminder:registration:sent",
        event_occurred_at=sent_due_at,
        created_at=sent_at,
        title="报名截止提醒",
        body="Day 1 演示赛事即将截止报名。",
        target_snapshot={
            "competition_id": published.id,
            "competition_title": published.title,
            "node_type": registration_node.node_type,
            "node_occurs_at": registration_node.occurs_at.isoformat(),
            "reason_summary": None,
        },
        is_read=False,
    )
    schedule_changed_at = DEMO_VERIFIED_AT - timedelta(days=2)
    _ensure_message(
        records=records,
        key="schedule-change-read",
        student=student,
        competition=published,
        reminder=None,
        message_type="competition_time_changed",
        idempotency_key="development-demo:competition:published:time-changed",
        event_occurred_at=schedule_changed_at,
        created_at=schedule_changed_at,
        title="赛事时间已更新",
        body="请查看更新后的赛事时间线。",
        target_snapshot={
            "competition_id": published.id,
            "competition_title": published.title,
            "node_type": None,
            "node_occurs_at": None,
            "reason_summary": "Competition timeline changed.",
        },
        is_read=True,
        read_at=schedule_changed_at + timedelta(hours=1),
    )
    offline_at = DEMO_VERIFIED_AT - timedelta(days=1)
    _ensure_message(
        records=records,
        key="offline-unread",
        student=student,
        competition=offline,
        reminder=None,
        message_type="competition_offline",
        idempotency_key="development-demo:competition:offline",
        event_occurred_at=offline_at,
        created_at=offline_at,
        title="赛事已下线",
        body="该届次已不再对外展示。",
        target_snapshot={
            "competition_id": offline.id,
            "competition_title": offline.title,
            "node_type": None,
            "node_occurs_at": None,
            "reason_summary": "The edition was withdrawn from public detail.",
        },
        is_read=False,
    )


def _ensure_reminder(
    records: dict,
    key: str,
    student: User,
    competition: Competition,
    node: CompetitionTimeNode,
    status: ReminderStatus,
    sent_at: datetime | None,
    remind_days: int,
) -> Reminder:
    due_at = node.occurs_at - timedelta(days=remind_days)
    return _ensure_model(
        records,
        "reminders",
        key,
        Reminder,
        lambda: Reminder.query.filter_by(
            user_id=student.id,
            competition_id=competition.id,
            logical_node_key=node.logical_node_key,
            time_node_revision=node.node_revision,
        ).one_or_none(),
        lambda record_id: Reminder(
            id=record_id,
            user_id=student.id,
            competition_id=competition.id,
            time_node_snapshot_id=node.id,
            logical_node_key=node.logical_node_key,
            time_node_revision=node.node_revision,
            node_type=node.node_type,
            due_at=due_at,
            title=f"{competition.title}：{node.description}",
            body="Development demo reminder.",
            status=status,
            attempt_count=1 if status == ReminderStatus.SENT else 0,
            sent_at=sent_at,
        ),
        {
            "user_id": student.id,
            "competition_id": competition.id,
            "time_node_snapshot_id": node.id,
            "logical_node_key": node.logical_node_key,
            "time_node_revision": node.node_revision,
            "node_type": node.node_type,
            "due_at": due_at,
            "title": f"{competition.title}：{node.description}",
            "body": "Development demo reminder.",
            "status": status,
            "cancel_reason": None,
            "attempt_count": 1 if status == ReminderStatus.SENT else 0,
            "next_attempt_at": None,
            "last_error_code": None,
            "failed_at": None,
            "sent_at": sent_at,
        },
        {
            "user_email": student.email,
            "edition_label": competition.edition_label,
            "logical_node_key": node.logical_node_key,
        },
    )


def _ensure_message(
    *,
    records: dict,
    key: str,
    student: User,
    competition: Competition,
    reminder: Reminder | None,
    message_type: str,
    idempotency_key: str,
    event_occurred_at: datetime,
    created_at: datetime,
    title: str,
    body: str,
    target_snapshot: dict,
    is_read: bool,
    read_at: datetime | None = None,
) -> Message:
    retained_until = created_at + timedelta(days=365)
    fields = {
        "user_id": student.id,
        "reminder_id": reminder.id if reminder is not None else None,
        "competition_id": competition.id,
        "message_type": message_type,
        "idempotency_key": idempotency_key,
        "event_occurred_at": event_occurred_at,
        "title_snapshot": title,
        "body_snapshot": body,
        "target_snapshot": target_snapshot,
        "retained_until": retained_until,
        "is_read": is_read,
        "read_at": read_at,
        "created_at": created_at,
        "updated_at": created_at,
    }
    return _ensure_model(
        records,
        "messages",
        key,
        Message,
        lambda: Message.query.filter_by(
            user_id=student.id,
            idempotency_key=idempotency_key,
        ).one_or_none(),
        lambda record_id: Message(id=record_id, **fields),
        fields,
        {
            "user_email": student.email,
            "idempotency_key": idempotency_key,
        },
    )


def _revision_fields(
    edition: Competition,
    *,
    status: CompetitionRevisionStatus,
    complete: bool,
    creator_id: int,
    submitter_id: int | None,
    decided_at: datetime | None,
) -> dict:
    source = _competition_fields(edition.title, edition.status, complete)
    return {
        "competition_id": edition.id,
        "revision_number": 1,
        "revision_status": status,
        "title": source["title"],
        "short_title": source["short_title"],
        "category": source["category"],
        "organizer": source["organizer"],
        "host": source["host"],
        "source_name": source["source_name"],
        "source_url": source["source_url"],
        "official_url": source["official_url"],
        "summary": source["summary"],
        "eligibility": source["eligibility"],
        "registration_applicability": source["registration_applicability"],
        "participant_forms": source["participant_forms"],
        "major_scope": source["major_scope"],
        "grade_scope": source["grade_scope"],
        "suitable_majors": source["suitable_majors"],
        "suitable_grades": source["suitable_grades"],
        "value_notes": source["value_notes"],
        "created_by_id": creator_id,
        "submitted_by_id": submitter_id,
        "submitted_at": decided_at if submitter_id is not None else None,
        "decided_at": decided_at,
        "published_at": decided_at if status == CompetitionRevisionStatus.APPROVED else None,
    }


def _ensure_model(
    records: dict,
    group: str,
    key: str,
    model,
    lookup,
    build,
    expected_fields: dict,
    stable_identity: dict,
):
    group_records = records.setdefault(group, {})
    registered = group_records.get(key)
    by_identity = lookup()
    if registered is None:
        if by_identity is not None:
            raise DevelopmentDemoConflict(
                f"reserved demo record is not registry-owned: {group}.{key}"
            )
        instance = build(_next_id(model))
        db.session.add(instance)
        db.session.flush()
        group_records[key] = {"id": instance.id, **stable_identity}
        return instance

    instance = db.session.get(model, _registered_id(registered, f"{group}.{key}"))
    if instance is None:
        if by_identity is not None:
            raise DevelopmentDemoConflict(
                f"registered demo record is missing but identity is occupied: {group}.{key}"
            )
        instance = build(_next_id(model))
        db.session.add(instance)
        db.session.flush()
        group_records[key] = {"id": instance.id, **stable_identity}
        return instance

    if by_identity is None or by_identity.id != instance.id:
        raise DevelopmentDemoConflict(f"registered demo identity drifted: {group}.{key}")
    for field, expected in expected_fields.items():
        if not _values_match(getattr(instance, field), expected):
            raise DevelopmentDemoConflict(f"registered demo record drifted: {group}.{key}.{field}")
    for field, expected in stable_identity.items():
        if registered.get(field) != expected:
            raise DevelopmentDemoConflict(
                f"development demo registry identity drifted: {group}.{key}.{field}"
            )
    return instance


def _values_match(actual, expected) -> bool:
    if isinstance(actual, datetime) and isinstance(expected, datetime):
        return _utc_naive(actual) == _utc_naive(expected)
    return actual == expected


def _utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


OWNED_GROUP_MODELS = {
    "messages": Message,
    "reminders": Reminder,
    "favorites": Favorite,
    "subscriptions": Subscription,
    "reminder_settings": ReminderSetting,
    "profiles": StudentProfile,
    "identities": UserIdentity,
    "review_records": ReviewRecord,
    "audit_logs": AuditLog,
    "tag_links": CompetitionTagLink,
    "time_nodes": CompetitionTimeNode,
    "stages": CompetitionStage,
    "revisions": CompetitionRevision,
    "competitions": Competition,
    "tags": CompetitionTag,
    "series": CompetitionSeries,
    "users": User,
}

DELETE_GROUP_ORDER = tuple(OWNED_GROUP_MODELS)


def _validate_reset_ownership(records: dict) -> None:
    for group, model in OWNED_GROUP_MODELS.items():
        entries = records.get(group, {})
        if not isinstance(entries, dict):
            raise DevelopmentDemoConflict(f"development demo registry group is invalid: {group}")
        for key, entry in entries.items():
            record_id = _registered_id(entry, f"{group}.{key}")
            instance = db.session.get(model, record_id)
            if instance is None:
                continue
            _validate_stable_identity(group, key, entry, instance, records)


def _validate_stable_identity(
    group: str,
    key: str,
    entry: dict,
    instance,
    records: dict,
) -> None:
    if group == "users" and instance.email != entry.get("email"):
        raise DevelopmentDemoConflict(f"demo ownership identity drifted: {group}.{key}")
    if group == "identities" and instance.display_value != entry.get("email"):
        raise DevelopmentDemoConflict(f"demo ownership identity drifted: {group}.{key}")
    if group == "series" and instance.canonical_name != entry.get("canonical_name"):
        raise DevelopmentDemoConflict(f"demo ownership identity drifted: {group}.{key}")
    if group == "competitions" and instance.edition_label != entry.get("edition_label"):
        raise DevelopmentDemoConflict(f"demo ownership identity drifted: {group}.{key}")
    if group == "tags" and instance.code != entry.get("code"):
        raise DevelopmentDemoConflict(f"demo ownership identity drifted: {group}.{key}")
    if group == "messages" and instance.idempotency_key != entry.get("idempotency_key"):
        raise DevelopmentDemoConflict(f"demo ownership identity drifted: {group}.{key}")
    if group == "reminders" and instance.logical_node_key != entry.get("logical_node_key"):
        raise DevelopmentDemoConflict(f"demo ownership identity drifted: {group}.{key}")
    if group in {"profiles", "reminder_settings", "favorites", "subscriptions"}:
        user_ids = _owned_ids(records, "users")
        if instance.user_id not in user_ids:
            raise DevelopmentDemoConflict(f"demo ownership relation drifted: {group}.{key}")
    if group in {"revisions", "time_nodes", "tag_links"}:
        competition_ids = _owned_ids(records, "competitions")
        if instance.competition_id not in competition_ids:
            raise DevelopmentDemoConflict(f"demo ownership relation drifted: {group}.{key}")


def _reject_external_references(records: dict) -> None:
    user_ids = _owned_ids(records, "users")
    series_ids = _owned_ids(records, "series")
    competition_ids = _owned_ids(records, "competitions")
    revision_ids = _owned_ids(records, "revisions")
    stage_ids = _owned_ids(records, "stages")
    node_ids = _owned_ids(records, "time_nodes")
    tag_ids = _owned_ids(records, "tags")

    checks = (
        (
            "competition_series.created_by_id",
            CompetitionSeries.query.filter(
                CompetitionSeries.created_by_id.in_(user_ids),
                CompetitionSeries.id.notin_(series_ids),
            ).first(),
        ),
        (
            "competitions",
            Competition.query.filter(
                or_(
                    Competition.created_by_id.in_(user_ids),
                    Competition.series_id.in_(series_ids),
                    Competition.published_revision_id.in_(revision_ids),
                ),
                Competition.id.notin_(competition_ids),
            ).first(),
        ),
        (
            "competition_revisions",
            CompetitionRevision.query.filter(
                or_(
                    CompetitionRevision.created_by_id.in_(user_ids),
                    CompetitionRevision.submitted_by_id.in_(user_ids),
                    CompetitionRevision.competition_id.in_(competition_ids),
                    CompetitionRevision.base_revision_id.in_(revision_ids),
                ),
                CompetitionRevision.id.notin_(revision_ids),
            ).first(),
        ),
        (
            "competition_stages",
            CompetitionStage.query.filter(
                CompetitionStage.competition_revision_id.in_(revision_ids),
                CompetitionStage.id.notin_(stage_ids),
            ).first(),
        ),
        (
            "competition_time_nodes",
            CompetitionTimeNode.query.filter(
                or_(
                    CompetitionTimeNode.competition_id.in_(competition_ids),
                    CompetitionTimeNode.competition_revision_id.in_(revision_ids),
                    CompetitionTimeNode.stage_id.in_(stage_ids),
                ),
                CompetitionTimeNode.id.notin_(node_ids),
            ).first(),
        ),
        (
            "competition_tag_links",
            CompetitionTagLink.query.filter(
                or_(
                    CompetitionTagLink.competition_id.in_(competition_ids),
                    CompetitionTagLink.competition_revision_id.in_(revision_ids),
                    CompetitionTagLink.tag_id.in_(tag_ids),
                ),
                CompetitionTagLink.id.notin_(_owned_ids(records, "tag_links")),
            ).first(),
        ),
        (
            "favorites",
            Favorite.query.filter(
                or_(
                    Favorite.user_id.in_(user_ids),
                    Favorite.competition_id.in_(competition_ids),
                ),
                Favorite.id.notin_(_owned_ids(records, "favorites")),
            ).first(),
        ),
        (
            "subscriptions",
            Subscription.query.filter(
                or_(
                    Subscription.user_id.in_(user_ids),
                    Subscription.competition_id.in_(competition_ids),
                ),
                Subscription.id.notin_(_owned_ids(records, "subscriptions")),
            ).first(),
        ),
        (
            "reminders",
            Reminder.query.filter(
                or_(
                    Reminder.user_id.in_(user_ids),
                    Reminder.competition_id.in_(competition_ids),
                    Reminder.time_node_snapshot_id.in_(node_ids),
                ),
                Reminder.id.notin_(_owned_ids(records, "reminders")),
            ).first(),
        ),
        (
            "messages",
            Message.query.filter(
                or_(
                    Message.user_id.in_(user_ids),
                    Message.competition_id.in_(competition_ids),
                    Message.reminder_id.in_(_owned_ids(records, "reminders")),
                ),
                Message.id.notin_(_owned_ids(records, "messages")),
            ).first(),
        ),
        (
            "review_records",
            ReviewRecord.query.filter(
                or_(
                    ReviewRecord.submitted_by_id.in_(user_ids),
                    ReviewRecord.reviewed_by_id.in_(user_ids),
                    and_(
                        ReviewRecord.target_type == "competition_revision",
                        ReviewRecord.target_id.in_(revision_ids),
                    ),
                ),
                ReviewRecord.id.notin_(_owned_ids(records, "review_records")),
            ).first(),
        ),
        (
            "audit_logs",
            AuditLog.query.filter(
                or_(
                    AuditLog.actor_id.in_(user_ids),
                    and_(
                        AuditLog.target_type == "competition",
                        AuditLog.target_id.in_(competition_ids),
                    ),
                ),
                AuditLog.id.notin_(_owned_ids(records, "audit_logs")),
            ).first(),
        ),
        (
            "recommendation_rule_sets",
            RecommendationRuleSet.query.filter(
                or_(
                    RecommendationRuleSet.created_by_id.in_(user_ids),
                    RecommendationRuleSet.submitted_by_id.in_(user_ids),
                    RecommendationRuleSet.reviewed_by_id.in_(user_ids),
                )
            ).first(),
        ),
    )
    for label, reference in checks:
        if reference is not None:
            raise DevelopmentDemoConflict(
                f"external reference blocks development demo reset: {label}"
            )


def _delete_owned_records(records: dict) -> None:
    for competition_id in _owned_ids(records, "competitions"):
        competition = db.session.get(Competition, competition_id)
        if competition is not None:
            competition.published_revision = None
    db.session.flush()

    for group in DELETE_GROUP_ORDER:
        model = OWNED_GROUP_MODELS[group]
        for entry in records.get(group, {}).values():
            instance = db.session.get(model, _registered_id(entry, group))
            if instance is not None:
                db.session.delete(instance)
        db.session.flush()


def _owned_ids(records: dict, group: str) -> set[int]:
    entries = records.get(group, {})
    if not isinstance(entries, dict):
        raise DevelopmentDemoConflict(f"development demo registry group is invalid: {group}")
    return {_registered_id(entry, f"{group}.{key}") for key, entry in entries.items()}
