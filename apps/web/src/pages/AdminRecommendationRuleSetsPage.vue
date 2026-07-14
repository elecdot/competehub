<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue"
import {
  Alert,
  Button,
  Empty,
  Input,
  InputNumber,
  Result,
  Select,
  Switch,
  Tag,
  Textarea,
  message,
} from "ant-design-vue"

import { fetchCurrentUser } from "@/api/client"
import {
  createRecommendationRuleSet,
  fetchRecommendationRuleSets,
  previewRecommendationRuleSet,
  reviewRecommendationRuleSet,
  submitRecommendationRuleSet,
  updateRecommendationRuleSet,
} from "@/api/recommendation_rule_sets"
import type { CurrentUserResponse } from "@/types/auth"
import type {
  RecommendationPreviewPayload,
  RecommendationRule,
  RecommendationRuleCode,
  RecommendationRuleSetSummary,
} from "@/types/recommendation_rule_set"

const statusLabels: Record<string, string> = {
  draft: "草稿",
  pending_review: "待审核",
  active: "当前生效",
  rejected: "已驳回",
  returned: "已退回",
  retired: "已退役",
}

const ruleLabels: Record<RecommendationRuleCode, string> = {
  major_match: "专业匹配",
  grade_match: "年级匹配",
  interest_match: "兴趣匹配",
  deadline_urgency: "截止临近",
  general_fallback: "通用兜底",
}

const cloneableStatuses = new Set(["active", "rejected", "returned"])
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref("")
const ruleSets = ref<RecommendationRuleSetSummary[]>([])
const selectedRuleSetId = ref<number | null>(null)
const editableRules = ref<RecommendationRule[]>([])
const reviewComment = ref("")
const previewCompetitionIds = ref("")
const previewPayload = reactive({
  scenario: "personalized" as "personalized" | "general",
  college: "计算机学院",
  major: "软件工程",
  grade: "大二",
  interest_tags: "人工智能",
})
const previewResult = ref<RecommendationPreviewPayload | null>(null)
const currentUser = ref<CurrentUserResponse | null>(null)

const hasEditorCapability = computed(() =>
  currentUser.value?.capabilities.includes("recommendation_editor") ?? false,
)
const hasReviewerCapability = computed(() =>
  currentUser.value?.capabilities.includes("recommendation_reviewer") ?? false,
)
const canAccessWorkbench = computed(
  () => hasEditorCapability.value || hasReviewerCapability.value,
)

const selectedRuleSet = computed(
  () => ruleSets.value.find((item) => item.rule_set_id === selectedRuleSetId.value) ?? null,
)
const activeRuleSet = computed(() => ruleSets.value.find((item) => item.status === "active") ?? null)
const canCloneSelected = computed(
  () =>
    hasEditorCapability.value &&
    selectedRuleSet.value !== null &&
    cloneableStatuses.has(selectedRuleSet.value.status),
)
const canEditSelected = computed(
  () =>
    hasEditorCapability.value &&
    selectedRuleSet.value?.status === "draft" &&
    selectedRuleSet.value.created_by?.id === currentUser.value?.id,
)
const isSelfReview = computed(
  () =>
    selectedRuleSet.value?.status === "pending_review" &&
    selectedRuleSet.value.submitted_by?.id === currentUser.value?.id,
)
const canReviewSelected = computed(
  () =>
    hasReviewerCapability.value &&
    selectedRuleSet.value?.status === "pending_review" &&
    !isSelfReview.value,
)
const selectedImpactEntries = computed(() =>
  selectedRuleSet.value?.impact_summary ? Object.entries(selectedRuleSet.value.impact_summary) : [],
)
const selectedDifference = computed(() => selectedRuleSet.value?.difference_snapshot ?? null)

watch(selectedRuleSet, (ruleSet) => {
  editableRules.value = ruleSet ? ruleSet.rules.map((rule) => ({ ...rule })) : []
  previewResult.value = null
})

onMounted(() => {
  void initializeWorkbench()
})

async function initializeWorkbench() {
  loading.value = true
  errorMessage.value = ""
  try {
    currentUser.value = await fetchCurrentUser()
    if (canAccessWorkbench.value) {
      await loadRuleSets()
    }
  } catch (error) {
    errorMessage.value = errorToMessage(error)
  } finally {
    loading.value = false
  }
}

