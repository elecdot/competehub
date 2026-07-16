export type CalendarView = 'month' | 'week' | 'list'

export interface CalendarRange {
  from: string
  to: string
  time_zone: 'Asia/Shanghai'
  view: CalendarView
}

export interface CalendarItem {
  competition_id: number
  competition_title: string
  detail_url: string | null
  lifecycle_status: string
  target_available: boolean
  stage_id: number | null
  stage_label: string | null
  stage_order: number | null
  stage_type: string | null
  is_current_stage: boolean
  node_snapshot_id: number
  logical_node_key: string | null
  node_revision: number
  node_type: string
  description: string | null
  occurs_at: string
  prominence: 'primary' | 'secondary'
  pair_kind: 'registration' | 'competition' | null
  pair_role: 'start' | 'deadline' | 'end' | null
}

export interface CalendarPayload {
  range: CalendarRange
  items: CalendarItem[]
}

export interface CalendarQuery {
  from: string
  to: string
  view: CalendarView
}
