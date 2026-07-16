from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from competehub_api import create_app
from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionRevision,
    CompetitionStage,
    CompetitionTag,
    CompetitionTagLink,
    CompetitionTimeNode,
    Favorite,
    OutboundClickDailyStat,
    OutboundClickEvent,
    Reminder,
    ReminderSetting,
    Subscription,
    User,
)
from competehub_api.models.enums import (
    CompetitionRevisionStatus,
    CompetitionStatus,
    ReminderStatus,
    SubscriptionStatus,
    UserRole,
)
from competehub_api.services.auth import start_session
from competehub_api.services.outbound_clicks import aggregate_outbound_clicks
from competehub_api.services.profiles import provision_student_owned_rows
from competehub_api.timezones import stored_datetime_as_utc


class FakeRedisRateLimitStore:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}

    def eval(self, _script: str, num_keys: int, key: str, _window_seconds: int) -> int:
        assert num_keys == 1
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]


@pytest.fixture(autouse=True)
def seeded_day1_competitions(app) -> None:
    seed_day1_competitions()


def seed_day1_competitions() -> None:
    publisher = User(
        id=900,
        email="fixture-publisher@example.edu",
        password_hash="not-used",
        display_name="Fixture Publisher",
        role=UserRole.ADMIN,
    )
    ai_tag = CompetitionTag(id=1, code="ai", name="人工智能", tag_type="topic")
    innovation_tag = CompetitionTag(
        id=2,
        code="innovation",
        name="创新创业",
        tag_type="category",
    )

    ai_challenge = Competition(
        id=101,
        title="全国大学生人工智能创新挑战赛",
        short_title="AI创新挑战赛",
        category="创新创业",
        organizer="示例高校创新中心",
        source_name="示例高校竞赛通知",
        source_url="https://example.edu/notices/ai-challenge-2026",
        official_url="https://example.org/ai-challenge",
        attachment_url="https://example.edu/notices/ai-challenge-2026.pdf",
        summary="面向大学生的人工智能创新项目竞赛。",
        detail="参赛团队需要提交项目方案、作品材料和现场答辩。",
        eligibility="在校本科生可报名。",
        team_size="1-5人",
        participant_form="team",
        suitable_majors=["软件工程", "计算机科学与技术"],
        suitable_grades=["大二", "大三"],
        value_notes="校级推荐，适合有项目实践基础的学生",
        status=CompetitionStatus.PUBLISHED,
    )
    ai_challenge.time_nodes = [
        CompetitionTimeNode(
            id=201,
            node_type="registration_deadline",
            due_at=datetime(2026, 8, 15, 16, 0, tzinfo=UTC),
            description="报名截止",
        ),
        CompetitionTimeNode(
            id=202,
            node_type="submission_deadline",
            due_at=datetime(2026, 9, 10, 16, 0, tzinfo=UTC),
            description="作品提交截止",
        ),
    ]
    ai_challenge.tag_links = [
        CompetitionTagLink(id=301, tag=ai_tag),
        CompetitionTagLink(id=302, tag=innovation_tag),
    ]

    fallback = Competition(
        id=106,
        title="大学生创新创业训练计划",
        category="创新创业",
        organizer="示例教务处",
        source_name="示例教务通知",
        source_url="https://example.edu/notices/innovation-2026",
        official_url="https://example.org/innovation",
        summary="创新创业训练计划报名通知。",
        suitable_majors=["软件工程"],
        suitable_grades=["大一", "大二"],
        value_notes="适合作为通用推荐兜底样例",
        status=CompetitionStatus.PUBLISHED,
    )
    fallback.time_nodes = [
        CompetitionTimeNode(
            id=203,
            node_type="registration_deadline",
            due_at=datetime(2026, 8, 30, 16, 0, tzinfo=UTC),
            description="报名截止",
        )
    ]
    fallback.tag_links = [CompetitionTagLink(id=303, tag=innovation_tag)]

    no_time = Competition(
        id=107,
        title="无时间节点公开样例",
        category="创新创业",
        organizer="示例教务处",
        source_name="示例教务通知",
        source_url="https://example.edu/notices/no-time-2026",
        summary="用于验证缺失时间节点时的公开详情兜底。",
        suitable_majors=["软件工程"],
        suitable_grades=["大一"],
        value_notes="时间待确认时仍可稳定展示",
        status=CompetitionStatus.PUBLISHED,
    )
    no_time.tag_links = [CompetitionTagLink(id=304, tag=innovation_tag)]

    non_public = [
        Competition(
            id=102,
            title="材料不完整的赛事草稿",
            category="创新创业",
            source_name="示例高校竞赛通知",
            source_url="https://example.edu/notices/incomplete",
            status=CompetitionStatus.DRAFT,
        ),
        Competition(
            id=103,
            title="待审核人工智能挑战赛",
            category="创新创业",
            source_name="示例高校竞赛通知",
            source_url="https://example.edu/notices/pending",
            status=CompetitionStatus.PENDING_REVIEW,
        ),
        Competition(
            id=104,
            title="机器人挑战赛退回样例",
            category="机器人",
            source_name="示例高校竞赛通知",
            source_url="https://example.edu/notices/rejected",
            status=CompetitionStatus.REJECTED,
        ),
        Competition(
            id=105,
            title="数学建模下架样例",
            category="数学建模",
            source_name="示例高校竞赛通知",
            source_url="https://example.edu/notices/offline",
            status=CompetitionStatus.OFFLINE,
        ),
        Competition(
            id=108,
            title="已归档赛事样例",
            source_name="示例高校竞赛通知",
            source_url="https://example.edu/notices/archived",
            status=CompetitionStatus.ARCHIVED,
        ),
        Competition(
            id=109,
            title="已取消赛事样例",
            source_name="示例高校竞赛通知",
            source_url="https://example.edu/notices/cancelled",
            status=CompetitionStatus.CANCELLED,
        ),
        Competition(
            id=110,
            title="已过期赛事样例",
            source_name="示例高校竞赛通知",
            source_url="https://example.edu/notices/expired",
            status=CompetitionStatus.EXPIRED,
        ),
    ]

    db.session.add_all(
        [publisher, ai_tag, innovation_tag, ai_challenge, fallback, no_time, *non_public]
    )
    db.session.flush()
    for competition in (ai_challenge, fallback, no_time):
        attach_approved_revision(competition, publisher.id)
    db.session.commit()


def sign_in_as(client, app, *, role: UserRole = UserRole.STUDENT) -> int:
    with app.app_context():
        user = User(
            password_hash="not-used",
            display_name="Engagement Test User",
            role=role,
        )
        db.session.add(user)
        db.session.flush()
        if role == UserRole.STUDENT:
            provision_student_owned_rows(user)
        db.session.commit()
        user_id = user.id
        session_version = user.session_version

    with client.session_transaction() as browser_session:
        browser_session["user_id"] = user_id
        browser_session["session_version"] = session_version
        now = datetime.now(UTC).isoformat()
        browser_session["issued_at"] = now
        browser_session["last_activity_at"] = now
    return user_id