async function loadRuleSets() {
  loading.value = true
  errorMessage.value = ""
  try {
    const payload = await fetchRecommendationRuleSets()
    ruleSets.value = payload.items
    selectedRuleSetId.value =
      selectedRuleSetId.value ??
      payload.items.find((item) => item.status === "active")?.rule_set_id ??
      payload.items[0]?.rule_set_id ??
      null
  } catch (error) {
    errorMessage.value = errorToMessage(error)
  } finally {
    loading.value = false
  }
}

async function cloneSelectedRuleSet() {
  if (!selectedRuleSet.value) return
  saving.value = true
  errorMessage.value = ""
  try {
    const created = await createRecommendationRuleSet(selectedRuleSet.value.rule_set_id)
    message.success(`已创建 v${created.version} 草稿`)
    await loadRuleSets()
    selectedRuleSetId.value = created.rule_set_id
  } catch (error) {
    errorMessage.value = errorToMessage(error)
  } finally {
    saving.value = false
  }
}

async function saveDraft() {
  if (!selectedRuleSet.value) return
  saving.value = true
  errorMessage.value = ""
  try {
    const saved = await updateRecommendationRuleSet(selectedRuleSet.value.rule_set_id, editableRules.value)
    message.success(`已保存 v${saved.version}`)
    await loadRuleSets()
  } catch (error) {
    errorMessage.value = errorToMessage(error)
  } finally {
    saving.value = false
  }
}

async function submitDraft() {
  if (!selectedRuleSet.value) return
  saving.value = true
  errorMessage.value = ""
  try {
    const submitted = await submitRecommendationRuleSet(selectedRuleSet.value.rule_set_id)
    message.success(`v${submitted.version} 已提交审核`)
    await loadRuleSets()
  } catch (error) {
    errorMessage.value = errorToMessage(error)
  } finally {
    saving.value = false
  }
}

async function decide(action: "approve" | "reject" | "return") {
  if (!selectedRuleSet.value) return
  saving.value = true
  errorMessage.value = ""
  try {
    const reviewed = await reviewRecommendationRuleSet(
      selectedRuleSet.value.rule_set_id,
      action,
      reviewComment.value,
    )
    message.success(`v${reviewed.version} 已处理`)
    reviewComment.value = ""
    await loadRuleSets()
  } catch (error) {
    errorMessage.value = errorToMessage(error)
  } finally {
    saving.value = false
  }
}

async function runPreview() {
  if (!selectedRuleSet.value) return
  saving.value = true
  errorMessage.value = ""
  previewResult.value = null
  try {
    const competitionIds = previewCompetitionIds.value
      .split(",")
      .map((item) => Number(item.trim()))
      .filter((item) => Number.isInteger(item) && item > 0)
    previewResult.value = await previewRecommendationRuleSet(selectedRuleSet.value.rule_set_id, {
      scenario: previewPayload.scenario,
      competition_ids: competitionIds,
      ...(previewPayload.scenario === "personalized"
        ? {
            synthetic_profile: {
              college: previewPayload.college,
              major: previewPayload.major,
              grade: previewPayload.grade,
              interest_tags: previewPayload.interest_tags
                .split(",")
                .map((item) => item.trim())
                .filter(Boolean),
            },
          }
        : {}),
    })
  } catch (error) {
    errorMessage.value = errorToMessage(error)
  } finally {
    saving.value = false
  }
}

function updateDeadlineDays(rule: RecommendationRule, value: number | null) {
  if (rule.code !== "deadline_urgency") return
  rule.conditions = {
    operator: "within_days",
    min_days: 0,
    max_days: value ?? 0,
  }
}

function conditionLabel(rule: RecommendationRule) {
  if (rule.conditions.operator === "within_days") {
    return `0-${rule.conditions.max_days} 天`
  }
  return rule.conditions.operator
}

function actorLabel(actor: { id: number; display_name: string | null } | null) {
  return actor ? `${actor.display_name ?? "未命名用户"} (#${actor.id})` : "—"
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString("zh-CN") : "—"
}

function impactLabel(key: string) {
  const labels: Record<string, string> = {
    enabled_rule_count_delta: "启用规则数变化",
    changed_rule_codes: "变更规则代码",
    active_version_at_submission: "提交时 active 版本",
    candidate_version: "候选版本",
  }
  return labels[key] ?? key
}

function errorToMessage(error: unknown) {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { data?: { error?: { message?: string } } } }).response
    return response?.data?.error?.message ?? "请求失败"
  }
  return error instanceof Error ? error.message : "请求失败"
}
</script>

