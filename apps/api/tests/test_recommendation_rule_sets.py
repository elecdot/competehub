from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from competehub_api.extensions import db
from competehub_api.models import (
    AuditLog,
    Competition,
    CompetitionRevision,
    CompetitionTag,
    CompetitionTagLink,
    CompetitionTimeNode,
    RecommendationRule,
    RecommendationRuleSet,
    ReviewRecord,
    User,
)
from competehub_api.models.enums import (
    CompetitionRevisionStatus,
    CompetitionStatus,
    RecommendationRuleSetStatus,
    ReviewStatus,
    UserRole,
)
from competehub_api.schemas.recommendation_rule_sets import recommendation_rule_input_schema
from competehub_api.seeds.recommendation_rules import (
    CONTROLLED_RECOMMENDATION_RULE_CODES,
    InitialRecommendationRuleSetConflict,
    seed_initial_recommendation_rule_set,
)
from competehub_api.services.auth import start_session
from competehub_api.services.errors import ServiceError
from competehub_api.services.recommendation_rule_set_views import (
    recommendation_rule_set_history,
)
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
    assert pending_item["created_by"] == {"id": editor_id, "display_name": "Workflow Editor"}
    assert pending_item["submitted_by"] == {
        "id": editor_id,
        "display_name": "Workflow Editor",
    }
    assert pending_item["reviewed_by"] is None
    assert pending_item["submitted_at"] is not None
    assert pending_item["terminal_review_status"] is None
    assert approved.status_code == 200
    approved_data = approved.get_json()["data"]
    assert approved_data["status"] == "active"
    assert approved_data["reviewed_by"] == {
        "id": reviewer_id,
        "display_name": "Workflow Reviewer",
    }
    assert approved_data["review_comment"] == "independent review"
    assert approved_data["terminal_review_status"] == "approved"
    assert approved_data["decided_at"] is not None
    assert approved_data["activated_at"] is not None


def test_history_service_uses_frozen_terminal_review_evidence(app) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        editor = _create_admin("history-editor@example.edu", "History Editor")
        reviewer = _create_admin("history-reviewer@example.edu", "History Reviewer")
        candidate = _changed_submitted_candidate(active, editor)
        review_recommendation_rule_set(candidate.id, reviewer, "approve", "frozen evidence")
        decision = ReviewRecord.query.filter_by(target_id=candidate.id).one()
        frozen_difference = decision.difference_snapshot
        frozen_impact = decision.impact_summary
        db.session.add(
            ReviewRecord(
                target_type="recommendation_rule_set",
                target_id=candidate.id,
                target_revision=candidate.version + 100,
                submitted_by_id=reviewer.id,
                reviewed_by_id=editor.id,
                status=ReviewStatus.REJECTED,
                comment="wrong revision evidence",
                difference_snapshot={"wrong": True},
                impact_summary={"wrong": True},
                submitted_at=datetime.now(UTC),
                decided_at=datetime.now(UTC),
            )
        )
        db.session.commit()

        history = recommendation_rule_set_history()["items"]
        candidate_item = next(item for item in history if item["rule_set_id"] == candidate.id)
        retired_item = next(item for item in history if item["rule_set_id"] == active.id)

        assert candidate_item["difference_snapshot"] == frozen_difference
        assert candidate_item["impact_summary"] == frozen_impact
        assert candidate_item["submitted_by"]["id"] == editor.id
        assert candidate_item["reviewed_by"]["id"] == reviewer.id
        assert candidate_item["terminal_review_status"] == "approved"
        assert candidate_item["review_comment"] == "frozen evidence"
        assert candidate_item["cloned_from_version"] == 1
        assert candidate_item["base_version"] == 1
        assert candidate_item["active_version"] == candidate.version
        assert retired_item["status"] == "retired"
        assert retired_item["retired_at"] is not None


