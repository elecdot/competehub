<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">竞赛服务工作台</h1>
        <p class="page-subtitle">集中查看赛事库、推荐能力、订阅提醒和论坛协作的运行状态。</p>
      </div>
      <div class="toolbar">
        <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
        <el-button type="primary" :icon="Search" @click="$router.push('/competitions')">查找赛事</el-button>
      </div>
    </div>

    <div class="stat-grid">
      <div class="stat-card">
        <span>已发布赛事</span>
        <strong>{{ stats.total }}</strong>
      </div>
      <div class="stat-card">
        <span>国家级赛事</span>
        <strong>{{ stats.national }}</strong>
      </div>
      <div class="stat-card">
        <span>近期高热度</span>
        <strong>{{ stats.hot }}</strong>
      </div>
      <div class="stat-card">
        <span>当前登录</span>
        <strong>{{ auth.user?.username || '访客' }}</strong>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="15">
        <div class="panel panel-body">
          <div class="section-head">
            <h2 class="section-title">近期赛事</h2>
            <el-button text type="primary" @click="$router.push('/competitions')">查看全部</el-button>
          </div>
          <el-table :data="competitions" v-loading="loading" stripe>
            <el-table-column label="赛事名称" min-width="240">
              <template #default="{ row }">
                <router-link class="link-text" :to="`/competitions/${row.id}`">{{ row.title }}</router-link>
                <div class="muted small">{{ row.organizer || '未设置主办方' }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="category" label="类别" width="110" />
            <el-table-column prop="level" label="级别" width="100" />
            <el-table-column label="报名截止" width="180">
              <template #default="{ row }">{{ formatDateTime(row.registration_deadline_at) }}</template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>

      <el-col :xs="24" :lg="9">
        <div class="panel panel-body side-panel">
          <h2 class="section-title">核心流程</h2>
          <div class="flow-item">
            <span>1</span>
            <div>
              <strong>完善画像</strong>
              <p>维护专业、年级、兴趣方向，为筛选和推荐提供依据。</p>
            </div>
          </div>
          <div class="flow-item">
            <span>2</span>
            <div>
              <strong>筛选赛事</strong>
              <p>按类别、级别、主办方和截止时间定位适合参加的比赛。</p>
            </div>
          </div>
          <div class="flow-item">
            <span>3</span>
            <div>
              <strong>订阅提醒</strong>
              <p>收藏赛事后统一进入日历，减少错过报名和提交节点。</p>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { Refresh, Search } from '@element-plus/icons-vue';
import { getCompetitions } from '@/api/competition';
import type { Competition } from '@/api/types';
import { useAuthStore } from '@/stores/auth';
import { formatDateTime } from '@/utils/format';

const auth = useAuthStore();
const loading = ref(false);
const competitions = ref<Competition[]>([]);

const stats = computed(() => ({
  total: competitions.value.length,
  national: competitions.value.filter((item) => item.level === '国家级').length,
  hot: competitions.value.filter((item) => item.heat >= 20).length,
}));

async function load() {
  loading.value = true;
  try {
    const data = await getCompetitions({ page: 1, page_size: 6, sort: 'deadline' });
    competitions.value = data.items;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.small {
  margin-top: 4px;
  font-size: 12px;
}

.side-panel {
  min-height: 100%;
}

.flow-item {
  display: flex;
  gap: 12px;
  padding: 14px 0;
  border-top: 1px solid #edf2f7;
}

.flow-item:first-of-type {
  border-top: 0;
}

.flow-item span {
  display: grid;
  flex: 0 0 28px;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 999px;
  background: #eaf2ff;
  color: #1d4ed8;
  font-weight: 700;
}

.flow-item strong {
  display: block;
  margin-bottom: 4px;
}

.flow-item p {
  margin: 0;
  color: #65758b;
  font-size: 13px;
  line-height: 1.6;
}
</style>
