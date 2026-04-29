<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">交流论坛</h1>
        <p class="page-subtitle">围绕赛事提问、经验分享、组队交流和认证答疑沉淀内容。</p>
      </div>
      <el-button type="primary" :icon="EditPen">发布帖子</el-button>
    </div>

    <div class="panel panel-body">
      <div class="toolbar forum-toolbar">
        <el-input v-model="keyword" :prefix-icon="Search" placeholder="搜索帖子" clearable @keyup.enter="load" />
        <el-select v-model="postType" placeholder="帖子类型" clearable>
          <el-option label="提问" value="question" />
          <el-option label="经验分享" value="experience" />
          <el-option label="组队" value="team" />
        </el-select>
        <el-button type="primary" :loading="loading" @click="load">查询</el-button>
      </div>
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column label="帖子" min-width="280">
          <template #default="{ row }">
            <strong>{{ row.title }}</strong>
            <div class="muted small">{{ row.content }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="post_type" label="类型" width="120" />
        <el-table-column prop="view_count" label="浏览" width="90" />
        <el-table-column prop="like_count" label="点赞" width="90" />
        <el-table-column label="发布时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { EditPen, Search } from '@element-plus/icons-vue';
import { getPosts } from '@/api/forum';
import type { ForumPost } from '@/api/types';
import { formatDateTime } from '@/utils/format';

const keyword = ref('');
const postType = ref('');
const loading = ref(false);
const items = ref<ForumPost[]>([]);

async function load() {
  loading.value = true;
  try {
    const data = await getPosts({ keyword: keyword.value, post_type: postType.value, page: 1, page_size: 20 });
    items.value = data.items;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.forum-toolbar :deep(.el-input) {
  width: 280px;
}

.forum-toolbar :deep(.el-select) {
  width: 150px;
}

.small {
  margin-top: 6px;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
