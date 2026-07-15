<script setup lang="ts">
import {
  ExportOutlined,
  LeftOutlined,
  PaperClipOutlined,
  ReloadOutlined,
} from '@ant-design/icons-vue'
import {
  Alert as AAlert,
  Button as AButton,
  Checkbox as ACheckbox,
  CheckboxGroup as ACheckboxGroup,
  Empty as AEmpty,
  Form as AForm,
  FormItem as AFormItem,
  InputNumber as AInputNumber,
  Result as AResult,
  Skeleton as ASkeleton,
  Tag as ATag,
} from 'ant-design-vue'
import { isAxiosError } from 'axios'
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import {
  cancelCompetitionSubscription,
  createCompetitionSubscription,
  favoriteCompetition,
  fetchCompetitionDetail,
  fetchCurrentProfile,
  recordCompetitionOutboundClick,
  unfavoriteCompetition,
  updateCompetitionSubscription,
} from '@/api/client'
import { useAuthStore } from '@/stores/auth_store'
import type {
  CompetitionDetail,
  CompetitionTimeNode,
  SubscriptionConsent,
  SubscriptionNodeType,
  SubscriptionSummary,
} from '@/types/competition'
import {
  formatCompetitionStatus,
  formatNodeDate,
  formatNodeLabel,
  formatParticipantForm,
  formatRegistrationStatus,
} from '@/utils/competition'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const competition = ref<CompetitionDetail | null>(null)
const loading = ref(false)
const errorMessage = ref('')
const notFound = ref(false)
const historical = computed(
  () => competition.value !== null && competition.value.status !== 'published',
)
const historicalWarningDescription = computed(() => {
  const warning = competition.value?.lifecycle_warning
  if (!warning) {
    return '该赛事已不在默认发现列表中，请以官方或学校通知为准。'
  }
  return `维护原因：${warning.reason}；该赛事已不在默认发现列表中，请以官方或学校通知为准。`
})
const groupedTimeNodes = computed(() => groupTimeNodes(competition.value?.time_nodes ?? []))
const favoritePending = ref(false)
const subscriptionPending = ref(false)
const engagementError = ref('')
const showSubscriptionConsent = ref(false)
const subscriptionSummary = ref<SubscriptionSummary | null>(null)
const authoritativeReminderSettings = ref<SubscriptionConsent | null>(null)
const persistedSubscriptionConsent = ref<SubscriptionConsent | null>(null)
const subscriptionFormDraft = ref<SubscriptionConsent>({
  reminder_enabled: false,
  remind_days: 0,
  node_types: [],
})
const subscriptionNodeOptions: Array<{ value: SubscriptionNodeType; label: string }> = [
  { value: 'registration_deadline', label: '报名截止' },
  { value: 'submission_deadline', label: '作品提交截止' },
  { value: 'competition_start', label: '比赛开始' },
]
const isStudent = computed(() => auth.currentUser?.role === 'student')
const canStartEngagement = computed(() => auth.currentUser === null || isStudent.value)
const currentSubscriptionState = computed(() => competition.value?.is_subscribed ?? false)
const selectableSubscriptionNodeTypes = computed<SubscriptionNodeType[]>(() => {
  if (!competition.value) return []
  return subscriptionNodeOptions
    .map((option) => option.value)
    .filter((nodeType) =>
      competition.value?.time_nodes.some(
        (node) => node.node_type === nodeType && node.occurs_at != null,
      ),
    )
})
const selectableSubscriptionNodeOptions = computed(() =>
  subscriptionNodeOptions.filter((option) =>
    selectableSubscriptionNodeTypes.value.includes(option.value),
  ),
)
const subscriptionFormIsValid = computed(
  () =>
    Number.isInteger(subscriptionFormDraft.value.remind_days) &&
    subscriptionFormDraft.value.remind_days >= 0 &&
    subscriptionFormDraft.value.remind_days <= 30 &&
    subscriptionFormDraft.value.node_types.length > 0,
)

function consentFromSummary(summary: SubscriptionSummary): SubscriptionConsent {
  return {
    reminder_enabled: summary.reminder_enabled,
    remind_days: summary.remind_days,
    node_types: [...summary.node_types],
  }
}

