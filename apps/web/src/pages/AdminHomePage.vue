<script setup lang="ts">
import {
  CheckOutlined,
  CloseOutlined,
  DeleteOutlined,
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
  Form,
  FormItem,
  Input,
  InputNumber,
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
  updateCompetitionRevision,
} from '@/api/client'
import type {
  CompetitionRevision,
  CompetitionSeries,
  RevisionDraftUpdate,
  RevisionStageInput,
  RevisionTagInput,
  RevisionTimeNodeInput,
} from '@/types/admin'

const nodeTypeOptions = [
  'registration_start',
  'registration_deadline',
  'submission_deadline',
  'competition_start',
  'competition_end',
  'defense_or_review',
  'result_announcement',
  'other',
]

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
  registrationApplicability: 'applicable' as 'applicable' | 'not_applicable' | 'unknown',
  participantForms: ['individual'] as string[],
  teamSize: '',
  majorScope: 'selected' as 'all' | 'selected' | 'unknown',
  gradeScope: 'selected' as 'all' | 'selected' | 'unknown',
  majors: '',
  grades: '',
  tags: [] as RevisionTagInput[],
  stages: [initialRegistrationStage()] as RevisionStageInput[],
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

function initialRegistrationStage(): RevisionStageInput {
  return {
    stage_key: 'registration',
    stage_type: 'registration',
    label: '报名阶段',
    order: 1,
    time_nodes: [
      createNode('registration_start', 'registration-open', 'secondary', '报名开始'),
      createNode('registration_deadline', 'registration-deadline', 'primary', '报名截止'),
    ],
  }
}

function createNode(
  nodeType = 'other',
  logicalKey = '',
  prominence: 'primary' | 'secondary' = 'secondary',
  description = '',
): RevisionTimeNodeInput {
  return {
    logical_node_key: logicalKey,
    node_type: nodeType,
    occurs_at: '',
    description,
    prominence,
  }
}

function addStage() {
  const index = draft.stages.length + 1
  draft.stages.push({
    stage_key: `stage-${index}`,
    stage_type: 'competition',
    label: `阶段 ${index}`,
    order: index,
    time_nodes: [createNode()],
  })
}

function removeStage(index: number) {
  draft.stages.splice(index, 1)
  draft.stages.forEach((stage, stageIndex) => {
    stage.order = stageIndex + 1
  })
}

function addNode(stage: RevisionStageInput) {
  stage.time_nodes.push(createNode())
}

function removeNode(stage: RevisionStageInput, index: number) {
  stage.time_nodes.splice(index, 1)
}

function addTag() {
  draft.tags.push({ code: '', name: '', tag_type: 'topic' })
}

