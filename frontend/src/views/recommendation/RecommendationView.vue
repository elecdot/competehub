<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">个性化推荐</h1>
        <p class="page-subtitle">结合专业、兴趣标签、收藏订阅和赛事热度，生成带理由的推荐结果。</p>
      </div>
      <el-button type="primary" :icon="Refresh" :loading="loading" @click="load">刷新推荐</el-button>
    </div>

    <div class="recommend-grid" v-loading="loading">
      <div v-for="item in items" :key="item.id" class="panel recommendation-card">
        <div class="card-head">
          <div>
            <router-link class="competition-title" :to="`/competitions/${item.id}`">{{ item.title }}</router-link>
            <p>{{ item.summary || `${item.category} / ${item.level}` }}</p>
          </div>
          <div class="score">{{ item.recommend_score || 0 }}</div>
        </div>
        <div class="tag-list">
          <el-tag v-for="reason in item.recommend_reasons || []" :key="reason" effect="light">
            {{ reason }}
          </el-tag>
        </div>
        <div class="card-foot">
          <span>{{ item.category }} · {{ item.level }}</span>
          <el-button text type="primary" @click="$router.push(`/competitions/${item.id}`)">查看详情</el-button>
        </div>
      </div>
    </div>

    <EmptyState
      v-if="!loading && items.length === 0"
      title="暂无推荐"
      description="请先登录并完善个人画像，系统会生成更准确的竞赛推荐。"
    />
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { Refresh } from '@element-plus/icons-vue';
import { getRecommendations } from '@/api/recommendation';
import type { Competition } from '@/api/types';
import EmptyState from '@/components/common/EmptyState.vue';

const loading = ref(false);
const items = ref<Competition[]>([]);

async function load() {
  loading.value = true;
  try {
    items.value = await getRecommendations();
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.recommend-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.recommendation-card {
  padding: 18px;
}

.card-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.competition-title {
  color: #1d4ed8;
  font-size: 17px;
  font-weight: 700;
}

.card-head p {
  margin: 8px 0 14px;
  color: #65758b;
  line-height: 1.6;
}

.score {
  display: grid;
  flex: 0 0 54px;
  width: 54px;
  height: 54px;
  place-items: center;
  border-radius: 8px;
  background: #ecfdf5;
  color: #047857;
  font-size: 18px;
  font-weight: 800;
}

.card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  color: #65758b;
  font-size: 13px;
}

@media (max-width: 960px) {
  .recommend-grid {
    grid-template-columns: 1fr;
  }
}
</style>
