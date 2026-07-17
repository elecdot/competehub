<script setup lang="ts">
import {
  CheckOutlined,
  ClockCircleOutlined,
  LinkOutlined,
  ReloadOutlined,
} from '@ant-design/icons-vue'
import {
  Alert as AAlert,
  Button as AButton,
  Empty as AEmpty,
  Pagination as APagination,
  Result as AResult,
  Select as ASelect,
  Skeleton as ASkeleton,
  TabPane as ATabPane,
  Tabs as ATabs,
  Tag as ATag,
} from 'ant-design-vue'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth_store'
import { useNotificationStore } from '@/stores/notification_store'
import type { MessageType } from '@/types/notification'
import { formatNodeLabel } from '@/utils/competition'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const notifications = useNotificationStore()
const initializing = ref(true)
const accessDenied = ref(false)

const messageTypeOptions: Array<{ value: MessageType | ''; label: string }> = [
  { value: '', label: '全部类型' },
  { value: 'reminder_due', label: '节点提醒' },
  { value: 'competition_time_changed', label: '赛事时间变更' },
  { value: 'competition_cancelled', label: '赛事取消' },
  { value: 'competition_offline', label: '赛事紧急下架' },
]
const messageTypeLabels: Record<MessageType, string> = {
  reminder_due: '节点提醒',
  competition_time_changed: '赛事时间变更',
  competition_cancelled: '赛事取消',
  competition_offline: '赛事紧急下架',
}
const formattedTotal = computed(() =>
  new Intl.NumberFormat('zh-CN').format(notifications.total),
)

function changeReadStatus(value: string | number) {
  notifications.readStatus = value === 'unread' ? 'unread' : 'all'
  notifications.page = 1
  void applyFiltersToRoute()
}

function changeMessageType(value: unknown) {
  notifications.messageType =
    messageTypeOptions.find((option) => option.value === value)?.value ?? ''
  notifications.page = 1
  void applyFiltersToRoute()
}

function changePage(page: number) {
  notifications.page = page
  void applyFiltersToRoute()
}

async function applyFiltersToRoute() {
  const query = notifications.toRouteQuery()
  const target = router.resolve({ name: 'messages', query })
  if (target.fullPath === route.fullPath) {
    await refreshMessages()
    return
  }
  await router.push({ name: 'messages', query })
}

async function initializeAndLoad() {
  const returnTo = route.fullPath
  if (!auth.initialized) initializing.value = true
  await auth.ensureCurrentUser()

  if (await redirectIfSessionEnded(returnTo)) return
  const currentUser = auth.currentUser
  if (!currentUser) {
    await redirectIfSessionEnded(returnTo)
    return
  }

  accessDenied.value = currentUser.role !== 'student'
  initializing.value = false
  if (accessDenied.value) return
  await refreshMessages()
}

async function refreshMessages() {
  if (route.name !== 'messages' || auth.currentUser?.role !== 'student') return
  const returnTo = route.fullPath
  await Promise.all([notifications.loadMessages(), notifications.loadUnreadCount()])
  if (await redirectIfSessionEnded(returnTo)) return
  if (route.name !== 'messages' || auth.currentUser?.role !== 'student') return
  if (!notifications.listError) await correctEmptyPage()
}

async function redirectIfSessionEnded(returnTo: string) {
  if (auth.currentUser) return false
  initializing.value = false
  accessDenied.value = false
  if (route.name === 'messages') {
    await router.replace({
      name: 'personal-info',
      query: { return_to: returnTo },
    })
  }
  return true
}

async function correctEmptyPage() {
  if (route.name !== 'messages') return
  const lastPage = Math.max(1, Math.ceil(notifications.total / notifications.pageSize))
  if (notifications.page <= lastPage) return
  notifications.page = lastPage
  await router.replace({ name: 'messages', query: notifications.toRouteQuery() })
}

async function readMessage(messageId: number) {
  const returnTo = route.fullPath
  try {
    await notifications.markRead(messageId)
    if (await redirectIfSessionEnded(returnTo)) return
    await notifications.loadMessages()
    if (await redirectIfSessionEnded(returnTo)) return
    if (!notifications.listError) await correctEmptyPage()
  } catch {
    await redirectIfSessionEnded(returnTo)
    // The store exposes a user-facing mutation error and keeps the snapshot intact.
  }
}

async function readAllMessages() {
  const returnTo = route.fullPath
  try {
    await notifications.markAllRead()
    if (await redirectIfSessionEnded(returnTo)) return
    await notifications.loadMessages()
    if (await redirectIfSessionEnded(returnTo)) return
    if (!notifications.listError) await correctEmptyPage()
  } catch {
    await redirectIfSessionEnded(returnTo)
    // The store exposes a user-facing mutation error and keeps the list retryable.
  }
}

function formatMessageTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '时间未知'
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Shanghai',
  }).format(date)
}

function handleWindowFocus() {
  void refreshMessages()
}

watch(
  () => route.query,
  async (query) => {
    if (route.name !== 'messages') return
    notifications.replaceFromRouteQuery(query)
    const canonicalRoute = router.resolve({
      name: 'messages',
      query: notifications.toRouteQuery(),
    })
    if (canonicalRoute.fullPath !== route.fullPath) {
      await router.replace({ name: 'messages', query: notifications.toRouteQuery() })
      return
    }
    await initializeAndLoad()
  },
  { immediate: true },
)

onMounted(() => window.addEventListener('focus', handleWindowFocus))
onUnmounted(() => window.removeEventListener('focus', handleWindowFocus))
</script>

