from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import click
from flask import Flask, current_app
from werkzeug.security import generate_password_hash

from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionRevision,
    CompetitionSeries,
    CompetitionStage,
    CompetitionTimeNode,
    ReviewRecord,
    User,
)
from competehub_api.models.enums import (
    CompetitionRevisionStatus,
    CompetitionStatus,
    ReviewStatus,
    UserRole,
    UserStatus,
)


@dataclass(frozen=True)
class E2EActor:
    id: int
    email: str
    password: str
    display_name: str
    role: UserRole
    capabilities: tuple[str, ...] = ()


# These are public test credentials for the isolated browser-test database, not
# production secrets or a substitute for the verified registration workflow.
E2E_ACTORS = (
    E2EActor(
        id=1001,
        email="student.day1@example.edu",
        password="violet harbor lantern orbit 47",
        display_name="Day 1 Student",
        role=UserRole.STUDENT,
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
        db.session.add_all(
            User(
                id=actor.id,
                email=actor.email,
                password_hash=generate_password_hash(actor.password),
                display_name=actor.display_name,
                role=actor.role,
                status=UserStatus.ACTIVE,
                capabilities=list(actor.capabilities),
            )
            for actor in E2E_ACTORS
        )
        _seed_publication_fixture()
        db.session.commit()

        click.echo(f"Provisioned {len(E2E_ACTORS)} deterministic E2E actors.")


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
        participant_form="individual",
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
        participant_forms=["individual"],
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
                differences=[{"field": "title", "before": None, "after": edition.title}],
                impact={"public_visibility": "publish", "active_subscriptions": 0},
                decided_at=decided_at,
            ),
        ]
    )
