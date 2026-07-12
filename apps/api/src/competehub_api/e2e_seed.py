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
    CompetitionTimeNode,
    ReviewRecord,
    StudentProfile,
    User,
    UserIdentity,
)
from competehub_api.models.enums import (
    CompetitionRevisionStatus,
    CompetitionStatus,
    IdentityVerificationStatus,
    ReviewStatus,
    UserRole,
    UserStatus,
)
from competehub_api.services.auth import hash_password, normalize_identity


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
        capabilities=("competition_editor",),
    ),
    E2EActor(
        id=1003,
        email="reviewer.day1@example.edu",
        password="silver orchard compass cloud 59",
        display_name="Day 1 Reviewer",
        role=UserRole.ADMIN,
        capabilities=("competition_reviewer", "competition_maintainer"),
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
            if actor.role == UserRole.STUDENT and actor.profile is not None:
                db.session.add(
                    StudentProfile(
                        user_id=actor.id,
                        interest_tags=actor.profile.get("interest_tags", []),
                        college=actor.profile.get("college"),
                        major=actor.profile.get("major"),
                        grade=actor.profile.get("grade"),
                        goal_preferences=[],
                        blocked_tags=[],
                    )
                )
        _seed_publication_fixture()
        db.session.commit()

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
        summary="A deterministic published edition used by browser acceptance.",
        eligibility="Enrolled students.",
        registration_applicability="applicable",
        participant_form="individual",
        participant_forms=["individual"],
        major_scope="selected",
        grade_scope="selected",
        suitable_majors=["Computer Science"],
        suitable_grades=["Year 2"],
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
            id=2001,
            competition=edition,
            revision=revision,
            logical_node_key="registration-deadline",
            node_revision=1,
            node_type="registration_deadline",
            occurs_at=datetime(2026, 8, 15, 16, 0, tzinfo=UTC),
            description="Registration closes",
            prominence="primary",
        )
    )
    revision.stages.append(stage)
    edition.published_revision = revision
    db.session.add_all(
        [
            series,
            edition,
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
