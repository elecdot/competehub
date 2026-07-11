export interface CompetitionSeries {
  id: number
  canonical_name: string
}

export interface RevisionDifference {
  kind: 'field' | 'stage' | 'time_node'
  change?: 'added' | 'removed' | 'changed'
  field?: string
  stage_key?: string
  logical_node_key?: string
  before: unknown
  after: unknown
}

export interface RevisionTimeNodeInput {
  logical_node_key: string
  node_type: string
  occurs_at: string
  description: string
  prominence: 'primary' | 'secondary'
  prominence_override_reason?: string
}

export interface RevisionStageInput {
  stage_key: string
  stage_type: string
  label: string
  order: number
  time_nodes: RevisionTimeNodeInput[]
}

export interface RevisionTagInput {
  code: string
  name: string
  tag_type: string
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
  comparison: {
    field_changes: RevisionDifference[]
    stage_changes: RevisionDifference[]
    time_node_changes: RevisionDifference[]
  }
  completeness: {
    is_complete: boolean
    missing_fields: string[]
    warnings: Array<Record<string, string>>
  }
  impact: Record<string, unknown>
  published_revision_id: number | null
  registration_applicability: 'applicable' | 'not_applicable' | 'unknown' | null
  participant_forms: string[]
  major_scope: 'all' | 'selected' | 'unknown' | null
  grade_scope: 'all' | 'selected' | 'unknown' | null
  suitable_majors: string[] | null
  suitable_grades: string[] | null
  stages: RevisionStageInput[]
  tags: RevisionTagInput[]
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
  registration_applicability?: 'applicable' | 'not_applicable' | 'unknown'
  participant_forms: string[]
  team_size?: string
  major_scope?: 'all' | 'selected' | 'unknown'
  grade_scope?: 'all' | 'selected' | 'unknown'
  suitable_majors: string[]
  suitable_grades: string[]
  stages: RevisionStageInput[]
  tags: RevisionTagInput[]
}

export type RevisionDraftUpdate = Omit<
  EditionDraftInput,
  'series_id' | 'edition_label' | 'official_url' | 'team_size'
> & {
  official_url: string | null
  team_size: string | null
}
