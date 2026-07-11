from __future__ import annotations

import pytest
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from competehub_api.extensions import db
from competehub_api.models import (
    AuditLog,
    Competition,
    RecommendationRule,
    RecommendationRuleSet,
    ReviewRecord,
    User,
)
from competehub_api.models.enums import CompetitionStatus, RecommendationRuleSetStatus, UserRole
from competehub_api.schemas.recommendation_rule_sets import recommendation_rule_input_schema
from competehub_api.seeds.recommendation_rules import (
    CONTROLLED_RECOMMENDATION_RULE_CODES,
    InitialRecommendationRuleSetConflict,
    seed_initial_recommendation_rule_set,
)
from competehub_api.services.errors import ServiceError
from competehub_api.services.recommendation_rule_sets import (
    clone_recommendation_rule_set,
    review_recommendation_rule_set,
    submit_recommendation_rule_set,
    update_recommendation_rule_set,
)


def test_seed_creates_the_initial_active_rule_set(app) -> None:
    with app.app_context():
        rule_set = seed_initial_recommendation_rule_set()

        assert rule_set.version == 1
        assert rule_set.status == RecommendationRuleSetStatus.ACTIVE
        assert rule_set.base_rule_set_id is None
        assert rule_set.cloned_from_rule_set_id is None
        assert {rule.code for rule in rule_set.rules} == set(CONTROLLED_RECOMMENDATION_RULE_CODES)
        assert all(1 <= rule.weight <= 100 for rule in rule_set.rules)
        assert RecommendationRuleSet.query.count() == 1


def test_seed_is_idempotent(app) -> None:
    with app.app_context():
        first = seed_initial_recommendation_rule_set()
        second = seed_initial_recommendation_rule_set()

        assert second.id == first.id
        assert RecommendationRuleSet.query.count() == 1
        assert RecommendationRule.query.count() == len(CONTROLLED_RECOMMENDATION_RULE_CODES)


def test_seed_cli_creates_the_reproducible_active_v1(app) -> None:
    result = app.test_cli_runner().invoke(args=["seed-recommendation-rules"])

    assert result.exit_code == 0
    assert "active recommendation rule-set v1" in result.output
    with app.app_context():
        assert RecommendationRuleSet.query.filter_by(version=1).one().status == (
            RecommendationRuleSetStatus.ACTIVE
        )


def test_seed_rejects_a_conflicting_v1_without_overwriting_it(app) -> None:
    with app.app_context():
        rule_set = seed_initial_recommendation_rule_set()
        rule_set.rules[0].weight = 99
        db.session.commit()

        with pytest.raises(InitialRecommendationRuleSetConflict):
            seed_initial_recommendation_rule_set()

        assert rule_set.rules[0].weight == 99
        assert RecommendationRuleSet.query.count() == 1


@pytest.mark.parametrize("weight", [0, -1, 101])
def test_database_rejects_weights_outside_the_contract(app, weight: int) -> None:
    with app.app_context():
        rule_set = RecommendationRuleSet(
            version=2,
            status=RecommendationRuleSetStatus.DRAFT,
            rules=[
                RecommendationRule(
                    code="major_match",
                    name="专业匹配",
                    weight=weight,
                    conditions={"operator": "overlap"},
                    reason_template="与你的专业 {major} 匹配",
                    enabled=True,
                )
            ],
        )
        db.session.add(rule_set)

        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_database_allows_at_most_one_active_rule_set(app) -> None:
    with app.app_context():
        seed_initial_recommendation_rule_set()
        db.session.add(RecommendationRuleSet(version=2, status=RecommendationRuleSetStatus.ACTIVE))

        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_clone_active_rule_set_creates_a_versioned_owned_draft(app) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        editor = User(
            email="editor@example.edu",
            password_hash="test-only",
            display_name="Rule Editor",
            role=UserRole.ADMIN,
        )
        db.session.add(editor)
        db.session.commit()

        draft = clone_recommendation_rule_set(active.id, editor)

        assert draft.version == 2
        assert draft.status == RecommendationRuleSetStatus.DRAFT
        assert draft.created_by_id == editor.id
        assert draft.cloned_from_rule_set_id == active.id
        assert draft.base_rule_set_id == active.id
        assert {rule.code for rule in draft.rules} == {rule.code for rule in active.rules}
        assert {rule.id for rule in draft.rules}.isdisjoint({rule.id for rule in active.rules})
        audit = AuditLog.query.filter_by(action="recommendation_rule_set.create").one()
        assert audit.actor_id == editor.id
        assert audit.target_id == draft.id
        assert audit.detail == {
            "source_rule_set_id": active.id,
            "base_rule_set_id": active.id,
            "version": 2,
        }


