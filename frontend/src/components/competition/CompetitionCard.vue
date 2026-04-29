<template>
  <article class="competition-card">
    <div>
      <h3>{{ competition.title }}</h3>
      <p>{{ competition.summary || competition.category }}</p>
    </div>
    <div class="meta">
      <el-tag>{{ competition.level }}</el-tag>
      <span>{{ competition.registration_deadline_at || '未设置截止时间' }}</span>
    </div>
  </article>
</template>

<script setup lang="ts">
import type { Competition } from '@/api/types';

defineProps<{
  competition: Competition;
}>();
</script>

<style scoped>
.competition-card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.competition-card h3 {
  margin: 0 0 8px;
  font-size: 16px;
}

.competition-card p {
  margin: 0;
  color: #64748b;
}

.meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  color: #64748b;
  font-size: 13px;
}
</style>

