<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">赛事查询</h1>
        <p class="page-subtitle">按关键词、类别、级别和热度筛选竞赛，支持收藏和订阅提醒。</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </div>

    <div class="panel panel-body filter-panel">
      <div class="toolbar">
        <el-input
          v-model="filters.keyword"
          :prefix-icon="Search"
          placeholder="搜索赛事名称、主办方"
          clearable
          class="search-input"
          @keyup.enter="load"
        />
        <el-select v-model="filters.category" placeholder="类别" clearable class="filter-select">
          <el-option label="程序设计" value="程序设计" />
          <el-option label="数学建模" value="数学建模" />
          <el-option label="创新创业" value="创新创业" />
          <el-option label="电子设计" value="电子设计" />
        </el-select>
        <el-select v-model="filters.level" placeholder="级别" clearable class="filter-select">
          <el-option label="校级" value="校级" />
          <el-option label="省级" value="省级" />
          <el-option label="国家级" value="国家级" />
        </el-select>
        <el-select v-model="filters.sort" placeholder="排序" class="filter-select">
          <el-option label="截止时间" value="deadline" />
          <el-option label="热度" value="heat" />
          <el-option label="评分" value="score" />
        </el-select>
        <el-button type="primary" :loading="loading" @click="load">查询</el-button>
      </div>
    </div>

    <div class="panel panel-body">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column label="赛事信息" min-width="320">
          <template #default="{ row }">
            <router-link class="competition-title" :to="`/competitions/${row.id}`">{{ row.title }}</router-link>
            <div class="competition-summary">{{ row.summary || row.organizer || '暂无简介' }}</div>
            <div class="tag-list">
              <el-tag v-for="tag in row.tags || []" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="类别" width="120" />
        <el-table-column prop="level" label="级别" width="100">
          <template #default="{ row }">
            <el-tag :type="levelTag(row.level)" effect="light">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="报名截止" width="180">
          <template #default="{ row }">{{ formatDateTime(row.registration_deadline_at) }}</template>
        </el-table-column>
        <el-table-column label="热度/评分" width="150">
          <template #default="{ row }">
            <div class="score-line">热度 {{ row.heat }}</div>
            <el-progress :percentage="Math.min(Number(row.score || 0), 100)" :stroke-width="6" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="$router.push(`/competitions/${row.id}`)">详情</el-button>
            <el-button text @click="subscribe(row.id)">订阅</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Refresh, Search } from '@element-plus/icons-vue';
import { getCompetitions, subscribeCompetition } from '@/api/competition';
import type { Competition } from '@/api/types';
import { useAuthStore } from '@/stores/auth';
import { formatDateTime } from '@/utils/format';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const items = ref<Competition[]>([]);
const filters = reactive({ keyword: '', category: '', level: '', sort: 'deadline' });

function levelTag(level: string) {
  if (level === '国家级') return 'danger';
  if (level === '省级') return 'warning';
  return 'info';
}

async function load() {
  loading.value = true;
  try {
    const data = await getCompetitions({ ...filters, page: 1, page_size: 20 });
    items.value = data.items;
  } finally {
    loading.value = false;
  }
}

function requireLogin() {
  if (auth.isAuthenticated) return true;
  ElMessage.warning('请先登录后再订阅赛事');
  router.push({ name: 'login', query: { redirect: route.fullPath } });
  return false;
}

async function subscribe(id: number) {
  if (!requireLogin()) return;
  await subscribeCompetition(id);
  ElMessage.success('已加入订阅提醒');
}

onMounted(load);
</script>

<style scoped>
.filter-panel {
  margin-bottom: 16px;
}

.search-input {
  width: 300px;
}

.filter-select {
  width: 150px;
}

.competition-title {
  color: #1d4ed8;
  font-weight: 700;
}

.competition-summary {
  margin: 6px 0 8px;
  color: #65758b;
  font-size: 13px;
}

.score-line {
  margin-bottom: 6px;
  color: #475569;
  font-size: 12px;
}
</style>
