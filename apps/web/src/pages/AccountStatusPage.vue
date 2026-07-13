<script setup lang="ts">
import { LoginOutlined, ReloadOutlined, SaveOutlined, UserOutlined } from '@ant-design/icons-vue'
import {
  Alert as AAlert,
  Button as AButton,
  Descriptions as ADescriptions,
  DescriptionsItem as ADescriptionsItem,
  Form as AForm,
  FormItem as AFormItem,
  Input as AInput,
  Result as AResult,
  Select as ASelect,
  Skeleton as ASkeleton,
  Tag as ATag,
} from 'ant-design-vue'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchCurrentProfile, fetchProfileOptions, updateCurrentProfile } from '@/api/client'
import { useAuthStore } from '@/stores/auth_store'
import type { IdentityType, LoginPayload, ProfileOptions, StudentProfile } from '@/types/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const profile = ref<StudentProfile | null>(null)
const profileOptions = ref<ProfileOptions | null>(null)
const profileLoading = ref(false)
const profileSaving = ref(false)
const profileLoadError = ref('')
const profileSaveError = ref('')
const loginError = ref('')

const loginForm = ref<LoginPayload>({
  identity_type: 'email',
  identifier: '',
  password: '',
})
const profileForm = ref({
  college: undefined as string | undefined,
  major: undefined as string | undefined,
  grade: undefined as string | undefined,
  interest_tags: [] as string[],
})

const missingFieldLabels: Record<string, string> = {
  college: '学院',
  major: '专业',
  grade: '年级',
  interest_tags: '兴趣标签',
}

const identityTypeOptions = [
  { value: 'email', label: '邮箱' },
  { value: 'phone', label: '手机号' },
  { value: 'student_no', label: '学号' },
] satisfies Array<{ value: IdentityType; label: string }>

