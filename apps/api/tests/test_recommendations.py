from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionRevision,
    CompetitionTag,
    CompetitionTagLink,
    CompetitionTimeNode,
    RecommendationRule,
    RecommendationRuleSet,
    StudentProfile,
    User,
)
from competehub_api.models.enums import (
    CompetitionRevisionStatus,
    CompetitionStatus,
    RecommendationRuleSetStatus,
    UserRole,
)
from competehub_api.repositories.recommendation_rule_sets import (
    get_active_recommendation_rule_set,
)
from competehub_api.seeds.recommendation_rules import seed_initial_recommendation_rule_set
from competehub_api.services.auth import start_session
from competehub_api.services.recommendation_engine import (
    RecommendationMode,
    rank_recommendation_candidates,
)
from competehub_api.services.recommendations import (
    GeneralFallbackCause,
    resolve_recommendation_context,
)


def test_engine_ranks_by_private_weight_then_stable_competition_id() -> None:
    profile = {
        "college": "Engineering",
        "major": "Software Engineering",
        "grade": "2024",
        "interest_tags": [],
    }
    rules = [
        _rule("major_match", 30, "Major: {major}"),
        _rule("grade_match", 20, "Grade: {grade}"),
    ]
    lower_weight = _candidate(10, majors=["Other"], grades=[profile["grade"]])
    higher_weight = _candidate(20, majors=[profile["major"]], grades=["Other"])

    results = rank_recommendation_candidates(
        candidates=[lower_weight, higher_weight],
        rules=rules,
        mode=RecommendationMode.PERSONALIZED,
        profile=profile,
        evaluation_time=datetime(2026, 7, 15, tzinfo=UTC),
        rule_set_version=7,
    )

    assert [(item.position, item.competition.id) for item in results] == [(1, 20), (2, 10)]
    assert results[0].reason_codes == ("major_match",)
    assert results[0].reasons == ("Major: Software Engineering",)
    assert results[0].mode == RecommendationMode.PERSONALIZED
    assert results[0].rule_set_version == 7
    assert not hasattr(results[0], "score")


def test_engine_breaks_equal_weight_ties_by_competition_id() -> None:
    fallback = _rule("general_fallback", 10, "General recommendation")

    results = rank_recommendation_candidates(
        candidates=[
            _candidate(30, majors=[], grades=[]),
            _candidate(5, majors=[], grades=[]),
        ],
        rules=[fallback],
        mode=RecommendationMode.GENERAL,
        profile=None,
        evaluation_time=datetime(2026, 7, 15, tzinfo=UTC),
        rule_set_version=99,
    )

    assert [(item.position, item.competition.id) for item in results] == [(1, 5), (2, 30)]
    assert all(item.rule_set_version is None for item in results)


def test_engine_scores_fourth_match_before_capping_displayed_reasons() -> None:
    evaluation_time = datetime(2026, 7, 15, tzinfo=UTC)
    profile = {
        "college": "Engineering",
        "major": "Software Engineering",
        "grade": "2024",
        "interest_tags": ["Artificial Intelligence"],
    }
    rules = [
        _rule("major_match", 40, "Major: {major}"),
        _rule("grade_match", 30, "Grade: {grade}"),
        _rule("interest_match", 20, "Interest: {interest_tag}"),
        RecommendationRule(
            code="deadline_urgency",
            name="deadline_urgency",
            weight=10,
            conditions={"operator": "within_days", "min_days": 0, "max_days": 30},
            reason_template="Deadline: {deadline_date} ({days_remaining})",
            enabled=True,
        ),
    ]
    three_matches = _candidate(
        10,
        majors=[profile["major"]],
        grades=[profile["grade"]],
        tags=[profile["interest_tags"][0]],
        deadline_days=60,
        evaluation_time=evaluation_time,
    )
    four_matches = _candidate(
        20,
        majors=[profile["major"]],
        grades=[profile["grade"]],
        tags=[profile["interest_tags"][0]],
        deadline_days=10,
        evaluation_time=evaluation_time,
    )

    results = rank_recommendation_candidates(
        candidates=[three_matches, four_matches],
        rules=rules,
        mode=RecommendationMode.PERSONALIZED,
        profile=profile,
        evaluation_time=evaluation_time,
        rule_set_version=7,
    )

    assert [item.competition.id for item in results] == [20, 10]
    assert results[0].reason_codes == ("major_match", "grade_match", "interest_match")
    assert results[1].reason_codes == results[0].reason_codes


