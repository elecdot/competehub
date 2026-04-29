<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ competition?.title || '赛事详情' }}</h1>
        <p class="page-subtitle">{{ competition?.summary || '查看赛事要求、时间节点、价值评分与官方入口。' }}</p>
      </div>
      <div class="toolbar">
        <el-button :icon="Star" @click="favorite">收藏</el-button>
        <el-button type="primary" :icon="Bell" @click="subscribe">订阅提醒</el-button>
      </div>
    </div>

    <el-row :gutter="16" v-loading="loading">
      <el-col :xs="24" :lg="16">
        <div class="panel panel-body">
          <h2 class="section-title">赛事概况</h2>
          <el-descriptions v-if="competition" :column="2" border>
            <el-descriptions-item label="类别">{{ competition.category }}</el-descriptions-item>
            <el-descriptions-item label="级别">{{ competition.level }}</el-descriptions-item>
            <el-descriptions-item label="主办方">{{ competition.organizer || '-' }}</el-descriptions-item>
            <el-descriptions-item label="报名截止">{{ formatDateTime(competition.registration_deadline_at) }}</el-descriptions-item>
            <el-descriptions-item label="热度">{{ competition.heat }}</el-descriptions-item>
            <el-descriptions-item label="价值评分">{{ competition.score }}</el-descriptions-item>
          </el-descriptions>

          <div class="detail-content">
            <h2 class="section-title">详细说明</h2>
            <p>{{ competition?.description || '暂无详细说明。' }}</p>
          </div>
        </div>
      </el-col>

      <el-col :xs="24" :lg="8">
        <div class="panel panel-body side">
          <h2 class="section-title">参赛辅助</h2>
          <div class="score-box">
            <span>综合评分</span>
            <strong>{{ competition?.score || 0 }}</strong>
            <el-progress :percentage="Math.min(Number(competition?.score || 0), 100)" />
          </div>
          <div class="tag-list side-tags">
            <el-tag v-for="tag in competition?.tags || []" :key="tag" effect="plain">{{ tag }}</el-tag>
          </div>
          <el-button
            v-if="competition?.official_url"
            type="primary"
            class="full-button"
            :icon="Link"
            @click="openOfficial"
          >
            官方通道
          </el-button>
        </div>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Bell, Link, Star } from '@element-plus/icons-vue';
import { favoriteCompetition, getCompetition, subscribeCompetition } from '@/api/competition';
import type { Competition } from '@/api/types';
import { useAuthStore } from '@/stores/auth';
import { formatDateTime } from '@/utils/format';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const competition = ref<Competition | null>(null);

async function load() {
  loading.value = true;
  try {
    competition.value = await getCompetition(Number(route.params.id));
  } finally {
    loading.value = false;
  }
}

function requireLogin() {
  if (auth.isAuthenticated) return true;
  ElMessage.warning('请先登录后再操作');
  router.push({ name: 'login', query: { redirect: route.fullPath } });
  return false;
}

async function favorite() {
  if (!competition.value) return;
  if (!requireLogin()) return;
  await favoriteCompetition(competition.value.id);
  ElMessage.success('已收藏');
}

async function subscribe() {
  if (!competition.value) return;
  if (!requireLogin()) return;
  await subscribeCompetition(competition.value.id);
  ElMessage.success('已订阅提醒');
}

function openOfficial() {
  if (competition.value?.official_url) {
    window.open(competition.value.official_url, '_blank');
  }
}

onMounted(load);
</script>

<style scoped>
.detail-content {
  margin-top: 22px;
}

.detail-content p {
  margin: 0;
  color: #334155;
  line-height: 1.9;
  white-space: pre-wrap;
}

.side {
  position: sticky;
  top: 82px;
}

.score-box {
  margin-bottom: 18px;
}

.score-box span {
  color: #65758b;
  font-size: 13px;
}

.score-box strong {
  display: block;
  margin: 8px 0;
  font-size: 32px;
}

.side-tags {
  margin-bottom: 18px;
}

.full-button {
  width: 100%;
}
</style>