const displayName = computed(() => auth.currentUser?.displayName || `用户 ${auth.currentUser?.id}`)
const capabilities = computed(() => auth.currentUser?.capabilities ?? [])
const missingFields = computed(() =>
  (profile.value?.missing_fields ?? []).map((field) => missingFieldLabels[field] ?? field),
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

async function submitLogin() {
  loginError.value = ''
  try {
    await auth.login(loginForm.value)
    await loadProfile()
    const returnTo = getSafeReturnPath(route.query.returnTo)
    if (returnTo) {
      await router.replace(returnTo)
    }
  } catch {
    loginError.value = '登录失败'
  }
}

function getSafeReturnPath(value: unknown) {
  if (typeof value !== 'string') return null
  if (!value.startsWith('/') || value.startsWith('//') || value.includes('\\')) return null
  return value
}

async function loadProfile() {
  if (auth.currentUser?.role !== 'student') {
    profile.value = null
    return
  }
  profileLoading.value = true
  profileLoadError.value = ''
  profileSaveError.value = ''
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
  try {
    profile.value = await updateCurrentProfile({
      college: profileForm.value.college ?? null,
      major: profileForm.value.major ?? null,
      grade: profileForm.value.grade ?? null,
      interest_tags: profileForm.value.interest_tags,
    })
    syncProfileForm(profile.value)
  } catch {
    profileSaveError.value = 'profile_save_failed'
  } finally {
    profileSaving.value = false
  }
}

async function reload() {
  await auth.loadCurrentUser()
  await loadProfile()
}

function syncProfileForm(currentProfile: StudentProfile) {
  profileForm.value = {
    college: currentProfile.college ?? undefined,
    major: currentProfile.major ?? undefined,
    grade: currentProfile.grade ?? undefined,
    interest_tags: [...currentProfile.interest_tags],
  }
}

function toSelectOptions(values: string[]) {
  return values.map((value) => ({ value, label: value }))
}

onMounted(reload)
</script>

<template>
  <section class="account-page">
    <div class="page-heading">
      <div>
        <h1 class="page-title">账号状态</h1>
        <p class="page-description">当前会话、角色权限和学生画像就绪状态。</p>
      </div>
      <AButton :loading="auth.loading || profileLoading" @click="reload">
        <template #icon><ReloadOutlined /></template>
        刷新
      </AButton>
    </div>

    <ASkeleton v-if="auth.loading && !auth.currentUser" active />

    <div v-else-if="!auth.currentUser" class="status-layout single">
      <AResult
        class="state-panel"
        status="403"
        title="未登录"
        sub-title="当前浏览器没有有效会话。"
      />
      <section class="status-section" aria-labelledby="login-heading">
        <div class="section-title-row">
          <LoginOutlined />
          <h2 id="login-heading">登录</h2>
        </div>
        <AAlert
          v-if="loginError"
          data-testid="login-error"
          type="error"
          :message="loginError"
          show-icon
        />
        <AForm
          data-testid="login-form"
          layout="vertical"
          :model="loginForm"
          @finish="submitLogin"
        >
          <AFormItem label="身份类型" name="identity_type">
            <ASelect v-model:value="loginForm.identity_type" :options="identityTypeOptions" />
          </AFormItem>
          <AFormItem label="身份标识" name="identifier">
            <AInput v-model:value="loginForm.identifier" autocomplete="username" />
          </AFormItem>
          <AFormItem label="密码" name="password">
            <AInput
              v-model:value="loginForm.password"
              type="password"
              autocomplete="current-password"
            />
          </AFormItem>
          <AButton type="primary" html-type="submit" :loading="auth.loading">
            <template #icon><LoginOutlined /></template>
            登录
          </AButton>
        </AForm>
      </section>
    </div>

    <div v-else class="status-layout">
      <section class="status-section" aria-labelledby="account-heading">
        <div class="section-title-row">
          <UserOutlined />
          <h2 id="account-heading">当前用户</h2>
        </div>
        <ADescriptions bordered :column="1" size="small">
          <ADescriptionsItem label="显示名">{{ displayName }}</ADescriptionsItem>
          <ADescriptionsItem label="角色">
            <ATag color="green">{{ auth.currentUser.role }}</ATag>
          </ADescriptionsItem>
          <ADescriptionsItem label="Capabilities">
            <span v-if="capabilities.length" class="inline-tags">
              <ATag v-for="capability in capabilities" :key="capability" color="blue">
                {{ capability }}
              </ATag>
            </span>
            <span v-else>[]</span>
          </ADescriptionsItem>
        </ADescriptions>
      </section>

      <section
        v-if="auth.currentUser.role === 'student'"
        class="status-section"
        aria-labelledby="profile-heading"
      >
        <h2 id="profile-heading">学生画像</h2>
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
            message="画像保存失败，请检查后重试"
            show-icon
          />
          <ADescriptions bordered :column="1" size="small">
            <ADescriptionsItem label="状态">
              <ATag
                data-testid="profile-status"
                :color="profile.profile_status === 'recommendation_ready' ? 'green' : 'orange'"
              >
                {{ profile.profile_status }}
              </ATag>
            </ADescriptionsItem>
            <ADescriptionsItem label="缺少字段">
              <span v-if="missingFields.length" class="inline-tags">
                <ATag v-for="field in missingFields" :key="field" color="orange">
                  {{ field }}
                </ATag>
              </span>
              <span v-else>[]</span>
            </ADescriptionsItem>
          </ADescriptions>

          <AForm class="profile-form" layout="vertical" :model="profileForm" @finish="saveProfile">
            <AFormItem label="学院" name="college">
              <ASelect
                v-model:value="profileForm.college"
                allow-clear
                :options="collegeOptions"
              />
            </AFormItem>
            <AFormItem label="专业" name="major">
              <ASelect
                v-model:value="profileForm.major"
                allow-clear
                :options="majorOptions"
              />
            </AFormItem>
            <AFormItem label="年级" name="grade">
              <ASelect v-model:value="profileForm.grade" allow-clear :options="gradeOptions" />
            </AFormItem>
            <AFormItem label="兴趣标签" name="interest_tags">
              <ASelect
                v-model:value="profileForm.interest_tags"
                mode="multiple"
                :max-tag-count="3"
                :options="interestTagOptions"
              />
            </AFormItem>
            <AButton
              data-testid="profile-save"
              type="primary"
              html-type="submit"
              :loading="profileSaving"
            >
              <template #icon><SaveOutlined /></template>
              保存
            </AButton>
          </AForm>
        </template>
      </section>
    </div>
  </section>
</template>
