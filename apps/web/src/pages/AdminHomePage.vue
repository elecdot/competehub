<script setup lang="ts">
import {
  CheckOutlined,
  CloseOutlined,
  PlusOutlined,
  ReloadOutlined,
  SaveOutlined,
  SendOutlined,
} from '@ant-design/icons-vue'
import {
  Alert,
  Button,
  Descriptions,
  DescriptionsItem,
  Empty,
  Input,
  message,
  Result,
  Select,
  SelectOption,
  Space,
  Spin,
  TabPane,
  Tabs,
  Tag,
  Textarea,
} from 'ant-design-vue'
import { computed, onMounted, reactive, ref } from 'vue'

import {
  createCompetitionEdition,
  createCompetitionSeries,
  fetchCompetitionSeries,
  fetchCurrentUser,
  fetchPendingCompetitionRevisions,
  reviewCompetitionRevision,
  submitCompetitionRevision,
} from '@/api/client'
import type { CompetitionRevision, CompetitionSeries } from '@/types/admin'

const activeTab = ref('editor')
const accessDenied = ref(false)
const loading = ref(false)
const series = ref<CompetitionSeries[]>([])
const selectedSeriesId = ref<number>()
const newSeriesName = ref('')
const currentUserId = ref<number>()
const createdRevision = ref<CompetitionRevision>()
const pendingRevisions = ref<CompetitionRevision[]>([])
const selectedRevision = ref<CompetitionRevision>()
const reviewComment = ref('')

const draft = reactive({
  editionLabel: '',
  title: '',
  category: '',
  organizer: '',
  sourceName: '',
  sourceUrl: '',
  officialUrl: '',
  summary: '',
  eligibility: '',
  participantForms: ['individual'] as string[],
  teamSize: '',
  majors: '',
  grades: '',
  registrationStart: '',
  registrationDeadline: '',
})

const isSelfReview = computed(
  () =>
    selectedRevision.value?.submitted_by_id != null &&
    selectedRevision.value.submitted_by_id === currentUserId.value,
)

onMounted(async () => {
  try {
    const user = await fetchCurrentUser()
    currentUserId.value = user.id
    if (
      user.role !== 'admin' ||
      !user.capabilities.some((capability) =>
        ['competition_editor', 'competition_reviewer', 'competition_maintainer'].includes(
          capability,
        ),
      )
    ) {
      accessDenied.value = true
      return
    }
    await Promise.all([loadSeries(), loadPending()])
  } catch {
    accessDenied.value = true
  }
})

async function loadSeries() {
  series.value = await fetchCompetitionSeries()
  const [firstSeries] = series.value
  if (selectedSeriesId.value == null && firstSeries != null) {
    selectedSeriesId.value = firstSeries.id
  }
}

async function addSeries() {
  if (!newSeriesName.value.trim()) return
  loading.value = true
  try {
    const created = await createCompetitionSeries(newSeriesName.value.trim())
    series.value = [...series.value, created]
    selectedSeriesId.value = created.id
    newSeriesName.value = ''
    message.success('赛事系列已创建')
  } catch {
    message.error('赛事系列创建失败，请检查名称是否重复')
  } finally {
    loading.value = false
  }
}

