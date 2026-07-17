<script setup lang="ts">
import {
  CalendarOutlined,
  CompassOutlined,
  LoginOutlined,
  SafetyCertificateOutlined,
  TrophyOutlined,
  UserAddOutlined,
} from '@ant-design/icons-vue'
import {
  Alert as AAlert,
  Button as AButton,
  Form as AForm,
  FormItem as AFormItem,
  Input as AInput,
  InputPassword as AInputPassword,
  Select as ASelect,
} from 'ant-design-vue'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth_store'
import type { IdentityType, LoginPayload } from '@/types/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const loginError = ref('')

const identityTypeOptions: Array<{ value: IdentityType; label: string }> = [
  { value: 'email', label: '邮箱' },
  { value: 'student_no', label: '学号' },
  { value: 'phone', label: '手机号' },
]

const loginForm = ref<LoginPayload>({
  identity_type: 'email',
  identifier: '',
  password: '',
})

const identityInputLabel = computed(() => {
  switch (loginForm.value.identity_type) {
    case 'student_no':
      return '学号 Student number'
    case 'phone':
      return '手机号 Phone'
    default:
      return '邮箱 Email'
  }
})

const identityInputPlaceholder = computed(() => {
  switch (loginForm.value.identity_type) {
    case 'student_no':
      return '请输入学校配置的学号'
    case 'phone':
      return '请输入已配置的手机号'
    default:
      return 'name@example.com'
  }
})

async function submitLogin() {
  loginError.value = ''
  try {
    await auth.login(loginForm.value)
    await router.push(getSafeReturnPath(route.query.return_to))
  } catch {
    loginError.value = '登录失败'
  }
}

function getSafeReturnPath(value: unknown) {
  if (typeof value !== 'string' || !value) return '/me'

  let decoded: string
  try {
    decoded = decodeURIComponent(value)
  } catch {
    return '/me'
  }

  if (!decoded.startsWith('/') || decoded.startsWith('//') || decoded.includes('\\')) {
    return '/me'
  }

  const origin = 'https://competehub.invalid'
  try {
    const target = new URL(decoded, origin)
    if (target.origin !== origin || !target.pathname.startsWith('/')) {
      return '/me'
    }
  } catch {
    return '/me'
  }

  return decoded
}

onMounted(() => {
  if (!auth.capabilitiesLoaded) {
    void auth.loadAuthCapabilities()
  }
})

</script>

<template>
  <section class="auth-page">
    <div class="auth-card">
      <div class="auth-brand-panel">
        <div class="auth-brand-icon">
          <TrophyOutlined />
        </div>
        <div>
          <p class="auth-eyebrow">CompeteHub</p>
          <h1>竞赛发现中心</h1>
          <p>集中查看可信赛事，保存个人画像，并跟进关键时间节点。</p>
        </div>
        <ul class="auth-feature-list" aria-label="平台能力">
          <li>
            <CompassOutlined />
            <span>按专业、年级和兴趣筛选合适赛事</span>
          </li>
          <li>
            <CalendarOutlined />
            <span>订阅报名、截止和评审等关键节点</span>
          </li>
          <li>
            <SafetyCertificateOutlined />
            <span>邮箱验证后再进入个人赛事工作台</span>
          </li>
        </ul>
      </div>

      <div class="auth-form-panel">
        <div class="auth-heading">
          <h2 id="login-heading">欢迎回来</h2>
          <p>登录后继续维护个人信息和赛事日程。</p>
        </div>
        <div class="auth-tabs" aria-label="登录注册切换">
          <RouterLink class="active" to="/login">登录</RouterLink>
          <RouterLink v-if="auth.publicEmailRegistrationEnabled" to="/register">注册</RouterLink>
        </div>
        <AAlert
          v-if="loginError"
          data-testid="login-error"
          type="error"
          :message="loginError"
          show-icon
        />
        <AForm
          class="auth-form"
          data-testid="login-form"
          layout="vertical"
          :model="loginForm"
          @finish="submitLogin"
        >
          <AFormItem label="登录方式" name="identity_type">
            <ASelect
              data-testid="identity-type"
              v-model:value="loginForm.identity_type"
              :options="identityTypeOptions"
            />
          </AFormItem>
          <AFormItem :label="identityInputLabel" name="identifier">
            <AInput
              v-model:value="loginForm.identifier"
              autocomplete="username"
              :placeholder="identityInputPlaceholder"
            />
          </AFormItem>
          <AFormItem label="密码 Password" name="password">
            <AInputPassword
              v-model:value="loginForm.password"
              autocomplete="current-password"
              placeholder="请输入密码"
            />
          </AFormItem>
          <AButton class="auth-submit" type="primary" html-type="submit" :loading="auth.loading">
            <template #icon><LoginOutlined /></template>
            登录
          </AButton>
        </AForm>
        <p class="auth-switch-line">
          还没有账号？
          <RouterLink v-if="auth.publicEmailRegistrationEnabled" to="/register">
            <UserAddOutlined />
            去注册
          </RouterLink>
          <span v-else>当前暂未开放自助注册</span>
        </p>
      </div>
    </div>
  </section>
</template>
