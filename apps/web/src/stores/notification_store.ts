import { isAxiosError } from 'axios'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { LocationQuery, LocationQueryRaw } from 'vue-router'

import {
  fetchMessages,
  fetchUnreadMessageCount,
  markAllMessagesRead,
  markMessageRead,
  type MessageListParams,
} from '@/api/notifications'
import type {
  InAppMessage,
  MessageReadStatus,
  MessageType,
} from '@/types/notification'
import { useAuthStore } from '@/stores/auth_store'

const DEFAULT_PAGE_SIZE = 20
const MESSAGE_TYPES = new Set<MessageType>([
  'reminder_due',
  'competition_time_changed',
  'competition_cancelled',
  'competition_offline',
])

interface UnreadCountRequest {
  sessionGeneration: number
  request: ReturnType<typeof fetchUnreadMessageCount>
}

function queryValue(query: LocationQuery, key: string): string {
  const value = query[key]
  return (Array.isArray(value) ? value[0] : value) ?? ''
}

function positiveInteger(value: string, fallback: number, maximum?: number): number {
  if (!/^\d+$/.test(value)) return fallback
  const parsed = Number(value)
  if (parsed < 1 || (maximum !== undefined && parsed > maximum)) return fallback
  return parsed
}

function parseReadStatus(value: string): MessageReadStatus {
  return value === 'unread' ? 'unread' : 'all'
}

function parseMessageType(value: string): MessageType | '' {
  return MESSAGE_TYPES.has(value as MessageType) ? (value as MessageType) : ''
}

