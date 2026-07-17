<script setup lang="ts">
import {
  LoginOutlined,
  LogoutOutlined,
  ReloadOutlined,
  SaveOutlined,
  UserAddOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'
import {
  Alert as AAlert,
  Button as AButton,
  Form as AForm,
  FormItem as AFormItem,
  Result as AResult,
  Select as ASelect,
  Skeleton as ASkeleton,
  Tag as ATag,
  Textarea as ATextarea,
} from 'ant-design-vue'
import { isAxiosError } from 'axios'
import { computed, nextTick, onMounted, ref } from 'vue'

import { fetchCurrentProfile, fetchProfileOptions, updateCurrentProfile } from '@/api/client'
import { useAuthStore } from '@/stores/auth_store'
import type { ProfileOptions, StudentProfile } from '@/types/auth'

const auth = useAuthStore()
const profile = ref<StudentProfile | null>(null)
const profileOptions = ref<ProfileOptions | null>(null)
const profileLoading = ref(false)
const profileSaving = ref(false)
const profileLoadError = ref('')
const profileSaveError = ref('')
const profileSaveSuccess = ref('')
const invalidProfileField = ref('')
const logoutError = ref('')

const profileForm = ref({
  college: undefined as string | undefined,
  major: undefined as string | undefined,
  grade: undefined as string | undefined,
  interest_tags: [] as string[],
  competition_experience: '',
  goal_preferences: [] as string[],
})

const missingFieldLabels: Record<string, string> = {
  college: '学院',
  major: '专业',
  grade: '年级',
  interest_tags: '兴趣标签',
}

const goalPreferenceOptions = toSelectOptions([
  '保研',
  '就业',
  '科研',
  '创业',
  '提升技术能力',
  '积累项目经历',
  '获奖加分',
])

const displayName = computed(() => auth.currentUser?.displayName || `用户 ${auth.currentUser?.id}`)
const userInitial = computed(() => displayName.value.trim().slice(0, 1).toUpperCase() || 'U')
const identityLabel = computed(() => {
  switch (auth.currentUser?.role) {
    case 'student':
      return '学生'
    case 'admin':
      return '管理员'
    case 'teacher':
      return '教师'
    case 'organizer':
      return '组织者'
    default:
      return '未登录'
  }
})
const missingFields = computed(() =>
  (profile.value?.missing_fields ?? []).map((field) => missingFieldLabels[field] ?? field),
)
const isProfileRecommendationReady = computed(
  () => profile.value?.profile_status === 'recommendation_ready',
)
const profileStatusText = computed(() =>
  isProfileRecommendationReady.value ? '推荐资料已完善' : '资料待完善',
)
const collegeOptions = computed(() => toSelectOptions(profileOptions.value?.colleges ?? []))
const gradeOptions = computed(() => toSelectOptions(profileOptions.value?.grades ?? []))
const interestTagOptions = computed(() => toSelectOptions(profileOptions.value?.interest_tags ?? []))
const majorOptions = computed(() => {
  const options = profileOptions.value
  if (!options) {
    return []
  }
  if (profileForm.value.college) {
    return toSelectOptions(options.majors_by_college[profileForm.value.college] ?? [])
  }
  return toSelectOptions([...new Set(Object.values(options.majors_by_college).flat())])
})

async function loadProfile() {
  if (auth.currentUser?.role !== 'student') {
    profile.value = null
    return
  }
  profileLoading.value = true
  profileLoadError.value = ''
  profileSaveError.value = ''
  profileSaveSuccess.value = ''
  invalidProfileField.value = ''
  try {
    const [options, currentProfile] = await Promise.all([
      fetchProfileOptions(),
      fetchCurrentProfile(),
    ])
    profileOptions.value = options
    profile.value = currentProfile
    syncProfileForm(currentProfile)
  } catch {
    profile.value = null
    profileLoadError.value = 'profile_load_failed'
  } finally {
    profileLoading.value = false
  }
}

async function saveProfile() {
  profileSaving.value = true
  profileSaveError.value = ''
  profileSaveSuccess.value = ''
  invalidProfileField.value = ''
  try {
    profile.value = await updateCurrentProfile({
      college: profileForm.value.college ?? null,
      major: profileForm.value.major ?? null,
      grade: profileForm.value.grade ?? null,
      interest_tags: profileForm.value.interest_tags,
      competition_experience: profileForm.value.competition_experience.trim() || null,
      goal_preferences: profileForm.value.goal_preferences,
    })
    syncProfileForm(profile.value)
    profileSaveSuccess.value = '画像已保存'
  } catch (error) {
    const field = profileValidationField(error)
    invalidProfileField.value = field
    profileSaveError.value = profileValidationMessage(field)
    await focusProfileField(field)
  } finally {
    profileSaving.value = false
  }
}

async function reload() {
  logoutError.value = ''
  await auth.loadCurrentUser()
  await loadProfile()
}

async function logout() {
  logoutError.value = ''
  try {
    await auth.logout()
    profile.value = null
    profileOptions.value = null
  } catch {
    logoutError.value = '退出登录失败，请稍后重试'
  }
}

function syncProfileForm(currentProfile: StudentProfile) {
  profileForm.value = {
    college: currentProfile.college ?? undefined,
    major: currentProfile.major ?? undefined,
    grade: currentProfile.grade ?? undefined,
    interest_tags: [...currentProfile.interest_tags],
    competition_experience: currentProfile.competition_experience ?? '',
    goal_preferences: [...currentProfile.goal_preferences],
  }
}

function toSelectOptions(values: string[]) {
  return values.map((value) => ({ value, label: value }))
}

function profileValidationField(error: unknown) {
  if (!isAxiosError(error)) {
    return ''
  }
  const field = error.response?.data?.error?.details?.field
  return typeof field === 'string' ? field : ''
}

function profileValidationMessage(field: string) {
  switch (field) {
    case 'college':
      return '请选择受控字典中的学院。'
    case 'major':
      return '请选择当前学院下的受控专业。'
    case 'grade':
      return '请选择受控字典中的年级。'
    case 'interest_tags':
      return '请选择 1 到 10 个不重复的受控兴趣标签。'
    default:
      return '画像保存失败，请检查后重试。'
  }
}

function profileFieldStatus(field: string) {
  return invalidProfileField.value === field ? 'error' : undefined
}

function profileFieldHelp(field: string) {
  return invalidProfileField.value === field ? profileValidationMessage(field) : undefined
}

async function focusProfileField(field: string) {
  if (!field) return
  await nextTick()
  const fieldRoot = document.querySelector<HTMLElement>(`[data-profile-field="${field}"]`)
  fieldRoot?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  const control = fieldRoot?.matches('.ant-select-selector, textarea, input')
    ? fieldRoot
    : fieldRoot?.querySelector<HTMLElement>('.ant-select-selector, textarea, input')
  control?.focus()
}

onMounted(reload)
</script>

<template>
  <section class="account-page">
    <div class="page-heading">
      <div>
        <h1 class="page-title">个人信息</h1>
        <p class="page-description">查看用户名、身份信息和学生画像。</p>
      </div>
    </div>

    <ASkeleton v-if="auth.loading && !auth.currentUser" active />

    <div v-else-if="!auth.currentUser" class="status-layout single">
      <AResult
        class="state-panel"
        status="403"
        title="请先登录"
        sub-title="登录后可以查看用户名、身份信息和学生画像。"
      >
        <template #extra>
          <div class="form-actions centered-actions">
            <RouterLink class="detail-link" to="/login">
              <LoginOutlined />
              去登录
            </RouterLink>
            <RouterLink
              v-if="auth.publicEmailRegistrationEnabled"
              class="secondary-action-link"
              to="/register"
            >
              <UserAddOutlined />
              注册
            </RouterLink>
          </div>
        </template>
      </AResult>
    </div>

    <div v-else class="personal-layout">
      <section class="personal-hero" aria-labelledby="account-heading">
        <div class="avatar-mark" aria-hidden="true">{{ userInitial }}</div>
        <div class="personal-hero-main">
          <span class="field-label">用户名</span>
          <h2 id="account-heading">{{ displayName }}</h2>
          <div class="inline-tags">
            <ATag color="green">{{ identityLabel }}</ATag>
          </div>
        </div>
        <div class="personal-actions">
          <AButton :loading="auth.loading || profileLoading" @click="reload">
            <template #icon><ReloadOutlined /></template>
            刷新
          </AButton>
          <AButton data-testid="logout-button" danger :loading="auth.loading" @click="logout">
            <template #icon><LogoutOutlined /></template>
            退出登录
          </AButton>
        </div>
        <AAlert
          v-if="logoutError"
          data-testid="logout-error"
          type="error"
          :message="logoutError"
          show-icon
        />
      </section>

      <section
        v-if="auth.currentUser.role === 'student'"
        class="status-section profile-panel"
        aria-labelledby="profile-heading"
      >
        <div class="profile-panel-heading">
          <div>
            <h2 id="profile-heading">学生画像</h2>
            <p class="panel-description">完善基础资料后，系统会优先展示更适合你的赛事。</p>
          </div>
          <div v-if="profile" class="profile-status-line">
            <ATag
              data-testid="profile-status"
              :color="isProfileRecommendationReady ? 'green' : 'orange'"
            >
              {{ profileStatusText }}
            </ATag>
            <template v-if="missingFields.length">
              <ATag v-for="field in missingFields" :key="field" color="orange">
                缺少{{ field }}
              </ATag>
            </template>
          </div>
        </div>
        <ASkeleton v-if="profileLoading" active />
        <AAlert
          v-else-if="profileLoadError"
          type="error"
          message="画像状态加载失败"
          show-icon
        />
        <template v-else-if="profile">
          <AAlert
            v-if="profileSaveError"
            data-testid="profile-save-error"
            type="error"
            :message="profileSaveError"
            show-icon
          />
          <AAlert
            v-if="profileSaveSuccess"
            data-testid="profile-save-success"
            type="success"
            :message="profileSaveSuccess"
            show-icon
          />

          <AForm class="profile-form" layout="vertical" :model="profileForm" @finish="saveProfile">
            <AFormItem
              label="学院"
              name="college"
              :validate-status="profileFieldStatus('college')"
              :help="profileFieldHelp('college')"
            >
              <ASelect
                v-model:value="profileForm.college"
                data-profile-field="college"
                allow-clear
                :options="collegeOptions"
                placeholder="请选择学院"
              />
            </AFormItem>
            <AFormItem
              label="专业"
              name="major"
              :validate-status="profileFieldStatus('major')"
              :help="profileFieldHelp('major')"
            >
              <ASelect
                v-model:value="profileForm.major"
                data-profile-field="major"
                allow-clear
                :options="majorOptions"
                placeholder="请选择专业"
              />
            </AFormItem>
            <AFormItem
              label="年级"
              name="grade"
              :validate-status="profileFieldStatus('grade')"
              :help="profileFieldHelp('grade')"
            >
              <ASelect
                v-model:value="profileForm.grade"
                data-profile-field="grade"
                allow-clear
                :options="gradeOptions"
                placeholder="请选择年级"
              />
            </AFormItem>
            <AFormItem
              class="span-three"
              label="兴趣标签"
              name="interest_tags"
              :validate-status="profileFieldStatus('interest_tags')"
              :help="profileFieldHelp('interest_tags')"
            >
              <ASelect
                v-model:value="profileForm.interest_tags"
                data-profile-field="interest_tags"
                mode="multiple"
                :options="interestTagOptions"
                placeholder="请选择兴趣标签，可多选"
              />
            </AFormItem>
            <AFormItem class="span-three" label="竞赛经历" name="competition_experience">
              <ATextarea
                v-model:value="profileForm.competition_experience"
                class="textarea-control"
                data-testid="competition-experience"
                :rows="4"
                placeholder="可填写参加过的竞赛、项目或相关经历"
              />
            </AFormItem>
            <AFormItem class="span-three" label="目标偏好" name="goal_preferences">
              <ASelect
                v-model:value="profileForm.goal_preferences"
                data-testid="goal-preferences"
                mode="multiple"
                :options="goalPreferenceOptions"
                placeholder="请选择目标偏好，可多选"
              />
            </AFormItem>
            <div class="profile-actions">
              <AButton
                data-testid="profile-save"
                type="primary"
                html-type="submit"
                :loading="profileSaving"
              >
                <template #icon><SaveOutlined /></template>
                保存
              </AButton>
            </div>
          </AForm>
        </template>
      </section>
    </div>
  </section>
</template>
