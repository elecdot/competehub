<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">赛事查询</h1>
        <p class="page-subtitle">当前已导入 {{ total }} 个赛事，可按关键词、方向、认定类别和热度筛选。</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </div>

    <div class="panel panel-body filter-panel">
      <div class="toolbar">
        <el-input
          v-model="filters.keyword"
          :prefix-icon="Search"
          placeholder="搜索赛事名称、主办方或简介"
          clearable
          class="search-input"
          @keyup.enter="search"
        />
        <el-select v-model="filters.category" placeholder="方向" clearable class="filter-select">
          <el-option v-for="item in options.categories" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.level" placeholder="认定类别" clearable class="filter-select">
          <el-option v-for="item in options.levels" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.sort" placeholder="排序" class="filter-select">
          <el-option label="时间优先" value="deadline" />
          <el-option label="热度" value="heat" />
          <el-option label="评分" value="score" />
        </el-select>
        <el-button type="primary" :loading="loading" @click="search">查询</el-button>
      </div>
    </div>

    <div class="panel panel-body">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column label="赛事信息" min-width="340">
          <template #default="{ row }">
            <router-link class="competition-title" :to="`/competitions/${row.id}`">{{ row.title }}</router-link>
            <div class="competition-summary">{{ row.summary || row.organizer || '暂无简介' }}</div>
            <div class="tag-list">
              <el-tag v-for="tag in row.tags || []" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="方向" width="150" />
        <el-table-column prop="level" label="类别" width="100">
          <template #default="{ row }">
            <el-tag :type="levelTag(row.level)" effect="light">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="报名截止" width="160">
          <template #default="{ row }">{{ formatDateTime(row.registration_deadline_at, '时间待公布') }}</template>
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

      <div class="pagination-row">
        <span>共 {{ total }} 条</span>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="sizes, prev, pager, next, jumper"
          @current-change="load"
          @size-change="search"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Refresh, Search } from '@element-plus/icons-vue';
import { getCompetitionOptions, getCompetitions, subscribeCompetition } from '@/api/competition';
import type { Competition, CompetitionOptions } from '@/api/types';
import { useAuthStore } from '@/stores/auth';
import { formatDateTime } from '@/utils/format';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const items = ref<Competition[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const filters = reactive({ keyword: '', category: '', level: '', sort: 'deadline' });
const options = reactive<CompetitionOptions>({ competitions: [], categories: [], levels: [], tags: [], skills: [], forum_tags: [] });

function levelTag(level: string) {
  if (level === 'A类') return 'danger';
  if (level === 'B类') return 'warning';
  if (level === 'C类') return 'success';
  return 'info';
}

async function loadOptions() {
  Object.assign(options, await getCompetitionOptions());
}

async function load() {
  loading.value = true;
  try {
    const data = await getCompetitions({ ...filters, page: page.value, page_size: pageSize.value });
    items.value = data.items;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
}

function search() {
  page.value = 1;
  load();
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

onMounted(async () => {
  await loadOptions();
  await load();
});
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

.pagination-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 16px;
  color: #64748b;
}
</style>
