<script setup lang="ts">
import {
  ArrowRightOutlined,
  BankOutlined,
  CalendarOutlined,
  DownOutlined,
  ReloadOutlined,
  SearchOutlined,
  UpOutlined,
} from '@ant-design/icons-vue'
import {
  Alert as AAlert,
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
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { fetchCompetitionFilterOptions, fetchCompetitions } from '@/api/client'
import {
  COMPETITION_FILTER_MAX_LENGTHS,
  useCompetitionFilterStore,
} from '@/stores/competition_filter_store'
import type {
  CompetitionFilterOptions,
  CompetitionSummary,
  RegistrationStatus,
} from '@/types/competition'
import { formatNodeDate, formatNodeLabel, formatRegistrationStatus } from '@/utils/competition'

const route = useRoute()
const router = useRouter()
const filters = useCompetitionFilterStore()
const participantFormOptions = [
  { label: '不限参赛形式', value: '' },
  { label: '个人参赛', value: 'individual' },
  { label: '团队参赛', value: 'team' },
]
const registrationStatusOptions = [
  { label: '不限报名状态', value: '' },
  { label: '报名开放', value: 'open' },
  { label: '即将报名', value: 'upcoming' },
  { label: '报名结束', value: 'closed' },
  { label: '报名待确认', value: 'unknown' },
  { label: '无需报名', value: 'not_applicable' },
]
const sortOptions = [
  { label: '按可行动性', value: 'actionable' },
  { label: '按报名截止', value: 'registration_deadline' },
  { label: '按发布时间', value: 'published_at' },
]
const guidedFilterDefinitions = [
  { filterKey: 'category', optionsKey: 'categories', label: '类别' },
  { filterKey: 'major', optionsKey: 'majors', label: '专业' },
  { filterKey: 'grade', optionsKey: 'grades', label: '年级' },
  { filterKey: 'tag', optionsKey: 'tags', label: '标签' },
] as const
type DatePickerRef = { $el: HTMLElement; focus: () => void }

const competitions = ref<CompetitionSummary[]>([])
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')
const filterOptions = ref<CompetitionFilterOptions>({
  categories: [],
  majors: [],
  grades: [],
  tags: [],
})
const filterOptionsLoading = ref(false)
const filterOptionsError = ref('')
const filterOptionsLoaded = ref(false)
const invalidFilterNotice = ref('')
const invalidFilterNoticeRoute = ref('')
const advancedFiltersOpen = ref(false)
const deadlineFromPicker = ref<DatePickerRef | null>(null)
const deadlineToPicker = ref<DatePickerRef | null>(null)
const formattedTotal = computed(() => new Intl.NumberFormat('zh-CN').format(total.value))
const activeAdvancedFilterCount = computed(
  () =>
    [
      filters.category,
      filters.major,
      filters.grade,
      filters.tag,
      filters.deadlineFrom,
      filters.deadlineTo,
    ].filter(Boolean).length,
)
const categoryOptions = computed(() => selectOptions(filterOptions.value.categories))
const majorOptions = computed(() => selectOptions(filterOptions.value.majors))
const gradeOptions = computed(() => selectOptions(filterOptions.value.grades))
const tagOptions = computed(() => selectOptions(filterOptions.value.tags))
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

function selectOptions(values: string[]) {
  return values.map((value) => ({ label: value, value }))
}

async function loadFilterOptions() {
  filterOptionsLoading.value = true
  filterOptionsError.value = ''
  try {
    filterOptions.value = await fetchCompetitionFilterOptions()
    filterOptionsLoaded.value = true
    const removedLabels = clearUnavailableGuidedFilters()
    if (removedLabels.length > 0) {
      filters.page = 1
      showInvalidFilterNotice(removedLabels)
      await applyFiltersToRoute(true)
    }
  } catch {
    filterOptions.value = { categories: [], majors: [], grades: [], tags: [] }
    filterOptionsLoaded.value = false
    filterOptionsError.value = '更多筛选选项暂时无法加载，关键词和常用筛选仍可使用。'
  } finally {
    filterOptionsLoading.value = false
  }
}

function clearUnavailableGuidedFilters(): string[] {
  const removedLabels: string[] = []
  for (const definition of guidedFilterDefinitions) {
    const value = filters[definition.filterKey]
    if (value && !filterOptions.value[definition.optionsKey].includes(value)) {
      filters[definition.filterKey] = ''
      removedLabels.push(definition.label)
    }
  }
  return removedLabels
}

function showInvalidFilterNotice(removedLabels: string[]) {
  invalidFilterNotice.value = `已移除失效的筛选条件：${removedLabels.join('、')}。`
  invalidFilterNoticeRoute.value = router.resolve({
    name: 'competitions',
    query: filters.toRouteQuery(),
  }).fullPath
}

function dismissInvalidFilterNotice() {
  invalidFilterNotice.value = ''
  invalidFilterNoticeRoute.value = ''
}

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
  dismissInvalidFilterNotice()
  advancedFiltersOpen.value = false
  void applyFiltersToRoute()
}

