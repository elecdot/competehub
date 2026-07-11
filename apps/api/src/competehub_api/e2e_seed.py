from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import click
from flask import Flask, current_app

from competehub_api.extensions import db
from competehub_api.models import User, UserIdentity
from competehub_api.models.enums import IdentityVerificationStatus, UserRole, UserStatus
from competehub_api.services.auth import hash_password, normalize_identity


@dataclass(frozen=True)
class E2EActor:
    id: int
    email: str
    password: str
    display_name: str
    role: UserRole


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
    ),
    E2EActor(
        id=1003,
        email="reviewer.day1@example.edu",
        password="silver orchard compass cloud 59",
        display_name="Day 1 Reviewer",
        role=UserRole.ADMIN,
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
                password_hash=hash_password(actor.password, identity=actor.email),
                display_name=actor.display_name,
                role=actor.role,
                status=UserStatus.ACTIVE,
                identities=[
                    UserIdentity(
                        identity_type="email",
                        normalized_value=normalize_identity("email", actor.email),
                        display_value=actor.email,
                        verification_status=IdentityVerificationStatus.VERIFIED,
                        verification_method="e2e_seed",
                        verified_at=datetime.now(UTC),
                    )
                ],
            )
            for actor in E2E_ACTORS
        )
        db.session.commit()

        click.echo(f"Provisioned {len(E2E_ACTORS)} deterministic E2E actors.")