function splitScope(value: string) {
  return value
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

async function saveDraft() {
  if (selectedSeriesId.value == null) {
    message.error('请先选择赛事系列')
    return
  }
  loading.value = true
  try {
    const workspace = await createCompetitionEdition({
      series_id: selectedSeriesId.value,
      edition_label: draft.editionLabel,
      title: draft.title,
      category: draft.category,
      organizer: draft.organizer,
      source_name: draft.sourceName,
      source_url: draft.sourceUrl,
      official_url: draft.officialUrl || undefined,
      summary: draft.summary,
      eligibility: draft.eligibility,
      participant_forms: draft.participantForms,
      team_size: draft.participantForms.includes('team') ? draft.teamSize : undefined,
      suitable_majors: splitScope(draft.majors),
      suitable_grades: splitScope(draft.grades),
      stages: [
        {
          stage_key: 'registration',
          stage_type: 'registration',
          label: '报名阶段',
          order: 1,
          time_nodes: [
            {
              logical_node_key: 'registration-open',
              node_type: 'registration_start',
              occurs_at: draft.registrationStart,
              description: '报名开始',
              prominence: 'secondary',
            },
            {
              logical_node_key: 'registration-deadline',
              node_type: 'registration_deadline',
              occurs_at: draft.registrationDeadline,
              description: '报名截止',
              prominence: 'primary',
            },
          ],
        },
      ],
    })
    createdRevision.value = workspace.revision
    message.success('不可变候选修订已保存')
  } catch {
    message.error('保存失败，请检查必填字段、链接和时间顺序')
  } finally {
    loading.value = false
  }
}

async function submitDraft() {
  if (createdRevision.value == null) return
  loading.value = true
  try {
    createdRevision.value = await submitCompetitionRevision(createdRevision.value.id)
    await loadPending()
    message.success('修订已提交独立审核')
  } catch {
    message.error('提交失败，请检查完整性要求')
  } finally {
    loading.value = false
  }
}

async function loadPending() {
  pendingRevisions.value = await fetchPendingCompetitionRevisions()
  if (selectedRevision.value != null) {
    selectedRevision.value = pendingRevisions.value.find(
      (revision) => revision.id === selectedRevision.value?.id,
    )
  }
}

async function decide(action: 'approve' | 'reject' | 'return') {
  if (selectedRevision.value == null || !reviewComment.value.trim()) return
  loading.value = true
  try {
    await reviewCompetitionRevision(
      selectedRevision.value.id,
      action,
      reviewComment.value.trim(),
    )
    message.success(action === 'approve' ? '修订已发布' : '审核决定已记录')
    reviewComment.value = ''
    selectedRevision.value = undefined
    await loadPending()
  } catch {
    message.error(isSelfReview.value ? '提交者不能审核自己的修订' : '审核操作失败')
  } finally {
    loading.value = false
  }
}

function displayValue(value: unknown) {
  if (value == null || value === '') return '未设置'
  if (Array.isArray(value)) return value.join('、') || '空列表'
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}
</script>

<template>
  <section class="admin-workbench">
    <header class="page-heading">
      <div>
        <h1 class="page-title">赛事发布工作台</h1>
        <p class="page-description">编辑者提交不可变修订，独立审核者确认差异与影响后发布。</p>
      </div>
      <Tag color="green">P1</Tag>
    </header>

    <Result
      v-if="accessDenied"
      status="403"
      title="无权访问赛事发布工作台"
      sub-title="当前账号缺少赛事编辑、审核或维护权限。"
    />

    <Tabs v-else v-model:active-key="activeTab" :animated="false" class="workbench-tabs">
      <TabPane key="editor" tab="编辑发布">
        <Spin :spinning="loading">
          <div class="workbench-grid">
            <section class="workbench-section" aria-labelledby="series-title">
              <h2 id="series-title">赛事系列</h2>
              <div class="inline-form">
                <Select
                  v-model:value="selectedSeriesId"
                  data-testid="series-select"
                  placeholder="选择赛事系列"
                >
                  <SelectOption v-for="item in series" :key="item.id" :value="item.id">
                    {{ item.canonical_name }}
                  </SelectOption>
                </Select>
                <Input
                  v-model:value="newSeriesName"
                  data-testid="series-name"
                  placeholder="新系列名称"
                  @press-enter="addSeries"
                />
                <Button data-testid="create-series" @click="addSeries">
                  <template #icon><PlusOutlined /></template>
                  创建系列
                </Button>
              </div>
            </section>

            <section class="workbench-section" aria-labelledby="revision-title">
              <div class="section-heading">
                <h2 id="revision-title">首个届次修订</h2>
                <Tag v-if="createdRevision" color="blue">
                  {{ createdRevision.revision_status }} · r{{ createdRevision.revision_number }}
                </Tag>
              </div>
              <div class="editor-form">
                <label>届次<input v-model="draft.editionLabel" data-testid="edition-label" /></label>
                <label>赛事名称<input v-model="draft.title" data-testid="edition-title" /></label>
                <label>分类<input v-model="draft.category" data-testid="category" /></label>
                <label>主办方<input v-model="draft.organizer" data-testid="organizer" /></label>
                <label>来源名称<input v-model="draft.sourceName" data-testid="source-name" /></label>
                <label>来源链接<input v-model="draft.sourceUrl" data-testid="source-url" type="url" /></label>
                <label>官方网站<input v-model="draft.officialUrl" data-testid="official-url" type="url" /></label>
                <label>参赛形式
                  <Select v-model:value="draft.participantForms" mode="multiple" data-testid="participant-forms">
                    <SelectOption value="individual">个人</SelectOption>
                    <SelectOption value="team">团队</SelectOption>
                  </Select>
                </label>
                <label v-if="draft.participantForms.includes('team')">团队规模<input v-model="draft.teamSize" /></label>
                <label>适用专业<input v-model="draft.majors" data-testid="majors" placeholder="使用逗号分隔" /></label>
                <label>适用年级<input v-model="draft.grades" data-testid="grades" placeholder="使用逗号分隔" /></label>
                <label>报名开始<input v-model="draft.registrationStart" data-testid="registration-start" type="datetime-local" /></label>
                <label>报名截止<input v-model="draft.registrationDeadline" data-testid="registration-deadline" type="datetime-local" /></label>
                <label class="span-two">摘要<textarea v-model="draft.summary" data-testid="summary" rows="3" /></label>
                <label class="span-two">参赛资格<textarea v-model="draft.eligibility" data-testid="eligibility" rows="3" /></label>
              </div>
              <Space class="section-actions">
                <Button data-testid="save-revision" type="primary" @click="saveDraft">
                  <template #icon><SaveOutlined /></template>
                  保存候选修订
                </Button>
                <Button
                  data-testid="submit-revision"
                  :disabled="createdRevision?.revision_status !== 'draft'"
                  @click="submitDraft"
                >
                  <template #icon><SendOutlined /></template>
                  提交审核
                </Button>
              </Space>
            </section>
          </div>
        </Spin>
      </TabPane>

      <TabPane key="reviewer" tab="审核队列">
        <Spin :spinning="loading">
          <div class="review-toolbar">
            <span>待审核 {{ pendingRevisions.length }} 项</span>
            <Button aria-label="刷新审核队列" @click="loadPending">
              <template #icon><ReloadOutlined /></template>
            </Button>
          </div>
          <div v-if="pendingRevisions.length" class="review-layout">
            <aside class="revision-list" aria-label="待审核修订">
              <button
                v-for="revision in pendingRevisions"
                :key="revision.id"
                type="button"
                :class="{ selected: selectedRevision?.id === revision.id }"
                :data-testid="`review-item-${revision.id}`"
                @click="selectedRevision = revision"
              >
                <strong>{{ revision.title }}</strong>
                <span>r{{ revision.revision_number }} · 提交者 #{{ revision.submitted_by_id }}</span>
              </button>
            </aside>
            <section v-if="selectedRevision" class="review-detail">
              <div class="section-heading">
                <h2>{{ selectedRevision.title }}</h2>
                <Tag color="gold">待审核</Tag>
              </div>
              <Descriptions bordered size="small" :column="1">
                <DescriptionsItem label="来源">{{ selectedRevision.source_name }}</DescriptionsItem>
                <DescriptionsItem label="来源链接">{{ selectedRevision.source_url }}</DescriptionsItem>
                <DescriptionsItem label="公开影响">
                  {{ displayValue(selectedRevision.impact.public_visibility) }}
                </DescriptionsItem>
                <DescriptionsItem label="影响快照">
                  {{ displayValue(selectedRevision.impact.as_of) }}
                </DescriptionsItem>
              </Descriptions>
              <h3>差异</h3>
              <div class="diff-table">
                <div v-for="difference in selectedRevision.differences" :key="difference.field">
                  <strong>{{ difference.field }}</strong>
                  <span>{{ displayValue(difference.before) }}</span>
                  <span>{{ displayValue(difference.after) }}</span>
                </div>
              </div>
              <Alert
                v-if="isSelfReview"
                data-testid="self-review-warning"
                type="warning"
                show-icon
                message="提交者不能审核自己的修订"
              />
              <Textarea
                v-model:value="reviewComment"
                data-testid="review-comment"
                :rows="3"
                placeholder="填写审核依据与结论"
              />
              <Space>
                <Button
                  data-testid="approve-revision"
                  type="primary"
                  :disabled="isSelfReview || !reviewComment.trim()"
                  @click="decide('approve')"
                ><template #icon><CheckOutlined /></template>批准发布</Button>
                <Button
                  danger
                  :disabled="isSelfReview || !reviewComment.trim()"
                  @click="decide('reject')"
                ><template #icon><CloseOutlined /></template>拒绝</Button>
                <Button :disabled="isSelfReview || !reviewComment.trim()" @click="decide('return')">
                  退回
                </Button>
              </Space>
            </section>
          </div>
          <Empty v-else description="暂无待审核修订" />
        </Spin>
      </TabPane>
    </Tabs>
  </section>
</template>