async function loadSeries() {
  series.value = await fetchCompetitionSeries()
  if (selectedSeriesId.value == null && series.value[0] != null) {
    selectedSeriesId.value = series.value[0].id
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

function revisionPayload(): RevisionDraftUpdate {
  return {
    title: draft.title,
    category: draft.category,
    organizer: draft.organizer,
    source_name: draft.sourceName,
    source_url: draft.sourceUrl,
    official_url: draft.officialUrl || null,
    summary: draft.summary,
    eligibility: draft.eligibility,
    registration_applicability: draft.registrationApplicability,
    participant_forms: draft.participantForms,
    team_size: draft.participantForms.includes('team') ? draft.teamSize || null : null,
    major_scope: draft.majorScope,
    grade_scope: draft.gradeScope,
    suitable_majors: draft.majorScope === 'selected' ? splitScope(draft.majors) : [],
    suitable_grades: draft.gradeScope === 'selected' ? splitScope(draft.grades) : [],
    tags: draft.tags,
    stages: draft.stages,
  }
}

async function saveDraft() {
  if (selectedSeriesId.value == null) {
    message.error('请先选择赛事系列')
    return
  }
  loading.value = true
  try {
    if (createdRevision.value?.revision_status === 'draft') {
      createdRevision.value = await updateCompetitionRevision(
        createdRevision.value.id,
        revisionPayload(),
      )
      message.success('候选修订已更新')
    } else {
      const payload = revisionPayload()
      const workspace = await createCompetitionEdition({
        series_id: selectedSeriesId.value,
        edition_label: draft.editionLabel,
        ...payload,
        official_url: payload.official_url ?? undefined,
        team_size: payload.team_size ?? undefined,
      })
      createdRevision.value = workspace.revision
      message.success('不可变候选修订已保存')
    }
  } catch {
    message.error('保存失败，请检查完整度、链接、受控值和时间顺序')
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
    message.error('提交失败，请检查完整度要求')
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

function differenceLabel(difference: CompetitionRevision['differences'][number]) {
  return difference.field ?? difference.stage_key ?? difference.logical_node_key ?? difference.kind
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
        <p class="page-description">编辑者维护候选修订，独立审核者确认差异与影响后发布。</p>
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

              <Form layout="vertical" class="editor-form">
                <FormItem label="届次"><Input v-model:value="draft.editionLabel" data-testid="edition-label" /></FormItem>
                <FormItem label="赛事名称"><Input v-model:value="draft.title" data-testid="edition-title" /></FormItem>
                <FormItem label="分类"><Input v-model:value="draft.category" data-testid="category" /></FormItem>
                <FormItem label="主办方"><Input v-model:value="draft.organizer" data-testid="organizer" /></FormItem>
                <FormItem label="来源名称"><Input v-model:value="draft.sourceName" data-testid="source-name" /></FormItem>
                <FormItem label="来源链接"><Input v-model:value="draft.sourceUrl" data-testid="source-url" /></FormItem>
                <FormItem label="官方网站"><Input v-model:value="draft.officialUrl" data-testid="official-url" /></FormItem>
                <FormItem label="报名适用性">
                  <Select v-model:value="draft.registrationApplicability" data-testid="registration-applicability">
                    <SelectOption value="applicable">适用</SelectOption>
                    <SelectOption value="not_applicable">不适用</SelectOption>
                    <SelectOption value="unknown">未知</SelectOption>
                  </Select>
                </FormItem>
                <FormItem label="参赛形式">
                  <Select v-model:value="draft.participantForms" mode="multiple" data-testid="participant-forms">
                    <SelectOption value="individual">个人</SelectOption>
                    <SelectOption value="team">团队</SelectOption>
                  </Select>
                </FormItem>
                <FormItem v-if="draft.participantForms.includes('team')" label="团队规模">
                  <Input v-model:value="draft.teamSize" data-testid="team-size" />
                </FormItem>
                <FormItem label="专业范围">
                  <Select v-model:value="draft.majorScope" data-testid="major-scope">
                    <SelectOption value="all">全部</SelectOption>
                    <SelectOption value="selected">指定</SelectOption>
                    <SelectOption value="unknown">未知</SelectOption>
                  </Select>
                </FormItem>
                <FormItem label="指定专业">
                  <Input v-model:value="draft.majors" data-testid="majors" :disabled="draft.majorScope !== 'selected'" placeholder="使用逗号分隔" />
                </FormItem>
                <FormItem label="年级范围">
                  <Select v-model:value="draft.gradeScope" data-testid="grade-scope">
                    <SelectOption value="all">全部</SelectOption>
                    <SelectOption value="selected">指定</SelectOption>
                    <SelectOption value="unknown">未知</SelectOption>
                  </Select>
                </FormItem>
                <FormItem label="指定年级">
                  <Input v-model:value="draft.grades" data-testid="grades" :disabled="draft.gradeScope !== 'selected'" placeholder="使用逗号分隔" />
                </FormItem>
                <FormItem label="摘要" class="span-two"><Textarea v-model:value="draft.summary" data-testid="summary" :rows="3" /></FormItem>
                <FormItem label="参赛资格" class="span-two"><Textarea v-model:value="draft.eligibility" data-testid="eligibility" :rows="3" /></FormItem>
              </Form>

              <section class="nested-editor" aria-labelledby="tags-title">
                <div class="section-heading">
                  <h3 id="tags-title">受控标签</h3>
                  <Button data-testid="add-tag" @click="addTag"><template #icon><PlusOutlined /></template>添加标签</Button>
                </div>
                <div v-for="(tag, tagIndex) in draft.tags" :key="tagIndex" class="tag-editor-row">
                  <Input v-model:value="tag.code" :data-testid="`tag-code-${tagIndex}`" placeholder="code" />
                  <Input v-model:value="tag.name" :data-testid="`tag-name-${tagIndex}`" placeholder="名称" />
                  <Input v-model:value="tag.tag_type" placeholder="类型" />
                  <Button danger :aria-label="`删除标签 ${tagIndex + 1}`" @click="draft.tags.splice(tagIndex, 1)"><template #icon><DeleteOutlined /></template></Button>
                </div>
              </section>

              <section class="nested-editor" aria-labelledby="stages-title">
                <div class="section-heading">
                  <h3 id="stages-title">阶段与单点时间节点</h3>
                  <Button data-testid="add-stage" @click="addStage"><template #icon><PlusOutlined /></template>添加阶段</Button>
                </div>
                <section v-for="(stage, stageIndex) in draft.stages" :key="stageIndex" class="stage-editor" :data-testid="`stage-editor-${stageIndex}`">
                  <div class="stage-fields">
                    <FormItem label="阶段键"><Input v-model:value="stage.stage_key" :data-testid="`stage-key-${stageIndex}`" /></FormItem>
                    <FormItem label="阶段类型"><Input v-model:value="stage.stage_type" :data-testid="`stage-type-${stageIndex}`" /></FormItem>
                    <FormItem label="显示名称"><Input v-model:value="stage.label" :data-testid="`stage-label-${stageIndex}`" /></FormItem>
                    <FormItem label="顺序"><InputNumber v-model:value="stage.order" :min="1" /></FormItem>
                    <Button v-if="draft.stages.length > 1" danger :aria-label="`删除阶段 ${stageIndex + 1}`" @click="removeStage(stageIndex)"><template #icon><DeleteOutlined /></template></Button>
                  </div>
                  <div v-for="(node, nodeIndex) in stage.time_nodes" :key="nodeIndex" class="node-editor" :data-testid="`node-editor-${stageIndex}-${nodeIndex}`">
                    <FormItem label="节点键"><Input v-model:value="node.logical_node_key" :data-testid="`node-key-${stageIndex}-${nodeIndex}`" /></FormItem>
                    <FormItem label="节点类型">
                      <Select v-model:value="node.node_type" :data-testid="`node-type-${stageIndex}-${nodeIndex}`">
                        <SelectOption v-for="option in nodeTypeOptions" :key="option" :value="option">{{ option }}</SelectOption>
                      </Select>
                    </FormItem>
                    <FormItem label="发生时间"><Input v-model:value="node.occurs_at" :data-testid="`node-time-${stageIndex}-${nodeIndex}`" type="datetime-local" /></FormItem>
                    <FormItem label="重点级别">
                      <Select v-model:value="node.prominence">
                        <SelectOption value="primary">primary</SelectOption>
                        <SelectOption value="secondary">secondary</SelectOption>
                      </Select>
                    </FormItem>
                    <FormItem label="描述"><Input v-model:value="node.description" :data-testid="`node-description-${stageIndex}-${nodeIndex}`" /></FormItem>
                    <FormItem label="级别覆盖原因"><Input v-model:value="node.prominence_override_reason" /></FormItem>
                    <Button v-if="stage.time_nodes.length > 1" danger :aria-label="`删除节点 ${nodeIndex + 1}`" @click="removeNode(stage, nodeIndex)"><template #icon><DeleteOutlined /></template></Button>
                  </div>
                  <Button :data-testid="`add-node-${stageIndex}`" @click="addNode(stage)"><template #icon><PlusOutlined /></template>添加节点</Button>
                </section>
              </section>

              <Alert
                v-if="createdRevision"
                data-testid="revision-completeness"
                :type="createdRevision.completeness.is_complete ? 'success' : 'warning'"
                show-icon
                :message="createdRevision.completeness.is_complete ? '发布完整度已满足' : `缺少：${createdRevision.completeness.missing_fields.join('、')}`"
                :description="createdRevision.completeness.warnings.length ? `提示：${createdRevision.completeness.warnings.map((warning) => `${warning.stage_key} 缺少 ${warning.missing_node_type}`).join('；')}` : undefined"
              />

              <Space class="section-actions">
                <Button data-testid="save-revision" type="primary" :disabled="createdRevision?.revision_status === 'pending_review'" @click="saveDraft">
                  <template #icon><SaveOutlined /></template>
                  {{ createdRevision?.revision_status === 'draft' ? '更新候选修订' : '保存候选修订' }}
                </Button>
                <Button data-testid="submit-revision" :disabled="createdRevision?.revision_status !== 'draft' || !createdRevision.completeness.is_complete" @click="submitDraft">
                  <template #icon><SendOutlined /></template>提交审核
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
            <Button aria-label="刷新审核队列" @click="loadPending"><template #icon><ReloadOutlined /></template></Button>
          </div>
          <div v-if="pendingRevisions.length" class="review-layout">
            <aside class="revision-list" aria-label="待审核修订">
              <Button
                v-for="revision in pendingRevisions"
                :key="revision.id"
                class="revision-list-item"
                :class="{ selected: selectedRevision?.id === revision.id }"
                :data-testid="`review-item-${revision.id}`"
                @click="selectedRevision = revision"
              >
                <strong>{{ revision.title }}</strong>
                <span>r{{ revision.revision_number }} · 提交者 #{{ revision.submitted_by_id }}</span>
              </Button>
            </aside>
            <section v-if="selectedRevision" class="review-detail">
              <div class="section-heading"><h2>{{ selectedRevision.title }}</h2><Tag color="gold">待审核</Tag></div>
              <Descriptions bordered size="small" :column="1">
                <DescriptionsItem label="来源">{{ selectedRevision.source_name }}</DescriptionsItem>
                <DescriptionsItem label="来源链接">{{ selectedRevision.source_url }}</DescriptionsItem>
                <DescriptionsItem label="公开影响"><span data-testid="review-impact">{{ displayValue(selectedRevision.impact.public_visibility) }}</span></DescriptionsItem>
                <DescriptionsItem label="影响快照">{{ displayValue(selectedRevision.impact.as_of) }}</DescriptionsItem>
              </Descriptions>
              <h3>字段、阶段与节点差异</h3>
              <div class="diff-table" data-testid="review-diff">
                <div v-for="(difference, index) in selectedRevision.differences" :key="`${difference.kind}-${differenceLabel(difference)}-${index}`">
                  <strong>{{ difference.kind }} · {{ differenceLabel(difference) }}</strong>
                  <span>{{ displayValue(difference.before) }}</span>
                  <span>{{ displayValue(difference.after) }}</span>
                </div>
              </div>
              <Alert v-if="isSelfReview" data-testid="self-review-warning" type="warning" show-icon message="提交者不能审核自己的修订" />
              <Textarea v-model:value="reviewComment" data-testid="review-comment" :rows="3" placeholder="填写审核依据与结论" />
              <Space>
                <Button data-testid="approve-revision" type="primary" :disabled="isSelfReview || !reviewComment.trim()" @click="decide('approve')"><template #icon><CheckOutlined /></template>批准发布</Button>
                <Button danger :disabled="isSelfReview || !reviewComment.trim()" @click="decide('reject')"><template #icon><CloseOutlined /></template>拒绝</Button>
                <Button :disabled="isSelfReview || !reviewComment.trim()" @click="decide('return')">退回</Button>
              </Space>
            </section>
          </div>
          <Empty v-else description="暂无待审核修订" />
        </Spin>
      </TabPane>
    </Tabs>
  </section>
</template>
