<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">收件箱</h1>
        <p class="page-subtitle">帖子回复、评论回复、点赞、组队意向和同好联系都会出现在这里。</p>
      </div>
      <div class="toolbar">
        <el-tag type="danger" effect="light">未读 {{ unread }}</el-tag>
        <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
        <el-button type="primary" @click="readAll">全部已读</el-button>
      </div>
    </div>

    <div class="panel panel-body inbox-panel" v-loading="loading">
      <div v-for="item in items" :key="item.id" class="notice" :class="{ unread: item.status === 'unread' }">
        <div class="notice-main">
          <el-tag size="small" :type="tagType(item.type)">{{ typeLabel(item.type) }}</el-tag>
          <strong>{{ item.title }}</strong>
          <p>{{ item.content || '暂无详细内容' }}</p>
          <span>{{ formatDateTime(item.sent_at || item.created_at) }}</span>
        </div>
        <el-button v-if="item.status === 'unread'" text type="primary" @click="read(item.id)">标记已读</el-button>
      </div>

      <EmptyState
        v-if="!loading && items.length === 0"
        title="暂无消息"
        description="有人回复你的帖子、评论、点赞或发起组队联系后，会在这里提醒。"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { Refresh } from '@element-plus/icons-vue';
import { getNotifications, markAllNotificationsRead, markNotificationRead } from '@/api/reminder';
import type { NotificationItem } from '@/api/types';
import EmptyState from '@/components/common/EmptyState.vue';
import { formatDateTime } from '@/utils/format';

const loading = ref(false);
const unread = ref(0);
const items = ref<NotificationItem[]>([]);

async function load() {
  loading.value = true;
  try {
    const data = await getNotifications();
    items.value = data.items;
    unread.value = data.unread;
  } finally {
    loading.value = false;
  }
}

async function read(id: number) {
  await markNotificationRead(id);
  await load();
}

async function readAll() {
  await markAllNotificationsRead();
  await load();
}

function typeLabel(type: string) {
  return {
    forum_comment: '帖子回复',
    forum_reply: '评论回复',
    forum_like: '点赞',
    team_interest: '组队意向',
    teammate_contact: '同好联系',
  }[type] || '系统';
}

function tagType(type: string) {
  if (type === 'team_interest' || type === 'teammate_contact') return 'success';
  if (type === 'forum_like') return 'warning';
  return 'primary';
}

onMounted(load);
</script>

<style scoped>
.inbox-panel {
  display: grid;
  gap: 12px;
}

.notice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.notice.unread {
  border-color: #93c5fd;
  background: #eff6ff;
}

.notice-main {
  display: grid;
  gap: 6px;
}

.notice-main strong {
  font-size: 15px;
}

.notice-main p {
  margin: 0;
  color: #475569;
  line-height: 1.6;
}

.notice-main span {
  color: #64748b;
  font-size: 12px;
}
</style>
