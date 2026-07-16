import type { CompetitionSummary } from '@/types/competition'

export type RecommendationMode = 'personalized' | 'general'
export type RecommendationFallbackReason =
  | 'anonymous'
  | 'profile_incomplete'
  | 'no_active_rule_set'

export interface RecommendationItem {
  position: number
  reason_codes: string[]
  reasons: string[]
  competition: CompetitionSummary
}

export interface RecommendationFeed {
  recommendation_mode: RecommendationMode
  profile_status: 'incomplete' | 'recommendation_ready' | null
  missing_fields: string[]
  fallback_reason: RecommendationFallbackReason | null
  rule_set_version: number | null
  items: RecommendationItem[]
}
