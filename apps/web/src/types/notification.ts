import type { Pagination } from './competition'

export type MessageType =
  | 'reminder_due'
  | 'competition_time_changed'
  | 'competition_cancelled'
  | 'competition_offline'

export type MessageReadStatus = 'all' | 'unread'

export interface MessageTargetSnapshot {
  competition_id: number
  competition_title: string
  node_type: string | null
  node_occurs_at: string | null
  reason_summary: string | null
}

export interface InAppMessage {
  id: number
  message_type: MessageType
  title_snapshot: string
  body_snapshot: string | null
  target_snapshot: MessageTargetSnapshot
  event_occurred_at: string
  created_at: string
  retained_until: string
  is_read: boolean
  read_at: string | null
  target_available: boolean
  target_url: string | null
}

export interface MessageListPayload {
  items: InAppMessage[]
  pagination: Pagination
}

export interface UnreadCountPayload {
  unread_count: number
}

export interface ReadMessagePayload extends UnreadCountPayload {
  message: InAppMessage
}

export interface ReadAllMessagesPayload extends UnreadCountPayload {
  updated_count: number
}