async function loadAuthoritativeReminderSettings() {
  if (!isStudent.value) return
  try {
    const profile = await fetchCurrentProfile()
    authoritativeReminderSettings.value = {
      reminder_enabled: profile.message_enabled,
      remind_days: profile.default_remind_days,
      node_types: [...profile.default_reminder_node_types],
    }
  } catch {
    authoritativeReminderSettings.value = null
  }
}

async function loadCompetition() {
  const routeId = Array.isArray(route.params.id) ? route.params.id[0] : route.params.id
  const competitionId = Number(routeId)
  if (!Number.isInteger(competitionId) || competitionId < 1) {
    competition.value = null
    errorMessage.value = ''
    notFound.value = true
    return
  }

  loading.value = true
  errorMessage.value = ''
  notFound.value = false

  try {
    const detail = await fetchCompetitionDetail(competitionId)
    competition.value = detail
    subscriptionSummary.value = detail.subscription_summary
    persistedSubscriptionConsent.value = detail.subscription_summary
      ? consentFromSummary(detail.subscription_summary)
      : null
  } catch (error) {
    competition.value = null
    if (isAxiosError(error) && error.response?.status === 404) {
      notFound.value = true
    } else {
      errorMessage.value = '赛事详情暂时无法加载，请稍后再试。'
    }
  } finally {
    loading.value = false
  }
}

function loginForEngagement() {
  void router.push({ name: 'account-status', query: { return_to: route.fullPath } })
}

async function toggleFavorite() {
  if (!competition.value || favoritePending.value) return
  if (!auth.currentUser) {
    loginForEngagement()
    return
  }
  if (!isStudent.value) return

  favoritePending.value = true
  engagementError.value = ''
  try {
    const state = competition.value.is_favorited
      ? await unfavoriteCompetition(competition.value.id)
      : await favoriteCompetition(competition.value.id)
    competition.value.is_favorited = state.is_favorited
  } catch {
    engagementError.value = '收藏操作失败，请稍后重试。'
  } finally {
    favoritePending.value = false
  }
}

async function openSubscriptionConsent() {
  if (!competition.value || subscriptionPending.value) return
  if (!auth.currentUser) {
    loginForEngagement()
    return
  }
  if (!isStudent.value) return

  engagementError.value = ''
  if (selectableSubscriptionNodeTypes.value.length === 0) {
    engagementError.value = '当前赛事没有可订阅的提醒节点。'
    return
  }
  if (persistedSubscriptionConsent.value === null && authoritativeReminderSettings.value === null) {
    await loadAuthoritativeReminderSettings()
  }
  const prefill = persistedSubscriptionConsent.value ?? authoritativeReminderSettings.value
  if (prefill === null) {
    engagementError.value = '提醒默认设置暂时无法加载，请稍后重试。'
    return
  }
  subscriptionFormDraft.value = {
    reminder_enabled: prefill.reminder_enabled,
    remind_days: prefill.remind_days,
    node_types: selectableSubscriptionNodeTypes.value.filter((type) =>
      prefill.node_types.includes(type),
    ),
  }
  showSubscriptionConsent.value = true
}

async function saveSubscription() {
  if (!competition.value || subscriptionPending.value || !subscriptionFormIsValid.value) return
  const nodeTypes = selectableSubscriptionNodeTypes.value.filter((type) =>
    subscriptionFormDraft.value.node_types.includes(type),
  )
  if (nodeTypes.length === 0) {
    engagementError.value = '当前赛事没有可订阅的提醒节点。'
    return
  }
  subscriptionPending.value = true
  engagementError.value = ''
  try {
    const payload: SubscriptionConsent = {
      reminder_enabled: subscriptionFormDraft.value.reminder_enabled,
      remind_days: subscriptionFormDraft.value.remind_days,
      node_types: nodeTypes,
    }
    subscriptionSummary.value = currentSubscriptionState.value
      ? await updateCompetitionSubscription(competition.value.id, payload)
      : await createCompetitionSubscription(competition.value.id, payload)
    competition.value.is_subscribed = subscriptionSummary.value.is_subscribed
    persistedSubscriptionConsent.value = consentFromSummary(subscriptionSummary.value)
    showSubscriptionConsent.value = false
  } catch {
    engagementError.value = '订阅设置保存失败，请检查后重试。'
  } finally {
    subscriptionPending.value = false
  }
}

