<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { fetchCompetitionDetail } from '@/api/client'
import type { CompetitionDetail, CompetitionTimeNode } from '@/types/competition'

const route = useRoute()
const competition = ref<CompetitionDetail | null>(null)
const loading = ref(false)
const errorMessage = ref('')

async function loadCompetition() {
  const routeId = Array.isArray(route.params.id) ? route.params.id[0] : route.params.id
  const competitionId = Number(routeId)
  if (!Number.isInteger(competitionId)) {
    errorMessage.value = '赛事编号无效。'
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    competition.value = await fetchCompetitionDetail(competitionId)
  } catch {
    competition.value = null
    errorMessage.value = '赛事详情暂时无法加载，或该赛事尚未公开。'
  } finally {
    loading.value = false
  }
}

function formatNodeDate(node: CompetitionTimeNode) {
  const timestamp = node.due_at ?? node.starts_at
  return timestamp ? new Date(timestamp).toLocaleString() : '时间待确认'
}

onMounted(() => {
  void loadCompetition()
})
</script>

<template>
  <section class="competition-page">
    <RouterLink class="back-link" to="/competitions">返回赛事列表</RouterLink>

    <p v-if="loading" class="state-message">正在加载详情...</p>
    <p v-else-if="errorMessage" class="state-message error">{{ errorMessage }}</p>

    <article v-else-if="competition" class="detail-layout">
      <header class="detail-header">
        <p class="card-meta">{{ competition.category ?? '未分类' }} · {{ competition.status }}</p>
        <h1 class="page-title">{{ competition.title }}</h1>
        <p class="page-description">{{ competition.summary ?? competition.value_notes }}</p>
        <div class="tag-row">
          <span v-for="tag in competition.tags" :key="tag">{{ tag }}</span>
        </div>
      </header>

      <section class="detail-grid">
        <div class="detail-section">
          <h2>来源与通道</h2>
          <dl>
            <div>
              <dt>来源</dt>
              <dd>
                <a :href="competition.source_url" target="_blank" rel="noreferrer">
                  {{ competition.source_name }}
                </a>
              </dd>
            </div>
            <div v-if="competition.official_url">
              <dt>官方入口</dt>
              <dd>
                <a :href="competition.official_url" target="_blank" rel="noreferrer">
                  打开官方报名/通知
                </a>
              </dd>
            </div>
            <div v-if="competition.attachment_url">
              <dt>附件</dt>
              <dd>
                <a :href="competition.attachment_url" target="_blank" rel="noreferrer">
                  查看附件
                </a>
              </dd>
            </div>
          </dl>
        </div>

        <div class="detail-section">
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
        </div>
      </section>

      <section class="detail-section">
        <h2>关键时间节点</h2>
        <ul class="time-node-list">
          <li v-for="node in competition.time_nodes" :key="node.id">
            <strong>{{ node.node_type }}</strong>
            <span>{{ formatNodeDate(node) }}</span>
            <small v-if="node.description">{{ node.description }}</small>
          </li>
        </ul>
      </section>

      <section class="detail-section">
        <h2>详情</h2>
        <p>{{ competition.detail ?? competition.eligibility ?? '暂无更详细说明。' }}</p>
      </section>
    </article>
  </section>
</template>
