<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">订阅日历</h1>
        <p class="page-subtitle">集中查看已订阅赛事的报名截止、比赛开始和结束时间。</p>
      </div>
      <el-button type="primary" :icon="Refresh" :loading="loading" @click="load">刷新日历</el-button>
    </div>

    <div class="panel panel-body">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="title" label="赛事" min-width="240" />
        <el-table-column label="报名截止">
          <template #default="{ row }">{{ formatDateTime(row.registration_deadline_at) }}</template>
        </el-table-column>
        <el-table-column label="比赛开始">
          <template #default="{ row }">{{ formatDateTime(row.competition_start_at) }}</template>
        </el-table-column>
        <el-table-column label="比赛结束">
          <template #default="{ row }">{{ formatDateTime(row.competition_end_at) }}</template>
        </el-table-column>
      </el-table>
    </div>

    <EmptyState
      v-if="!loading && items.length === 0"
      title="暂无订阅赛事"
      description="在赛事详情页点击订阅后，关键时间节点会出现在这里。"
    />
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { Refresh } from '@element-plus/icons-vue';
import { getCalendar } from '@/api/reminder';
import EmptyState from '@/components/common/EmptyState.vue';
import { formatDateTime } from '@/utils/format';

interface CalendarItem {
  title: string;
  registration_deadline_at?: string;
  competition_start_at?: string;
  competition_end_at?: string;
}

const loading = ref(false);
const items = ref<CalendarItem[]>([]);

async function load() {
  loading.value = true;
  try {
    items.value = (await getCalendar()) as CalendarItem[];
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>