def test_preview_uses_synthetic_profile_and_validates_all_fixtures(
    client,
    app,
    monkeypatch,
) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        reviewer = _create_admin("preview-reviewer@example.edu", "Preview Reviewer")
        college, majors = next(iter(app.config["PROFILE_ALLOWED_MAJORS_BY_COLLEGE"].items()))
        major = majors[0]
        grade = app.config["PROFILE_ALLOWED_GRADES"][0]
        interest_tag = app.config["PROFILE_ALLOWED_INTEREST_TAGS"][0]
        public = Competition(
            id=201,
            title="Published AI Challenge",
            source_name="School Notice",
            source_url="https://example.edu/ai",
            status=CompetitionStatus.PUBLISHED,
            suitable_majors=[major],
            suitable_grades=[grade],
        )
        draft = Competition(
            id=202,
            title="Draft Challenge",
            source_name="School Notice",
            source_url="https://example.edu/draft",
            status=CompetitionStatus.DRAFT,
        )
        db.session.add_all([public, draft])
        db.session.flush()
        published_revision = CompetitionRevision(
            competition=public,
            revision_number=1,
            revision_status=CompetitionRevisionStatus.APPROVED,
            title=public.title,
            source_name=public.source_name,
            source_url=public.source_url,
            registration_applicability="applicable",
            participant_forms=[],
            major_scope="selected",
            grade_scope="selected",
            suitable_majors=[major],
            suitable_grades=[grade],
            created_by_id=reviewer.id,
            published_at=datetime(2026, 7, 12, 1, 0, tzinfo=UTC),
        )
        db.session.add(published_revision)
        db.session.flush()
        public.published_revision_id = published_revision.id
        tag = CompetitionTag(code="preview-interest", name=interest_tag, tag_type="topic")
        db.session.add(tag)
        db.session.flush()
        db.session.add(
            CompetitionTagLink(competition_revision_id=published_revision.id, tag_id=tag.id)
        )
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
            "college": college,
            "major": major,
            "grade": grade,
            "interest_tags": [interest_tag],
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
    assert item["competition"] == {
        "id": 201,
        "title": "Published AI Challenge",
        "edition_label": None,
    }
    assert item["position"] == 1
    assert item["matched_rule_codes"] == ["major_match", "grade_match", "interest_match"]
    assert item["reason_codes"] == ["major_match", "grade_match", "interest_match"]
    assert "score" not in item
    assert invalid.status_code == 400
    assert invalid.get_json()["error"]["details"] == {
        "duplicate": [201],
        "not_found": [999],
        "not_recommendable": [202],
    }


@pytest.mark.parametrize(
    ("stale_fact", "expected_current_code"),
    [
        ("major", "grade_match"),
        ("grade", "major_match"),
        ("deadline", "major_match"),
        ("tag", "major_match"),
    ],
)
def test_preview_never_falls_back_to_legacy_competition_facts(
    client,
    app,
    monkeypatch,
    stale_fact: str,
    expected_current_code: str,
) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        reviewer = _create_admin(f"legacy-{stale_fact}@example.edu", "Preview Reviewer")
        profile = _controlled_profile(app)
        competition = _public_competition_with_revision(
            300 + len(stale_fact),
            reviewer,
            current_majors=[profile["major"]] if stale_fact != "major" else ["not-current"],
            current_grades=[profile["grade"]] if stale_fact != "grade" else ["not-current"],
            current_tags=(
                [profile["interest_tags"][0]] if stale_fact != "tag" else ["not-current"]
            ),
            current_deadline=(
                datetime.now(UTC) + timedelta(days=5) if stale_fact != "deadline" else None
            ),
            legacy_profile=profile,
            legacy_deadline=datetime.now(UTC) + timedelta(days=5),
        )
        active_id = active.id
        reviewer_id = reviewer.id
        competition_id = competition.id
    monkeypatch.setattr(
        "competehub_api.blueprints.recommendation_rule_sets.user_has_capability",
        lambda user, capability: user.id == reviewer_id and capability == "recommendation_reviewer",
    )
    _login(client, reviewer_id)

    response = client.post(
        f"/api/v1/admin/recommendation_rule_sets/{active_id}/preview",
        json={
            "scenario": "personalized",
            "synthetic_profile": profile,
            "competition_ids": [competition_id],
        },
    )

    assert response.status_code == 200
    codes = response.get_json()["data"]["results"][0]["reason_codes"]
    stale_code = {
        "major": "major_match",
        "grade": "grade_match",
        "deadline": "deadline_urgency",
        "tag": "interest_match",
    }[stale_fact]
    assert expected_current_code in codes
    assert stale_code not in codes


