<script setup lang="ts">
import { ConfigProvider } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { computed, onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import { useAuthStore } from '@/stores/auth_store'

const auth = useAuthStore()
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

onMounted(() => {
  void auth.loadAuthCapabilities()
  void auth.loadCurrentUser()
})
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
          <nav class="account-nav" aria-label="用户导航">
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