<template>
  <section class="rule-governance-page">
    <header class="page-heading">
      <div>
        <h1 class="page-title">推荐规则治理</h1>
        <p class="page-description">
          查看版本历史、克隆候选、编辑受控规则、运行 synthetic preview，并完成独立审核。
        </p>
      </div>
      <Button data-testid="governance-refresh" :loading="loading" @click="initializeWorkbench">
        刷新
      </Button>
    </header>

    <Alert v-if="errorMessage" type="error" show-icon :message="errorMessage" />

    <Result
      v-if="currentUser && !canAccessWorkbench"
      status="403"
      title="无权访问推荐规则治理"
      sub-title="当前账号缺少 recommendation_editor 或 recommendation_reviewer capability。"
    />

    <div v-else-if="canAccessWorkbench" class="rule-workbench">
      <aside class="version-panel">
        <div class="panel-heading">
          <h2>版本历史</h2>
          <Button
            data-testid="clone-rule-set"
            type="primary"
            :disabled="!canCloneSelected"
            :loading="saving"
            @click="cloneSelectedRuleSet"
          >
            克隆为草稿
          </Button>
        </div>
        <Empty v-if="!loading && ruleSets.length === 0" description="暂无规则集版本" />
        <button
          v-for="ruleSet in ruleSets"
          :key="ruleSet.rule_set_id"
          class="version-row"
          :class="{ 'version-row-active': ruleSet.rule_set_id === selectedRuleSetId }"
          :data-testid="`rule-set-v${ruleSet.version}`"
          type="button"
          @click="selectedRuleSetId = ruleSet.rule_set_id"
        >
          <span>v{{ ruleSet.version }}</span>
          <Tag :color="ruleSet.status === 'active' ? 'green' : ruleSet.is_stale ? 'red' : 'blue'">
            {{ statusLabels[ruleSet.status] }}
          </Tag>
          <small>
            source v{{ ruleSet.cloned_from_version ?? "-" }} / base v{{
              ruleSet.base_version ?? "-"
            }}
          </small>
        </button>
      </aside>

      <main v-if="selectedRuleSet" class="rule-detail-panel">
        <section class="state-strip">
          <span>当前 active：v{{ activeRuleSet?.version ?? "-" }}</span>
          <span>候选基线：v{{ selectedRuleSet.base_version ?? "-" }}</span>
          <Tag v-if="selectedRuleSet.is_stale" color="red">基线已过期</Tag>
          <Tag v-else color="green">基线一致</Tag>
        </section>

        <section class="governance-evidence" data-testid="governance-evidence">
          <h2>治理证据</h2>
          <dl>
            <div><dt>状态</dt><dd>{{ statusLabels[selectedRuleSet.status] }}</dd></div>
            <div><dt>创建者</dt><dd>{{ actorLabel(selectedRuleSet.created_by) }}</dd></div>
            <div><dt>提交者</dt><dd>{{ actorLabel(selectedRuleSet.submitted_by) }}</dd></div>
            <div><dt>审核者</dt><dd>{{ actorLabel(selectedRuleSet.reviewed_by) }}</dd></div>
            <div><dt>创建时间</dt><dd>{{ formatDate(selectedRuleSet.created_at) }}</dd></div>
            <div><dt>提交时间</dt><dd>{{ formatDate(selectedRuleSet.submitted_at) }}</dd></div>
            <div><dt>决定时间</dt><dd>{{ formatDate(selectedRuleSet.decided_at) }}</dd></div>
            <div><dt>激活时间</dt><dd>{{ formatDate(selectedRuleSet.activated_at) }}</dd></div>
            <div><dt>退役时间</dt><dd>{{ formatDate(selectedRuleSet.retired_at) }}</dd></div>
            <div><dt>审核状态</dt><dd>{{ selectedRuleSet.terminal_review_status ?? "—" }}</dd></div>
            <div><dt>审核意见</dt><dd>{{ selectedRuleSet.review_comment ?? "—" }}</dd></div>
            <div><dt>来源版本</dt><dd>v{{ selectedRuleSet.cloned_from_version ?? "—" }}</dd></div>
            <div><dt>基线版本</dt><dd>v{{ selectedRuleSet.base_version ?? "—" }}</dd></div>
            <div><dt>当前 active</dt><dd>v{{ selectedRuleSet.active_version ?? "—" }}</dd></div>
          </dl>
        </section>

        <Alert
          v-if="selectedRuleSet.status === 'draft' && !canEditSelected"
          type="info"
          show-icon
          message="只有此草稿的创建者可保存或提交。"
        />
        <Alert
          v-if="isSelfReview"
          type="warning"
          show-icon
          message="提交者不能审核自己的候选版本，请使用独立 reviewer 账号。"
        />

        <section class="rules-section">
          <div class="panel-heading">
            <h2>规则配置</h2>
            <div class="button-row">
              <Button
                data-testid="save-rule-set"
                :disabled="!canEditSelected"
                :loading="saving"
                @click="saveDraft"
              >保存草稿</Button>
              <Button
                data-testid="submit-rule-set"
                type="primary"
                :disabled="!canEditSelected"
                :loading="saving"
                @click="submitDraft"
              >
                提交审核
              </Button>
            </div>
          </div>

          <div class="rule-table" role="table" aria-label="推荐规则配置">
            <div class="rule-table-row rule-table-head" role="row">
              <span>规则</span>
              <span>启用</span>
              <span>权重</span>
              <span>条件</span>
              <span>理由模板</span>
            </div>
            <div
              v-for="rule in editableRules"
              :key="rule.code"
              class="rule-table-row"
              role="row"
              :data-testid="`rule-${rule.code}`"
            >
              <label>
                <span>{{ ruleLabels[rule.code] }}</span>
                <Input v-model:value="rule.name" :disabled="!canEditSelected" />
              </label>
              <Switch v-model:checked="rule.enabled" :disabled="!canEditSelected" />
              <InputNumber
                v-model:value="rule.weight"
                :data-testid="`rule-weight-${rule.code}`"
                :disabled="!canEditSelected"
                :min="1"
                :max="100"
              />
              <div>
                <InputNumber
                  v-if="rule.code === 'deadline_urgency'"
                  :value="rule.conditions.operator === 'within_days' ? rule.conditions.max_days : 0"
                  :disabled="!canEditSelected"
                  :min="0"
                  @change="(value) => updateDeadlineDays(rule, value as number | null)"
                />
                <span v-else>{{ conditionLabel(rule) }}</span>
              </div>
              <Input v-model:value="rule.reason_template" :disabled="!canEditSelected" />
            </div>
          </div>
        </section>

        <section class="review-grid">
          <div class="governance-box">
            <h2>差异</h2>
            <dl v-if="selectedDifference">
              <div><dt>基线版本</dt><dd>v{{ selectedDifference.base_version }}</dd></div>
              <div><dt>候选版本</dt><dd>v{{ selectedDifference.candidate_version }}</dd></div>
              <div>
                <dt>变更规则</dt>
                <dd>{{ selectedDifference.changed_rules.map((item) => item.code).join(", ") || "无" }}</dd>
              </div>
              <div><dt>新增规则</dt><dd>{{ selectedDifference.added_rules.length }}</dd></div>
              <div><dt>移除规则</dt><dd>{{ selectedDifference.removed_rules.length }}</dd></div>
            </dl>
            <p v-else>当前状态没有差异快照。</p>
            <details v-if="selectedDifference">
              <summary>技术 JSON 详情</summary>
            <pre>{{ JSON.stringify(selectedRuleSet.difference_snapshot, null, 2) }}</pre>
            </details>
          </div>
          <div class="governance-box">
            <h2>影响</h2>
            <dl>
              <div v-for="[key, value] in selectedImpactEntries" :key="key">
                <dt>{{ impactLabel(key) }}</dt>
                <dd>{{ value }}</dd>
              </div>
            </dl>
          </div>
        </section>

        <section class="action-panel">
          <h2>审核决定</h2>
          <Textarea
            v-model:value="reviewComment"
            data-testid="review-comment"
            :disabled="!canReviewSelected"
            :rows="2"
            placeholder="填写审核意见"
          />
          <div class="button-row">
            <Button :disabled="!canReviewSelected" :loading="saving" @click="decide('return')">退回</Button>
            <Button danger :disabled="!canReviewSelected" :loading="saving" @click="decide('reject')">
              驳回
            </Button>
            <Button
              data-testid="approve-rule-set"
              type="primary"
              :disabled="!canReviewSelected"
              :loading="saving"
              @click="decide('approve')"
            >
              通过并激活
            </Button>
          </div>
        </section>

        <section class="action-panel">
          <h2>Preview</h2>
          <div class="preview-form">
            <label>
              场景
              <Select
                v-model:value="previewPayload.scenario"
                :options="[
                  { value: 'personalized', label: 'personalized' },
                  { value: 'general', label: 'general' },
                ]"
              />
            </label>
            <label>
              赛事 ID
              <Input
                v-model:value="previewCompetitionIds"
                data-testid="preview-competition-ids"
                placeholder="例如 201,305"
              />
            </label>
            <template v-if="previewPayload.scenario === 'personalized'">
              <label>
                学院
                <Input v-model:value="previewPayload.college" data-testid="preview-college" />
              </label>
              <label>
                专业
                <Input v-model:value="previewPayload.major" data-testid="preview-major" />
              </label>
              <label>
                年级
                <Input v-model:value="previewPayload.grade" data-testid="preview-grade" />
              </label>
              <label>
                兴趣标签
                <Input
                  v-model:value="previewPayload.interest_tags"
                  data-testid="preview-interest-tags"
                  placeholder="逗号分隔"
                />
              </label>
            </template>
          </div>
          <Button data-testid="run-preview" type="primary" :loading="saving" @click="runPreview">
            运行 preview
          </Button>
          <div v-if="previewResult" class="preview-results" data-testid="preview-results">
            <h3>v{{ previewResult.version }} / {{ previewResult.scenario }}</h3>
            <ol>
              <li v-for="item in previewResult.results" :key="item.competition_id">
                #{{ item.position }} {{ item.competition.title }}
                <span v-if="item.competition.edition_label">（{{ item.competition.edition_label }}）</span>
                · ID {{ item.competition.id }} · reason codes：{{ item.reason_codes.join(", ") }}
                · {{ item.reasons.join("；") }}
              </li>
            </ol>
          </div>
        </section>
      </main>
    </div>
  </section>