def test_context_resolver_selects_general_or_personalized_without_hidden_version(app) -> None:
    with app.app_context():
        active = RecommendationRuleSet(
            id=17,
            version=7,
            status=RecommendationRuleSetStatus.ACTIVE,
            rules=[
                _rule("major_match", 30, "Major: {major}"),
                _rule("general_fallback", 10, "General recommendation"),
            ],
        )
        anonymous = resolve_recommendation_context(None, active)
        incomplete = resolve_recommendation_context(
            _user_with_profile(StudentProfile(interest_tags=[])),
            active,
        )
        ready_user = _user_with_profile(_ready_profile(app))
        personalized = resolve_recommendation_context(ready_user, active)
        no_active = resolve_recommendation_context(ready_user, None)

    assert anonymous.mode == RecommendationMode.GENERAL
    assert anonymous.profile_status is None
    assert anonymous.missing_fields == ()
    assert anonymous.fallback_cause == GeneralFallbackCause.ANONYMOUS
    assert anonymous.rule_set_id is None
    assert anonymous.rule_set_version is None

    assert incomplete.mode == RecommendationMode.GENERAL
    assert incomplete.profile_status == "incomplete"
    assert incomplete.missing_fields == ("college", "major", "grade", "interest_tags")
    assert incomplete.fallback_cause == GeneralFallbackCause.PROFILE_INCOMPLETE
    assert incomplete.rule_set_version is None

    assert personalized.mode == RecommendationMode.PERSONALIZED
    assert personalized.profile_status == "recommendation_ready"
    assert personalized.missing_fields == ()
    assert personalized.fallback_cause is None
    assert personalized.rule_set_id == 17
    assert personalized.rule_set_version == 7

    assert no_active.mode == RecommendationMode.GENERAL
    assert no_active.profile_status == "recommendation_ready"
    assert no_active.missing_fields == ()
    assert no_active.fallback_cause == GeneralFallbackCause.NO_ACTIVE_RULE_SET
    assert no_active.rule_set_id is None
    assert no_active.rule_set_version is None


def test_active_rule_set_lookup_returns_governed_rules_or_none(app) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()

        found = get_active_recommendation_rule_set()

        assert found is not None
        assert found.id == active.id
        assert found.version == 1
        assert {rule.code for rule in found.rules} >= {"general_fallback", "major_match"}

        active.status = RecommendationRuleSetStatus.RETIRED
        db.session.commit()

        assert get_active_recommendation_rule_set() is None


def test_anonymous_api_returns_only_current_published_general_recommendations(
    client,
    app,
) -> None:
    with app.app_context():
        seed_initial_recommendation_rule_set()
        _persist_candidate(101, status=CompetitionStatus.PUBLISHED)
        for competition_id, status in enumerate(
            [
                CompetitionStatus.DRAFT,
                CompetitionStatus.PENDING_REVIEW,
                CompetitionStatus.REJECTED,
                CompetitionStatus.OFFLINE,
                CompetitionStatus.CANCELLED,
            ],
            start=102,
        ):
            _persist_candidate(competition_id, status=status)
        db.session.commit()

    response = client.get("/api/v1/recommendations")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["recommendation_mode"] == "general"
    assert data["profile_status"] is None
    assert data["missing_fields"] == []
    assert data["fallback_reason"] == "anonymous"
    assert data["rule_set_version"] is None
    assert [item["competition"]["id"] for item in data["items"]] == [101]
    assert data["items"][0]["position"] == 1
    assert data["items"][0]["reason_codes"] == ["general_fallback"]
    assert data["items"][0]["reasons"] == ["近期可行动的公开赛事"]
    assert "score" not in data["items"][0]
    assert "value_rating" not in data["items"][0]


