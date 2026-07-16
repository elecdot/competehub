from __future__ import annotations

from datetime import timedelta

import pytest

from competehub_api import create_app
from competehub_api.extensions import db
from competehub_api.models import (
    AuditLog,
    Competition,
    CompetitionRevision,
    CompetitionSeries,
    CompetitionTag,
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
    RecommendationRuleSetStatus,
    ReminderStatus,
    ReviewStatus,
    SubscriptionStatus,
    UserRole,
    UserStatus,
)
from competehub_api.seeds.development_demo import (
    DEVELOPMENT_DEMO_ACTORS,
    DEVELOPMENT_DEMO_REGISTRY_KEY,
)


@pytest.fixture()
def development_app():
    app = create_app(
        {
            "TESTING": False,
            "E2E_TESTING": False,
            "COMPETEHUB_ENV": "development",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "AUTH_RATE_LIMIT_ENABLED": False,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.mark.parametrize(
    ("environment", "testing", "e2e_testing"),
    [
        ("development", True, False),
        ("development", False, True),
        ("production", False, False),
        ("staging", False, False),
    ],
)
def test_development_demo_bootstrap_refuses_unsupported_environment(
    environment: str,
    testing: bool,
    e2e_testing: bool,
) -> None:
    app = create_app(
        {
            "TESTING": testing,
            "E2E_TESTING": e2e_testing,
            "COMPETEHUB_ENV": environment,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "AUTH_RATE_LIMIT_ENABLED": False,
        }
    )
    with app.app_context():
        db.create_all()
        result = app.test_cli_runner().invoke(args=["bootstrap-development-demo"])

        assert result.exit_code != 0
        assert "development environment" in result.output
        assert SystemConfig.query.count() == 0


def test_development_demo_bootstrap_requires_migrated_tables() -> None:
    app = create_app(
        {
            "TESTING": False,
            "E2E_TESTING": False,
            "COMPETEHUB_ENV": "development",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "AUTH_RATE_LIMIT_ENABLED": False,
        }
    )

    result = app.test_cli_runner().invoke(args=["bootstrap-development-demo"])

    assert result.exit_code != 0
    assert "requires a migrated database" in result.output


def test_development_demo_bootstrap_creates_registry_in_development_app(
    development_app,
) -> None:
    result = development_app.test_cli_runner().invoke(args=["bootstrap-development-demo"])

    assert result.exit_code == 0
    with development_app.app_context():
        registry = SystemConfig.query.filter_by(key=DEVELOPMENT_DEMO_REGISTRY_KEY).one()
        assert registry.value["schema_version"] == 1
        assert registry.value["dataset_version"] == 1


def test_development_demo_bootstrap_provisions_expected_actors_idempotently(
    development_app,
) -> None:
    runner = development_app.test_cli_runner()
    first = runner.invoke(args=["bootstrap-development-demo"])

    assert first.exit_code == 0
    with development_app.app_context():
        users = User.query.order_by(User.email).all()
        initial_ids = {user.email: user.id for user in users}
        initial_counts = {
            "users": User.query.count(),
            "identities": UserIdentity.query.count(),
            "profiles": StudentProfile.query.count(),
            "settings": ReminderSetting.query.count(),
        }

        assert [user.email for user in users] == sorted(
            actor.email for actor in DEVELOPMENT_DEMO_ACTORS
        )
        by_email = {user.email: user for user in users}
        assert by_email["student.day1@example.edu"].role == UserRole.STUDENT
        assert by_email["student.day1@example.edu"].capabilities == []
        assert by_email["admin.day1@example.edu"].capabilities == [
            "competition_editor",
            "competition_maintainer",
            "recommendation_editor",
        ]
        assert by_email["reviewer.day1@example.edu"].capabilities == [
            "competition_reviewer",
            "competition_maintainer",
            "recommendation_reviewer",
        ]
        assert by_email["owner.day1@example.edu"].capabilities == ["user_administrator"]
        assert {
            identity.display_value: identity.verification_status
            for identity in UserIdentity.query.all()
        } == {actor.email: IdentityVerificationStatus.VERIFIED for actor in DEVELOPMENT_DEMO_ACTORS}
        student = by_email["student.day1@example.edu"]
        assert student.profile.college == "计算机学院"
        assert student.profile.major == "软件工程"
        assert student.profile.grade == "大二"
        assert student.profile.interest_tags == ["人工智能", "创新创业", "程序设计"]
        assert student.reminder_settings.enabled is True
        assert student.reminder_settings.default_remind_days == 3

    second = runner.invoke(args=["bootstrap-development-demo"])

    assert second.exit_code == 0
    assert "verified" in second.output
    with development_app.app_context():
        assert {user.email: user.id for user in User.query.all()} == initial_ids
        assert {
            "users": User.query.count(),
            "identities": UserIdentity.query.count(),
            "profiles": StudentProfile.query.count(),
            "settings": ReminderSetting.query.count(),
        } == initial_counts


def test_development_demo_bootstrap_provisions_competition_and_governance_facts(
    development_app,
) -> None:
    result = development_app.test_cli_runner().invoke(args=["bootstrap-development-demo"])

    assert result.exit_code == 0
    with development_app.app_context():
        series = CompetitionSeries.query.filter_by(
            canonical_name="CompeteHub Day 1 Demo Series"
        ).one()
        editions = {
            edition.edition_label: edition
            for edition in Competition.query.filter_by(series_id=series.id).all()
        }
        assert set(editions) == {
            "2026-published",
            "2027-pending",
            "2026-incomplete",
            "2025-cancelled",
            "2025-offline",
        }
        assert editions["2026-published"].status == CompetitionStatus.PUBLISHED
        assert editions["2027-pending"].status == CompetitionStatus.UNPUBLISHED
        assert editions["2026-incomplete"].status == CompetitionStatus.UNPUBLISHED
        assert editions["2025-cancelled"].status == CompetitionStatus.CANCELLED
        assert editions["2025-offline"].status == CompetitionStatus.OFFLINE

        published = editions["2026-published"]
        assert published.published_revision is not None
        assert published.published_revision.revision_status == CompetitionRevisionStatus.APPROVED
        assert [stage.stage_key for stage in published.published_revision.stages] == [
            "registration",
            "submission",
            "competition",
        ]
        assert [
            node.logical_node_key
            for stage in published.published_revision.stages
            for node in stage.time_nodes
        ] == [
            "registration-deadline",
            "submission-deadline",
            "competition-start",
        ]
        assert {link.tag.code for link in published.published_revision.tag_links} == {
            "demo-ai",
            "demo-innovation",
        }

        pending_revision = CompetitionRevision.query.filter_by(
            competition_id=editions["2027-pending"].id
        ).one()
        assert pending_revision.revision_status == CompetitionRevisionStatus.PENDING_REVIEW
        assert (
            pending_revision.submitted_by_id
            == User.query.filter_by(email="admin.day1@example.edu").one().id
        )
        assert editions["2027-pending"].published_revision_id is None

        draft_revision = CompetitionRevision.query.filter_by(
            competition_id=editions["2026-incomplete"].id
        ).one()
        assert draft_revision.revision_status == CompetitionRevisionStatus.DRAFT
        assert draft_revision.summary is None

        review = ReviewRecord.query.filter_by(
            target_type="competition_revision",
            target_id=published.published_revision_id,
        ).one()
        assert review.status == ReviewStatus.APPROVED
        assert (
            review.reviewed_by_id
            == User.query.filter_by(email="reviewer.day1@example.edu").one().id
        )
        assert (
            AuditLog.query.filter_by(
                action="development_demo.competition_published",
                target_id=published.id,
            ).count()
            == 1
        )

        rule_set = RecommendationRuleSet.query.filter_by(version=1).one()
        assert rule_set.status == RecommendationRuleSetStatus.ACTIVE
        assert {rule.code for rule in rule_set.rules} == {
            "major_match",
            "grade_match",
            "interest_match",
            "deadline_urgency",
            "general_fallback",
        }
        assert CompetitionTag.query.count() == 2


def test_development_demo_bootstrap_provisions_engagement_and_actor_login_smoke(
    development_app,
) -> None:
    result = development_app.test_cli_runner().invoke(args=["bootstrap-development-demo"])

    assert result.exit_code == 0
    with development_app.app_context():
        student = User.query.filter_by(email="student.day1@example.edu").one()
        published = Competition.query.filter_by(edition_label="2026-published").one()
        favorite = Favorite.query.filter_by(
            user_id=student.id,
            competition_id=published.id,
        ).one()
        subscription = Subscription.query.filter_by(
            user_id=student.id,
            competition_id=published.id,
        ).one()
        reminders = (
            Reminder.query.filter_by(
                user_id=student.id,
                competition_id=published.id,
            )
            .order_by(Reminder.logical_node_key)
            .all()
        )
        messages = (
            Message.query.filter_by(user_id=student.id).order_by(Message.created_at.desc()).all()
        )

        assert favorite.is_active is True
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.reminder_enabled is True
        assert subscription.remind_days == 30
        assert subscription.reminder_confirmed_at is not None
        assert [reminder.status for reminder in reminders] == [
            ReminderStatus.SENT,
            ReminderStatus.PENDING,
        ]
        assert [message.message_type for message in messages] == [
            "competition_offline",
            "competition_time_changed",
            "reminder_due",
        ]
        offline_message, schedule_message, reminder_message = messages
        assert reminder_message.reminder_id == reminders[0].id
        assert reminder_message.is_read is False
        assert reminder_message.idempotency_key == "development-demo:reminder:registration:sent"
        assert reminder_message.event_occurred_at == reminders[0].due_at
        assert reminder_message.created_at == reminders[0].sent_at
        assert reminder_message.target_snapshot["node_type"] == ("registration_deadline")
        assert offline_message.is_read is False
        assert schedule_message.is_read is True
        assert schedule_message.read_at is not None
        assert all(
            message.retained_until - message.created_at == timedelta(days=365)
            for message in messages
        )

    client = development_app.test_client()
    for actor in DEVELOPMENT_DEMO_ACTORS:
        login = client.post(
            "/api/v1/auth/login",
            json={
                "identity_type": "email",
                "identity": actor.email,
                "password": actor.password,
            },
        )
        assert login.status_code == 200
        current = client.get("/api/v1/me")
        assert current.status_code == 200
        payload = current.get_json()["data"]
        assert payload["role"] == actor.role.value
        assert payload["capabilities"] == list(actor.capabilities)
        assert client.post("/api/v1/auth/logout").status_code == 200


def test_default_bootstrap_rejects_registered_record_drift_and_rolls_back(
    development_app,
) -> None:
    runner = development_app.test_cli_runner()
    assert runner.invoke(args=["bootstrap-development-demo"]).exit_code == 0
    with development_app.app_context():
        student = User.query.filter_by(email="student.day1@example.edu").one()
        student.display_name = "Member-edited student"
        db.session.commit()
        registry_before = (
            SystemConfig.query.filter_by(key=DEVELOPMENT_DEMO_REGISTRY_KEY).one().value.copy()
        )

    result = runner.invoke(args=["bootstrap-development-demo"])

    assert result.exit_code != 0
    assert "drifted" in result.output
    with development_app.app_context():
        assert (
            User.query.filter_by(email="student.day1@example.edu").one().display_name
            == "Member-edited student"
        )
        assert (
            SystemConfig.query.filter_by(key=DEVELOPMENT_DEMO_REGISTRY_KEY).one().value
            == registry_before
        )


def test_reset_rejects_external_reference_and_rolls_back(development_app) -> None:
    runner = development_app.test_cli_runner()
    assert runner.invoke(args=["bootstrap-development-demo"]).exit_code == 0
    with development_app.app_context():
        editor = User.query.filter_by(email="admin.day1@example.edu").one()
        external_series = CompetitionSeries(
            id=9001,
            canonical_name="Member-created external series",
            created_by_id=editor.id,
        )
        external_competition = Competition(
            id=9001,
            series=external_series,
            edition_label="member-data",
            title="Member-created competition",
            source_name="Member source",
            source_url="https://example.edu/member-created",
            participant_forms=[],
            status=CompetitionStatus.UNPUBLISHED,
            created_by_id=editor.id,
        )
        db.session.add_all([external_series, external_competition])
        db.session.commit()

    result = runner.invoke(args=["bootstrap-development-demo", "--reset-demo"])

    assert result.exit_code != 0
    assert "external reference" in result.output
    with development_app.app_context():
        assert Competition.query.filter_by(id=9001).one().title == ("Member-created competition")
        assert User.query.filter_by(email="admin.day1@example.edu").count() == 1
        assert SystemConfig.query.filter_by(key=DEVELOPMENT_DEMO_REGISTRY_KEY).count() == 1


def test_reset_ignores_unrelated_polymorphic_targets_with_matching_ids(
    development_app,
) -> None:
    runner = development_app.test_cli_runner()
    assert runner.invoke(args=["bootstrap-development-demo"]).exit_code == 0
    with development_app.app_context():
        demo_revision_id = CompetitionRevision.query.first().id
        demo_competition_id = Competition.query.first().id
        db.session.add_all(
            [
                ReviewRecord(
                    id=9002,
                    target_type="recommendation_rule_set",
                    target_id=demo_revision_id,
                    target_revision=1,
                    status=ReviewStatus.PENDING,
                ),
                AuditLog(
                    id=9002,
                    action="member.unrelated_action",
                    target_type="recommendation_rule_set",
                    target_id=demo_competition_id,
                    result="success",
                ),
            ]
        )
        db.session.commit()

    result = runner.invoke(args=["bootstrap-development-demo", "--reset-demo"])

    assert result.exit_code == 0
    with development_app.app_context():
        assert ReviewRecord.query.filter_by(id=9002).count() == 1
        assert AuditLog.query.filter_by(id=9002).count() == 1


def test_safe_reset_recreates_demo_graph_and_preserves_non_demo_data(
    development_app,
) -> None:
    with development_app.app_context():
        member_user = User(
            id=9000,
            email="member-created@example.edu",
            password_hash="member-owned-hash",
            display_name="Member-owned user",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
            capabilities=[],
        )
        member_series = CompetitionSeries(
            id=9000,
            canonical_name="Member-owned series",
            created_by_id=member_user.id,
        )
        member_competition = Competition(
            id=9000,
            series=member_series,
            edition_label="member-owned",
            title="Member-owned competition",
            source_name="Member source",
            source_url="https://example.edu/member-owned",
            participant_forms=[],
            status=CompetitionStatus.UNPUBLISHED,
            created_by_id=member_user.id,
        )
        db.session.add_all([member_user, member_series, member_competition])
        db.session.commit()

    runner = development_app.test_cli_runner()
    assert runner.invoke(args=["bootstrap-development-demo"]).exit_code == 0
    with development_app.app_context():
        original_rule_set_id = RecommendationRuleSet.query.filter_by(version=1).one().id
        demo_student = User.query.filter_by(email="student.day1@example.edu").one()
        demo_student.display_name = "Drifted before explicit reset"
        db.session.commit()

    result = runner.invoke(args=["bootstrap-development-demo", "--reset-demo"])

    assert result.exit_code == 0
    assert "reset" in result.output
    with development_app.app_context():
        assert User.query.filter_by(id=9000).one().display_name == "Member-owned user"
        assert Competition.query.filter_by(id=9000).one().title == "Member-owned competition"
        assert User.query.filter_by(email="student.day1@example.edu").count() == 1
        assert Competition.query.filter_by(edition_label="2026-published").count() == 1
        assert Favorite.query.count() == 1
        assert Subscription.query.count() == 1
        assert Reminder.query.count() == 2
        assert Message.query.count() == 3
        assert RecommendationRuleSet.query.filter_by(version=1).one().id == (original_rule_set_id)
        assert (
            User.query.filter_by(email="student.day1@example.edu").one().display_name
            == "Day 1 Student"
        )


def test_conflicting_recommendation_v1_rolls_back_the_complete_bootstrap(
    development_app,
) -> None:
    with development_app.app_context():
        db.session.add(
            RecommendationRuleSet(
                id=7000,
                version=1,
                status=RecommendationRuleSetStatus.DRAFT,
            )
        )
        db.session.commit()

    result = development_app.test_cli_runner().invoke(args=["bootstrap-development-demo"])

    assert result.exit_code != 0
    assert "conflicts with the reproducible seed" in result.output
    with development_app.app_context():
        assert User.query.count() == 0
        assert Competition.query.count() == 0
        assert SystemConfig.query.filter_by(key=DEVELOPMENT_DEMO_REGISTRY_KEY).count() == 0
