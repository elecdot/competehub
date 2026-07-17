export type ParticipantForm = 'individual' | 'team'
export type RegistrationStatus = 'open' | 'upcoming' | 'closed' | 'unknown' | 'not_applicable'
export type CompetitionLifecycleStatus =
  | 'published'
  | 'cancelled'
  | 'archived'
  | 'expired'
export type DiscoverySort = 'actionable' | 'registration_deadline' | 'published_at'

export interface CompetitionSummary {
  id: number
  revision_id?: number | null
  title: string
  short_title?: string | null
  category?: string | null
  organizer?: string | null
  status: CompetitionLifecycleStatus
  registration_status: RegistrationStatus
  registration_status_basis?: CompetitionTimeNode | null
  source_name: string
  source_url: string
  official_url?: string | null
  content_updated_at?: string | null
  tags: string[]
  participant_forms: ParticipantForm[]
  suitable_majors: string[]
  suitable_grades: string[]
  major_scope?: 'all' | 'selected' | 'unknown' | null
  grade_scope?: 'all' | 'selected' | 'unknown' | null
  value_notes?: string | null
  next_node?: CompetitionTimeNode | null
  is_favorited: boolean
  is_subscribed: boolean
}

export interface CompetitionTimeNode {
  id: number
  logical_node_key?: string | null
  node_revision?: number
  node_type: string
  occurs_at?: string | null
  prominence?: 'primary' | 'secondary'
  stage_id?: number | null
  snapshot_id?: number
  stage_label?: string | null
  stage_order?: number | null
  stage_type?: string | null
  starts_at?: string | null
  due_at?: string | null
  description?: string | null
}

export interface CompetitionDetail extends CompetitionSummary {
  edition_label?: string | null
  current_revision?: {
    id: number
    revision_number: number
  } | null
  lifecycle_warning: {
    status: Exclude<CompetitionLifecycleStatus, 'published'>
    reason: string
    changed_at: string
  } | null
  host?: string | null
  attachment_url?: string | null
  summary?: string | null
  detail?: string | null
  eligibility?: string | null
  team_size?: string | null
  registration_applicability?: 'applicable' | 'not_applicable' | 'unknown' | null
  time_nodes: CompetitionTimeNode[]
  subscription_summary: SubscriptionSummary | null
}

export type SubscriptionNodeType =
  | 'registration_deadline'
  | 'submission_deadline'
  | 'competition_start'

export interface SubscriptionConsent {
  reminder_enabled: boolean
  remind_days: number
  node_types: SubscriptionNodeType[]
}

export interface FavoriteState {
  is_favorited: boolean
}

export interface SubscriptionSummary extends SubscriptionConsent {
  competition_id: number
  status: 'active' | 'cancelled'
  is_subscribed: boolean
  reminder_confirmed_at?: string | null
  scheduled_reminder_count?: number
  next_reminder_at?: string | null
  unscheduled_reason?: string | null
}

export interface SubscriptionCancellation {
  competition_id: number
  status: 'cancelled'
  is_subscribed: false
}

export interface Pagination {
  page: number
  page_size: number
  total: number
}

export interface CompetitionListPayload {
  items: CompetitionSummary[]
  pagination: Pagination
}

export interface CompetitionFilterOptions {
  categories: string[]
  majors: string[]
  grades: string[]
  tags: string[]
}

export interface ApiEnvelope<T> {
  data: T
  error: null
}
