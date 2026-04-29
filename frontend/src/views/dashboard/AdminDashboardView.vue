<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">后台管理</h1>
        <p class="page-subtitle">集中查看用户、赛事、收藏订阅、论坛内容等运营指标。</p>
      </div>
      <el-button type="primary" :icon="Refresh" :loading="loading" @click="load">刷新统计</el-button>
    </div>

    <div class="stat-grid">
      <div v-for="item in statItems" :key="item.key" class="stat-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </div>
    </div>

    <div class="panel panel-body">
      <h2 class="section-title">管理入口</h2>
      <div class="admin-actions">
        <el-button>赛事审核</el-button>
        <el-button>认证审批</el-button>
        <el-button>评分规则</el-button>
        <el-button>反馈处理</el-button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { Refresh } from '@element-plus/icons-vue';
import { getStatistics } from '@/api/admin';

const loading = ref(false);
const stats = ref<Record<string, number>>({});

const labels: Record<string, string> = {
  users: '用户数',
  competitions: '赛事总数',
  published_competitions: '已发布赛事',
  favorites: '收藏记录',
  subscriptions: '订阅记录',
  posts: '论坛帖子',
};

const statItems = computed(() =>
  Object.entries(labels).map(([key, label]) => ({
    key,
    label,
    value: stats.value[key] ?? 0,
  })),
);

async function load() {
  loading.value = true;
  try {
    stats.value = await getStatistics();
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.admin-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
</style>