def attach_approved_revision(competition: Competition, publisher_id: int) -> CompetitionRevision:
    revision = CompetitionRevision(
        competition=competition,
        revision_number=1,
        revision_status=CompetitionRevisionStatus.APPROVED,
        title=competition.title,
        short_title=competition.short_title,
        category=competition.category,
        organizer=competition.organizer,
        host=competition.host,
        source_name=competition.source_name,
        source_url=competition.source_url,
        official_url=competition.official_url,
        attachment_url=competition.attachment_url,
        summary=competition.summary,
        detail=competition.detail,
        eligibility=competition.eligibility,
        registration_applicability="applicable",
        team_size=competition.team_size,
        participant_forms=[competition.participant_form] if competition.participant_form else [],
        major_scope="selected" if competition.suitable_majors else "unknown",
        grade_scope="selected" if competition.suitable_grades else "unknown",
        suitable_majors=competition.suitable_majors,
        suitable_grades=competition.suitable_grades,
        value_notes=competition.value_notes,
        created_by_id=publisher_id,
        published_at=datetime(2026, 7, 10, 1, 0, tzinfo=UTC),
    )
    db.session.add(revision)
    db.session.flush()
    for node in competition.time_nodes:
        node.revision = revision
        node.occurs_at = node.occurs_at or node.due_at or node.starts_at
    for link in competition.tag_links:
        link.revision = revision
    competition.published_revision_id = revision.id
    competition.participant_forms = revision.participant_forms
    competition.major_scope = revision.major_scope
    competition.grade_scope = revision.grade_scope
    return revision


def create_unpublished_edition() -> Competition:
    competition = Competition(
        id=130,
        title="Unpublished Challenge",
        source_name="School Notice",
        source_url="https://example.edu/notices/unpublished",
        status=CompetitionStatus.UNPUBLISHED,
    )
    db.session.add(competition)
    db.session.commit()
    return competition


def test_public_competition_list_uses_envelope_and_hides_non_public_states(client) -> None:
    response = client.get("/api/v1/competitions")

    assert response.status_code == 200
    body = response.get_json()
    assert body["error"] is None
    assert body["data"]["pagination"] == {"page": 1, "page_size": 20, "total": 3}

    items = body["data"]["items"]
    assert {item["id"] for item in items} == {101, 106, 107}
    assert all(item["status"] == "published" for item in items)
    assert all(item["is_favorited"] is False for item in items)
    assert all(item["is_subscribed"] is False for item in items)
    assert [item["id"] for item in items] == [101, 106, 107]
    assert items[2]["next_node"] is None


def test_public_competition_filters_preserve_visibility_contract(client) -> None:
    keyword_response = client.get("/api/v1/competitions?keyword=人工智能")
    keyword_items = keyword_response.get_json()["data"]["items"]
    assert [item["id"] for item in keyword_items] == [101]

    major_response = client.get("/api/v1/competitions?major=软件工程&tag=人工智能")
    major_items = major_response.get_json()["data"]["items"]
    assert [item["id"] for item in major_items] == [101]
    assert major_items[0]["suitable_majors"] == ["软件工程", "计算机科学与技术"]
    assert major_items[0]["next_node"]["node_type"] == "registration_deadline"

    lifecycle_status_response = client.get("/api/v1/competitions?status=published")
    assert lifecycle_status_response.status_code == 400
    assert lifecycle_status_response.get_json()["error"]["code"] == "validation_error"

    hidden_category_response = client.get("/api/v1/competitions?category=数学建模")
    assert hidden_category_response.get_json()["data"]["items"] == []

    field_response = client.get(
        "/api/v1/competitions?category=创新创业&grade=大二&participant_form=team"
    )
    assert [item["id"] for item in field_response.get_json()["data"]["items"]] == [101]

    deadline_response = client.get(
        "/api/v1/competitions?deadline_from=2026-08-20&deadline_to=2026-09-01"
    )
    assert [item["id"] for item in deadline_response.get_json()["data"]["items"]] == [106]


def test_public_competition_deadline_filter_only_matches_registration_deadlines(client) -> None:
    registration_deadline_response = client.get(
        "/api/v1/competitions?deadline_from=2026-08-10&deadline_to=2026-08-16"
    )
    assert [item["id"] for item in registration_deadline_response.get_json()["data"]["items"]] == [
        101
    ]

    submission_deadline_response = client.get(
        "/api/v1/competitions?deadline_from=2026-09-01&deadline_to=2026-09-15"
    )
    assert submission_deadline_response.get_json()["data"]["items"] == []


def test_public_competition_deadline_filter_uses_shanghai_calendar_dates(client) -> None:
    shanghai_date_response = client.get(
        "/api/v1/competitions?deadline_from=2026-08-16&deadline_to=2026-08-16"
    )
    assert [item["id"] for item in shanghai_date_response.get_json()["data"]["items"]] == [101]

    utc_date_response = client.get(
        "/api/v1/competitions?deadline_from=2026-08-15&deadline_to=2026-08-15"
    )
    assert utc_date_response.get_json()["data"]["items"] == []


def test_public_competition_pagination_is_applied_after_filters(client) -> None:
    response = client.get("/api/v1/competitions?category=创新创业&page=2&page_size=1")

    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["pagination"] == {"page": 2, "page_size": 1, "total": 3}
    assert [item["id"] for item in body["data"]["items"]] == [106]


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page=invalid",
        "page_size=0",
        "page_size=101",
        "deadline_from=invalid",
        "deadline_from=2026-09-01&deadline_to=2026-08-01",
        "participant_form=unsupported",
    ],
)
def test_public_competition_rejects_invalid_query_parameters(client, query) -> None:
    response = client.get(f"/api/v1/competitions?{query}")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_public_competition_detail_returns_stable_summary_and_detail_contract(client) -> None:
    response = client.get("/api/v1/competitions/101")

    assert response.status_code == 200
    body = response.get_json()
    data = body["data"]
    assert body["error"] is None
    assert data["id"] == 101
    assert data["title"] == "全国大学生人工智能创新挑战赛"
    assert data["status"] == "published"
    assert data["category"] == "创新创业"
    assert data["source_name"] == "示例高校竞赛通知"
    assert data["source_url"] == "https://example.edu/notices/ai-challenge-2026"
    assert data["official_url"] == "https://example.org/ai-challenge"
    assert data["attachment_url"] == "https://example.edu/notices/ai-challenge-2026.pdf"
    assert data["edition_label"] is None
    assert data["current_revision"] == {"id": 1, "revision_number": 1}
    assert data["tags"] == ["人工智能", "创新创业"]
    assert data["suitable_majors"] == ["软件工程", "计算机科学与技术"]
    assert data["suitable_grades"] == ["大二", "大三"]
    assert data["value_notes"] == "校级推荐，适合有项目实践基础的学生"
    assert [node["node_type"] for node in data["time_nodes"]] == [
        "registration_deadline",
        "submission_deadline",
    ]
    assert data["next_node"]["node_type"] == "registration_deadline"


def test_public_competition_detail_keeps_missing_time_nodes_stable(client) -> None:
    response = client.get("/api/v1/competitions/107")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["next_node"] is None
    assert data["time_nodes"] == []


