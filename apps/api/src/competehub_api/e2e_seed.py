from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import click
from flask import Flask, current_app

from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionRevision,
    CompetitionSeries,
    CompetitionStage,
    CompetitionTag,
    CompetitionTagLink,
    CompetitionTimeNode,
    Favorite,
    ReminderSetting,
    ReviewRecord,
    StudentProfile,
    Subscription,
    User,
    UserIdentity,
)
from competehub_api.models.enums import (
    CompetitionRevisionStatus,
    CompetitionStatus,
    IdentityVerificationStatus,
    ReviewStatus,
    SubscriptionStatus,
    UserRole,
    UserStatus,
)
from competehub_api.seeds.recommendation_rules import seed_initial_recommendation_rule_set
from competehub_api.services.auth import hash_password, normalize_identity
from competehub_api.services.profiles import DEFAULT_REMINDER_NODE_TYPES


@dataclass(frozen=True)
class E2EActor:
    id: int
    email: str
    password: str
    display_name: str
    role: UserRole
    capabilities: tuple[str, ...] = ()
    status: UserStatus = UserStatus.ACTIVE
    verification_status: IdentityVerificationStatus = IdentityVerificationStatus.VERIFIED
    profile: dict[str, object] | None = None


# These are public test credentials for the isolated browser-test database, not
# production secrets or a substitute for the verified registration workflow.
E2E_ACTORS = (
    E2EActor(
        id=1001,
        email="student.day1@example.edu",
        password="violet harbor lantern orbit 47",
        display_name="Day 1 Student",
        role=UserRole.STUDENT,
        profile={},
    ),
    E2EActor(
        id=1004,
        email="profile.student-day1@example.edu",
        password="green campus theorem delta 64",
        display_name="Profile Ready Student",
        role=UserRole.STUDENT,
        profile={
            "college": "计算机学院",
            "major": "软件工程",
            "grade": "大二",
            "interest_tags": ["人工智能", "创新创业", "程序设计"],
        },
    ),
    E2EActor(
        id=1002,
        email="admin.day1@example.edu",
        password="copper meadow signal river 82",
        display_name="Day 1 Admin",
        role=UserRole.ADMIN,
        capabilities=(
            "competition_editor",
            "competition_maintainer",
            "recommendation_editor",
            "recommendation_reviewer",
        ),
    ),
    E2EActor(
        id=1003,
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
    E2EActor(
        id=1006,
        email="admin.no-recommendation@example.edu",
        password="granite garden ordinary admin 28",
        display_name="Admin Without Recommendation Capability",
        role=UserRole.ADMIN,
        capabilities=("competition_maintainer",),
    ),
)

PENDING_E2E_ACTORS = (
    E2EActor(
        id=1005,
        email="pending.day1@example.edu",
        password="amber bridge pending code 91",
        display_name="Pending Student",
        role=UserRole.STUDENT,
        status=UserStatus.PENDING_ACTIVATION,
        verification_status=IdentityVerificationStatus.PENDING,
        profile=None,
    ),
)

SEEDED_E2E_ACTORS = E2E_ACTORS + PENDING_E2E_ACTORS


def register_e2e_commands(app: Flask) -> None:
    @app.cli.command("seed-e2e")
    @click.option(
        "--reset",
        is_flag=True,
        help="Rebuild the isolated E2E database before provisioning actors.",
    )
    def seed_e2e(reset: bool) -> None:
        """Provision deterministic actors for browser tests."""
        if not current_app.config.get("E2E_TESTING"):
            raise click.ClickException("seed-e2e requires the isolated E2E app factory")
        if not reset:
            raise click.ClickException("seed-e2e requires --reset for deterministic state")

        db.session.remove()
        db.drop_all()
        db.create_all()
        users = [
            User(
                id=actor.id,
                email=actor.email,
                password_hash=hash_password(actor.password, identity=actor.email),
                display_name=actor.display_name,
                role=actor.role,
                status=actor.status,
                capabilities=list(actor.capabilities),
                identities=[
                    UserIdentity(
                        identity_type="email",
                        normalized_value=normalize_identity("email", actor.email),
                        display_value=actor.email,
                        verification_status=actor.verification_status,
                        verification_method="e2e_seed",
                        verified_at=datetime.now(UTC)
                        if actor.verification_status == IdentityVerificationStatus.VERIFIED
                        else None,
                    )
                ],
            )
            for actor in SEEDED_E2E_ACTORS
        ]
        db.session.add_all(users)
        db.session.flush()
        for actor in SEEDED_E2E_ACTORS:
            if actor.role == UserRole.STUDENT:
                profile = actor.profile or {}
                db.session.add(
                    StudentProfile(
                        user_id=actor.id,
                        interest_tags=profile.get("interest_tags", []),
                        college=profile.get("college"),
                        major=profile.get("major"),
                        grade=profile.get("grade"),
                        goal_preferences=[],
                        blocked_tags=[],
                    )
                )
                db.session.add(
                    ReminderSetting(
                        id=actor.id,
                        user_id=actor.id,
                        enabled=True,
                        default_remind_days=3,
                        node_types=list(DEFAULT_REMINDER_NODE_TYPES),
                    )
                )
        _seed_publication_fixture()
        _seed_owned_lifecycle_engagement()
        db.session.commit()
        seed_initial_recommendation_rule_set()

        click.echo(f"Provisioned {len(SEEDED_E2E_ACTORS)} deterministic E2E actors.")


def _seed_publication_fixture() -> None:
    decided_at = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
    series = CompetitionSeries(
        id=2001,
        canonical_name="Seeded University Innovation Challenge",
        created_by_id=1002,
    )
    edition = Competition(
        id=2001,
        series=series,
        edition_label="2025",
        title="Seeded University Innovation Challenge 2025",
        category="innovation",
        organizer="Example University",
        source_name="Example University Notice",
        source_url="https://example.edu/notices/seeded-innovation-2025",
        official_url="https://example.org/seeded-innovation-2025",
        summary="A deterministic published edition used by browser acceptance.",
        eligibility="Enrolled students.",
        registration_applicability="applicable",
        participant_form="individual",
        participant_forms=["individual"],
        major_scope="selected",
        grade_scope="selected",
        suitable_majors=["软件工程"],
        suitable_grades=["大二"],
        status=CompetitionStatus.PUBLISHED,
        created_by_id=1002,
    )
    revision = CompetitionRevision(
        id=2001,
        competition=edition,
        revision_number=1,
        revision_status=CompetitionRevisionStatus.APPROVED,
        title=edition.title,
        category=edition.category,
        organizer=edition.organizer,
        source_name=edition.source_name,
        source_url=edition.source_url,
        official_url=edition.official_url,
        summary=edition.summary,
        eligibility=edition.eligibility,
        registration_applicability=edition.registration_applicability,
        participant_forms=["individual"],
        major_scope=edition.major_scope,
        grade_scope=edition.grade_scope,
        suitable_majors=edition.suitable_majors,
        suitable_grades=edition.suitable_grades,
        created_by_id=1002,
        submitted_by_id=1002,
        submitted_at=decided_at,
        decided_at=decided_at,
        published_at=decided_at,
    )
    stage = CompetitionStage(
        id=2001,
        revision=revision,
        stage_key="registration",
        stage_type="registration",
        label="Registration",
        stage_order=1,
    )
    stage.time_nodes.append(
        CompetitionTimeNode(
            id=2002,
            competition=edition,
            revision=revision,
            logical_node_key="registration-start",
            node_revision=1,
            node_type="registration_start",
            occurs_at=datetime(2020, 1, 1, 0, 0, tzinfo=UTC),
            description="Registration opens",
            prominence="secondary",
        )
    )
    stage.time_nodes.append(
        CompetitionTimeNode(
            id=2001,
            competition=edition,
            revision=revision,
            logical_node_key="registration-deadline",
            node_revision=1,
            node_type="registration_deadline",
            occurs_at=datetime(2099, 8, 15, 16, 0, tzinfo=UTC),
            description="Registration closes",
            prominence="primary",
        )
    )
    revision.stages.append(stage)
    tag = CompetitionTag(
        id=2001,
        code="seeded-ai",
        name="人工智能",
        tag_type="topic",
    )
    revision.tag_links.append(
        CompetitionTagLink(
            competition=edition,
            tag=tag,
        )
    )
    edition.published_revision = revision
    historical_edition = Competition(
        id=2004,
        series=CompetitionSeries(
            id=2004,
            canonical_name="Seeded Historical Innovation Challenge",
            created_by_id=1002,
        ),
        edition_label="2024",
        title="Seeded Historical Innovation Challenge 2024",
        category="innovation",
        organizer="Example University",
        source_name="Example University Archive",
        source_url="https://example.edu/notices/seeded-historical-2024",
        summary="A deterministic historical edition used by browser acceptance.",
        eligibility="Enrolled students.",
        registration_applicability="applicable",
        participant_form="individual",
        participant_forms=["individual"],
        major_scope="selected",
        grade_scope="selected",
        suitable_majors=["Computer Science"],
        suitable_grades=["Year 2"],
        status=CompetitionStatus.ARCHIVED,
        lifecycle_reason="Official archive notice retained for student reference.",
        lifecycle_changed_at=decided_at,
        created_by_id=1002,
    )
    historical_revision = CompetitionRevision(
        id=2004,
        competition=historical_edition,
        revision_number=1,
        revision_status=CompetitionRevisionStatus.APPROVED,
        title=historical_edition.title,
        category=historical_edition.category,
        organizer=historical_edition.organizer,
        source_name=historical_edition.source_name,
        source_url=historical_edition.source_url,
        summary=historical_edition.summary,
        eligibility=historical_edition.eligibility,
        registration_applicability=historical_edition.registration_applicability,
        participant_forms=["individual"],
        major_scope=historical_edition.major_scope,
        grade_scope=historical_edition.grade_scope,
        suitable_majors=historical_edition.suitable_majors,
        suitable_grades=historical_edition.suitable_grades,
        created_by_id=1002,
        submitted_by_id=1002,
        submitted_at=decided_at,
        decided_at=decided_at,
        published_at=decided_at,
    )
    historical_edition.published_revision = historical_revision
    db.session.add_all(
        [
            series,
            edition,
            historical_edition,
            tag,
            ReviewRecord(
                target_type="competition_revision",
                target_id=2001,
                submitted_by_id=1002,
                reviewed_by_id=1003,
                status=ReviewStatus.APPROVED,
                comment="Deterministic seed approval.",
                differences=[
                    {
                        "kind": "field",
                        "field": "title",
                        "before": None,
                        "after": edition.title,
                    }
                ],
                impact={"public_visibility": "publish", "active_subscriptions": 0},
                submitted_at=decided_at,
                decided_at=decided_at,
            ),
        ]
    )


def _seed_owned_lifecycle_engagement() -> None:
    series = db.session.get(CompetitionSeries, 2001)
    if series is None:
        raise RuntimeError("The E2E publication fixture must exist before lifecycle engagement")
    student_id = 1001
    offline = Competition(
        id=2002,
        series=series,
        edition_label="2024-offline",
        title="Seeded Offline Engagement Edition",
        source_name="Example University Notice",
        source_url="https://example.edu/notices/seeded-offline",
        status=CompetitionStatus.OFFLINE,
        created_by_id=1002,
    )
    offline_revision = CompetitionRevision(
        id=2002,
        competition=offline,
        revision_number=1,
        revision_status=CompetitionRevisionStatus.APPROVED,
        title=offline.title,
        source_name=offline.source_name,
        source_url=offline.source_url,
        created_by_id=1002,
    )
    offline.published_revision = offline_revision
    unpublished = Competition(
        id=2003,
        series=series,
        edition_label="2027-unpublished",
        title="Seeded Unpublished Engagement Edition",
        source_name="Example University Notice",
        source_url="https://example.edu/notices/seeded-unpublished",
        status=CompetitionStatus.UNPUBLISHED,
        created_by_id=1002,
    )
    CompetitionRevision(
        id=2003,
        competition=unpublished,
        revision_number=1,
        revision_status=CompetitionRevisionStatus.DRAFT,
        title=unpublished.title,
        source_name=unpublished.source_name,
        source_url=unpublished.source_url,
        created_by_id=1002,
    )
    db.session.add_all([offline, unpublished])
    db.session.flush()
    db.session.add_all(
        [
            Favorite(
                id=2002,
                user_id=student_id,
                competition_id=offline.id,
                is_active=True,
            ),
            Subscription(
                id=2003,
                user_id=student_id,
                competition_id=unpublished.id,
                status=SubscriptionStatus.ACTIVE,
                reminder_enabled=False,
                remind_days=3,
                node_types=["registration_deadline"],
            ),
            Subscription(
                id=2004,
                user_id=student_id,
                competition_id=2004,
                status=SubscriptionStatus.ACTIVE,
                reminder_enabled=False,
                remind_days=3,
                node_types=["registration_deadline"],
            ),
        ]
    )
