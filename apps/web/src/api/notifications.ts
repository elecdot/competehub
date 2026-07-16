import { apiClient } from '@/api/client'
import type { ApiEnvelope } from '@/types/competition'
import type {
  MessageListPayload,
  MessageReadStatus,
  MessageType,
  ReadAllMessagesPayload,
  ReadMessagePayload,
  UnreadCountPayload,
} from '@/types/notification'

export interface MessageListParams {
  page?: number
  page_size?: number
  read_status?: MessageReadStatus
  message_type?: MessageType
}

export async function fetchMessages(params: MessageListParams = {}) {
  const response = await apiClient.get<ApiEnvelope<MessageListPayload>>('/me/messages', { params })
  return response.data.data
}

export async function fetchUnreadMessageCount() {
  const response = await apiClient.get<ApiEnvelope<UnreadCountPayload>>(
    '/me/messages/unread_count',
  )
  return response.data.data
}

export async function markMessageRead(messageId: number) {
  const response = await apiClient.post<ApiEnvelope<ReadMessagePayload>>(
    `/me/messages/${messageId}/read`,
  )
  return response.data.data
}

export async function markAllMessagesRead() {
  const response = await apiClient.post<ApiEnvelope<ReadAllMessagesPayload>>(
    '/me/messages/read_all',
  )
  return response.data.data
}
