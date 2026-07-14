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
  created_by: GovernanceActor | null
  submitted_by: GovernanceActor | null
  reviewed_by: GovernanceActor | null
  created_at: string
  submitted_at: string | null
  decided_at: string | null
  activated_at: string | null
  retired_at: string | null
  review_comment: string | null
  terminal_review_status: "approved" | "rejected" | "returned" | null
  cloned_from_rule_set_id: number | null
  cloned_from_version: number | null
  base_rule_set_id: number | null
  base_version: number | null
  active_rule_set_id: number | null
  active_version: number | null
  is_stale: boolean
  difference_snapshot: RecommendationDifferenceSnapshot | null
  impact_summary: RecommendationImpactSummary | null
  rules: RecommendationRule[]
}

export interface RecommendationRuleChange {
  code: RecommendationRuleCode
  changes: Record<string, { before: unknown; after: unknown }>
}

export interface RecommendationDifferenceSnapshot {
  base_rule_set_id: number
  base_version: number
  candidate_rule_set_id: number
  candidate_version: number
  added_rules: RecommendationRule[]
  removed_rules: RecommendationRule[]
  changed_rules: RecommendationRuleChange[]
  unchanged_rule_count: number
}

export interface RecommendationImpactSummary {
  activation_effect: string
  base_version: number
  current_active_version: number | null
  candidate_version: number
  is_stale: boolean
  enabled_rule_count_before: number
  enabled_rule_count_after: number
  added_rule_count: number
  removed_rule_count: number
  changed_rule_count: number
  ordering_may_change: boolean
  reasons_may_change: boolean
  active_behavior_unchanged_until_activation: boolean
  real_profile_evaluation_performed: false
}

export interface GovernanceActor {
  id: number
  display_name: string | null
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
  competition: {
    id: number
    title: string
    edition_label: string | null
  }
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
