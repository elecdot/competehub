<script setup lang="ts">
import {
  ArrowRightOutlined,
  BulbOutlined,
  CalendarOutlined,
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
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { fetchRecommendations } from '@/api/client'
import type { RegistrationStatus } from '@/types/competition'
import type { RecommendationFallbackReason, RecommendationFeed } from '@/types/recommendation'
import { formatNodeDate, formatNodeLabel, formatRegistrationStatus } from '@/utils/competition'

const feed = ref<RecommendationFeed | null>(null)
const loading = ref(true)
const errorMessage = ref('')

const missingFieldLabels: Record<string, string> = {
  college: '学院',
  major: '专业',
  grade: '年级',
  interest_tags: '兴趣方向',
}

const fallbackMessage = computed(() => {
  const reason = feed.value?.fallback_reason
  if (!reason) return ''
  const messages: Record<RecommendationFallbackReason, string> = {
    anonymous: '当前无可用学生画像，展示通用可行动推荐。',
    profile_incomplete: '画像尚未完整，当前展示通用推荐。',
    no_active_rule_set: '推荐规则暂不可用，已切换为通用推荐。',
  }
  return messages[reason]
})

const missingFieldsText = computed(() => {
  if (!feed.value?.missing_fields.length) return ''
  const labels = feed.value.missing_fields.map((field) => missingFieldLabels[field] ?? field)
  return `待补充：${labels.join('、')}`
})

async function loadRecommendations() {
  loading.value = true
  errorMessage.value = ''
  try {
    feed.value = await fetchRecommendations()
  } catch {
    feed.value = null
    errorMessage.value = '推荐服务暂时无法加载。你仍可浏览全部公开赛事。'
  } finally {
    loading.value = false
  }
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

onMounted(loadRecommendations)
</script>

<template>
  <section class="competition-page recommendation-page">
    <div class="page-heading recommendation-heading">
      <div>
        <h1 class="page-title">推荐赛事</h1>
        <p class="page-description">通过受控规则和公开赛事事实解释每一项推荐。</p>
      </div>
      <template v-if="feed">
        <ATag :color="feed.recommendation_mode === 'personalized' ? 'green' : 'blue'">
          {{ feed.recommendation_mode === 'personalized' ? '个性化推荐' : '通用推荐' }}
        </ATag>
        <span v-if="feed.rule_set_version" class="rule-set-version">
          规则集 v{{ feed.rule_set_version }}
        </span>
      </template>
    </div>

    <div v-if="loading" class="state-panel" role="status" aria-live="polite">
      <span class="sr-only">正在加载推荐赛事…</span>
      <ASkeleton aria-hidden="true" active :paragraph="{ rows: 5 }" />
    </div>

    <AResult
      v-else-if="errorMessage"
      class="state-panel"
      role="alert"
      status="error"
      title="推荐赛事加载失败"
      :sub-title="errorMessage"
    >
      <template #extra>
        <div class="recommendation-error-actions">
          <AButton type="primary" @click="loadRecommendations">
            <template #icon><ReloadOutlined /></template>
            重新加载
          </AButton>
          <RouterLink class="detail-link" to="/competitions">浏览全部赛事</RouterLink>
        </div>
      </template>
    </AResult>

    <template v-else-if="feed">
      <AAlert
        v-if="fallbackMessage"
        class="recommendation-fallback"
        :message="fallbackMessage"
        :description="missingFieldsText || undefined"
        show-icon
        type="info"
      />

      <AEmpty
        v-if="feed.items.length === 0"
        class="state-panel"
        description="暂无可推荐的公开赛事"
        role="status"
      >
        <template #description><span>暂无可推荐的公开赛事</span></template>
        <RouterLink class="detail-link" to="/competitions">浏览全部赛事</RouterLink>
      </AEmpty>

      <div v-else class="competition-list recommendation-list">
        <article
          v-for="item in feed.items"
          :key="item.competition.id"
          class="competition-card recommendation-card"
        >
          <div class="card-main">
            <div class="card-meta">
              <span class="recommendation-position">#{{ item.position }}</span>
              <ATag :color="registrationStatusColor(item.competition.registration_status)">
                {{ formatRegistrationStatus(item.competition.registration_status) }}
              </ATag>
              <span>{{ item.competition.category ?? '未分类' }}</span>
            </div>
            <h2>{{ item.competition.title }}</h2>
            <div v-if="item.competition.tags.length" class="tag-row">
              <ATag v-for="tag in item.competition.tags" :key="tag" color="cyan">
                {{ tag }}
              </ATag>
            </div>
            <div class="recommendation-reason-block">
              <h3><BulbOutlined /> 推荐理由</h3>
              <ul class="recommendation-reasons">
                <li v-for="(reason, index) in item.reasons" :key="item.reason_codes[index]">
                  {{ reason }}
                </li>
              </ul>
            </div>
          </div>
          <div class="card-side">
            <p v-if="item.competition.suitable_majors.length" class="recommendation-fact">
              适合专业：{{ item.competition.suitable_majors.join('、') }}
            </p>
            <p v-if="item.competition.suitable_grades.length" class="recommendation-fact">
              适合年级：{{ item.competition.suitable_grades.join('、') }}
            </p>
            <p class="next-node">
              <CalendarOutlined />
              <template v-if="item.competition.next_node">
                {{ formatNodeLabel(item.competition.next_node.node_type) }} ·
                {{ formatNodeDate(item.competition.next_node) }}
              </template>
              <template v-else>暂无后续时间</template>
            </p>
            <RouterLink
              class="detail-link"
              :to="{ name: 'competition-detail', params: { id: item.competition.id } }"
            >
              查看赛事详情
              <ArrowRightOutlined />
            </RouterLink>
          </div>
        </article>
      </div>
    </template>
  </section>
</template>