def test_preview_switches_atomically_to_replacement_revision_facts(
    client,
    app,
    monkeypatch,
) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        reviewer = _create_admin("replacement-preview@example.edu", "Preview Reviewer")
        profile = _controlled_profile(app)
        competition = _public_competition_with_revision(
            401,
            reviewer,
            current_majors=[profile["major"]],
            current_grades=["not-current"],
            current_tags=[],
            current_deadline=None,
        )
        historical_revision_id = competition.published_revision_id
        replacement = CompetitionRevision(
            competition=competition,
            revision_number=2,
            revision_status=CompetitionRevisionStatus.APPROVED,
            title="Replacement facts",
            source_name="School Notice",
            source_url="https://example.edu/replacement",
            participant_forms=["individual"],
            major_scope="selected",
            grade_scope="selected",
            suitable_majors=["not-current"],
            suitable_grades=[profile["grade"]],
            created_by_id=reviewer.id,
            published_at=datetime.now(UTC),
        )
        db.session.add(replacement)
        db.session.flush()
        active_id = active.id
        reviewer_id = reviewer.id
        competition_id = competition.id
        replacement_id = replacement.id
        db.session.commit()
    monkeypatch.setattr(
        "competehub_api.blueprints.recommendation_rule_sets.user_has_capability",
        lambda user, capability: user.id == reviewer_id and capability == "recommendation_reviewer",
    )
    _login(client, reviewer_id)

    before = client.post(
        f"/api/v1/admin/recommendation_rule_sets/{active_id}/preview",
        json={
            "scenario": "personalized",
            "synthetic_profile": profile,
            "competition_ids": [competition_id],
        },
    )
    with app.app_context():
        competition = db.session.get(Competition, competition_id)
        assert competition.published_revision_id == historical_revision_id
        competition.published_revision_id = replacement_id
        db.session.commit()
    after = client.post(
        f"/api/v1/admin/recommendation_rule_sets/{active_id}/preview",
        json={
            "scenario": "personalized",
            "synthetic_profile": profile,
            "competition_ids": [competition_id],
        },
    )

    assert before.get_json()["data"]["results"][0]["reason_codes"] == ["major_match"]
    assert after.get_json()["data"]["results"][0]["reason_codes"] == ["grade_match"]