<template>
  <section class="message-center-page">
    <div class="page-heading">
      <div>
        <h1 class="page-title">消息中心</h1>
        <p class="page-description">查看节点提醒和已订阅赛事的重要变更。</p>
      </div>
      <AButton
        v-if="!initializing && !accessDenied"
        data-testid="mark-all-read"
        :disabled="notifications.unreadCount === 0 || notifications.mutationLoading"
        :loading="notifications.mutationLoading"
        @click="readAllMessages"
      >
        <template #icon><CheckOutlined aria-hidden="true" /></template>
        全部标为已读
      </AButton>
    </div>

    <div v-if="initializing" class="state-panel" role="status" aria-live="polite">
      <span class="sr-only">正在加载消息中心…</span>
      <ASkeleton aria-hidden="true" active :paragraph="{ rows: 5 }" />
    </div>

    <AResult
      v-else-if="accessDenied"
      class="state-panel"
      status="403"
      title="仅学生账号可查看消息"
      sub-title="当前账号没有个人赛事消息中心。"
    />

    <template v-else>
      <div class="message-toolbar">
        <ATabs
          :active-key="notifications.readStatus"
          aria-label="消息已读筛选"
          @change="changeReadStatus"
        >
          <ATabPane key="all" tab="全部" />
          <ATabPane key="unread" tab="未读" />
        </ATabs>
        <label for="message-type-filter">
          消息类型
          <ASelect
            id="message-type-filter"
            data-testid="message-type-filter"
            :value="notifications.messageType"
            :options="messageTypeOptions"
            aria-label="消息类型"
            autocomplete="off"
            @change="changeMessageType"
          />
        </label>
      </div>

      <AAlert
        v-if="notifications.mutationError"
        type="error"
        show-icon
        :message="notifications.mutationError"
      />

      <div v-if="notifications.listLoading" class="state-panel" role="status" aria-live="polite">
        <span class="sr-only">正在加载消息…</span>
        <ASkeleton aria-hidden="true" active :paragraph="{ rows: 5 }" />
      </div>

      <AResult
        v-else-if="notifications.listError"
        class="state-panel"
        role="alert"
        status="error"
        title="消息加载失败"
        :sub-title="notifications.listError"
      >
        <template #extra>
          <AButton type="primary" @click="refreshMessages">
            <template #icon><ReloadOutlined aria-hidden="true" /></template>
            重新加载
          </AButton>
        </template>
      </AResult>

      <AEmpty
        v-else-if="notifications.items.length === 0"
        data-testid="message-empty"
        class="state-panel"
        :description="notifications.readStatus === 'unread' ? '没有未读消息' : '暂无消息'"
        role="status"
      />

      <template v-else>
        <p class="message-result-count" aria-live="polite">共 {{ formattedTotal }} 条消息</p>
        <ul data-testid="message-list" class="message-list">
          <li
            v-for="message in notifications.items"
            :id="`message-${message.id}`"
            :key="message.id"
            data-testid="message-item"
            :class="{ unread: !message.is_read }"
          >
            <article :data-testid="`message-item-${message.id}`" class="message-entry">
              <div class="message-entry-main">
                <div class="message-meta">
                  <ATag :color="message.is_read ? 'default' : 'green'">
                    {{ message.is_read ? '已读' : '未读' }}
                  </ATag>
                  <span>{{ messageTypeLabels[message.message_type] }}</span>
                  <span class="message-time">
                    <ClockCircleOutlined aria-hidden="true" />
                    {{ formatMessageTime(message.event_occurred_at) }}
                  </span>
                </div>
                <h2>{{ message.title_snapshot }}</h2>
                <p v-if="message.body_snapshot" class="message-body">
                  {{ message.body_snapshot }}
                </p>
                <dl class="message-target-snapshot">
                  <div>
                    <dt>赛事</dt>
                    <dd>{{ message.target_snapshot.competition_title }}</dd>
                  </div>
                  <div v-if="message.target_snapshot.node_type">
                    <dt>节点</dt>
                    <dd>
                      {{ formatNodeLabel(message.target_snapshot.node_type) }}
                      <template v-if="message.target_snapshot.node_occurs_at">
                        · {{ formatMessageTime(message.target_snapshot.node_occurs_at) }}
                      </template>
                    </dd>
                  </div>
                  <div v-if="message.target_snapshot.reason_summary">
                    <dt>原因</dt>
                    <dd>{{ message.target_snapshot.reason_summary }}</dd>
                  </div>
                </dl>
              </div>

              <div class="message-entry-actions">
                <RouterLink
                  v-if="message.target_available && message.target_url"
                  class="message-target-link"
                  :to="message.target_url"
                >
                  <LinkOutlined aria-hidden="true" />
                  查看赛事
                </RouterLink>
                <span v-else class="message-target-unavailable">赛事当前不可访问</span>
                <AButton
                  v-if="!message.is_read"
                  :loading="notifications.mutationLoading"
                  :disabled="notifications.mutationLoading"
                  :aria-label="`将“${message.title_snapshot}”标为已读`"
                  @click="readMessage(message.id)"
                >
                  标为已读
                </AButton>
              </div>
            </article>
          </li>
        </ul>

        <APagination
          v-if="notifications.total > notifications.pageSize"
          data-testid="message-pagination"
          class="message-pagination"
          :current="notifications.page"
          :page-size="notifications.pageSize"
          :total="notifications.total"
          :show-size-changer="false"
          show-less-items
          @change="changePage"
        />
      </template>
    </template>
  </section>
</template>
