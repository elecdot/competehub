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
  Empty as AEmpty,
  Result as AResult,
  Skeleton as ASkeleton,
  Tag as ATag,
} from 'ant-design-vue'
import { isAxiosError } from 'axios'
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { fetchCompetitionDetail, recordCompetitionOutboundClick } from '@/api/client'
import type { CompetitionDetail, CompetitionTimeNode } from '@/types/competition'
import {
  formatCompetitionStatus,
  formatNodeDate,
  formatNodeLabel,
  formatParticipantForm,
  formatRegistrationStatus,
} from '@/utils/competition'

const route = useRoute()
const competition = ref<CompetitionDetail | null>(null)
const loading = ref(false)
const errorMessage = ref('')
const notFound = ref(false)
const historical = computed(
  () => competition.value !== null && competition.value.status !== 'published',
)
const groupedTimeNodes = computed(() => groupTimeNodes(competition.value?.time_nodes ?? []))

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
    competition.value = await fetchCompetitionDetail(competitionId)
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

onMounted(() => {
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
          description="该赛事已不在默认发现列表中，请以官方或学校通知为准。"
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
    </article>
  </section>
</template>
