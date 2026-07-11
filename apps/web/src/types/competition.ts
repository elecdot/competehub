export type ParticipantForm = 'individual' | 'team'

export interface CompetitionSummary {
  id: number
  revision_id?: number | null
  title: string
  short_title?: string | null
  category?: string | null
  organizer?: string | null
  status: 'published'
  source_name: string
  source_url: string
  official_url?: string | null
  tags: string[]
  suitable_majors: string[]
  suitable_grades: string[]
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
  starts_at?: string | null
  due_at?: string | null
  description?: string | null
}

export interface CompetitionDetail extends CompetitionSummary {
  host?: string | null
  attachment_url?: string | null
  summary?: string | null
  detail?: string | null
  eligibility?: string | null
  team_size?: string | null
  participant_form?: ParticipantForm | null
  time_nodes: CompetitionTimeNode[]
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

export interface ApiEnvelope<T> {
  data: T
  error: null
}