def test_incomplete_student_api_returns_exact_missing_fields_and_general_reasons(
    client,
    app,
) -> None:
    with app.app_context():
        seed_initial_recommendation_rule_set()
        user = User(
            email="incomplete-recommendations@example.edu",
            password_hash="not-used",
            role=UserRole.STUDENT,
            profile=StudentProfile(college="计算机学院", interest_tags=[]),
        )
        db.session.add(user)
        _persist_candidate(201, status=CompetitionStatus.PUBLISHED)
        db.session.commit()
        user_id = user.id
    _login(client, user_id)

    response = client.get("/api/v1/recommendations")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["recommendation_mode"] == "general"
    assert data["profile_status"] == "incomplete"
    assert data["missing_fields"] == ["major", "grade", "interest_tags"]
    assert data["fallback_reason"] == "profile_incomplete"
    assert data["rule_set_version"] is None
    assert data["items"][0]["reason_codes"] == ["general_fallback"]
    assert not {
        "major_match",
        "grade_match",
        "interest_match",
        "deadline_urgency",
    } & set(data["items"][0]["reason_codes"])


def test_ready_student_api_exposes_traceable_reasons_and_private_ordering_only(
    client,
    app,
) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        ready_profile = _ready_profile(app)
        user = User(
            email="ready-recommendations@example.edu",
            password_hash="not-used",
            role=UserRole.STUDENT,
            profile=ready_profile,
        )
        db.session.add(user)
        _persist_candidate(
            301,
            status=CompetitionStatus.PUBLISHED,
            majors=[ready_profile.major],
            grades=[ready_profile.grade],
            tags=[ready_profile.interest_tags[0]],
            deadline_days=10,
        )
        _persist_candidate(
            302,
            status=CompetitionStatus.PUBLISHED,
            majors=["not-a-match"],
            grades=["not-a-match"],
            tags=[],
            deadline_days=60,
        )
        db.session.commit()
        user_id = user.id
        active_version = active.version
    _login(client, user_id)

    response = client.get("/api/v1/recommendations")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["recommendation_mode"] == "personalized"
    assert data["profile_status"] == "recommendation_ready"
    assert data["missing_fields"] == []
    assert data["fallback_reason"] is None
    assert data["rule_set_version"] == active_version
    assert [item["competition"]["id"] for item in data["items"]] == [301, 302]
    matched, supplemented = data["items"]
    assert matched["position"] == 1
    assert 1 <= len(matched["reason_codes"]) <= 3
    assert set(matched["reason_codes"]) <= {
        "major_match",
        "grade_match",
        "interest_match",
        "deadline_urgency",
    }
    assert supplemented["reason_codes"] == ["general_fallback"]
    assert all("score" not in item and "value_rating" not in item for item in data["items"])


def test_personalized_ranking_considers_the_complete_eligible_candidate_set(
    client,
    app,
) -> None:
    with app.app_context():
        seed_initial_recommendation_rule_set()
        ready_profile = _ready_profile(app)
        user = User(
            email="ready-complete-candidate-set@example.edu",
            password_hash="not-used",
            role=UserRole.STUDENT,
            profile=ready_profile,
        )
        db.session.add(user)
        for offset in range(100):
            _persist_candidate(
                500 + offset,
                status=CompetitionStatus.PUBLISHED,
                majors=["not-a-match"],
                grades=["not-a-match"],
                deadline_days=offset + 1,
            )
        _persist_candidate(
            700,
            status=CompetitionStatus.PUBLISHED,
            majors=["not-a-match"],
            grades=["not-a-match"],
            tags=[ready_profile.interest_tags[0]],
            deadline_days=200,
        )
        db.session.commit()
        user_id = user.id
    _login(client, user_id)

    response = client.get("/api/v1/recommendations")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert len(data["items"]) == 20
    assert data["items"][0]["competition"]["id"] == 700
    assert data["items"][0]["reason_codes"] == ["interest_match"]


