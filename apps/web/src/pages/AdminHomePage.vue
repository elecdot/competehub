<script setup lang="ts">
import { RouterLink } from "vue-router"
</script>

<template>
  <section>
    <h1 class="page-title">后台管理</h1>
    <p class="page-description">赛事录入、审核、配置和操作日志入口。</p>
    <nav class="admin-entry-list" aria-label="后台功能">
      <RouterLink class="admin-entry" to="/admin/recommendation-rule-sets">
        推荐规则治理
      </RouterLink>
    </nav>
  </section>
</template>

<style scoped>
.admin-entry-list {
  display: grid;
  gap: 12px;
  margin-top: 20px;
}

.admin-entry {
  background: #ffffff;
  border: 1px solid #dde2e7;
  border-radius: 8px;
  color: #176b4d;
  font-weight: 700;
  padding: 14px 16px;
  width: fit-content;
}

.admin-entry:hover {
  border-color: #176b4d;
  text-decoration: underline;
}
</style>