function changePage(page: number) {
  filters.page = page
  void applyFiltersToRoute()
}

function changeSort() {
  filters.page = 1
  void applyFiltersToRoute()
}

function toggleAdvancedFilters() {
  advancedFiltersOpen.value = !advancedFiltersOpen.value
}

function registrationStatusColor(status: RegistrationStatus) {
  return {
    open: 'green',
    upcoming: 'blue',
    closed: 'default',
    unknown: 'orange',
    not_applicable: 'cyan',
  }[status]
}

async function applyFiltersToRoute(replace = false) {
  const query = filters.toRouteQuery()
  const target = router.resolve({ name: 'competitions', query })
  if (target.fullPath === route.fullPath) {
    await loadCompetitions()
    return
  }
  if (replace) {
    await router.replace({ name: 'competitions', query })
  } else {
    await router.push({ name: 'competitions', query })
  }
}

watch(deadlineError, () => {
  void nextTick(syncDeadlineAccessibility)
})

watch(
  () => route.query,
  (query) => {
    filters.replaceFromRouteQuery(query)
    if (invalidFilterNotice.value && invalidFilterNoticeRoute.value !== route.fullPath) {
      dismissInvalidFilterNotice()
    }
    if (activeAdvancedFilterCount.value > 0 || deadlineError.value) {
      advancedFiltersOpen.value = true
    }

    if (filterOptionsLoaded.value) {
      const removedLabels = clearUnavailableGuidedFilters()
      if (removedLabels.length > 0) {
        filters.page = 1
        showInvalidFilterNotice(removedLabels)
        void applyFiltersToRoute(true)
        return
      }
    }

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

onMounted(() => {
  void loadFilterOptions()
})
</script>

<template>
  <section class="competition-page">
    <div class="page-heading">
      <h1 class="page-title">赛事列表</h1>
    </div>

    <form class="filter-bar" aria-label="赛事筛选" @submit.prevent="submitFilters">
      <div class="filter-primary">
        <label for="competition-keyword" class="keyword-filter">
          关键词
          <AInput
            id="competition-keyword"
            v-model:value="filters.keyword"
            allow-clear
            autocomplete="off"
            :maxlength="COMPETITION_FILTER_MAX_LENGTHS.keyword"
            name="keyword"
            placeholder="输入名称、主办方或类别…"
            type="search"
          />
        </label>
        <label for="competition-registration-status">
          报名状态
          <ASelect
            id="competition-registration-status"
            v-model:value="filters.registrationStatus"
            :options="registrationStatusOptions"
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
        <div class="filter-actions">
          <AButton type="primary" html-type="submit" :loading="loading">
            <template #icon><SearchOutlined /></template>
            查询
          </AButton>
          <AButton :disabled="loading" @click="clearFilters">
            <template #icon><ReloadOutlined /></template>
            重置
          </AButton>
        </div>
      </div>

      <div class="advanced-toggle-row">
        <AButton
          type="text"
          :aria-controls="'competition-advanced-filters'"
          :aria-expanded="advancedFiltersOpen"
          @click="toggleAdvancedFilters"
        >
          <template #icon>
            <UpOutlined v-if="advancedFiltersOpen" />
            <DownOutlined v-else />
          </template>
          {{ advancedFiltersOpen ? '收起筛选' : '更多筛选' }}
          <span v-if="activeAdvancedFilterCount">({{ activeAdvancedFilterCount }})</span>
        </AButton>
      </div>

      <AAlert
        v-if="filterOptionsError"
        data-testid="filter-options-error"
        class="filter-options-alert"
        type="warning"
        :message="filterOptionsError"
        show-icon
      >
        <template #action>
          <AButton size="small" :loading="filterOptionsLoading" @click="loadFilterOptions">
            重试
          </AButton>
        </template>
      </AAlert>

      <AAlert
        v-if="invalidFilterNotice"
        data-testid="invalid-filter-notice"
        class="filter-options-alert"
        type="info"
        :message="invalidFilterNotice"
        show-icon
        closable
        @close="dismissInvalidFilterNotice"
      />

      <div
        v-show="advancedFiltersOpen"
        id="competition-advanced-filters"
        data-testid="advanced-filters"
        class="advanced-filters"
      >
        <label for="competition-category">
          类别
          <ASelect
            id="competition-category"
            v-model:value="filters.category"
            data-testid="filter-category"
            allow-clear
            show-search
            option-filter-prop="label"
            :loading="filterOptionsLoading"
            :options="categoryOptions"
            placeholder="选择类别"
          />
        </label>
        <label for="competition-major">
          专业
          <ASelect
            id="competition-major"
            v-model:value="filters.major"
            data-testid="filter-major"
            allow-clear
            show-search
            option-filter-prop="label"
            :loading="filterOptionsLoading"
            :options="majorOptions"
            placeholder="选择专业"
          />
        </label>
        <label for="competition-grade">
          年级
          <ASelect
            id="competition-grade"
            v-model:value="filters.grade"
            data-testid="filter-grade"
            allow-clear
            show-search
            option-filter-prop="label"
            :loading="filterOptionsLoading"
            :options="gradeOptions"
            placeholder="选择年级"
          />
        </label>
        <label for="competition-tag">
          标签
          <ASelect
            id="competition-tag"
            v-model:value="filters.tag"
            data-testid="filter-tag"
            allow-clear
            show-search
            option-filter-prop="label"
            :loading="filterOptionsLoading"
            :options="tagOptions"
            placeholder="选择标签"
          />
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
        <p
          v-if="deadlineError"
          id="competition-deadline-error"
          class="field-error"
          role="alert"
        >
          {{ deadlineError }}
        </p>
      </div>
    </form>

    <div class="results-toolbar">
      <span class="result-count" aria-live="polite">{{ formattedTotal }} 项公开赛事</span>
      <label for="competition-sort">
        排序
        <ASelect
          id="competition-sort"
          v-model:value="filters.sort"
          :options="sortOptions"
          @change="changeSort"
        />
      </label>
    </div>

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
              <ATag :color="registrationStatusColor(competition.registration_status)">
                {{ formatRegistrationStatus(competition.registration_status) }}
              </ATag>
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
            <div
              v-if="competition.is_favorited || competition.is_subscribed"
              class="tag-row personal-state"
            >
              <ATag v-if="competition.is_favorited" color="gold">已收藏</ATag>
              <ATag v-if="competition.is_subscribed" color="green">已订阅</ATag>
            </div>
          </div>
          <div class="card-side">
            <p v-if="competition.registration_status_basis" class="registration-basis">
              报名状态依据：{{ formatNodeLabel(competition.registration_status_basis.node_type) }} ·
              {{ formatNodeDate(competition.registration_status_basis, true) }}
            </p>
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