def test_preview_reports_published_competition_without_current_revision_as_not_recommendable(
    client,
    app,
    monkeypatch,
) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        reviewer = _create_admin("missing-pointer@example.edu", "Preview Reviewer")
        profile = _controlled_profile(app)
        competition = Competition(
            id=450,
            title="Broken public pointer",
            source_name="School Notice",
            source_url="https://example.edu/broken",
            status=CompetitionStatus.PUBLISHED,
        )
        db.session.add(competition)
        db.session.commit()
        active_id = active.id
        reviewer_id = reviewer.id
    monkeypatch.setattr(
        "competehub_api.blueprints.recommendation_rule_sets.user_has_capability",
        lambda user, capability: user.id == reviewer_id and capability == "recommendation_reviewer",
    )
    _login(client, reviewer_id)

    response = client.post(
        f"/api/v1/admin/recommendation_rule_sets/{active_id}/preview",
        json={"scenario": "personalized", "synthetic_profile": profile, "competition_ids": [450]},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["not_recommendable"] == [450]


@pytest.mark.parametrize(
    "profile_mutation",
    [
        {"college": "unknown-college"},
        {"major": "major-from-another-college"},
        {"grade": "unknown-grade"},
        {"interest_tags": ["unknown-interest"]},
        {"interest_tags": ["duplicate", "duplicate"]},
        {"interest_tags": [f"tag-{index}" for index in range(11)]},
        {"user_id": 999},
    ],
)
def test_preview_rejects_synthetic_profiles_outside_the_shared_controlled_dictionary(
    client,
    app,
    monkeypatch,
    profile_mutation: dict,
) -> None:
    with app.app_context():
        active = seed_initial_recommendation_rule_set()
        reviewer = _create_admin("profile-validation@example.edu", "Preview Reviewer")
        profile = _controlled_profile(app)
        if profile_mutation.get("major") == "major-from-another-college":
            colleges = list(app.config["PROFILE_ALLOWED_MAJORS_BY_COLLEGE"].items())
            if len(colleges) < 2:
                pytest.skip("profile dictionary needs two colleges for mismatch coverage")
            profile_mutation = {"major": colleges[1][1][0]}
        competition = _public_competition_with_revision(
            460,
            reviewer,
            current_majors=[profile["major"]],
            current_grades=[profile["grade"]],
            current_tags=[profile["interest_tags"][0]],
            current_deadline=None,
        )
        profile.update(profile_mutation)
        active_id = active.id
        reviewer_id = reviewer.id
        competition_id = competition.id
    monkeypatch.setattr(
        "competehub_api.blueprints.recommendation_rule_sets.user_has_capability",
        lambda user, capability: user.id == reviewer_id and capability == "recommendation_reviewer",
    )
    _login(client, reviewer_id)

    response = client.post(
        f"/api/v1/admin/recommendation_rule_sets/{active_id}/preview",
        json={
            "scenario": "personalized",
            "synthetic_profile": profile,
            "competition_ids": [competition_id],
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def _controlled_profile(app) -> dict:
    college, majors = next(iter(app.config["PROFILE_ALLOWED_MAJORS_BY_COLLEGE"].items()))
    return {
        "college": college,
        "major": majors[0],
        "grade": app.config["PROFILE_ALLOWED_GRADES"][0],
        "interest_tags": [app.config["PROFILE_ALLOWED_INTEREST_TAGS"][0]],
    }


def _public_competition_with_revision(
    competition_id: int,
    creator: User,
    *,
    current_majors: list[str],
    current_grades: list[str],
    current_tags: list[str],
    current_deadline: datetime | None,
    legacy_profile: dict | None = None,
    legacy_deadline: datetime | None = None,
) -> Competition:
    competition = Competition(
        id=competition_id,
        title=f"Preview fixture {competition_id}",
        source_name="School Notice",
        source_url=f"https://example.edu/{competition_id}",
        status=CompetitionStatus.PUBLISHED,
        suitable_majors=[legacy_profile["major"]] if legacy_profile else [],
        suitable_grades=[legacy_profile["grade"]] if legacy_profile else [],
    )
    db.session.add(competition)
    db.session.flush()
    if legacy_deadline is not None:
        db.session.add(
            CompetitionTimeNode(
                competition=competition,
                node_type="registration_deadline",
                due_at=legacy_deadline,
                occurs_at=legacy_deadline,
                prominence="primary",
            )
        )
    if legacy_profile is not None:
        legacy_tag = CompetitionTag(
            code=f"legacy-{competition_id}",
            name=legacy_profile["interest_tags"][0],
            tag_type="topic",
        )
        db.session.add(legacy_tag)
        db.session.flush()
        db.session.add(CompetitionTagLink(competition=competition, tag_id=legacy_tag.id))
    revision = CompetitionRevision(
        competition=competition,
        revision_number=1,
        revision_status=CompetitionRevisionStatus.APPROVED,
        title=competition.title,
        source_name=competition.source_name,
        source_url=competition.source_url,
        participant_forms=["individual"],
        major_scope="selected",
        grade_scope="selected",
        suitable_majors=current_majors,
        suitable_grades=current_grades,
        created_by_id=creator.id,
        published_at=datetime.now(UTC),
    )
    db.session.add(revision)
    db.session.flush()
    if current_deadline is not None:
        db.session.add(
            CompetitionTimeNode(
                revision=revision,
                node_type="registration_deadline",
                logical_node_key=f"deadline-{competition_id}",
                due_at=current_deadline,
                occurs_at=current_deadline,
                prominence="primary",
            )
        )
    for index, tag_name in enumerate(current_tags):
        tag = CompetitionTag(
            code=f"current-{competition_id}-{index}",
            name=tag_name,
            tag_type="topic",
        )
        db.session.add(tag)
        db.session.flush()
        db.session.add(CompetitionTagLink(revision=revision, tag_id=tag.id))
    competition.published_revision_id = revision.id
    db.session.commit()
    return competition


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
    with client.application.app_context():
        user = db.session.get(User, user_id)
    with client.session_transaction() as session:
        start_session(session, user)


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
