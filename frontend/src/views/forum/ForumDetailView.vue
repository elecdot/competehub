<template>
  <section class="page">
    <div class="detail-shell" v-loading="loading">
      <div v-if="post" class="post-stage">
        <div class="post-hero">
          <el-button text @click="$router.push('/forum')">返回论坛</el-button>
          <h1>{{ post.title }}</h1>
          <div class="author-line">
            <span>{{ post.author?.username || '用户' }}</span>
            <el-tag v-if="post.author?.premium" type="success">premium 指导人</el-tag>
            <span>{{ formatDateTime(post.created_at) }}</span>
          </div>
          <p>{{ post.content }}</p>
          <div class="tag-list">
            <el-tag v-for="tag in post.tags || []" :key="tag" effect="plain">{{ tag }}</el-tag>
          </div>
          <div class="action-bar">
            <el-button :icon="Pointer" @click="like">点赞 {{ post.like_count || 0 }}</el-button>
            <el-button :icon="ChatDotRound" @click="focusComment">评论 {{ post.comment_count || comments.length }}</el-button>
            <el-button v-if="post.post_type === 'team'" type="primary" :icon="Connection" @click="interest">
              有意向 {{ post.interest_count || 0 }}
            </el-button>
          </div>
        </div>

        <div class="conversation">
          <div class="flow-line" />
          <div class="composer" ref="composerRef">
            <el-input
              v-model="commentText"
              type="textarea"
              :rows="3"
              :placeholder="replyTarget ? `回复 ${replyTarget.author?.username || '该评论'}` : '写下评论、咨询问题或经验补充'"
            />
            <div class="composer-actions">
              <el-button v-if="replyTarget" text @click="replyTarget = null">取消回复</el-button>
              <el-button type="primary" :loading="commenting" @click="submitComment">发布评论</el-button>
            </div>
          </div>

          <div v-for="item in flatComments" :key="item.comment.id" class="dialog-row" :style="{ marginLeft: `${item.depth * 34}px` }">
            <div class="avatar">{{ item.comment.author?.username?.slice(0, 1).toUpperCase() || 'U' }}</div>
            <div class="bubble" :class="{ premium: item.comment.author?.premium }">
              <div class="bubble-head">
                <strong>{{ item.comment.author?.username || '用户' }}</strong>
                <el-tag v-if="item.comment.author?.premium" size="small" type="success">认证指导人</el-tag>
                <span>{{ formatDateTime(item.comment.created_at) }}</span>
              </div>
              <p>{{ item.comment.content }}</p>
              <el-button text size="small" @click="replyTo(item.comment)">回复</el-button>
            </div>
          </div>

          <EmptyState
            v-if="!loading && comments.length === 0"
            title="暂无评论"
            description="成为第一个回复的人，发帖人会在收件箱收到提醒。"
          />
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { ChatDotRound, Connection, Pointer } from '@element-plus/icons-vue';
import { createComment, getComments, getPost, likePost, markInterest } from '@/api/forum';
import type { ForumComment, ForumPost } from '@/api/types';
import EmptyState from '@/components/common/EmptyState.vue';
import { useAuthStore } from '@/stores/auth';
import { formatDateTime } from '@/utils/format';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const commenting = ref(false);
const post = ref<ForumPost | null>(null);
const comments = ref<ForumComment[]>([]);
const commentText = ref('');
const replyTarget = ref<ForumComment | null>(null);
const composerRef = ref<HTMLElement | null>(null);

const flatComments = computed(() => {
  const byParent = new Map<number | null, ForumComment[]>();
  comments.value.forEach((comment) => {
    const key = comment.parent_id || null;
    byParent.set(key, [...(byParent.get(key) || []), comment]);
  });
  const result: Array<{ comment: ForumComment; depth: number }> = [];
  function walk(parentId: number | null, depth: number) {
    (byParent.get(parentId) || []).forEach((comment) => {
      result.push({ comment, depth });
      walk(comment.id, depth + 1);
    });
  }
  walk(null, 0);
  return result;
});

function requireLogin() {
  if (auth.isAuthenticated) return true;
  ElMessage.warning('请先登录后再操作');
  router.push({ name: 'login', query: { redirect: route.fullPath } });
  return false;
}

async function load() {
  loading.value = true;
  try {
    const id = Number(route.params.id);
    post.value = await getPost(id);
    comments.value = await getComments(id);
  } finally {
    loading.value = false;
  }
}

function focusComment() {
  composerRef.value?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function replyTo(comment: ForumComment) {
  replyTarget.value = comment;
  focusComment();
}

async function submitComment() {
  if (!post.value || !commentText.value) return;
  if (!requireLogin()) return;
  commenting.value = true;
  try {
    const comment = await createComment(post.value.id, {
      content: commentText.value,
      parent_id: replyTarget.value?.id,
    });
    comments.value = [...comments.value, comment];
    post.value.comment_count = (post.value.comment_count || 0) + 1;
    commentText.value = '';
    replyTarget.value = null;
    ElMessage.success('评论已发布，对方会在收件箱收到提醒');
  } finally {
    commenting.value = false;
  }
}

async function like() {
  if (!post.value) return;
  if (!requireLogin()) return;
  post.value = await likePost(post.value.id);
}

async function interest() {
  if (!post.value) return;
  if (!requireLogin()) return;
  const { value } = await ElMessageBox.prompt('给发帖人留一句说明，系统会发送到对方收件箱', '标记有意向', {
    confirmButtonText: '提交',
    cancelButtonText: '取消',
    inputPlaceholder: '例如：我擅长算法，希望加入队伍',
  });
  await markInterest(post.value.id, { message: value });
  post.value.interest_count = (post.value.interest_count || 0) + 1;
  post.value.interested = true;
  ElMessage.success('已发送到发帖人的收件箱');
}

onMounted(load);
</script>

<style scoped>
.detail-shell {
  padding: 24px;
}

.post-stage {
  display: grid;
  gap: 18px;
  max-width: 980px;
  margin: 0 auto;
}

.post-hero {
  animation: rise-in 0.28s ease both;
  padding: 24px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e5e7eb;
}

.post-hero h1 {
  margin: 8px 0;
  font-size: 26px;
}

.post-hero p {
  color: #334155;
  line-height: 1.9;
}

.author-line,
.action-bar,
.composer-actions,
.bubble-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.author-line,
.bubble-head span {
  color: #64748b;
  font-size: 13px;
}

.action-bar {
  margin-top: 18px;
}

.conversation {
  position: relative;
  display: grid;
  gap: 14px;
  padding: 24px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e5e7eb;
}

.flow-line {
  position: absolute;
  left: 45px;
  top: 96px;
  bottom: 24px;
  width: 2px;
  background: #e2e8f0;
}

.composer {
  display: grid;
  gap: 10px;
  z-index: 1;
}

.composer-actions {
  justify-content: flex-end;
}

.dialog-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  animation: slide-in 0.22s ease both;
  z-index: 1;
}

.avatar {
  display: grid;
  flex: 0 0 42px;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 50%;
  background: #1f2937;
  color: #fff;
  font-weight: 800;
}

.bubble {
  max-width: 760px;
  padding: 12px 14px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
}

.bubble.premium {
  background: #f0fdf4;
  border-color: #86efac;
}

.bubble p {
  margin: 8px 0 4px;
  color: #334155;
  line-height: 1.75;
}

@keyframes rise-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateX(-8px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