def test_ready_student_without_active_rule_set_gets_explicit_configuration_fallback(
    client,
    app,
) -> None:
    with app.app_context():
        invalid_active = seed_initial_recommendation_rule_set()
        fallback = next(rule for rule in invalid_active.rules if rule.code == "general_fallback")
        fallback.enabled = False
        fallback.reason_template = "invalid configuration must not be used"
        ready_profile = _ready_profile(app)
        user = User(
            email="ready-no-active@example.edu",
            password_hash="not-used",
            role=UserRole.STUDENT,
            profile=ready_profile,
        )
        db.session.add(user)
        _persist_candidate(401, status=CompetitionStatus.PUBLISHED)
        db.session.commit()
        user_id = user.id
    _login(client, user_id)

    response = client.get("/api/v1/recommendations")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["recommendation_mode"] == "general"
    assert data["profile_status"] == "recommendation_ready"
    assert data["missing_fields"] == []
    assert data["fallback_reason"] == "no_active_rule_set"
    assert data["rule_set_version"] is None
    assert data["items"][0]["reason_codes"] == ["general_fallback"]
    assert data["items"][0]["reasons"] == ["按当前报名可行动性排序的公开赛事"]


@pytest.mark.parametrize(
    ("rule_code", "field", "invalid_value"),
    [
        ("deadline_urgency", "conditions", {"operator": "always"}),
        ("interest_match", "reason_template", "Invalid placeholder {major}"),
    ],
)
def test_invalid_active_snapshot_degrades_without_evaluating_broken_rules(
    client,
    app,
    rule_code: str,
    field: str,
    invalid_value,
) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        setattr(next(rule for rule in active.rules if rule.code == rule_code), field, invalid_value)
        ready_profile = _ready_profile(app)
        user = User(
            email=f"invalid-{rule_code}-{field}@example.edu",
            password_hash="not-used",
            role=UserRole.STUDENT,
            profile=ready_profile,
        )
        db.session.add(user)
        _persist_candidate(
            450,
            status=CompetitionStatus.PUBLISHED,
            majors=[ready_profile.major],
            grades=[ready_profile.grade],
            tags=[ready_profile.interest_tags[0]],
            deadline_days=10,
        )
        db.session.commit()
        user_id = user.id
    _login(client, user_id)

    response = client.get("/api/v1/recommendations")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["recommendation_mode"] == "general"
    assert data["fallback_reason"] == "no_active_rule_set"
    assert data["rule_set_version"] is None
    assert data["items"][0]["reasons"] == ["按当前报名可行动性排序的公开赛事"]


def test_caller_fallback_precedes_unavailable_configuration_metadata(client, app) -> None:
    with app.app_context():
        invalid_active = seed_initial_recommendation_rule_set()
        next(
            rule for rule in invalid_active.rules if rule.code == "general_fallback"
        ).enabled = False
        incomplete = User(
            email="incomplete-without-configuration@example.edu",
            password_hash="not-used",
            role=UserRole.STUDENT,
            profile=StudentProfile(college="Computer Science", interest_tags=[]),
        )
        db.session.add(incomplete)
        _persist_candidate(460, status=CompetitionStatus.PUBLISHED)
        db.session.commit()
        incomplete_id = incomplete.id

    anonymous_response = client.get("/api/v1/recommendations")
    _login(client, incomplete_id)
    incomplete_response = client.get("/api/v1/recommendations")

    anonymous = anonymous_response.get_json()["data"]
    incomplete_data = incomplete_response.get_json()["data"]
    assert anonymous["fallback_reason"] == "anonymous"
    assert incomplete_data["fallback_reason"] == "profile_incomplete"
    assert anonymous["items"][0]["reasons"] == ["按当前报名可行动性排序的公开赛事"]
    assert incomplete_data["items"][0]["reasons"] == ["按当前报名可行动性排序的公开赛事"]


