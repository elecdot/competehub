<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { fetchCompetitions } from '@/api/client'
import type { CompetitionSummary, Pagination } from '@/types/competition'

const filters = reactive({
  keyword: '',
  category: '',
  major: '',
  grade: '',
})
const competitions = ref<CompetitionSummary[]>([])
const pagination = ref<Pagination>({ page: 1, page_size: 20, total: 0 })
const loading = ref(false)
const errorMessage = ref('')

async function loadCompetitions(page = 1) {
  loading.value = true
  errorMessage.value = ''

  try {
    const payload = await fetchCompetitions({
      keyword: filters.keyword || undefined,
      category: filters.category || undefined,
      major: filters.major || undefined,
      grade: filters.grade || undefined,
      page,
      page_size: pagination.value.page_size,
    })
    competitions.value = payload.items
    pagination.value = payload.pagination
  } catch {
    competitions.value = []
    errorMessage.value = '赛事列表暂时无法加载，请稍后再试。'
  } finally {
    loading.value = false
  }
}

function submitFilters() {
  void loadCompetitions(1)
}

function clearFilters() {
  filters.keyword = ''
  filters.category = ''
  filters.major = ''
  filters.grade = ''
  void loadCompetitions(1)
}

function formatNode(node: CompetitionSummary['next_node']) {
  if (!node) {
    return '暂无关键时间'
  }
  const timestamp = node.due_at ?? node.starts_at
  return timestamp ? `${node.node_type} · ${new Date(timestamp).toLocaleDateString()}` : node.node_type
}

onMounted(() => {
  void loadCompetitions()
})
</script>

<template>
  <section class="competition-page">
    <div class="page-heading">
      <div>
        <h1 class="page-title">赛事列表</h1>
        <p class="page-description">仅展示已发布赛事，支持按基础字段收窄结果。</p>
      </div>
      <span class="result-count">{{ pagination.total }} 项</span>
    </div>

    <form class="filter-bar" @submit.prevent="submitFilters">
      <label>
        关键词
        <input v-model="filters.keyword" type="search" placeholder="名称、主办方、类别" />
      </label>
      <label>
        类别
        <input v-model="filters.category" type="text" placeholder="创新创业" />
      </label>
      <label>
        专业
        <input v-model="filters.major" type="text" placeholder="软件工程" />
      </label>
      <label>
        年级
        <input v-model="filters.grade" type="text" placeholder="大二" />
      </label>
      <div class="filter-actions">
        <button type="submit">搜索</button>
        <button class="secondary-button" type="button" @click="clearFilters">清除</button>
      </div>
    </form>

    <p v-if="loading" class="state-message">正在加载赛事...</p>
    <p v-else-if="errorMessage" class="state-message error">{{ errorMessage }}</p>
    <p v-else-if="competitions.length === 0" class="state-message">没有匹配的已发布赛事。</p>

    <div v-else class="competition-list">
      <article v-for="competition in competitions" :key="competition.id" class="competition-card">
        <div class="card-main">
          <p class="card-meta">{{ competition.category ?? '未分类' }} · {{ competition.status }}</p>
          <h2>{{ competition.title }}</h2>
          <p class="card-description">
            {{ competition.value_notes ?? competition.organizer ?? competition.source_name }}
          </p>
          <div class="tag-row">
            <span v-for="tag in competition.tags" :key="tag">{{ tag }}</span>
          </div>
        </div>
        <div class="card-side">
          <p>{{ formatNode(competition.next_node) }}</p>
          <RouterLink class="detail-link" :to="`/competitions/${competition.id}`">
            查看详情
          </RouterLink>
        </div>
      </article>
    </div>
  </section>
</template>