export const useNotificationStore = defineStore('notification', () => {
  const auth = useAuthStore()
  const items = ref<InAppMessage[]>([])
  const readStatus = ref<MessageReadStatus>('all')
  const messageType = ref<MessageType | ''>('')
  const page = ref(1)
  const pageSize = ref(DEFAULT_PAGE_SIZE)
  const total = ref(0)
  const listLoading = ref(false)
  const listError = ref('')
  const unreadCount = ref(0)
  const countLoading = ref(false)
  const mutationLoading = ref(false)
  const mutationError = ref('')

  let listRequestSequence = 0
  let countRequestGeneration = 0
  let mutationRequestSequence = 0
  let unreadCountRequest: UnreadCountRequest | null = null

  function replaceFromRouteQuery(query: LocationQuery) {
    readStatus.value = parseReadStatus(queryValue(query, 'read_status'))
    messageType.value = parseMessageType(queryValue(query, 'message_type'))
    page.value = positiveInteger(queryValue(query, 'page'), 1)
    pageSize.value = positiveInteger(
      queryValue(query, 'page_size'),
      DEFAULT_PAGE_SIZE,
      100,
    )
  }

  function toRouteQuery(): LocationQueryRaw {
    const query: LocationQueryRaw = {}
    if (readStatus.value === 'unread') query.read_status = readStatus.value
    if (messageType.value) query.message_type = messageType.value
    if (page.value > 1) query.page = String(page.value)
    if (pageSize.value !== DEFAULT_PAGE_SIZE) query.page_size = String(pageSize.value)
    return query
  }

  function toQueryParams(): MessageListParams {
    return {
      page: page.value,
      page_size: pageSize.value,
      read_status: readStatus.value,
      message_type: messageType.value || undefined,
    }
  }

  async function loadMessages() {
    const requestId = ++listRequestSequence
    const sessionGeneration = auth.sessionGeneration
    listLoading.value = true
    listError.value = ''
    try {
      const payload = await fetchMessages(toQueryParams())
      if (
        requestId !== listRequestSequence ||
        sessionGeneration !== auth.sessionGeneration
      ) {
        return
      }
      items.value = payload.items
      page.value = payload.pagination.page
      pageSize.value = payload.pagination.page_size
      total.value = payload.pagination.total
    } catch (error) {
      if (
        requestId !== listRequestSequence ||
        sessionGeneration !== auth.sessionGeneration
      ) {
        return
      }
      if (clearExpiredSession(error, sessionGeneration)) return
      items.value = []
      total.value = 0
      listError.value = '消息暂时无法加载，请稍后再试。'
    } finally {
      if (
        requestId === listRequestSequence &&
        sessionGeneration === auth.sessionGeneration
      ) {
        listLoading.value = false
      }
    }
  }

  async function loadUnreadCount() {
    const generation = countRequestGeneration
    const sessionGeneration = auth.sessionGeneration
    const requestState =
      unreadCountRequest?.sessionGeneration === sessionGeneration
        ? unreadCountRequest
        : {
            sessionGeneration,
            request: fetchUnreadMessageCount(),
          }
    unreadCountRequest = requestState
    countLoading.value = true
    try {
      const payload = await requestState.request
      if (
        generation === countRequestGeneration &&
        sessionGeneration === auth.sessionGeneration
      ) {
        unreadCount.value = payload.unread_count
      }
    } catch (error) {
      if (
        generation !== countRequestGeneration ||
        sessionGeneration !== auth.sessionGeneration
      ) {
        return
      }
      if (clearExpiredSession(error, sessionGeneration)) return
      // Keep the last confirmed count during a transient refresh failure.
    } finally {
      if (unreadCountRequest === requestState) unreadCountRequest = null
      if (
        generation === countRequestGeneration &&
        sessionGeneration === auth.sessionGeneration
      ) {
        countLoading.value = false
      }
    }
  }

  function invalidateUnreadCountRequests() {
    countRequestGeneration += 1
    unreadCountRequest = null
    countLoading.value = false
  }

  function clearExpiredSession(error: unknown, sessionGeneration: number) {
    if (!isAxiosError(error) || error.response?.status !== 401) return false
    if (sessionGeneration !== auth.sessionGeneration) return true
    clear()
    auth.clearCurrentUser()
    return true
  }

  async function markRead(messageId: number) {
    const requestId = ++mutationRequestSequence
    const sessionGeneration = auth.sessionGeneration
    invalidateUnreadCountRequests()
    mutationLoading.value = true
    mutationError.value = ''
    try {
      const payload = await markMessageRead(messageId)
      if (
        requestId !== mutationRequestSequence ||
        sessionGeneration !== auth.sessionGeneration
      ) {
        return
      }
      invalidateUnreadCountRequests()
      unreadCount.value = payload.unread_count
      const index = items.value.findIndex((message) => message.id === messageId)
      if (index >= 0) items.value[index] = payload.message
    } catch (error) {
      if (sessionGeneration !== auth.sessionGeneration) {
        throw new Error('notification_session_changed')
      }
      if (requestId !== mutationRequestSequence) return
      if (clearExpiredSession(error, sessionGeneration)) {
        throw new Error('notification_session_expired')
      }
      mutationError.value = '消息已读状态更新失败，请重试。'
      throw new Error('message_read_failed')
    } finally {
      if (
        requestId === mutationRequestSequence &&
        sessionGeneration === auth.sessionGeneration
      ) {
        mutationLoading.value = false
      }
    }
  }

  async function markAllRead() {
    const requestId = ++mutationRequestSequence
    const sessionGeneration = auth.sessionGeneration
    invalidateUnreadCountRequests()
    mutationLoading.value = true
    mutationError.value = ''
    try {
      const payload = await markAllMessagesRead()
      if (
        requestId !== mutationRequestSequence ||
        sessionGeneration !== auth.sessionGeneration
      ) {
        return
      }
      invalidateUnreadCountRequests()
      unreadCount.value = payload.unread_count
    } catch (error) {
      if (sessionGeneration !== auth.sessionGeneration) {
        throw new Error('notification_session_changed')
      }
      if (requestId !== mutationRequestSequence) return
      if (clearExpiredSession(error, sessionGeneration)) {
        throw new Error('notification_session_expired')
      }
      mutationError.value = '全部已读操作失败，请重试。'
      throw new Error('messages_read_all_failed')
    } finally {
      if (
        requestId === mutationRequestSequence &&
        sessionGeneration === auth.sessionGeneration
      ) {
        mutationLoading.value = false
      }
    }
  }

  function clearSessionSnapshot() {
    listRequestSequence += 1
    mutationRequestSequence += 1
    invalidateUnreadCountRequests()
    items.value = []
    total.value = 0
    listLoading.value = false
    listError.value = ''
    unreadCount.value = 0
    mutationLoading.value = false
    mutationError.value = ''
  }

  function clear() {
    clearSessionSnapshot()
    readStatus.value = 'all'
    messageType.value = ''
    page.value = 1
    pageSize.value = DEFAULT_PAGE_SIZE
  }

  return {
    items,
    readStatus,
    messageType,
    page,
    pageSize,
    total,
    listLoading,
    listError,
    unreadCount,
    countLoading,
    mutationLoading,
    mutationError,
    replaceFromRouteQuery,
    toRouteQuery,
    toQueryParams,
    loadMessages,
    loadUnreadCount,
    markRead,
    markAllRead,
    clearSessionSnapshot,
    clear,
  }
})