def test_public_competition_next_node_skips_elapsed_nodes(client) -> None:
    now = datetime.now(UTC)
    elapsed_node = CompetitionTimeNode(
        id=220,
        node_type="registration_start",
        starts_at=now - timedelta(days=1),
        description="报名已开始",
    )
    upcoming_node = CompetitionTimeNode(
        id=221,
        node_type="registration_deadline",
        due_at=now + timedelta(days=1),
        description="报名截止",
    )
    competition = Competition(
        id=120,
        title="动态时间节点赛事",
        source_name="示例高校竞赛通知",
        source_url="https://example.edu/notices/dynamic-time",
        status=CompetitionStatus.PUBLISHED,
        time_nodes=[elapsed_node, upcoming_node],
    )
    db.session.add(competition)
    db.session.flush()
    attach_approved_revision(competition, 900)
    db.session.commit()

    response = client.get("/api/v1/competitions/120")

    assert response.status_code == 200
    assert response.get_json()["data"]["next_node"]["id"] == 221


def test_public_competition_next_node_prefers_primary_before_secondary_fallback(client) -> None:
    now = datetime.now(UTC)
    earlier_secondary = CompetitionTimeNode(
        id=222,
        node_type="registration_period",
        starts_at=now + timedelta(days=1),
        due_at=now + timedelta(days=5),
        prominence="secondary",
    )
    later_primary = CompetitionTimeNode(
        id=223,
        node_type="submission_deadline",
        due_at=now + timedelta(days=2),
        prominence="primary",
    )
    competition = Competition(
        id=121,
        title="多时间字段赛事",
        source_name="示例高校竞赛通知",
        source_url="https://example.edu/notices/multiple-times",
        status=CompetitionStatus.PUBLISHED,
        time_nodes=[earlier_secondary, later_primary],
    )
    db.session.add(competition)
    db.session.flush()
    attach_approved_revision(competition, 900)
    db.session.commit()

    response = client.get("/api/v1/competitions/121")

    assert response.status_code == 200
    assert response.get_json()["data"]["next_node"]["id"] == 223


@pytest.mark.parametrize("competition_id", [102, 103, 104, 105, 108, 109, 110])
def test_public_competition_detail_returns_404_for_non_public_competition(
    client,
    competition_id,
) -> None:
    response = client.get(f"/api/v1/competitions/{competition_id}")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_public_competition_requires_published_revision_pointer(client) -> None:
    create_unpublished_edition()

    response = client.get("/api/v1/competitions/130")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_public_list_derives_registration_status_and_actionable_order(client) -> None:
    now = datetime.now(UTC)
    open_edition = _add_public_edition(
        competition_id=140,
        node_definitions=[
            ("registration_deadline", now + timedelta(days=10)),
        ],
    )
    upcoming_edition = _add_public_edition(
        competition_id=141,
        node_definitions=[
            ("registration_start", now + timedelta(days=2)),
            ("registration_deadline", now + timedelta(days=20)),
        ],
    )
    closed_edition = _add_public_edition(
        competition_id=142,
        node_definitions=[
            ("registration_deadline", now - timedelta(days=2)),
        ],
    )
    unknown_edition = _add_public_edition(competition_id=143, node_definitions=[])
    not_applicable_edition = _add_public_edition(
        competition_id=144,
        node_definitions=[],
        registration_applicability="not_applicable",
    )
    db.session.commit()

    response = client.get("/api/v1/competitions")

    assert response.status_code == 200
    items = response.get_json()["data"]["items"]
    item_by_id = {item["id"]: item for item in items}
    assert item_by_id[open_edition.id]["registration_status"] == "open"
    assert item_by_id[upcoming_edition.id]["registration_status"] == "upcoming"
    assert item_by_id[closed_edition.id]["registration_status"] == "closed"
    assert item_by_id[unknown_edition.id]["registration_status"] == "unknown"
    assert item_by_id[not_applicable_edition.id]["registration_status"] == "not_applicable"
    assert item_by_id[open_edition.id]["registration_status_basis"]["node_type"] == (
        "registration_deadline"
    )
    assert item_by_id[upcoming_edition.id]["registration_status_basis"]["node_type"] == (
        "registration_start"
    )

    ids = [item["id"] for item in items]
    assert ids.index(open_edition.id) < ids.index(upcoming_edition.id)
    assert ids.index(upcoming_edition.id) < ids.index(unknown_edition.id)
    assert ids.index(unknown_edition.id) < ids.index(not_applicable_edition.id)
    assert ids.index(not_applicable_edition.id) < ids.index(closed_edition.id)

    upcoming_response = client.get("/api/v1/competitions?registration_status=upcoming")
    assert [item["id"] for item in upcoming_response.get_json()["data"]["items"]] == [
        upcoming_edition.id
    ]

    actionable_response = client.get(
        "/api/v1/competitions?keyword=Registration%20fixture&sort=actionable"
    )
    assert [item["id"] for item in actionable_response.get_json()["data"]["items"]] == [
        open_edition.id,
        upcoming_edition.id,
        unknown_edition.id,
        not_applicable_edition.id,
        closed_edition.id,
    ]

    deadline_sort_response = client.get(
        "/api/v1/competitions?keyword=Registration%20fixture&sort=registration_deadline"
    )
    assert [item["id"] for item in deadline_sort_response.get_json()["data"]["items"]][:2] == [
        open_edition.id,
        upcoming_edition.id,
    ]

    published_sort_response = client.get(
        "/api/v1/competitions?keyword=Registration%20fixture&sort=published_at"
    )
    assert [item["id"] for item in published_sort_response.get_json()["data"]["items"]] == [
        not_applicable_edition.id,
        unknown_edition.id,
        closed_edition.id,
        upcoming_edition.id,
        open_edition.id,
    ]


def test_public_detail_keeps_historical_editions_viewable_with_status(client) -> None:
    archived = Competition(
        id=150,
        title="Historical Archive",
        source_name="Example University Notice",
        source_url="https://example.edu/notices/historical-archive",
        status=CompetitionStatus.ARCHIVED,
        lifecycle_reason="Official archive notice",
        lifecycle_changed_at=datetime(2026, 7, 15, 9, 0, tzinfo=UTC),
    )
    db.session.add(archived)
    db.session.flush()
    attach_approved_revision(archived, 900)
    db.session.commit()

    response = client.get("/api/v1/competitions/150")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["id"] == 150
    assert data["status"] == "archived"
    assert data["content_updated_at"] is not None
    assert data["lifecycle_warning"] == {
        "status": "archived",
        "reason": "Official archive notice",
        "changed_at": "2026-07-15T09:00:00+00:00",
    }