async function cancelSubscription() {
  if (!competition.value || subscriptionPending.value || !isStudent.value) return
  subscriptionPending.value = true
  engagementError.value = ''
  try {
    const cancellation = await cancelCompetitionSubscription(competition.value.id)
    subscriptionSummary.value = null
    competition.value.is_subscribed = cancellation.is_subscribed
  } catch {
    engagementError.value = '取消订阅失败，请稍后重试。'
  } finally {
    subscriptionPending.value = false
  }
}

onMounted(() => {
  void auth.loadCurrentUser().then(() => loadAuthoritativeReminderSettings())
  void loadCompetition()
})

function recordOutbound(targetType: 'source_url' | 'official_url' | 'attachment_url') {
  if (!competition.value) return
  void recordCompetitionOutboundClick(
    competition.value.id,
    targetType,
    'competition_detail',
  ).catch(() => undefined)
}

function groupTimeNodes(nodes: CompetitionTimeNode[]) {
  const groups = new Map<
    string,
    { key: string; label: string; order: number; nodes: CompetitionTimeNode[] }
  >()
  for (const node of nodes) {
    const key = node.stage_id === null || node.stage_id === undefined ? `unassigned-${node.id}` : String(node.stage_id)
    const group = groups.get(key) ?? {
      key,
      label: node.stage_label ?? '关键时间',
      order: node.stage_order ?? Number.MAX_SAFE_INTEGER,
      nodes: [],
    }
    group.nodes.push(node)
    groups.set(key, group)
  }
  return [...groups.values()]
    .map((group) => ({
      ...group,
      nodes: [...group.nodes].sort((left, right) => nodeTime(left) - nodeTime(right)),
    }))
    .sort((left, right) => left.order - right.order || left.key.localeCompare(right.key))
}

function nodeTime(node: CompetitionTimeNode) {
  const timestamp = node.occurs_at ?? node.starts_at ?? node.due_at
  return timestamp ? new Date(timestamp).getTime() : Number.MAX_SAFE_INTEGER
}
</script>

