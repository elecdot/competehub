import type { ApiEnvelope } from "@/types/competition"

export type RecommendationRuleSetStatus =
  | "draft"
  | "pending_review"
  | "active"
  | "rejected"
  | "returned"
  | "retired"

export type RecommendationRuleCode =
  | "major_match"
  | "grade_match"
  | "interest_match"
  | "deadline_urgency"
  | "general_fallback"

export type RecommendationRuleConditions =
  | { operator: "overlap" }
  | { operator: "within_days"; min_days: 0; max_days: number }
  | { operator: "always" }

export interface RecommendationRule {
  code: RecommendationRuleCode
  name: string
  weight: number
  conditions: RecommendationRuleConditions
  reason_template: string
  enabled: boolean
}

export interface RecommendationRuleSetSummary {
  rule_set_id: number
  version: number
  status: RecommendationRuleSetStatus
  created_by: { id: number; display_name: string | null } | null
  cloned_from_rule_set_id: number | null
  cloned_from_version: number | null
  base_rule_set_id: number | null
  base_version: number | null
  active_rule_set_id: number | null
  active_version: number | null
  is_stale: boolean
  difference_snapshot: Record<string, unknown> | null
  impact_summary: Record<string, unknown> | null
  rules: RecommendationRule[]
}

export interface RecommendationRuleSetListPayload {
  items: RecommendationRuleSetSummary[]
}

export interface SyntheticProfile {
  college: string
  major: string
  grade: string
  interest_tags: string[]
}

export interface RecommendationPreviewRequest {
  scenario: "personalized" | "general"
  synthetic_profile?: SyntheticProfile
  competition_ids: number[]
}

export interface RecommendationPreviewResult {
  position: number
  competition_id: number
  matched_rule_codes: RecommendationRuleCode[]
  reason_codes: RecommendationRuleCode[]
  reasons: string[]
}

export interface RecommendationPreviewPayload {
  rule_set_id: number
  version: number
  scenario: "personalized" | "general"
  fixture_ids: number[]
  results: RecommendationPreviewResult[]
}

export type RecommendationRuleSetEnvelope<T> = ApiEnvelope<T>