def test_outbound_click_records_controlled_current_public_link(client) -> None:
    response = client.post(
        "/api/v1/competitions/101/outbound_clicks",
        json={"target_type": "official_url", "source_surface": "competition_detail"},
    )

    assert response.status_code == 202
    assert response.get_json()["data"] == {"accepted": True}
    event = db.session.scalar(select(OutboundClickEvent))
    assert event is not None
    assert event.competition_id == 101
    assert event.competition_revision_id == 1
    assert event.target_type == "official_url"
    assert event.source_surface == "competition_detail"
    assert event.actor_kind == "anonymous"
    assert not hasattr(event, "user_id")
    assert not hasattr(event, "ip_address")
    assert not hasattr(event, "user_agent")

    invalid_target = client.post(
        "/api/v1/competitions/101/outbound_clicks",
        json={"target_type": "https://attacker.invalid", "source_surface": "competition_detail"},
    )
    assert invalid_target.status_code == 400

    missing_target = client.post(
        "/api/v1/competitions/106/outbound_clicks",
        json={"target_type": "attachment_url", "source_surface": "competition_detail"},
    )
    assert missing_target.status_code == 404


def test_outbound_click_records_authenticated_kind_without_personal_identity(client) -> None:
    student = User(
        id=901,
        email="fixture-student@example.edu",
        password_hash="not-used",
        display_name="Fixture Student",
        role=UserRole.STUDENT,
    )
    db.session.add(student)
    db.session.commit()
    with client.session_transaction() as session_data:
        start_session(session_data, student)

    response = client.post(
        "/api/v1/competitions/101/outbound_clicks",
        json={"target_type": "source_url", "source_surface": "competition_detail"},
    )

    assert response.status_code == 202
    event = db.session.scalar(select(OutboundClickEvent))
    assert event is not None
    assert event.actor_kind == "authenticated"
    assert not hasattr(event, "user_id")


def test_outbound_click_rate_limit_returns_429_without_recording_an_extra_event() -> None:
    rate_limited_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "OUTBOUND_RATE_LIMIT_ENABLED": True,
            "OUTBOUND_RATE_LIMIT_MAX_ATTEMPTS": 1,
            "OUTBOUND_RATE_LIMIT_STORE": FakeRedisRateLimitStore(),
        }
    )
    with rate_limited_app.app_context():
        db.create_all()
        seed_day1_competitions()
        rate_limited_client = rate_limited_app.test_client()
        payload = {"target_type": "official_url", "source_surface": "competition_detail"}

        accepted = rate_limited_client.post(
            "/api/v1/competitions/101/outbound_clicks",
            json=payload,
            environ_base={"REMOTE_ADDR": "198.51.100.10"},
        )
        limited = rate_limited_client.post(
            "/api/v1/competitions/101/outbound_clicks",
            json=payload,
            environ_base={"REMOTE_ADDR": "198.51.100.10"},
        )

        assert accepted.status_code == 202
        assert limited.status_code == 429
        assert limited.get_json()["error"]["code"] == "rate_limited"
        assert db.session.query(OutboundClickEvent).count() == 1
        db.session.remove()
        db.drop_all()


def test_outbound_click_aggregation_is_idempotent_at_exact_retention_boundary() -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    retention_cutoff = now - timedelta(days=90)
    expired_at = retention_cutoff - timedelta(microseconds=1)
    db.session.add_all(
        [
            OutboundClickEvent(
                competition_id=101,
                competition_revision_id=1,
                target_type="official_url",
                source_surface="competition_detail",
                actor_kind="anonymous",
                occurred_at=expired_at,
            ),
            OutboundClickEvent(
                competition_id=101,
                competition_revision_id=1,
                target_type="official_url",
                source_surface="competition_detail",
                actor_kind="anonymous",
                occurred_at=retention_cutoff,
            ),
            OutboundClickEvent(
                competition_id=101,
                competition_revision_id=1,
                target_type="official_url",
                source_surface="competition_detail",
                actor_kind="anonymous",
                occurred_at=retention_cutoff + timedelta(hours=1),
            ),
        ]
    )
    db.session.commit()

    aggregate_outbound_clicks(now=now)
    aggregate_outbound_clicks(now=now)

    stat = db.session.scalar(select(OutboundClickDailyStat))
    assert stat is not None
    assert stat.competition_id == 101
    assert stat.target_type == "official_url"
    assert stat.source_surface == "competition_detail"
    assert stat.actor_kind == "anonymous"
    assert stat.click_count == 3
    retained_events = list(
        db.session.scalars(select(OutboundClickEvent).order_by(OutboundClickEvent.occurred_at))
    )
    assert [stored_datetime_as_utc(event.occurred_at) for event in retained_events] == [
        retention_cutoff,
        retention_cutoff + timedelta(hours=1),
    ]
    assert all(event.aggregated_at is not None for event in retained_events)


def _add_public_edition(
    *,
    competition_id: int,
    node_definitions: list[tuple[str, datetime]],
    registration_applicability: str = "applicable",
) -> Competition:
    competition = Competition(
        id=competition_id,
        title=f"Registration fixture {competition_id}",
        source_name="Example University Notice",
        source_url=f"https://example.edu/notices/registration-{competition_id}",
        registration_applicability=registration_applicability,
        status=CompetitionStatus.PUBLISHED,
    )
    competition.time_nodes = [
        CompetitionTimeNode(
            id=competition_id * 10 + index,
            node_type=node_type,
            occurs_at=occurs_at,
            description=node_type,
            prominence="primary",
        )
        for index, (node_type, occurs_at) in enumerate(node_definitions, start=1)
    ]
    db.session.add(competition)
    db.session.flush()
    revision = attach_approved_revision(competition, 900)
    revision.registration_applicability = registration_applicability
    if competition.time_nodes:
        stage = CompetitionStage(
            id=competition_id,
            revision=revision,
            stage_key="registration",
            stage_type="registration",
            label="Registration",
            stage_order=1,
        )
        for node in competition.time_nodes:
            node.stage = stage
        db.session.add(stage)
    return competition


def test_favorite_post_creates_reactivates_and_is_owner_scoped(client, app) -> None:
    student_id = sign_in_as(client, app)

    created = client.post("/api/v1/competitions/101/favorite")
    repeated = client.post("/api/v1/competitions/101/favorite")
    with app.app_context():
        favorite = (
            db.session.query(Favorite).filter_by(user_id=student_id, competition_id=101).one()
        )
        favorite.is_active = False
        db.session.commit()
    reactivated = client.post("/api/v1/competitions/101/favorite")

    assert created.status_code == 201
    assert repeated.status_code == 200
    assert reactivated.status_code == 200
    assert created.get_json()["data"] == {"competition_id": 101, "is_favorited": True}
    assert repeated.get_json()["data"] == {"competition_id": 101, "is_favorited": True}
    assert reactivated.get_json()["data"] == {"competition_id": 101, "is_favorited": True}
    with app.app_context():
        assert db.session.query(Favorite).filter_by(competition_id=101).count() == 1
        assert (
            db.session.query(Favorite)
            .filter_by(user_id=student_id, competition_id=101)
            .one()
            .is_active
            is True
        )