def _rule(code: str, weight: int, reason_template: str) -> RecommendationRule:
    return RecommendationRule(
        code=code,
        name=code,
        weight=weight,
        conditions={"operator": "always"}
        if code == "general_fallback"
        else {"operator": "overlap"},
        reason_template=reason_template,
        enabled=True,
    )


def _user_with_profile(profile: StudentProfile) -> User:
    return User(password_hash="not-persisted", profile=profile)


def _ready_profile(app) -> StudentProfile:
    college, majors = next(iter(app.config["PROFILE_ALLOWED_MAJORS_BY_COLLEGE"].items()))
    return StudentProfile(
        college=college,
        major=majors[0],
        grade=app.config["PROFILE_ALLOWED_GRADES"][0],
        interest_tags=[app.config["PROFILE_ALLOWED_INTEREST_TAGS"][0]],
    )


def _candidate(
    competition_id: int,
    *,
    majors: list[str],
    grades: list[str],
    tags: list[str] | None = None,
    deadline_days: int | None = None,
    evaluation_time: datetime | None = None,
) -> Competition:
    competition = Competition(
        id=competition_id,
        title=f"Competition {competition_id}",
        source_name="School Notice",
        source_url=f"https://example.edu/{competition_id}",
        status=CompetitionStatus.PUBLISHED,
    )
    revision = CompetitionRevision(
        competition=competition,
        revision_number=1,
        revision_status=CompetitionRevisionStatus.APPROVED,
        title=competition.title,
        source_name=competition.source_name,
        source_url=competition.source_url,
        participant_forms=[],
        major_scope="selected",
        grade_scope="selected",
        suitable_majors=majors,
        suitable_grades=grades,
        created_by_id=1,
    )
    for index, tag_name in enumerate(tags or []):
        revision.tag_links.append(
            CompetitionTagLink(
                tag=CompetitionTag(
                    code=f"engine-{competition_id}-{index}",
                    name=tag_name,
                    tag_type="topic",
                )
            )
        )
    if deadline_days is not None:
        revision.time_nodes.append(
            CompetitionTimeNode(
                node_type="registration_deadline",
                occurs_at=(evaluation_time or datetime.now(UTC)) + timedelta(days=deadline_days),
                prominence="primary",
            )
        )
    competition.published_revision = revision
    return competition


def _login(client, user_id: int) -> None:
    with client.session_transaction() as session_data:
        with client.application.app_context():
            start_session(session_data, db.session.get(User, user_id))


def _persist_candidate(
    competition_id: int,
    *,
    status: CompetitionStatus,
    majors: list[str] | None = None,
    grades: list[str] | None = None,
    tags: list[str] | None = None,
    deadline_days: int | None = 20,
) -> Competition:
    competition = Competition(
        id=competition_id,
        title=f"Competition {competition_id}",
        source_name="School Notice",
        source_url=f"https://example.edu/{competition_id}",
        status=status,
    )
    revision = CompetitionRevision(
        competition=competition,
        revision_number=1,
        revision_status=CompetitionRevisionStatus.APPROVED,
        title=competition.title,
        source_name=competition.source_name,
        source_url=competition.source_url,
        participant_forms=[],
        registration_applicability="applicable",
        major_scope="selected",
        grade_scope="selected",
        suitable_majors=majors or [],
        suitable_grades=grades or [],
        created_by_id=1,
        published_at=datetime.now(UTC),
    )
    if deadline_days is not None:
        revision.time_nodes.append(
            CompetitionTimeNode(
                node_type="registration_deadline",
                occurs_at=datetime.now(UTC) + timedelta(days=deadline_days),
                prominence="primary",
            )
        )
    for index, tag_name in enumerate(tags or []):
        revision.tag_links.append(
            CompetitionTagLink(
                tag=CompetitionTag(
                    code=f"recommendation-{competition_id}-{index}",
                    name=tag_name,
                    tag_type="topic",
                )
            )
        )
    competition.published_revision = revision
    db.session.add(competition)
    return competition
