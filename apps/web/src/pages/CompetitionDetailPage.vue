<script setup lang="ts">
import {
  ExportOutlined,
  LeftOutlined,
  PaperClipOutlined,
  ReloadOutlined,
} from '@ant-design/icons-vue'
import {
  Button as AButton,
  Empty as AEmpty,
  Result as AResult,
  Skeleton as ASkeleton,
  Tag as ATag,
} from 'ant-design-vue'
import { isAxiosError } from 'axios'
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { fetchCompetitionDetail } from '@/api/client'
import type { CompetitionDetail } from '@/types/competition'
import {
  formatNodeDate,
  formatNodeLabel,
  formatParticipantForm,
} from '@/utils/competition'

const route = useRoute()
const competition = ref<CompetitionDetail | null>(null)
const loading = ref(false)
const errorMessage = ref('')
const notFound = ref(false)

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
          <ATag color="green">公开中</ATag>
          <span>{{ competition.category ?? '未分类' }}</span>
        </div>
        <h1 class="page-title">{{ competition.title }}</h1>
        <p class="page-description">
          {{ competition.summary ?? competition.value_notes ?? '暂无赛事摘要。' }}
        </p>
        <div v-if="competition.tags.length" class="tag-row">
          <ATag v-for="tag in competition.tags" :key="tag" color="cyan">{{ tag }}</ATag>
        </div>
      </header>

      <div class="detail-grid">
        <section class="detail-section">
          <h2>来源与官方通道</h2>
          <dl>
            <div>
              <dt>可信来源</dt>
              <dd>
                <a :href="competition.source_url" target="_blank" rel="noreferrer">
                  {{ competition.source_name }}
                  <ExportOutlined />
                </a>
              </dd>
            </div>
            <div v-if="competition.official_url">
              <dt>官方入口</dt>
              <dd>
                <a :href="competition.official_url" target="_blank" rel="noreferrer">
                  打开官方报名或通知
                  <ExportOutlined />
                </a>
              </dd>
            </div>
            <div v-if="competition.attachment_url">
              <dt>赛事附件</dt>
              <dd>
                <a :href="competition.attachment_url" target="_blank" rel="noreferrer">
                  查看附件
                  <PaperClipOutlined />
                </a>
              </dd>
            </div>
          </dl>
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
              <dd>{{ formatParticipantForm(competition.participant_form) }}</dd>
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
        <ul v-if="competition.time_nodes.length" class="time-node-list">
          <li v-for="node in competition.time_nodes" :key="node.id">
            <strong>{{ formatNodeLabel(node.node_type) }}</strong>
            <span>{{ formatNodeDate(node, true) }}</span>
            <small v-if="node.description">{{ node.description }}</small>
          </li>
        </ul>
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