def test_favorite_delete_is_idempotent_and_does_not_create_absent_relation(client, app) -> None:
    student_id = sign_in_as(client, app)

    absent = client.delete("/api/v1/competitions/101/favorite")
    assert absent.status_code == 200
    with app.app_context():
        assert (
            db.session.query(Favorite).filter_by(user_id=student_id, competition_id=101).count()
            == 0
        )

    assert client.post("/api/v1/competitions/101/favorite").status_code == 201
    deleted = client.delete("/api/v1/competitions/101/favorite")
    repeated = client.delete("/api/v1/competitions/101/favorite")

    assert deleted.status_code == 200
    assert repeated.status_code == 200
    assert deleted.get_json()["data"] == {"competition_id": 101, "is_favorited": False}
    assert repeated.get_json()["data"] == {"competition_id": 101, "is_favorited": False}
    with app.app_context():
        favorite = (
            db.session.query(Favorite).filter_by(user_id=student_id, competition_id=101).one()
        )
        assert favorite.is_active is False


def test_favorite_read_state_is_personalized_for_list_and_detail(client, app) -> None:
    student_id = sign_in_as(client, app)
    with app.app_context():
        db.session.add(Favorite(id=1, user_id=student_id, competition_id=101, is_active=True))
        db.session.commit()

    list_response = client.get("/api/v1/competitions")
    detail_response = client.get("/api/v1/competitions/101")

    assert {item["id"]: item["is_favorited"] for item in list_response.get_json()["data"]["items"]}[
        101
    ] is True
    assert detail_response.get_json()["data"]["is_favorited"] is True

    other_client = app.test_client()
    sign_in_as(other_client, app)
    assert other_client.get("/api/v1/competitions/101").get_json()["data"]["is_favorited"] is False


def test_authenticated_competition_detail_exposes_persisted_subscription_consent_without_mutation(
    client, app
) -> None:
    student_id = sign_in_as(client, app)
    created = client.post(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(reminder_enabled=False, remind_days=7),
    )
    assert created.status_code == 201
    with app.app_context():
        before = {
            "subscription_count": db.session.query(Subscription)
            .filter_by(user_id=student_id, competition_id=101)
            .count(),
            "reminder_count": db.session.query(Reminder)
            .filter_by(user_id=student_id, competition_id=101)
            .count(),
            "setting": (
                db.session.query(ReminderSetting).filter_by(user_id=student_id).one().enabled,
                db.session.query(ReminderSetting)
                .filter_by(user_id=student_id)
                .one()
                .default_remind_days,
            ),
        }

    detail = client.get("/api/v1/competitions/101")

    assert detail.status_code == 200
    assert detail.get_json()["data"]["subscription_summary"] == {
        "competition_id": 101,
        "status": "active",
        "is_subscribed": True,
        "reminder_enabled": False,
        "remind_days": 7,
        "node_types": ["registration_deadline", "submission_deadline"],
        "reminder_confirmed_at": created.get_json()["data"]["reminder_confirmed_at"],
        "scheduled_reminder_count": 0,
        "next_reminder_at": None,
        "unscheduled_reason": "reminder_disabled",
    }
    with app.app_context():
        after = {
            "subscription_count": db.session.query(Subscription)
            .filter_by(user_id=student_id, competition_id=101)
            .count(),
            "reminder_count": db.session.query(Reminder)
            .filter_by(user_id=student_id, competition_id=101)
            .count(),
            "setting": (
                db.session.query(ReminderSetting).filter_by(user_id=student_id).one().enabled,
                db.session.query(ReminderSetting)
                .filter_by(user_id=student_id)
                .one()
                .default_remind_days,
            ),
        }
    assert after == before


def test_anonymous_competition_detail_has_no_subscription_summary(client) -> None:
    response = client.get("/api/v1/competitions/101")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["is_favorited"] is False
    assert data["is_subscribed"] is False
    assert data["subscription_summary"] is None


def test_favorite_mutations_require_an_authenticated_student(client, app) -> None:
    assert client.post("/api/v1/competitions/101/favorite").status_code == 401
    assert client.delete("/api/v1/competitions/101/favorite").status_code == 401

    sign_in_as(client, app, role=UserRole.ADMIN)
    assert client.post("/api/v1/competitions/101/favorite").status_code == 403
    assert client.delete("/api/v1/competitions/101/favorite").status_code == 403


@pytest.mark.parametrize(
    ("status", "expected_status"),
    [
        (CompetitionStatus.CANCELLED, 201),
        (CompetitionStatus.ARCHIVED, 201),
        (CompetitionStatus.EXPIRED, 201),
        (CompetitionStatus.OFFLINE, 409),
        (CompetitionStatus.UNPUBLISHED, 409),
    ],
)
def test_favorite_lifecycle_alignment(client, app, status, expected_status) -> None:
    sign_in_as(client, app)
    with app.app_context():
        competition = db.session.get(Competition, 101)
        competition.status = status
        db.session.commit()

    response = client.post("/api/v1/competitions/101/favorite")

    assert response.status_code == expected_status
    if expected_status == 409:
        assert response.get_json()["error"]["code"] == "engagement_unavailable"


def test_favorite_missing_competition_returns_not_found(client, app) -> None:
    sign_in_as(client, app)

    response = client.post("/api/v1/competitions/999/favorite")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_favorite_existing_edition_without_public_revision_is_unavailable(client, app) -> None:
    sign_in_as(client, app)
    with app.app_context():
        create_unpublished_edition()

    response = client.post("/api/v1/competitions/130/favorite")

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "engagement_unavailable"


def subscription_payload(**overrides) -> dict:
    payload = {
        "reminder_enabled": True,
        "remind_days": 3,
        "node_types": ["registration_deadline", "submission_deadline"],
    }
    payload.update(overrides)
    return payload


def test_subscription_first_create_records_explicit_consent_and_pending_plans(client, app) -> None:
    student_id = sign_in_as(client, app)

    response = client.post(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(),
    )

    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["competition_id"] == 101
    assert data["status"] == "active"
    assert data["is_subscribed"] is True
    assert data["reminder_enabled"] is True
    assert data["remind_days"] == 3
    assert data["node_types"] == ["registration_deadline", "submission_deadline"]
    assert data["reminder_confirmed_at"] is not None
    assert data["scheduled_reminder_count"] == 2
    assert data["next_reminder_at"] is not None
    assert data["unscheduled_reason"] is None
    with app.app_context():
        subscription = (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).one()
        )
        reminders = (
            db.session.query(Reminder).filter_by(user_id=student_id, competition_id=101).all()
        )
        assert subscription.reminder_confirmed_at is not None
        assert {reminder.node_type for reminder in reminders} == {
            "registration_deadline",
            "submission_deadline",
        }
        assert all(reminder.status.value == "pending" for reminder in reminders)
        assert {stored_datetime_as_utc(reminder.due_at) for reminder in reminders} == {
            datetime(2026, 8, 12, 16, 0, tzinfo=UTC),
            datetime(2026, 9, 7, 16, 0, tzinfo=UTC),
        }
        assert all(reminder.logical_node_key for reminder in reminders)
        assert {reminder.time_node_revision for reminder in reminders} == {1}


def test_subscription_post_canonicalizes_reversed_node_types_before_persistence(
    client, app
) -> None:
    student_id = sign_in_as(client, app)

    response = client.post(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(node_types=["submission_deadline", "registration_deadline"]),
    )

    assert response.status_code == 201
    assert response.get_json()["data"]["node_types"] == [
        "registration_deadline",
        "submission_deadline",
    ]
    with app.app_context():
        db.session.remove()
        subscription = (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).one()
        )
        assert subscription.node_types == ["registration_deadline", "submission_deadline"]


