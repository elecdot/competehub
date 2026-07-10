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
      <a class="skip-link" href="#main-content">跳至主要内容</a>
      <header class="topbar">
        <RouterLink class="brand" to="/" translate="no">CompeteHub</RouterLink>
        <nav class="nav-links" aria-label="主导航">
          <RouterLink to="/competitions">赛事</RouterLink>
          <RouterLink to="/recommendations">推荐</RouterLink>
          <RouterLink to="/me/calendar">日历</RouterLink>
          <RouterLink to="/admin">后台</RouterLink>
        </nav>
      </header>
      <main id="main-content" class="main-content" tabindex="-1">
        <RouterView />
      </main>
    </div>
  </ConfigProvider>
</template>
