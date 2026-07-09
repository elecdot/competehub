export interface CompetitionSummary {
  id: number
  title: string
  short_title?: string | null
  category?: string | null
  organizer?: string | null
  status: string
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
  node_type: string
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
  participant_form?: string | null
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