def test_subscription_reminders_disabled_retains_confirmation_without_plans(client, app) -> None:
    student_id = sign_in_as(client, app)

    response = client.post(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(reminder_enabled=False),
    )

    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["competition_id"] == 101
    assert data["status"] == "active"
    assert data["is_subscribed"] is True
    assert data["reminder_enabled"] is False
    assert data["remind_days"] == 3
    assert data["node_types"] == ["registration_deadline", "submission_deadline"]
    assert data["reminder_confirmed_at"] is not None
    assert data["scheduled_reminder_count"] == 0
    assert data["next_reminder_at"] is None
    assert data["unscheduled_reason"] == "reminder_disabled"
    with app.app_context():
        assert db.session.query(Reminder).filter_by(user_id=student_id).count() == 0


def test_subscription_post_with_missing_reminder_settings_returns_integrity_error(
    client, app
) -> None:
    student_id = sign_in_as(client, app)
    with app.app_context():
        db.session.delete(db.session.query(ReminderSetting).filter_by(user_id=student_id).one())
        db.session.commit()

    response = client.post("/api/v1/competitions/101/subscription", json=subscription_payload())

    assert response.status_code == 500
    assert response.get_json() == {
        "data": None,
        "error": {
            "code": "internal_server_error",
            "message": "student-owned profile data is missing",
            "details": {},
        },
    }
    with app.app_context():
        assert (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).count()
            == 0
        )
        assert (
            db.session.query(Reminder).filter_by(user_id=student_id, competition_id=101).count()
            == 0
        )


def test_subscription_patch_with_missing_reminder_settings_returns_integrity_error(
    client, app
) -> None:
    student_id = sign_in_as(client, app)
    created = client.post("/api/v1/competitions/101/subscription", json=subscription_payload())
    assert created.status_code == 201
    with app.app_context():
        subscription = (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).one()
        )
        original_confirmation = subscription.reminder_confirmed_at
        reminder_state = [
            (reminder.id, reminder.status, reminder.due_at, reminder.cancel_reason)
            for reminder in db.session.query(Reminder)
            .filter_by(user_id=student_id, competition_id=101)
            .order_by(Reminder.id)
        ]
        db.session.delete(db.session.query(ReminderSetting).filter_by(user_id=student_id).one())
        db.session.commit()

    response = client.patch(
        "/api/v1/competitions/101/subscription", json=subscription_payload(remind_days=2)
    )

    assert response.status_code == 500
    assert response.get_json() == {
        "data": None,
        "error": {
            "code": "internal_server_error",
            "message": "student-owned profile data is missing",
            "details": {},
        },
    }
    with app.app_context():
        subscription = (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).one()
        )
        assert subscription.remind_days == 3
        assert subscription.reminder_confirmed_at == original_confirmation
        assert [
            (reminder.id, reminder.status, reminder.due_at, reminder.cancel_reason)
            for reminder in db.session.query(Reminder)
            .filter_by(user_id=student_id, competition_id=101)
            .order_by(Reminder.id)
        ] == reminder_state


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"reminder_enabled": True, "remind_days": 3}, "node_types"),
        ({"reminder_enabled": True, "node_types": ["registration_deadline"]}, "remind_days"),
        ({"remind_days": 3, "node_types": ["registration_deadline"]}, "reminder_enabled"),
        (subscription_payload(remind_days=True), "remind_days"),
        (subscription_payload(remind_days="3"), "remind_days"),
        (subscription_payload(remind_days=31), "remind_days"),
        (subscription_payload(node_types=[]), "node_types"),
        (
            subscription_payload(node_types=["registration_deadline", "registration_deadline"]),
            "node_types",
        ),
        (subscription_payload(node_types=["registration_start"]), "node_types"),
        (subscription_payload(user_id=900), "user_id"),
    ],
)
def test_subscription_rejects_invalid_or_untrusted_request_fields(
    client, app, payload, field
) -> None:
    sign_in_as(client, app)

    response = client.post("/api/v1/competitions/101/subscription", json=payload)

    assert response.status_code == 400
    error = response.get_json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]["field"] == field


