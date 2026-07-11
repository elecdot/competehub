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
    User,
)
from competehub_api.models.enums import CompetitionRevisionStatus, CompetitionStatus, UserRole


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
        team_size=competition.team_size,
        participant_forms=[competition.participant_form] if competition.participant_form else [],
        suitable_majors=competition.suitable_majors,
        suitable_grades=competition.suitable_grades,
        value_notes=competition.value_notes,
        created_by_id=publisher_id,
    )
    db.session.add(revision)
    db.session.flush()
    for node in competition.time_nodes:
        node.revision = revision
    for link in competition.tag_links:
        link.revision = revision
    competition.published_revision_id = revision.id
    return revision


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

    hidden_status_response = client.get("/api/v1/competitions?status=draft")
    assert hidden_status_response.get_json()["data"]["items"] == []

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


def test_public_competition_next_node_uses_earliest_current_or_future_timestamp(client) -> None:
    now = datetime.now(UTC)
    ranged_node = CompetitionTimeNode(
        id=222,
        node_type="registration_period",
        starts_at=now + timedelta(days=1),
        due_at=now + timedelta(days=5),
    )
    deadline_node = CompetitionTimeNode(
        id=223,
        node_type="submission_deadline",
        due_at=now + timedelta(days=2),
    )
    competition = Competition(
        id=121,
        title="多时间字段赛事",
        source_name="示例高校竞赛通知",
        source_url="https://example.edu/notices/multiple-times",
        status=CompetitionStatus.PUBLISHED,
        time_nodes=[ranged_node, deadline_node],
    )
    db.session.add(competition)
    db.session.flush()
    attach_approved_revision(competition, 900)
    db.session.commit()

    response = client.get("/api/v1/competitions/121")

    assert response.status_code == 200
    assert response.get_json()["data"]["next_node"]["id"] == 222


@pytest.mark.parametrize("competition_id", [102, 103, 104, 105, 108, 109, 110])
def test_public_competition_detail_returns_404_for_non_public_competition(
    client,
    competition_id,
) -> None:
    response = client.get(f"/api/v1/competitions/{competition_id}")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_public_competition_requires_published_revision_pointer(client) -> None:
    competition = Competition(
        id=130,
        title="Legacy Published Challenge",
        source_name="School Notice",
        source_url="https://example.edu/notices/legacy-published",
        status=CompetitionStatus.PUBLISHED,
    )
    db.session.add(competition)
    db.session.commit()

    response = client.get("/api/v1/competitions/130")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"