<template>
  <section class="competition-page">
    <RouterLink class="back-link" to="/competitions">
      <LeftOutlined />
      返回赛事列表
    </RouterLink>

    <div v-if="loading" class="state-panel" role="status" aria-live="polite">
      <span class="sr-only">正在加载赛事详情…</span>
      <ASkeleton aria-hidden="true" active :paragraph="{ rows: 8 }" />
    </div>
    <AResult
      v-else-if="notFound"
      class="state-panel"
      role="status"
      status="404"
      title="未找到公开赛事"
      sub-title="赛事不存在、尚未发布或已停止公开。"
    >
      <template #extra>
        <RouterLink class="detail-link" to="/competitions">
          <LeftOutlined />
          返回赛事列表
        </RouterLink>
      </template>
    </AResult>
    <AResult
      v-else-if="errorMessage"
      class="state-panel"
      role="alert"
      status="error"
      title="赛事详情加载失败"
      :sub-title="errorMessage"
    >
      <template #extra>
        <AButton type="primary" @click="loadCompetition">
          <template #icon><ReloadOutlined /></template>
          重新加载
        </AButton>
      </template>
    </AResult>

    <article v-else-if="competition" class="detail-layout">
      <header class="detail-header">
        <div class="card-meta">
          <ATag :color="historical ? 'orange' : 'green'">
            {{ formatCompetitionStatus(competition.status) }}
          </ATag>
          <ATag color="blue">{{ formatRegistrationStatus(competition.registration_status) }}</ATag>
          <span>{{ competition.category ?? '未分类' }}</span>
        </div>
        <h1 class="page-title">{{ competition.title }}</h1>
        <p class="page-description">
          {{ competition.summary ?? competition.value_notes ?? '暂无赛事摘要。' }}
        </p>
        <p class="revision-context">
          <span v-if="competition.current_revision">
            当前公开修订 r{{ competition.current_revision.revision_number }}
          </span>
          <span v-if="competition.edition_label">届次 {{ competition.edition_label }}</span>
          <span v-if="competition.content_updated_at">内容更新于 {{ competition.content_updated_at }}</span>
        </p>
        <p v-if="competition.registration_status_basis" class="registration-basis">
          报名状态依据：{{ formatNodeLabel(competition.registration_status_basis.node_type) }} ·
          {{ formatNodeDate(competition.registration_status_basis, true) }}
        </p>
        <AAlert
          v-if="historical"
          class="historical-warning"
          show-icon
          type="warning"
          :message="`${formatCompetitionStatus(competition.status)}赛事仍保留历史详情`"
          :description="historicalWarningDescription"
        />
        <div v-if="competition.tags.length" class="tag-row">
          <ATag v-for="tag in competition.tags" :key="tag" color="cyan">{{ tag }}</ATag>
        </div>
        <div
          v-if="competition.is_favorited || competition.is_subscribed"
          class="tag-row personal-state"
        >
          <ATag v-if="competition.is_favorited" color="gold">已收藏</ATag>
          <ATag v-if="competition.is_subscribed" color="green">已订阅</ATag>
        </div>
      </header>

      <div class="detail-grid">
        <section class="detail-section">
          <h2>来源与官方通道</h2>
          <dl>
            <div>
              <dt>可信来源</dt>
              <dd>
                <a
                  :href="competition.source_url"
                  data-testid="source-link"
                  rel="noopener noreferrer"
                  target="_blank"
                  @click="recordOutbound('source_url')"
                >
                  {{ competition.source_name }}
                  <ExportOutlined />
                </a>
              </dd>
            </div>
            <div v-if="competition.official_url">
              <dt>官方入口</dt>
              <dd>
                <a
                  :href="competition.official_url"
                  data-testid="official-link"
                  rel="noopener noreferrer"
                  target="_blank"
                  @click="recordOutbound('official_url')"
                >
                  打开官方报名或通知
                  <ExportOutlined />
                </a>
              </dd>
            </div>
            <div v-if="competition.attachment_url">
              <dt>赛事附件</dt>
              <dd>
                <a
                  :href="competition.attachment_url"
                  data-testid="attachment-link"
                  rel="noopener noreferrer"
                  target="_blank"
                  @click="recordOutbound('attachment_url')"
                >
                  查看附件
                  <PaperClipOutlined />
                </a>
              </dd>
            </div>
          </dl>
          <p class="reference-note">选择建议仅供参考，官方或学校通知具有最终效力。</p>
        </section>

        <section class="detail-section">
          <h2>赛事信息</h2>
          <dl>
            <div>
              <dt>主办方</dt>
              <dd>{{ competition.organizer ?? competition.host ?? '未填写' }}</dd>
            </div>
            <div>
              <dt>参赛形式</dt>
              <dd>{{ competition.participant_forms.map(formatParticipantForm).join('、') }}</dd>
            </div>
            <div>
              <dt>团队规模</dt>
              <dd>{{ competition.team_size ?? '未填写' }}</dd>
            </div>
          </dl>
        </section>

        <section class="detail-section">
          <h2>适配信息</h2>
          <dl>
            <div>
              <dt>适合专业</dt>
              <dd>{{ competition.suitable_majors.join('、') || '未填写' }}</dd>
            </div>
            <div>
              <dt>适合年级</dt>
              <dd>{{ competition.suitable_grades.join('、') || '未填写' }}</dd>
            </div>
            <div>
              <dt>价值依据</dt>
              <dd>{{ competition.value_notes ?? '暂无说明' }}</dd>
            </div>
          </dl>
        </section>
      </div>

      <section class="detail-section detail-section-wide">
        <h2>关键时间节点</h2>
        <div v-if="competition.time_nodes.length" class="time-stage-list">
          <section v-for="stage in groupedTimeNodes" :key="stage.key" class="time-stage">
            <h3>{{ stage.label }}</h3>
            <ul class="time-node-list">
              <li
                v-for="node in stage.nodes"
                :key="node.id"
                :class="{ 'time-node-primary': node.prominence === 'primary' }"
              >
                <strong>{{ formatNodeLabel(node.node_type) }}</strong>
                <span>{{ formatNodeDate(node, true) }}</span>
                <small v-if="node.description">{{ node.description }}</small>
              </li>
            </ul>
          </section>
        </div>
        <AEmpty v-else :image="AEmpty.PRESENTED_IMAGE_SIMPLE" description="关键时间待确认" />
      </section>

      <section class="detail-section detail-section-wide">
        <h2>赛事详情</h2>
        <p class="detail-copy">{{ competition.detail ?? '暂无更详细说明。' }}</p>
      </section>

      <section v-if="competition.eligibility" class="detail-section detail-section-wide">
        <h2>参赛要求</h2>
        <p class="detail-copy">{{ competition.eligibility }}</p>
      </section>

      <section
        v-if="!auth.loading && canStartEngagement"
        class="detail-section detail-section-wide"
        aria-labelledby="engagement-heading"
      >
        <h2 id="engagement-heading">收藏与订阅</h2>
        <p v-if="engagementError" role="alert" class="field-error">{{ engagementError }}</p>
        <div class="filter-actions">
          <AButton
            data-testid="favorite-action"
            :aria-pressed="competition.is_favorited"
            :loading="favoritePending"
            :disabled="favoritePending"
            @click="toggleFavorite"
          >
            {{ competition.is_favorited ? '取消收藏' : '收藏' }}
          </AButton>
          <AButton
            data-testid="subscription-action"
            type="primary"
            :loading="subscriptionPending"
            :disabled="subscriptionPending"
            @click="openSubscriptionConsent"
          >
            {{ competition.is_subscribed ? '修改订阅设置' : '订阅赛事' }}
          </AButton>
          <AButton
            v-if="competition.is_subscribed && auth.currentUser"
            data-testid="subscription-cancel"
            danger
            :loading="subscriptionPending"
            :disabled="subscriptionPending"
            @click="cancelSubscription"
          >
            取消订阅
          </AButton>
        </div>

        <p data-testid="subscription-summary">
          <template v-if="competition.is_subscribed">
            已订阅
            <template v-if="subscriptionSummary">
              ：{{ subscriptionSummary.reminder_enabled ? '已启用提醒' : '提醒已关闭' }}，提前
              {{ subscriptionSummary.remind_days }} 天
              <span v-if="subscriptionSummary.scheduled_reminder_count !== undefined">
                ，已安排 {{ subscriptionSummary.scheduled_reminder_count }} 个提醒
              </span>
            </template>
          </template>
          <template v-else>未订阅</template>
        </p>

        <AForm
          v-if="showSubscriptionConsent"
          data-testid="subscription-consent"
          class="profile-form"
          layout="vertical"
          :model="subscriptionFormDraft"
          @finish="saveSubscription"
        >
          <p>请确认本次订阅的提醒设置。</p>
          <AFormItem>
            <ACheckbox v-model:checked="subscriptionFormDraft.reminder_enabled">启用提醒</ACheckbox>
          </AFormItem>
          <AFormItem label="提前天数" name="remind_days">
            <AInputNumber v-model:value="subscriptionFormDraft.remind_days" :min="0" :max="30" />
          </AFormItem>
          <AFormItem label="提醒节点" name="node_types">
            <ACheckboxGroup
              data-testid="subscription-node-options"
              v-model:value="subscriptionFormDraft.node_types"
            >
              <ACheckbox
                v-for="option in selectableSubscriptionNodeOptions"
                :key="option.value"
                :value="option.value"
                :data-testid="`subscription-node-${option.value}`"
              >
                {{ option.label }}
              </ACheckbox>
            </ACheckboxGroup>
          </AFormItem>
          <AButton
            type="primary"
            html-type="submit"
            :loading="subscriptionPending"
            :disabled="subscriptionPending || !subscriptionFormIsValid"
          >
            {{ competition.is_subscribed ? '保存订阅设置' : '确认订阅' }}
          </AButton>
        </AForm>
      </section>
    </article>
  </section>
</template>