def test_subscription_requires_selected_types_in_published_revision(client, app) -> None:
    sign_in_as(client, app)

    response = client.post(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(node_types=["competition_start"]),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["field"] == "node_types"


def test_subscription_requires_student_and_currently_published_edition(client, app) -> None:
    assert (
        client.post(
            "/api/v1/competitions/101/subscription",
            json=subscription_payload(),
        ).status_code
        == 401
    )

    sign_in_as(client, app, role=UserRole.ADMIN)
    assert (
        client.post(
            "/api/v1/competitions/101/subscription",
            json=subscription_payload(),
        ).status_code
        == 403
    )


def test_subscription_missing_competition_returns_not_found(client, app) -> None:
    sign_in_as(client, app)

    response = client.post(
        "/api/v1/competitions/999/subscription",
        json=subscription_payload(),
    )

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_subscription_existing_edition_without_public_revision_is_unavailable(client, app) -> None:
    sign_in_as(client, app)
    with app.app_context():
        create_unpublished_edition()

    response = client.post(
        "/api/v1/competitions/130/subscription",
        json=subscription_payload(),
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "engagement_unavailable"


def test_subscription_patch_existing_edition_without_public_revision_is_unavailable(
    client, app
) -> None:
    student_id = sign_in_as(client, app)
    created = client.post("/api/v1/competitions/101/subscription", json=subscription_payload())
    assert created.status_code == 201
    with app.app_context():
        competition = db.session.get(Competition, 101)
        competition.status = CompetitionStatus.UNPUBLISHED
        competition.published_revision_id = None
        db.session.commit()

    response = client.patch(
        "/api/v1/competitions/101/subscription", json=subscription_payload(remind_days=2)
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "engagement_unavailable"
    with app.app_context():
        subscription = (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).one()
        )
        assert subscription.remind_days == 3


@pytest.mark.parametrize("status", [CompetitionStatus.CANCELLED, CompetitionStatus.OFFLINE])
def test_subscription_rejects_unavailable_lifecycle(client, app, status) -> None:
    sign_in_as(client, app)
    with app.app_context():
        db.session.get(Competition, 101).status = status
        db.session.commit()

    response = client.post("/api/v1/competitions/101/subscription", json=subscription_payload())

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "engagement_unavailable"


def test_subscription_rejects_when_no_eligible_nodes_exist(client, app) -> None:
    sign_in_as(client, app)
    with app.app_context():
        competition = db.session.get(Competition, 107)
        db.session.add(
            CompetitionTimeNode(
                id=270,
                competition=competition,
                revision=competition.published_revision,
                node_type="registration_deadline",
                occurs_at=None,
            )
        )
        db.session.commit()

    response = client.post(
        "/api/v1/competitions/107/subscription",
        json=subscription_payload(node_types=["registration_deadline"]),
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "engagement_unavailable"


def test_subscription_with_no_selectable_controlled_nodes_returns_conflict_without_writes(
    client, app
) -> None:
    student_id = sign_in_as(client, app)
    with app.app_context():
        setting = db.session.query(ReminderSetting).filter_by(user_id=student_id).one()
        before_setting = (setting.enabled, setting.default_remind_days, setting.node_types)

    response = client.post(
        "/api/v1/competitions/107/subscription",
        json=subscription_payload(node_types=[]),
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "engagement_unavailable"
    with app.app_context():
        assert (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=107).count()
            == 0
        )
        assert (
            db.session.query(Reminder).filter_by(user_id=student_id, competition_id=107).count()
            == 0
        )
        setting = db.session.query(ReminderSetting).filter_by(user_id=student_id).one()
        assert (setting.enabled, setting.default_remind_days, setting.node_types) == before_setting


def test_subscription_no_future_nodes_has_explicit_summary(client, app) -> None:
    sign_in_as(client, app)
    with app.app_context():
        for node in db.session.get(Competition, 101).published_revision.time_nodes:
            node.occurs_at = datetime.now(UTC) - timedelta(days=1)
        db.session.commit()

    response = client.post("/api/v1/competitions/101/subscription", json=subscription_payload())

    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["scheduled_reminder_count"] == 0
    assert data["next_reminder_at"] is None
    assert data["unscheduled_reason"] == "no_future_eligible_nodes"


def test_active_subscription_repeat_is_a_noop_without_edition_validation(client, app) -> None:
    student_id = sign_in_as(client, app)
    created = client.post("/api/v1/competitions/101/subscription", json=subscription_payload())
    assert created.status_code == 201
    created_data = created.get_json()["data"]
    with app.app_context():
        subscription = (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).one()
        )
        original_confirmation = subscription.reminder_confirmed_at
        original_reminder_ids = [reminder.id for reminder in db.session.query(Reminder).all()]
        db.session.get(Competition, 101).status = CompetitionStatus.OFFLINE
        db.session.commit()

    repeated = client.post(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(node_types=["competition_start"], remind_days=0),
    )

    assert repeated.status_code == 200
    assert repeated.get_json()["data"] == created_data
    with app.app_context():
        subscription = (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).one()
        )
        assert subscription.reminder_confirmed_at == original_confirmation
        assert [
            reminder.id for reminder in db.session.query(Reminder).all()
        ] == original_reminder_ids


def test_subscription_patch_reenables_and_restores_controlled_cancelled_plans(client, app) -> None:
    student_id = sign_in_as(client, app)
    created = client.post(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(),
    )
    assert created.status_code == 201

    disabled = client.patch(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(reminder_enabled=False),
    )

    assert disabled.status_code == 200
    assert disabled.get_json()["data"]["unscheduled_reason"] == "reminder_disabled"
    with app.app_context():
        reminders = (
            db.session.query(Reminder).filter_by(user_id=student_id, competition_id=101).all()
        )
        assert all(reminder.status == ReminderStatus.CANCELLED for reminder in reminders)
        assert {reminder.cancel_reason for reminder in reminders} == {"reminder_disabled"}

    enabled = client.patch(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(),
    )

    assert enabled.status_code == 200
    assert enabled.get_json()["data"]["scheduled_reminder_count"] == 2
    with app.app_context():
        reminders = (
            db.session.query(Reminder).filter_by(user_id=student_id, competition_id=101).all()
        )
        assert all(reminder.status == ReminderStatus.PENDING for reminder in reminders)
        assert all(reminder.cancel_reason is None for reminder in reminders)


def test_subscription_respects_global_reminder_disable_and_public_state_is_owner_scoped(
    client, app
) -> None:
    student_id = sign_in_as(client, app)
    with app.app_context():
        provision_student_owned_rows(db.session.get(User, student_id))
        db.session.commit()
    assert (
        client.patch("/api/v1/me/preferences", json={"message_enabled": False}).status_code == 200
    )

    created = client.post("/api/v1/competitions/101/subscription", json=subscription_payload())

    assert created.status_code == 201
    assert created.get_json()["data"]["scheduled_reminder_count"] == 0
    assert created.get_json()["data"]["unscheduled_reason"] == "reminder_disabled"
    detail = client.get("/api/v1/competitions/101")
    assert detail.status_code == 200
    assert detail.get_json()["data"]["is_subscribed"] is True
    with app.app_context():
        assert (
            db.session.query(Reminder).filter_by(user_id=student_id, competition_id=101).count()
            == 0
        )

    sign_in_as(client, app)
    other_detail = client.get("/api/v1/competitions/101")
    assert other_detail.status_code == 200
    assert other_detail.get_json()["data"]["is_subscribed"] is False


def test_subscription_patch_treats_node_order_as_a_semantic_noop(client, app) -> None:
    student_id = sign_in_as(client, app)
    created = client.post(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(),
    )
    assert created.status_code == 201
    with app.app_context():
        subscription = (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).one()
        )
        confirmed_at = subscription.reminder_confirmed_at
        reminder_state = [
            (reminder.id, reminder.status, reminder.due_at, reminder.cancel_reason)
            for reminder in db.session.query(Reminder).order_by(Reminder.id)
        ]

    response = client.patch(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(node_types=["submission_deadline", "registration_deadline"]),
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["node_types"] == [
        "registration_deadline",
        "submission_deadline",
    ]
    with app.app_context():
        subscription = (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).one()
        )
        assert subscription.reminder_confirmed_at == confirmed_at
        assert subscription.node_types == ["registration_deadline", "submission_deadline"]
        assert [
            (reminder.id, reminder.status, reminder.due_at, reminder.cancel_reason)
            for reminder in db.session.query(Reminder).order_by(Reminder.id)
        ] == reminder_state


def test_subscription_patch_canonicalizes_reversed_semantic_change(client, app) -> None:
    student_id = sign_in_as(client, app)
    assert (
        client.post(
            "/api/v1/competitions/101/subscription", json=subscription_payload()
        ).status_code
        == 201
    )

    response = client.patch(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(
            remind_days=2,
            node_types=["submission_deadline", "registration_deadline"],
        ),
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["node_types"] == [
        "registration_deadline",
        "submission_deadline",
    ]
    with app.app_context():
        subscription = (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).one()
        )
        assert subscription.node_types == ["registration_deadline", "submission_deadline"]
        assert subscription.remind_days == 2


