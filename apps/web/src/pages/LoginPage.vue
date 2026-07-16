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
} from 'ant-design-vue'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth_store'
import type { LoginPayload } from '@/types/auth'

const auth = useAuthStore()
const router = useRouter()
const loginError = ref('')

const loginForm = ref<LoginPayload>({
  identity_type: 'email',
  identifier: '',
  password: '',
})

async function submitLogin() {
  loginError.value = ''
  try {
    await auth.login(loginForm.value)
    await router.push('/me')
  } catch {
    loginError.value = '登录失败'
  }
}

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
          <RouterLink to="/register">注册</RouterLink>
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
          <AFormItem label="邮箱 Email" name="identifier">
            <AInput
              v-model:value="loginForm.identifier"
              autocomplete="username"
              placeholder="name@example.com"
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
          <RouterLink to="/register">
            <UserAddOutlined />
            去注册
          </RouterLink>
        </p>
      </div>
    </div>
  </section>
</template>