</template>

<style scoped>
.rule-governance-page,
.rule-detail-panel,
.rules-section,
.action-panel,
.governance-box,
.governance-evidence {
  display: grid;
  gap: 16px;
}

.rule-workbench {
  align-items: start;
  display: grid;
  gap: 18px;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
}

.version-panel,
.rule-detail-panel,
.rules-section,
.action-panel,
.governance-box,
.governance-evidence {
  background: #ffffff;
  border: 1px solid #dde2e7;
  border-radius: 8px;
  padding: 16px;
}

.panel-heading,
.button-row,
.state-strip {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: space-between;
}

.panel-heading h2,
.governance-box h2,
.governance-evidence h2,
.action-panel h2 {
  font-size: 16px;
  margin: 0;
}

.version-row {
  background: transparent;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: pointer;
  display: grid;
  gap: 6px;
  margin-top: 10px;
  padding: 10px;
  text-align: left;
  width: 100%;
}

.version-row-active {
  border-color: #176b4d;
  box-shadow: inset 3px 0 0 #176b4d;
}

.version-row small,
.state-strip {
  color: #52606d;
}

.rule-table {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow-x: auto;
}

.rule-table-row {
  align-items: center;
  display: grid;
  gap: 10px;
  grid-template-columns: minmax(160px, 1.2fr) 80px 100px 120px minmax(220px, 1.7fr);
  min-width: 860px;
  padding: 10px;
}

