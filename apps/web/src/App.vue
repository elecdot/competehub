<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
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
</template>
