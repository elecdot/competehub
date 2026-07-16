<script setup lang="ts">
import {
  CalendarOutlined,
  CheckCircleOutlined,
  CompassOutlined,
  LoginOutlined,
  MailOutlined,
  ReloadOutlined,
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
  Result as AResult,
  Steps as ASteps,
} from 'ant-design-vue'
import { isAxiosError } from 'axios'
import { computed, onUnmounted, ref } from 'vue'

import {
  registerCurrentUser,
  resendCurrentUserVerification,
  verifyCurrentUser,
} from '@/api/client'

const RESEND_COOLDOWN_SECONDS = 60

const currentStep = ref(0)
const registerLoading = ref(false)
const verifyLoading = ref(false)
const resendLoading = ref(false)
const errorMessage = ref('')
const infoMessage = ref('')
const cooldownRemaining = ref(0)
let cooldownTimer: number | undefined

const registerForm = ref({
  email: '',
  display_name: '',
  password: '',
})
const verifyForm = ref({
  code: '',
})

const normalizedEmail = computed(() => registerForm.value.email.trim())
const resendLabel = computed(() =>
  cooldownRemaining.value > 0 ? `${cooldownRemaining.value} 秒后可重发` : '重新发送验证码',
)

async function submitRegistration() {
  registerLoading.value = true
  errorMessage.value = ''
  infoMessage.value = ''
  try {
    await registerCurrentUser({
      identity_type: 'email',
      identifier: normalizedEmail.value,
      password: registerForm.value.password,
      display_name: registerForm.value.display_name.trim() || null,
    })
    currentStep.value = 1
    infoMessage.value = `请查看 ${normalizedEmail.value} 的验证码邮件；如果之前已经提交过注册，请使用之前收到的验证码，或稍后点击重新发送验证码。`
    startCooldown()
  } catch (error) {
    errorMessage.value = friendlyRegistrationError(error)
  } finally {
    registerLoading.value = false
  }
}

async function submitVerification() {
  verifyLoading.value = true
  errorMessage.value = ''
  infoMessage.value = ''
  try {
    await verifyCurrentUser({
      identity_type: 'email',
      identifier: normalizedEmail.value,
      code: verifyForm.value.code.trim(),
    })
    currentStep.value = 2
  } catch {
    errorMessage.value = '验证码验证失败，请检查后重试。'
  } finally {
    verifyLoading.value = false
  }
}

async function resendVerification() {
  if (cooldownRemaining.value > 0) {
    return
  }
  resendLoading.value = true
  errorMessage.value = ''
  infoMessage.value = ''
  try {
    await resendCurrentUserVerification({
      identity_type: 'email',
      identifier: normalizedEmail.value,
    })
    infoMessage.value = '验证码已重新发送，请查看邮箱。'
    startCooldown()
  } catch (error) {
    errorMessage.value = friendlyRegistrationError(error)
  } finally {
    resendLoading.value = false
  }
}

function friendlyRegistrationError(error: unknown) {
  if (!isAxiosError(error)) {
    return '注册请求失败，请检查邮箱和密码后重试。'
  }
  const errorCode = error.response?.data?.error?.code
  if (errorCode === 'registration_unavailable') {
    return '当前暂未开放自助注册，请联系管理员或使用学校预置登录信息。'
  }
  if (errorCode === 'identity_already_registered') {
    return '该邮箱已经被注册过，请直接登录。'
  }
  return '注册请求失败，请检查邮箱和密码后重试。'
}

function startCooldown() {
  cooldownRemaining.value = RESEND_COOLDOWN_SECONDS
  if (cooldownTimer !== undefined) {
    window.clearInterval(cooldownTimer)
  }
  cooldownTimer = window.setInterval(() => {
    cooldownRemaining.value -= 1
    if (cooldownRemaining.value <= 0 && cooldownTimer !== undefined) {
      window.clearInterval(cooldownTimer)
      cooldownTimer = undefined
    }
  }, 1000)
}

