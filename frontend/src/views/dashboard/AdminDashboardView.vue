<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">后台管理</h1>
        <p class="page-subtitle">查看账户、发帖、认证申请和系统统计，不展示密码字段。</p>
      </div>
      <el-button type="primary" :icon="Refresh" :loading="loading" @click="loadAll">刷新后台</el-button>
    </div>

    <div class="stat-grid">
      <div v-for="item in statItems" :key="item.key" class="stat-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </div>
    </div>

    <div class="panel panel-body">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="账户信息" name="users">
          <el-table :data="users" v-loading="loading" stripe>
            <el-table-column prop="username" label="账号" width="130" />
            <el-table-column prop="role" label="角色" width="100" />
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column label="画像" min-width="260">
              <template #default="{ row }">
                {{ row.profile?.real_name || '-' }} · {{ row.profile?.major || '未填专业' }} ·
                {{ row.profile?.grade || '未填年级' }}
              </template>
            </el-table-column>
            <el-table-column label="发帖数" width="90">
              <template #default="{ row }">{{ row.post_count || 0 }}</template>
            </el-table-column>
            <el-table-column label="认证" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.certifications?.some((item: any) => item.status === 'approved')" type="success">
                  已认证
                </el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="130">
              <template #default="{ row }">
                <el-button text type="primary" @click="loadPosts(row.id)">查看发帖</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="帖子管理" name="posts">
          <el-table :data="posts" v-loading="postLoading" stripe>
            <el-table-column prop="title" label="标题" min-width="260" />
            <el-table-column label="作者" width="130">
              <template #default="{ row }">{{ row.author?.username || row.author_id }}</template>
            </el-table-column>
            <el-table-column prop="post_type" label="类型" width="110" />
            <el-table-column prop="status" label="状态" width="110" />
            <el-table-column label="发布时间" width="180">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="110" fixed="right">
              <template #default="{ row }">
                <el-button text type="danger" :disabled="row.status === 'deleted'" @click="removePost(row.id)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="认证审核" name="certifications">
          <el-table :data="certifications" v-loading="certLoading" stripe>
            <el-table-column label="用户" width="130">
              <template #default="{ row }">{{ row.user?.username || row.user_id }}</template>
            </el-table-column>
            <el-table-column prop="certification_type" label="类型" width="130" />
            <el-table-column prop="description" label="说明" min-width="300" />
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column label="操作" width="170" fixed="right">
              <template #default="{ row }">
                <el-button text type="success" @click="review(row.id, 'approved')">通过</el-button>
                <el-button text type="danger" @click="review(row.id, 'rejected')">驳回</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Refresh } from '@element-plus/icons-vue';
import {
  deleteAdminPost,
  getAdminCertifications,
  getAdminPosts,
  getAdminUsers,
  getStatistics,
  reviewCertification,
} from '@/api/admin';
import type { CertificationRequest, ForumPost, User } from '@/api/types';
import { formatDateTime } from '@/utils/format';

const activeTab = ref('users');
const loading = ref(false);
const postLoading = ref(false);
const certLoading = ref(false);
const stats = ref<Record<string, number>>({});
const users = ref<Array<User & Record<string, any>>>([]);
const posts = ref<ForumPost[]>([]);
const certifications = ref<CertificationRequest[]>([]);

const labels: Record<string, string> = {
  users: '用户数',
  competitions: '赛事总数',
  published_competitions: '已发布赛事',
  favorites: '收藏记录',
  subscriptions: '订阅记录',
  posts: '论坛帖子',
  certifications_pending: '待审认证',
};

const statItems = computed(() =>
  Object.entries(labels).map(([key, label]) => ({
    key,
    label,
    value: stats.value[key] ?? 0,
  })),
);

async function loadAll() {
  loading.value = true;
  certLoading.value = true;
  try {
    const [statData, userData, certData] = await Promise.all([
      getStatistics(),
      getAdminUsers(),
      getAdminCertifications(),
    ]);
    stats.value = statData;
    users.value = userData;
    certifications.value = certData;
    await loadPosts();
  } finally {
    loading.value = false;
    certLoading.value = false;
  }
}

async function loadPosts(userId?: number) {
  postLoading.value = true;
  try {
    posts.value = await getAdminPosts(userId ? { user_id: userId } : {});
    activeTab.value = 'posts';
  } finally {
    postLoading.value = false;
  }
}

async function removePost(id: number) {
  await ElMessageBox.confirm('确认删除这条帖子？删除后普通用户不可见。', '删除帖子', { type: 'warning' });
  await deleteAdminPost(id);
  ElMessage.success('帖子已删除');
  await loadPosts();
}

async function review(id: number, status: 'approved' | 'rejected') {
  await reviewCertification(id, { status });
  ElMessage.success('认证状态已更新');
  certifications.value = await getAdminCertifications();
  stats.value = await getStatistics();
}

onMounted(loadAll);
</script>

<style scoped>
:deep(.el-tabs__header) {
  margin-bottom: 18px;
}
</style>
