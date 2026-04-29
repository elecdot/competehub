<template>
  <div class="empty-state">
    <strong>{{ title }}</strong>
    <span>{{ description }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
}>();
</script>

<style scoped>
.empty-state {
  display: grid;
  gap: 8px;
  place-items: center;
  min-height: 180px;
  color: #64748b;
}

.empty-state strong {
  color: #334155;
}
</style>

