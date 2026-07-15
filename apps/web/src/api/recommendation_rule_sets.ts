import { apiClient } from "@/api/client"
import type {
  RecommendationPreviewPayload,
  RecommendationPreviewRequest,
  RecommendationRule,
  RecommendationRuleSetEnvelope,
  RecommendationRuleSetListPayload,
  RecommendationRuleSetSummary,
} from "@/types/recommendation_rule_set"

export async function fetchRecommendationRuleSets() {
  const response = await apiClient.get<
    RecommendationRuleSetEnvelope<RecommendationRuleSetListPayload>
  >("/admin/recommendation_rule_sets")
  return response.data.data
}

export async function createRecommendationRuleSet(sourceRuleSetId: number) {
  const response = await apiClient.post<
    RecommendationRuleSetEnvelope<RecommendationRuleSetSummary>
  >("/admin/recommendation_rule_sets", {
    source_rule_set_id: sourceRuleSetId,
  })
  return response.data.data
}

export async function updateRecommendationRuleSet(ruleSetId: number, rules: RecommendationRule[]) {
  const response = await apiClient.patch<
    RecommendationRuleSetEnvelope<RecommendationRuleSetSummary>
  >(`/admin/recommendation_rule_sets/${ruleSetId}`, {
    rules,
  })
  return response.data.data
}

export async function submitRecommendationRuleSet(ruleSetId: number) {
  const response = await apiClient.post<
    RecommendationRuleSetEnvelope<RecommendationRuleSetSummary>
  >(`/admin/recommendation_rule_sets/${ruleSetId}/submit_review`)
  return response.data.data
}

export async function reviewRecommendationRuleSet(
  ruleSetId: number,
  action: "approve" | "reject" | "return",
  comment: string,
) {
  const response = await apiClient.post<
    RecommendationRuleSetEnvelope<RecommendationRuleSetSummary>
  >(`/admin/recommendation_rule_sets/${ruleSetId}/review`, {
    action,
    comment,
  })
  return response.data.data
}

export async function previewRecommendationRuleSet(
  ruleSetId: number,
  payload: RecommendationPreviewRequest,
) {
  const response = await apiClient.post<
    RecommendationRuleSetEnvelope<RecommendationPreviewPayload>
  >(`/admin/recommendation_rule_sets/${ruleSetId}/preview`, payload)
  return response.data.data
}