def test_rule_input_schema_accepts_the_bounded_contract() -> None:
    payload = {
        "code": "deadline_urgency",
        "name": "截止时间临近",
        "weight": 100,
        "conditions": {"max_days": 14, "operator": "within_days", "min_days": 0},
        "reason_template": "报名截止日期为 {deadline_date}，还有 {days_remaining} 天",
        "enabled": True,
    }

    assert recommendation_rule_input_schema.load(payload) == payload


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("code", "custom_expression"),
        ("weight", 0),
        ("weight", 101),
        ("conditions", {"operator": "overlap", "field": "profile.major"}),
        ("reason_template", "专业匹配 {major.__class__}"),
        ("reason_template", "专业匹配\n{major}"),
    ],
)
def test_rule_input_schema_rejects_uncontrolled_values(field: str, value: object) -> None:
    payload = {
        "code": "major_match",
        "name": "专业匹配",
        "weight": 30,
        "conditions": {"operator": "overlap"},
        "reason_template": "与你的专业 {major} 匹配",
        "enabled": True,
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        recommendation_rule_input_schema.load(payload)


def test_owner_can_update_and_submit_a_complete_changed_draft(app) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        editor = _create_admin("owner@example.edu", "Rule Owner")
        draft = clone_recommendation_rule_set(active.id, editor)
        payloads = [_rule_payload(rule) for rule in draft.rules]
        next(rule for rule in payloads if rule["code"] == "major_match")["weight"] = 31

        update_recommendation_rule_set(draft.id, editor, payloads)
        submitted = submit_recommendation_rule_set(draft.id, editor)

        assert submitted.status == RecommendationRuleSetStatus.PENDING_REVIEW
        assert submitted.submitted_by_id == editor.id
        assert submitted.submitted_at is not None
        assert ReviewRecord.query.count() == 0
        audit = AuditLog.query.filter_by(action="recommendation_rule_set.submit_review").one()
        assert audit.actor_id == editor.id
        assert audit.target_id == draft.id


def test_submitter_cannot_review_their_own_candidate(app) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        editor = _create_admin("self-review@example.edu", "Editor Reviewer")
        candidate = _changed_submitted_candidate(active, editor)

        with pytest.raises(ServiceError) as captured:
            review_recommendation_rule_set(candidate.id, editor, "approve", "looks good")

        assert captured.value.status_code == 403
        assert db.session.get(RecommendationRuleSet, candidate.id).status == (
            RecommendationRuleSetStatus.PENDING_REVIEW
        )
        assert ReviewRecord.query.count() == 0


def test_clone_from_returned_successor_preserves_the_original_governance_base(app) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        editor = _create_admin("returned-editor@example.edu", "Returned Editor")
        reviewer = _create_admin("returned-reviewer@example.edu", "Returned Reviewer")
        candidate = _changed_submitted_candidate(active, editor)

        review_recommendation_rule_set(candidate.id, reviewer, "return", "needs revision")
        successor = clone_recommendation_rule_set(candidate.id, reviewer)

        assert candidate.status == RecommendationRuleSetStatus.RETURNED
        assert successor.status == RecommendationRuleSetStatus.DRAFT
        assert successor.cloned_from_rule_set_id == candidate.id
        assert successor.base_rule_set_id == active.id
        assert {rule.code for rule in successor.rules} == {rule.code for rule in candidate.rules}
        assert {rule.id for rule in successor.rules}.isdisjoint(
            {rule.id for rule in candidate.rules}
        )


@pytest.mark.parametrize(
    "source_status",
    [
        RecommendationRuleSetStatus.DRAFT,
        RecommendationRuleSetStatus.PENDING_REVIEW,
        RecommendationRuleSetStatus.RETIRED,
    ],
)
def test_clone_rejects_sources_outside_the_thin_slice(app, source_status) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        editor = _create_admin(f"{source_status.value}@example.edu", "Source Editor")
        reviewer = _create_admin(f"reviewer-{source_status.value}@example.edu", "Reviewer")
        source = _changed_submitted_candidate(active, editor)
        if source_status == RecommendationRuleSetStatus.DRAFT:
            source = clone_recommendation_rule_set(active.id, editor)
        elif source_status == RecommendationRuleSetStatus.RETIRED:
            source = review_recommendation_rule_set(source.id, reviewer, "approve", "approved")
            source = active

        with pytest.raises(ServiceError) as captured:
            clone_recommendation_rule_set(source.id, reviewer)

        assert captured.value.status_code == 409
        assert captured.value.details["status"] == source_status.value


def test_distinct_reviewer_atomically_activates_candidate_and_retires_base(app) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        editor = _create_admin("editor2@example.edu", "Rule Editor")
        reviewer = _create_admin("reviewer@example.edu", "Rule Reviewer")
        candidate = _changed_submitted_candidate(active, editor)

        reviewed = review_recommendation_rule_set(
            candidate.id,
            reviewer,
            "approve",
            "controlled change approved",
        )

        assert reviewed.status == RecommendationRuleSetStatus.ACTIVE
        assert reviewed.reviewed_by_id == reviewer.id
        assert reviewed.activated_at is not None
        assert active.status == RecommendationRuleSetStatus.RETIRED
        assert active.retired_at is not None
        decision = ReviewRecord.query.filter_by(
            target_type="recommendation_rule_set",
            target_id=candidate.id,
        ).one()
        assert decision.target_revision == candidate.version
        assert decision.difference_snapshot["candidate_version"] == candidate.version
        assert decision.impact_summary["active_version_before"] == active.version
        assert decision.impact_summary["active_version_after"] == candidate.version
        assert {
            audit.action
            for audit in AuditLog.query.filter_by(target_type="recommendation_rule_set").all()
        } >= {
            "recommendation_rule_set.approve",
            "recommendation_rule_set.activate",
            "recommendation_rule_set.retire",
        }


def test_stale_approve_returns_conflict_without_terminal_review_record(app) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        first_editor = _create_admin("first-editor@example.edu", "First Editor")
        second_editor = _create_admin("second-editor@example.edu", "Second Editor")
        reviewer = _create_admin("stale-reviewer@example.edu", "Stale Reviewer")
        stale_candidate = _changed_submitted_candidate(active, first_editor)
        fresh_candidate = _changed_submitted_candidate(active, second_editor)
        review_recommendation_rule_set(fresh_candidate.id, reviewer, "approve", "approved")

        with pytest.raises(ServiceError) as captured:
            review_recommendation_rule_set(stale_candidate.id, reviewer, "approve", "too late")

        assert captured.value.status_code == 409
        assert captured.value.code == "stale_rule_set"
        assert db.session.get(RecommendationRuleSet, stale_candidate.id).status == (
            RecommendationRuleSetStatus.PENDING_REVIEW
        )
        assert ReviewRecord.query.filter_by(target_id=stale_candidate.id).count() == 0


def test_clone_api_requires_editor_capability_and_returns_lineage(
    client,
    app,
    monkeypatch,
) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        role_only_admin = _create_admin("role-only@example.edu", "Role Only")
        editor = _create_admin("api-editor@example.edu", "API Editor")
        active_id = active.id
        role_only_admin_id = role_only_admin.id
        editor_id = editor.id
    monkeypatch.setattr(
        "competehub_api.blueprints.recommendation_rule_sets.user_has_capability",
        lambda user, capability: user.id == editor_id and capability == "recommendation_editor",
    )

    _login(client, role_only_admin_id)
    forbidden = client.post(
        "/api/v1/admin/recommendation_rule_sets",
        json={"source_rule_set_id": active_id},
    )
    _login(client, editor_id)
    created = client.post(
        "/api/v1/admin/recommendation_rule_sets",
        json={"source_rule_set_id": active_id},
    )

    assert forbidden.status_code == 403
    assert created.status_code == 201
    data = created.get_json()["data"]
    assert data["version"] == 2
    assert data["status"] == "draft"
    assert data["cloned_from_rule_set_id"] == active_id
    assert data["base_rule_set_id"] == active_id
    assert data["active_rule_set_id"] == active_id
    assert data["is_stale"] is False


def test_api_editor_reviewer_workflow_blocks_self_review_and_activates(
    client,
    app,
    monkeypatch,
) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        editor = _create_admin("workflow-editor@example.edu", "Workflow Editor")
        reviewer = _create_admin("workflow-reviewer@example.edu", "Workflow Reviewer")
        active_id = active.id
        editor_id = editor.id
        reviewer_id = reviewer.id
    capabilities = {
        editor_id: {"recommendation_editor"},
        reviewer_id: {"recommendation_reviewer"},
    }
    monkeypatch.setattr(
        "competehub_api.blueprints.recommendation_rule_sets.user_has_capability",
        lambda user, capability: capability in capabilities.get(user.id, set()),
    )
    _login(client, editor_id)
    created = client.post(
        "/api/v1/admin/recommendation_rule_sets",
        json={"source_rule_set_id": active_id},
    ).get_json()["data"]
    rules = created["rules"]
    next(rule for rule in rules if rule["code"] == "interest_match")["weight"] = 41

    updated = client.patch(
        f"/api/v1/admin/recommendation_rule_sets/{created['rule_set_id']}",
        json={"rules": rules},
    )
    submitted = client.post(
        f"/api/v1/admin/recommendation_rule_sets/{created['rule_set_id']}/submit_review"
    )
    self_review = client.post(
        f"/api/v1/admin/recommendation_rule_sets/{created['rule_set_id']}/review",
        json={"action": "approve", "comment": "self approval"},
    )
    _login(client, reviewer_id)
    pending_history = client.get("/api/v1/admin/recommendation_rule_sets")
    approved = client.post(
        f"/api/v1/admin/recommendation_rule_sets/{created['rule_set_id']}/review",
        json={"action": "approve", "comment": "independent review"},
    )

    assert updated.status_code == 200
    assert submitted.status_code == 200
    assert submitted.get_json()["data"]["status"] == "pending_review"
    assert self_review.status_code == 403
    pending_item = next(
        item
        for item in pending_history.get_json()["data"]["items"]
        if item["rule_set_id"] == created["rule_set_id"]
    )
    assert pending_item["difference_snapshot"]["changed_rules"]
    assert pending_item["impact_summary"]["is_stale"] is False
    assert approved.status_code == 200
    assert approved.get_json()["data"]["status"] == "active"


def test_preview_uses_synthetic_profile_and_validates_all_fixtures(
    client,
    app,
    monkeypatch,
) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        reviewer = _create_admin("preview-reviewer@example.edu", "Preview Reviewer")
        public = Competition(
            id=201,
            title="Published AI Challenge",
            source_name="School Notice",
            source_url="https://example.edu/ai",
            status=CompetitionStatus.PUBLISHED,
            suitable_majors=["软件工程"],
            suitable_grades=["大二"],
        )
        draft = Competition(
            id=202,
            title="Draft Challenge",
            source_name="School Notice",
            source_url="https://example.edu/draft",
            status=CompetitionStatus.DRAFT,
        )
        db.session.add_all([public, draft])
        db.session.commit()
        active_id = active.id
        reviewer_id = reviewer.id
    monkeypatch.setattr(
        "competehub_api.blueprints.recommendation_rule_sets.user_has_capability",
        lambda user, capability: user.id == reviewer_id and capability == "recommendation_reviewer",
    )
    _login(client, reviewer_id)
    payload = {
        "scenario": "personalized",
        "synthetic_profile": {
            "college": "计算机学院",
            "major": "软件工程",
            "grade": "大二",
            "interest_tags": ["人工智能"],
        },
        "competition_ids": [201],
    }

    preview = client.post(
        f"/api/v1/admin/recommendation_rule_sets/{active_id}/preview",
        json=payload,
    )
    invalid = client.post(
        f"/api/v1/admin/recommendation_rule_sets/{active_id}/preview",
        json={**payload, "competition_ids": [201, 202, 999, 201]},
    )

    assert preview.status_code == 200
    item = preview.get_json()["data"]["results"][0]
    assert item["competition_id"] == 201
    assert item["position"] == 1
    assert item["matched_rule_codes"] == ["major_match", "grade_match"]
    assert item["reason_codes"] == ["major_match", "grade_match"]
    assert "score" not in item
    assert invalid.status_code == 400
    assert invalid.get_json()["error"]["details"] == {
        "duplicate": [201],
        "not_found": [999],
        "not_recommendable": [202],
    }


def _create_admin(email: str, display_name: str) -> User:
    user = User(
        email=email,
        password_hash="test-only",
        display_name=display_name,
        role=UserRole.ADMIN,
    )
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, user_id: int) -> None:
    with client.session_transaction() as session:
        session["user_id"] = user_id


def _rule_payload(rule: RecommendationRule) -> dict:
    return {
        "code": rule.code,
        "name": rule.name,
        "weight": rule.weight,
        "conditions": rule.conditions,
        "reason_template": rule.reason_template,
        "enabled": rule.enabled,
    }


def _changed_submitted_candidate(
    active: RecommendationRuleSet,
    editor: User,
) -> RecommendationRuleSet:
    draft = clone_recommendation_rule_set(active.id, editor)
    payloads = [_rule_payload(rule) for rule in draft.rules]
    next(rule for rule in payloads if rule["code"] == "major_match")["weight"] += 1
    update_recommendation_rule_set(draft.id, editor, payloads)
    return submit_recommendation_rule_set(draft.id, editor)
