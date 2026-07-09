from __future__ import annotations

from datetime import UTC, datetime

import pytest

from competehub_api import create_app
from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionTag,
    CompetitionTagLink,
    CompetitionTimeNode,
)
from competehub_api.models.enums import CompetitionStatus


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        seed_day1_competitions()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def seed_day1_competitions() -> None:
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
    ]

    db.session.add_all([ai_tag, innovation_tag, ai_challenge, fallback, no_time, *non_public])
    db.session.commit()


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


def test_public_competition_detail_returns_404_for_non_public_competition(client) -> None:
    response = client.get("/api/v1/competitions/102")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"
