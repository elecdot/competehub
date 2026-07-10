<script setup lang="ts">
import {
  ArrowRightOutlined,
  BankOutlined,
  CalendarOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons-vue'
import {
  Button as AButton,
  DatePicker as ADatePicker,
  Empty as AEmpty,
  Input as AInput,
  Pagination as APagination,
  Result as AResult,
  Select as ASelect,
  Skeleton as ASkeleton,
  Tag as ATag,
} from 'ant-design-vue'
import { computed, nextTick, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { fetchCompetitions } from '@/api/client'
import { useCompetitionFilterStore } from '@/stores/competition_filter_store'
import type { CompetitionSummary } from '@/types/competition'
import { formatNodeDate, formatNodeLabel } from '@/utils/competition'

const route = useRoute()
const router = useRouter()
const filters = useCompetitionFilterStore()
const participantFormOptions = [
  { label: '不限参赛形式', value: '' },
  { label: '个人参赛', value: 'individual' },
  { label: '团队参赛', value: 'team' },
]
type DatePickerRef = { $el: HTMLElement; focus: () => void }

const competitions = ref<CompetitionSummary[]>([])
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')
const deadlineFromPicker = ref<DatePickerRef | null>(null)
const deadlineToPicker = ref<DatePickerRef | null>(null)
const formattedTotal = computed(() => new Intl.NumberFormat('zh-CN').format(total.value))
const deadlineError = computed(() => {
  if (
    filters.deadlineFrom &&
    filters.deadlineTo &&
    filters.deadlineFrom > filters.deadlineTo
  ) {
    return '开始日期不能晚于结束日期。'
  }
  return ''
})
let requestSequence = 0

function syncDeadlineAccessibility() {
  // Ant DatePicker puts arbitrary ARIA attributes on its wrapper, not the actual input.
  for (const picker of [deadlineFromPicker.value, deadlineToPicker.value]) {
    const input = picker?.$el.querySelector('input')
    if (!input) continue

    if (deadlineError.value) {
      input.setAttribute('aria-describedby', 'competition-deadline-error')
      input.setAttribute('aria-invalid', 'true')
    } else {
      input.removeAttribute('aria-describedby')
      input.removeAttribute('aria-invalid')
    }
  }
}

async function loadCompetitions() {
  const requestId = ++requestSequence
  loading.value = true
  errorMessage.value = ''

  try {
    const payload = await fetchCompetitions(filters.toQueryParams())
    if (requestId !== requestSequence) return
    competitions.value = payload.items
    filters.page = payload.pagination.page
    filters.pageSize = payload.pagination.page_size
    total.value = payload.pagination.total
  } catch {
    if (requestId !== requestSequence) return
    competitions.value = []
    total.value = 0
    errorMessage.value = '赛事列表暂时无法加载，请稍后再试。'
  } finally {
    if (requestId === requestSequence) loading.value = false
  }
}

function submitFilters() {
  if (deadlineError.value) {
    void nextTick(() => deadlineFromPicker.value?.focus())
    return
  }

  filters.page = 1
  void applyFiltersToRoute()
}

function clearFilters() {
  filters.reset()
  void applyFiltersToRoute()
}

function changePage(page: number) {
  filters.page = page
  void applyFiltersToRoute()
}

async function applyFiltersToRoute() {
  const query = filters.toRouteQuery()
  const target = router.resolve({ name: 'competitions', query })
  if (target.fullPath === route.fullPath) {
    await loadCompetitions()
    return
  }
  await router.push({ name: 'competitions', query })
}

watch(deadlineError, () => {
  void nextTick(syncDeadlineAccessibility)
})

watch(
  () => route.query,
  (query) => {
    filters.replaceFromRouteQuery(query)

    const canonicalQuery = filters.toRouteQuery()
    const canonicalRoute = router.resolve({ name: 'competitions', query: canonicalQuery })
    if (canonicalRoute.fullPath !== route.fullPath) {
      void router.replace({ name: 'competitions', query: canonicalQuery })
      return
    }

    if (deadlineError.value) {
      requestSequence += 1
      loading.value = false
      errorMessage.value = ''
      competitions.value = []
      total.value = 0
      return
    }
    void loadCompetitions()
  },
  { immediate: true },
)
</script>

<template>
  <section class="competition-page">
    <div class="page-heading">
      <h1 class="page-title">赛事列表</h1>
      <span class="result-count" aria-live="polite">{{ formattedTotal }} 项公开赛事</span>
    </div>

    <form class="filter-bar" aria-label="赛事筛选" @submit.prevent="submitFilters">
      <label for="competition-keyword">
        关键词
        <AInput
          id="competition-keyword"
          v-model:value="filters.keyword"
          allow-clear
          autocomplete="off"
          name="keyword"
          placeholder="输入名称、主办方或类别…"
          type="search"
        />
      </label>
      <label for="competition-category">
        类别
        <AInput
          id="competition-category"
          v-model:value="filters.category"
          allow-clear
          autocomplete="off"
          name="category"
          placeholder="输入类别，例如创新创业…"
        />
      </label>
      <label for="competition-major">
        专业
        <AInput
          id="competition-major"
          v-model:value="filters.major"
          allow-clear
          autocomplete="off"
          name="major"
          placeholder="输入专业，例如软件工程…"
        />
      </label>
      <label for="competition-grade">
        年级
        <AInput
          id="competition-grade"
          v-model:value="filters.grade"
          allow-clear
          autocomplete="off"
          name="grade"
          placeholder="输入年级，例如大二…"
        />
      </label>
      <label for="competition-tag">
        标签
        <AInput
          id="competition-tag"
          v-model:value="filters.tag"
          allow-clear
          autocomplete="off"
          name="tag"
          placeholder="输入标签，例如人工智能…"
        />
      </label>
      <label for="competition-participant-form">
        参赛形式
        <ASelect
          id="competition-participant-form"
          v-model:value="filters.participantForm"
          :options="participantFormOptions"
          autocomplete="off"
        />
        <input type="hidden" name="participant_form" :value="filters.participantForm" />
      </label>
      <label for="competition-deadline-from">
        报名截止日期从
        <ADatePicker
          id="competition-deadline-from"
          ref="deadlineFromPicker"
          v-model:value="filters.deadlineFrom"
          :status="deadlineError ? 'error' : undefined"
          autocomplete="off"
          value-format="YYYY-MM-DD"
          placeholder="选择开始日期…"
        />
        <input type="hidden" name="deadline_from" :value="filters.deadlineFrom" />
      </label>
      <label for="competition-deadline-to">
        报名截止日期至
        <ADatePicker
          id="competition-deadline-to"
          ref="deadlineToPicker"
          v-model:value="filters.deadlineTo"
          :status="deadlineError ? 'error' : undefined"
          autocomplete="off"
          value-format="YYYY-MM-DD"
          placeholder="选择结束日期…"
        />
        <input type="hidden" name="deadline_to" :value="filters.deadlineTo" />
      </label>
      <p v-if="deadlineError" id="competition-deadline-error" class="field-error" role="alert">
        {{ deadlineError }}
      </p>
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

    <div v-if="loading" class="state-panel" role="status" aria-live="polite">
      <span class="sr-only">正在加载赛事…</span>
      <ASkeleton aria-hidden="true" active :paragraph="{ rows: 4 }" />
    </div>
    <AResult
      v-else-if="errorMessage"
      class="state-panel"
      role="alert"
      status="error"
      title="赛事列表加载失败"
      :sub-title="errorMessage"
    >
      <template #extra>
        <AButton type="primary" @click="loadCompetitions">
          <template #icon><ReloadOutlined /></template>
          重新加载
        </AButton>
      </template>
    </AResult>
    <AEmpty
      v-else-if="competitions.length === 0"
      class="state-panel"
      description="没有匹配的已发布赛事"
      role="status"
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
            <p class="card-organizer">
              <BankOutlined />
              {{ competition.organizer ?? '主办方未填写' }}
            </p>
            <p class="card-description">
              {{ competition.value_notes ?? competition.source_name }}
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
            <RouterLink
              class="detail-link"
              :to="{ name: 'competition-detail', params: { id: competition.id } }"
            >
              查看详情
              <ArrowRightOutlined />
            </RouterLink>
          </div>
        </article>
      </div>

      <APagination
        class="competition-pagination"
        :current="filters.page"
        :page-size="filters.pageSize"
        :total="total"
        :show-size-changer="false"
        show-less-items
        @change="changePage"
      />
    </template>
  </section>
</template>