def test_subscription_patch_cancels_deselected_pending_plans(client, app) -> None:
    student_id = sign_in_as(client, app)
    created = client.post(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(),
    )
    assert created.status_code == 201

    response = client.patch(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(node_types=["registration_deadline"]),
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["scheduled_reminder_count"] == 1
    with app.app_context():
        removed = (
            db.session.query(Reminder)
            .filter_by(
                user_id=student_id,
                competition_id=101,
                node_type="submission_deadline",
            )
            .one()
        )
        assert removed.status == ReminderStatus.CANCELLED
        assert removed.cancel_reason == "node_type_removed"


def test_subscription_patch_restores_cancelled_offset_plans_when_future_again(client, app) -> None:
    student_id = sign_in_as(client, app)
    created = client.post(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(),
    )
    assert created.status_code == 201
    with app.app_context():
        for node in db.session.get(Competition, 101).published_revision.time_nodes:
            node.occurs_at = datetime.now(UTC) + timedelta(days=10)
        db.session.commit()

    no_longer_future = client.patch(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(remind_days=30),
    )

    assert no_longer_future.status_code == 200
    assert no_longer_future.get_json()["data"]["unscheduled_reason"] == "no_future_eligible_nodes"
    with app.app_context():
        reminders = (
            db.session.query(Reminder).filter_by(user_id=student_id, competition_id=101).all()
        )
        assert all(reminder.status == ReminderStatus.CANCELLED for reminder in reminders)
        assert {reminder.cancel_reason for reminder in reminders} == {
            "subscription_offset_not_future"
        }

    restored = client.patch(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(),
    )

    assert restored.status_code == 200
    assert restored.get_json()["data"]["scheduled_reminder_count"] == 2
    with app.app_context():
        reminders = (
            db.session.query(Reminder).filter_by(user_id=student_id, competition_id=101).all()
        )
        assert all(reminder.status == ReminderStatus.PENDING for reminder in reminders)
        assert all(reminder.cancel_reason is None for reminder in reminders)


def test_subscription_patch_requires_active_owned_subscription_and_valid_consent(
    client, app
) -> None:
    unauthenticated = client.patch(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(),
    )
    assert unauthenticated.status_code == 401

    sign_in_as(client, app, role=UserRole.ADMIN)
    forbidden = client.patch(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(),
    )
    assert forbidden.status_code == 403

    sign_in_as(client, app)
    missing = client.patch(
        "/api/v1/competitions/101/subscription",
        json={"reminder_enabled": True, "remind_days": 3},
    )
    assert missing.status_code == 400
    assert missing.get_json()["error"]["details"]["field"] == "node_types"
    absent = client.patch(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(),
    )
    assert absent.status_code == 404
    invalid = client.patch(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(user_id=900),
    )
    assert invalid.status_code == 400
    assert invalid.get_json()["error"]["details"]["field"] == "user_id"

    created = client.post(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(),
    )
    assert created.status_code == 201
    assert client.delete("/api/v1/competitions/101/subscription").status_code == 200
    cancelled = client.patch(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(),
    )
    assert cancelled.status_code == 409


def test_subscription_delete_is_idempotent_and_cancels_only_pending_plans(client, app) -> None:
    student_id = sign_in_as(client, app)
    absent = client.delete("/api/v1/competitions/101/subscription")
    assert absent.status_code == 200
    with app.app_context():
        assert (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).count()
            == 0
        )

    created = client.post(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(),
    )
    assert created.status_code == 201
    with app.app_context():
        sent = (
            db.session.query(Reminder)
            .filter_by(user_id=student_id, competition_id=101, node_type="registration_deadline")
            .one()
        )
        sent.status = ReminderStatus.SENT
        db.session.commit()

    deleted = client.delete("/api/v1/competitions/101/subscription")
    with app.app_context():
        reminder_state_after_first_delete = [
            (reminder.id, reminder.status, reminder.cancel_reason)
            for reminder in db.session.query(Reminder)
            .filter_by(user_id=student_id, competition_id=101)
            .order_by(Reminder.id)
        ]
    repeated = client.delete("/api/v1/competitions/101/subscription")

    assert deleted.status_code == repeated.status_code == 200
    assert deleted.get_json()["data"] == {
        "competition_id": 101,
        "status": "cancelled",
        "is_subscribed": False,
    }
    with app.app_context():
        subscription = (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).one()
        )
        assert subscription.status == SubscriptionStatus.CANCELLED
        sent = (
            db.session.query(Reminder)
            .filter_by(user_id=student_id, competition_id=101, node_type="registration_deadline")
            .one()
        )
        cancelled = (
            db.session.query(Reminder)
            .filter_by(user_id=student_id, competition_id=101, node_type="submission_deadline")
            .one()
        )
        assert sent.status == ReminderStatus.SENT
        assert cancelled.status == ReminderStatus.CANCELLED
        assert cancelled.cancel_reason == "subscription_cancelled"
        assert reminder_state_after_first_delete == [
            (reminder.id, reminder.status, reminder.cancel_reason)
            for reminder in db.session.query(Reminder)
            .filter_by(user_id=student_id, competition_id=101)
            .order_by(Reminder.id)
        ]


def test_subscription_delete_for_missing_competition_returns_not_found_without_mutation(
    client, app
) -> None:
    student_id = sign_in_as(client, app)

    response = client.delete("/api/v1/competitions/999/subscription")

    assert response.status_code == 404
    assert response.get_json() == {
        "data": None,
        "error": {
            "code": "not_found",
            "message": "competition not found",
            "details": {},
        },
    }
    with app.app_context():
        assert db.session.query(Subscription).filter_by(user_id=student_id).count() == 0
        assert db.session.query(Reminder).filter_by(user_id=student_id).count() == 0


@pytest.mark.parametrize("status", [CompetitionStatus.OFFLINE, CompetitionStatus.UNPUBLISHED])
def test_owned_engagement_deletes_remain_available_without_public_revision(
    client, app, status
) -> None:
    sign_in_as(client, app)
    assert client.post("/api/v1/competitions/101/favorite").status_code == 201
    created = client.post("/api/v1/competitions/101/subscription", json=subscription_payload())
    assert created.status_code == 201
    with app.app_context():
        competition = db.session.get(Competition, 101)
        competition.status = status
        competition.published_revision_id = None
        db.session.commit()

    unfavorited = client.delete("/api/v1/competitions/101/favorite")
    unsubscribed = client.delete("/api/v1/competitions/101/subscription")

    assert unfavorited.status_code == 200
    assert unsubscribed.status_code == 200


def test_subscription_post_reactivates_relation_and_restores_controlled_cancelled_plans(
    client, app
) -> None:
    student_id = sign_in_as(client, app)
    created = client.post(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(),
    )
    assert created.status_code == 201
    assert client.delete("/api/v1/competitions/101/subscription").status_code == 200
    with app.app_context():
        blocked = (
            db.session.query(Reminder)
            .filter_by(user_id=student_id, competition_id=101, node_type="submission_deadline")
            .one()
        )
        blocked.cancel_reason = "global_reminder_disabled"
        db.session.commit()

    response = client.post(
        "/api/v1/competitions/101/subscription",
        json=subscription_payload(remind_days=0),
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["status"] == "active"
    assert response.get_json()["data"]["scheduled_reminder_count"] == 1
    with app.app_context():
        assert (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).count()
            == 1
        )
        cancelled = (
            db.session.query(Reminder)
            .filter_by(user_id=student_id, competition_id=101, node_type="registration_deadline")
            .one()
        )
        blocked = (
            db.session.query(Reminder)
            .filter_by(user_id=student_id, competition_id=101, node_type="submission_deadline")
            .one()
        )
        assert cancelled.status == ReminderStatus.PENDING
        assert cancelled.cancel_reason is None
        assert blocked.status == ReminderStatus.CANCELLED
        assert blocked.cancel_reason == "global_reminder_disabled"