.rule-table-row + .rule-table-row {
  border-top: 1px solid #edf0f3;
}

.rule-table-head {
  background: #f8fafc;
  color: #52606d;
  font-size: 13px;
  font-weight: 700;
}

.rule-table label,
.preview-form label {
  display: grid;
  gap: 6px;
}

.review-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.governance-box pre {
  background: #f8fafc;
  border-radius: 6px;
  margin: 0;
  max-height: 320px;
  overflow: auto;
  padding: 12px;
}

.governance-box dl,
.governance-evidence dl,
.preview-results ol {
  display: grid;
  gap: 8px;
  margin: 0;
}

.governance-box dl div {
  display: grid;
  gap: 4px;
  grid-template-columns: minmax(160px, 1fr) minmax(0, 1fr);
}

.governance-evidence dl {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.governance-evidence dl div {
  border-bottom: 1px solid #edf0f3;
  display: grid;
  gap: 6px;
  grid-template-columns: minmax(90px, 120px) minmax(0, 1fr);
  padding: 8px 0;
}

.governance-evidence dt {
  color: #52606d;
  font-weight: 700;
}

.governance-evidence dd {
  margin: 0;
  overflow-wrap: anywhere;
}

.governance-box dt {
  color: #52606d;
  font-weight: 700;
}

.governance-box dd {
  margin: 0;
  overflow-wrap: anywhere;
}

.preview-form {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.preview-results {
  background: #f8fafc;
  border-radius: 6px;
  padding: 12px;
}

.preview-results h3 {
  font-size: 15px;
  margin: 0 0 8px;
}

@media (max-width: 920px) {
  .rule-workbench,
  .review-grid,
  .governance-evidence dl,
  .preview-form {
    grid-template-columns: 1fr;
  }
}
</style>
