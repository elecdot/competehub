<script setup lang="ts">
import {
  ArrowRightOutlined,
  CalendarOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons-vue'
import {
  Button as AButton,
  Empty as AEmpty,
  Input as AInput,
  Pagination as APagination,
  Result as AResult,
  Select as ASelect,
  Skeleton as ASkeleton,
  Tag as ATag,
} from 'ant-design-vue'
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchCompetitions } from '@/api/client'
import type { CompetitionSummary, Pagination } from '@/types/competition'
import { formatNodeDate, formatNodeLabel } from '@/utils/competition'

const router = useRouter()
const filters = reactive({
  keyword: '',
  category: '',
  major: '',
  grade: '',
  tag: '',
  participant_form: '',
})
const participantFormOptions = [
  { label: '不限参赛形式', value: '' },
  { label: '个人参赛', value: 'individual' },
  { label: '团队参赛', value: 'team' },
]
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
      tag: filters.tag || undefined,
      participant_form: filters.participant_form || undefined,
      page,
      page_size: pagination.value.page_size,
    })
    competitions.value = payload.items
    pagination.value = payload.pagination
  } catch {
    competitions.value = []
    pagination.value = { page, page_size: pagination.value.page_size, total: 0 }
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
  filters.tag = ''
  filters.participant_form = ''
  void loadCompetitions(1)
}

function openDetail(competitionId: number) {
  void router.push(`/competitions/${competitionId}`)
}

onMounted(() => {
  void loadCompetitions()
})
</script>

<template>
  <section class="competition-page">
    <div class="page-heading">
      <h1 class="page-title">赛事列表</h1>
      <span class="result-count" aria-live="polite">{{ pagination.total }} 项公开赛事</span>
    </div>

    <form class="filter-bar" aria-label="赛事筛选" @submit.prevent="submitFilters">
      <label for="competition-keyword">
        关键词
        <AInput
          id="competition-keyword"
          v-model:value="filters.keyword"
          allow-clear
          placeholder="名称、主办方、类别"
        />
      </label>
      <label for="competition-category">
        类别
        <AInput
          id="competition-category"
          v-model:value="filters.category"
          allow-clear
          placeholder="创新创业"
        />
      </label>
      <label for="competition-major">
        专业
        <AInput
          id="competition-major"
          v-model:value="filters.major"
          allow-clear
          placeholder="软件工程"
        />
      </label>
      <label for="competition-grade">
        年级
        <AInput
          id="competition-grade"
          v-model:value="filters.grade"
          allow-clear
          placeholder="大二"
        />
      </label>
      <label for="competition-tag">
        标签
        <AInput
          id="competition-tag"
          v-model:value="filters.tag"
          allow-clear
          placeholder="人工智能"
        />
      </label>
      <label for="competition-participant-form">
        参赛形式
        <ASelect
          id="competition-participant-form"
          v-model:value="filters.participant_form"
          :options="participantFormOptions"
        />
      </label>
      <div class="filter-actions">
        <AButton type="primary" html-type="submit" :loading="loading">
          <template #icon><SearchOutlined /></template>
          筛选
        </AButton>
        <AButton :disabled="loading" @click="clearFilters">
          <template #icon><ReloadOutlined /></template>
          重置
        </AButton>
      </div>
    </form>

    <div v-if="loading" class="state-panel" aria-live="polite">
      <span class="sr-only">正在加载赛事</span>
      <ASkeleton active :paragraph="{ rows: 4 }" />
    </div>
    <AResult
      v-else-if="errorMessage"
      class="state-panel"
      status="error"
      title="赛事列表加载失败"
      :sub-title="errorMessage"
    >
      <template #extra>
        <AButton type="primary" @click="loadCompetitions(pagination.page)">
          <template #icon><ReloadOutlined /></template>
          重新加载
        </AButton>
      </template>
    </AResult>
    <AEmpty
      v-else-if="competitions.length === 0"
      class="state-panel"
      description="没有匹配的已发布赛事"
    />

    <template v-else>
      <div class="competition-list">
        <article
          v-for="competition in competitions"
          :key="competition.id"
          class="competition-card"
        >
          <div class="card-main">
            <div class="card-meta">
              <ATag color="green">公开中</ATag>
              <span>{{ competition.category ?? '未分类' }}</span>
            </div>
            <h2>{{ competition.title }}</h2>
            <p class="card-description">
              {{ competition.value_notes ?? competition.organizer ?? competition.source_name }}
            </p>
            <div v-if="competition.tags.length" class="tag-row">
              <ATag v-for="tag in competition.tags" :key="tag" color="cyan">{{ tag }}</ATag>
            </div>
          </div>
          <div class="card-side">
            <p class="next-node">
              <CalendarOutlined />
              <template v-if="competition.next_node">
                {{ formatNodeLabel(competition.next_node.node_type) }} ·
                {{ formatNodeDate(competition.next_node) }}
              </template>
              <template v-else>暂无后续时间</template>
            </p>
            <AButton type="primary" @click="openDetail(competition.id)">
              查看详情
              <template #icon><ArrowRightOutlined /></template>
            </AButton>
          </div>
        </article>
      </div>

      <APagination
        class="competition-pagination"
        :current="pagination.page"
        :page-size="pagination.page_size"
        :total="pagination.total"
        :show-size-changer="false"
        show-less-items
        @change="loadCompetitions"
      />
    </template>
  </section>
</template>
