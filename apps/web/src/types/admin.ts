export interface CompetitionSeries {
  id: number
  canonical_name: string
}

export interface RevisionDifference {
  field: string
  before: unknown
  after: unknown
}

export interface CompetitionRevision {
  id: number
  competition_id: number
  revision_number: number
  revision_status: 'draft' | 'pending_review' | 'approved' | 'rejected' | 'returned'
  title: string
  source_name: string
  source_url: string
  submitted_by_id: number | null
  differences: RevisionDifference[]
  impact: Record<string, unknown>
  published_revision_id: number | null
}

export interface EditionWorkspace {
  id: number
  series_id: number
  edition_label: string
  lifecycle_status: 'unpublished' | 'published'
  published_revision_id: number | null
  revision: CompetitionRevision
  active_revision: CompetitionRevision
}

export interface EditionDraftInput {
  series_id: number
  edition_label: string
  title: string
  category: string
  organizer: string
  source_name: string
  source_url: string
  official_url?: string
  summary: string
  eligibility: string
  participant_forms: string[]
  team_size?: string
  suitable_majors: string[]
  suitable_grades: string[]
  stages: Array<{
    stage_key: string
    stage_type: string
    label: string
    order: number
    time_nodes: Array<{
      logical_node_key: string
      node_type: string
      occurs_at: string
      description: string
      prominence: 'primary' | 'secondary'
    }>
  }>
}