onUnmounted(() => {
  if (cooldownTimer !== undefined) {
    window.clearInterval(cooldownTimer)
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
          <p>创建账号后完善画像，让系统帮你整理赛事、推荐理由和日程提醒。</p>
        </div>
        <ul class="auth-feature-list" aria-label="平台能力">
          <li>
            <CompassOutlined />
            <span>用画像匹配更适合自己的竞赛机会</span>
          </li>
          <li>
            <CalendarOutlined />
            <span>订阅后在日历里跟进报名与截止节点</span>
          </li>
          <li>
            <SafetyCertificateOutlined />
            <span>邮箱验证码激活后再登录使用</span>
          </li>
        </ul>
      </div>

      <div class="auth-form-panel">
        <div class="auth-heading">
          <h2 id="register-heading">创建你的账号</h2>
          <p>使用邮箱完成注册和验证码激活，激活后再登录系统。</p>
        </div>
        <div class="auth-tabs" aria-label="登录注册切换">
          <RouterLink to="/login">登录</RouterLink>
          <RouterLink class="active" to="/register">注册</RouterLink>
        </div>
        <ASteps class="auth-steps" :current="currentStep" size="small">
          <ASteps.Step title="提交邮箱" />
          <ASteps.Step title="验证邮箱" />
          <ASteps.Step title="完成激活" />
        </ASteps>

        <AAlert
          v-if="errorMessage"
          data-testid="register-error"
          type="error"
          :message="errorMessage"
          show-icon
        />
        <AAlert
          v-if="infoMessage"
          data-testid="register-info"
          type="success"
          :message="infoMessage"
          show-icon
        />

        <AForm
          v-if="currentStep === 0"
          class="auth-form"
          data-testid="register-form"
          layout="vertical"
          :model="registerForm"
          @finish="submitRegistration"
        >
          <AFormItem label="用户名 Username" name="display_name">
            <AInput
              v-model:value="registerForm.display_name"
              autocomplete="name"
              placeholder="请输入用户名，例如 张三"
            />
          </AFormItem>
          <AFormItem label="邮箱 Email" name="email">
            <AInput
              v-model:value="registerForm.email"
              autocomplete="email"
              placeholder="name@example.com"
            />
          </AFormItem>
          <AFormItem label="密码 Password" name="password">
            <AInput
              v-model:value="registerForm.password"
              type="password"
              autocomplete="new-password"
              placeholder="至少 15 个字符"
            />
          </AFormItem>
          <AButton class="auth-submit" type="primary" html-type="submit" :loading="registerLoading">
            <template #icon><UserAddOutlined /></template>
            提交注册
          </AButton>
        </AForm>

        <AForm
          v-else-if="currentStep === 1"
          class="auth-form"
          data-testid="verify-form"
          layout="vertical"
          :model="verifyForm"
          @finish="submitVerification"
        >
          <AFormItem label="邮箱验证码" name="code">
            <AInput
              v-model:value="verifyForm.code"
              autocomplete="one-time-code"
              placeholder="请输入邮箱中的 6 位验证码"
            />
          </AFormItem>
          <div class="form-actions">
            <AButton class="auth-submit" type="primary" html-type="submit" :loading="verifyLoading">
              <template #icon><CheckCircleOutlined /></template>
              完成激活
            </AButton>
            <AButton
              data-testid="resend-code"
              :disabled="cooldownRemaining > 0"
              :loading="resendLoading"
              @click="resendVerification"
            >
              <template #icon><ReloadOutlined /></template>
              {{ resendLabel }}
            </AButton>
          </div>
        </AForm>

        <AResult
          v-else
          data-testid="register-complete"
          status="success"
          title="注册已完成"
          sub-title="请回到登录页，用刚激活的邮箱登录。"
        >
          <template #extra>
            <RouterLink class="detail-link" to="/login">
              <MailOutlined />
              去登录
            </RouterLink>
          </template>
        </AResult>
        <p v-if="currentStep !== 2" class="auth-switch-line">
          已有账号？
          <RouterLink to="/login">
            <LoginOutlined />
            去登录
          </RouterLink>
        </p>
      </div>
    </div>
  </section>
</template>
