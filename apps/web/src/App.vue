<script setup lang="ts">
import { ConfigProvider } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { RouterLink, RouterView } from 'vue-router'

const theme = {
  token: {
    colorPrimary: '#176b4d',
    colorInfo: '#176b4d',
    borderRadius: 6,
    fontFamily:
      'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
}
</script>

<template>
  <ConfigProvider :locale="zhCN" :theme="theme">
    <div class="app-shell">
      <header class="topbar">
        <RouterLink class="brand" to="/">CompeteHub</RouterLink>
        <nav class="nav-links" aria-label="主导航">
          <RouterLink to="/competitions">赛事</RouterLink>
          <RouterLink to="/recommendations">推荐</RouterLink>
          <RouterLink to="/me/calendar">日历</RouterLink>
          <RouterLink to="/admin">后台</RouterLink>
        </nav>
      </header>
      <main class="main-content">
        <RouterView />
      </main>
    </div>
  </ConfigProvider>
</template>
