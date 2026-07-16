<script setup lang="ts">
import { BellOutlined } from '@ant-design/icons-vue'
import { Badge as ABadge, ConfigProvider } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

import { useAuthStore } from '@/stores/auth_store'
import { useNotificationStore } from '@/stores/notification_store'

const route = useRoute()
const auth = useAuthStore()
const notifications = useNotificationStore()
const showMessageLink = computed(() => auth.currentUser?.role === 'student')
const messageLinkLabel = computed(() =>
  notifications.unreadCount > 0
    ? `消息，${notifications.unreadCount} 条未读`
    : '消息，暂无未读',
)
const accountName = computed(() =>
  auth.currentUser?.displayName?.trim() || `用户 ${auth.currentUser?.id ?? ''}`.trim(),
)
const accountInitial = computed(() => accountName.value.slice(0, 1).toUpperCase() || 'U')

const theme = {
  token: {
    colorPrimary: '#176b4d',
    colorInfo: '#176b4d',
    borderRadius: 6,
    fontFamily:
      'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
}

async function refreshUnreadCount() {
  if (auth.currentUser?.role === 'student') {
    await notifications.loadUnreadCount()
  } else {
    notifications.clear()
  }
}

function refreshUnreadOutsideMessageCenter() {
  if (route.name !== 'messages') void refreshUnreadCount()
}

watch(
  () => `${auth.currentUser?.id ?? ''}:${auth.currentUser?.role ?? ''}`,
  () => {
    // A current-user probe can observe a cookie replaced by another tab. Drop
    // the previous identity's snapshot without losing URL-owned list filters.
    notifications.clearSessionSnapshot()
    refreshUnreadOutsideMessageCenter()
  },
  { immediate: true },
)
watch(
  () => route.fullPath,
  refreshUnreadOutsideMessageCenter,
)

onMounted(() => {
  window.addEventListener('focus', refreshUnreadOutsideMessageCenter)
  void auth.loadAuthCapabilities()
  void auth.ensureCurrentUser()
})
onUnmounted(() => window.removeEventListener('focus', refreshUnreadOutsideMessageCenter))
</script>

<template>
  <ConfigProvider :locale="zhCN" :theme="theme">
    <div class="app-shell">
      <a class="skip-link" href="#main-content">跳至主要内容</a>
      <header class="topbar">
        <div class="topbar-inner">
          <RouterLink class="brand" to="/" translate="no">CompeteHub</RouterLink>
          <nav class="nav-links" aria-label="主导航">
            <RouterLink to="/competitions">赛事</RouterLink>
            <RouterLink to="/recommendations">推荐</RouterLink>
            <RouterLink to="/me/calendar">日历</RouterLink>
            <RouterLink to="/admin">后台</RouterLink>
          </nav>
          <nav class="account-nav" aria-label="账号导航">
            <RouterLink
              v-if="showMessageLink"
              data-testid="message-center-link"
              class="message-nav-link"
              to="/me/messages"
              :aria-label="messageLinkLabel"
            >
              <ABadge :count="notifications.unreadCount" :overflow-count="99">
                <BellOutlined aria-hidden="true" />
                <span class="message-nav-label">消息</span>
              </ABadge>
            </RouterLink>
            <span v-if="showMessageLink" class="sr-only" aria-live="polite">
              {{ messageLinkLabel }}
            </span>
            <template v-if="auth.isAuthenticated">
              <RouterLink class="account-user-link" to="/me" aria-label="当前用户">
                <span class="account-avatar" aria-hidden="true">{{ accountInitial }}</span>
                <span class="account-name">{{ accountName }}</span>
              </RouterLink>
              <RouterLink to="/me">个人信息</RouterLink>
            </template>
            <template v-else>
              <RouterLink to="/login">登录</RouterLink>
              <RouterLink v-if="auth.publicEmailRegistrationEnabled" to="/register">
                注册
              </RouterLink>
            </template>
          </nav>
        </div>
      </header>
      <main id="main-content" class="main-content" tabindex="-1">
        <RouterView />
      </main>
    </div>
  </ConfigProvider>
</template>
