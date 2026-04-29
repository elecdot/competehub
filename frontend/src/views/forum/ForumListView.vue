<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">交流论坛</h1>
        <p class="page-subtitle">发帖找队友、查看同好名单，并向已认证指导人咨询。</p>
      </div>
      <el-button type="primary" :icon="EditPen" @click="openCreate">发布帖子</el-button>
    </div>

    <el-tabs v-model="activeTab" class="forum-tabs">
      <el-tab-pane label="同好交流区" name="posts">
        <div class="panel panel-body">
          <div class="toolbar forum-toolbar">
            <el-input v-model="keyword" :prefix-icon="Search" placeholder="搜索帖子" clearable @keyup.enter="loadPosts" />
            <el-select v-model="postType" placeholder="帖子类型" clearable>
              <el-option label="提问" value="question" />
              <el-option label="经验分享" value="experience" />
              <el-option label="找队友" value="team" />
              <el-option label="认证答疑" value="consulting" />
            </el-select>
            <el-button type="primary" :loading="loading" @click="loadPosts">查询</el-button>
          </div>
          <el-table :data="items" v-loading="loading" stripe>
            <el-table-column label="帖子" min-width="300">
              <template #default="{ row }">
                <button class="link-title" @click="openDetail(row)">{{ row.title }}</button>
                <div class="muted small">{{ row.content }}</div>
                <div class="tag-list">
                  <el-tag v-for="tag in row.tags || []" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
                  <el-tag v-if="row.author?.premium" size="small" type="success">premium 指导人</el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="作者" width="150">
              <template #default="{ row }">{{ row.author?.username || '-' }}</template>
            </el-table-column>
            <el-table-column prop="post_type" label="类型" width="110" />
            <el-table-column label="意向" width="90">
              <template #default="{ row }">{{ row.interest_count || 0 }}</template>
            </el-table-column>
            <el-table-column label="发布时间" width="180">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" @click="openDetail(row)">查看</el-button>
                <el-button v-if="row.post_type === 'team'" text @click="interest(row)">有意向</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="同好名单推荐" name="people">
        <div class="panel panel-body">
          <div class="toolbar forum-toolbar">
            <el-input v-model="peopleKeyword" :prefix-icon="Search" placeholder="按专业、技能、目标赛事筛选" clearable />
            <el-switch v-model="onlyLooking" active-text="只看正在找队友" />
            <el-button type="primary" :loading="peopleLoading" @click="loadPeople">筛选</el-button>
          </div>
          <div class="people-grid" v-loading="peopleLoading">
            <div v-for="item in people" :key="item.user.id" class="person-row">
              <div>
                <strong>{{ item.profile.real_name || item.user.username }}</strong>
                <span>{{ item.profile.major || '未填写专业' }} · {{ item.profile.grade || '未填写年级' }}</span>
                <div class="tag-list">
                  <el-tag v-for="tag in item.shared_tags" :key="tag" size="small">{{ tag }}</el-tag>
                  <el-tag v-if="item.team_preference?.looking_for_teammates" size="small" type="success">寻找队友</el-tag>
                  <el-tag v-if="item.certifications?.length" size="small" type="warning">已认证</el-tag>
                </div>
              </div>
              <div class="match-score">{{ item.match_score }}</div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="createVisible" title="发布帖子" width="620px">
      <el-form :model="postForm" label-width="90px">
        <el-form-item label="标题">
          <el-input v-model="postForm.title" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="postForm.post_type" class="full">
            <el-option label="提问" value="question" />
            <el-option label="经验分享" value="experience" />
            <el-option label="找队友" value="team" />
            <el-option label="认证答疑" value="consulting" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="tagText" placeholder="用逗号分隔，例如：蓝桥杯, Python, 组队" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="postForm.content" type="textarea" :rows="6" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitPost">发布</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" size="520px" title="帖子详情">
      <div v-if="currentPost" class="post-detail">
        <h2>{{ currentPost.title }}</h2>
        <div class="author-line">
          <span>{{ currentPost.author?.username }}</span>
          <el-tag v-if="currentPost.author?.premium" type="success">premium 指导人</el-tag>
        </div>
        <p>{{ currentPost.content }}</p>
        <el-button v-if="currentPost.post_type === 'team'" type="primary" plain @click="interest(currentPost)">我有意向</el-button>

        <h3>评论咨询</h3>
        <div class="comment-list">
          <div
            v-for="comment in comments"
            :key="comment.id"
            class="comment-item"
            :class="{ premium: comment.author?.premium }"
          >
            <div class="author-line">
              <strong>{{ comment.author?.username || '用户' }}</strong>
              <el-tag v-if="comment.author?.premium" size="small" type="success">认证指导人</el-tag>
            </div>
            <p>{{ comment.content }}</p>
          </div>
        </div>
        <div class="comment-box">
          <el-input v-model="commentText" type="textarea" :rows="3" placeholder="输入评论或咨询问题" />
          <el-button type="primary" :loading="commenting" @click="submitComment">发布评论</el-button>
        </div>
      </div>
    </el-drawer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { EditPen, Search } from '@element-plus/icons-vue';
import { createComment, createPost, getComments, getPosts, markInterest } from '@/api/forum';
import { getMatchmakingUsers } from '@/api/user';
import type { ForumComment, ForumPost, MatchmakingUser } from '@/api/types';
import { useAuthStore } from '@/stores/auth';
import { formatDateTime } from '@/utils/format';

const auth = useAuthStore();
const activeTab = ref('posts');
const keyword = ref('');
const postType = ref('');
const loading = ref(false);
const items = ref<ForumPost[]>([]);
const createVisible = ref(false);
const creating = ref(false);
const tagText = ref('');
const postForm = reactive({ title: '', content: '', post_type: 'team' });
const detailVisible = ref(false);
const currentPost = ref<ForumPost | null>(null);
const comments = ref<ForumComment[]>([]);
const commentText = ref('');
const commenting = ref(false);
const peopleKeyword = ref('');
const onlyLooking = ref(true);
const peopleLoading = ref(false);
const people = ref<MatchmakingUser[]>([]);

function requireLogin() {
  if (auth.isAuthenticated) return true;
  ElMessage.warning('请先登录后再操作');
  return false;
}

function splitTags(value: string) {
  return value
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

async function loadPosts() {
  loading.value = true;
  try {
    const data = await getPosts({ keyword: keyword.value, post_type: postType.value, page: 1, page_size: 30 });
    items.value = data.items;
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  if (!requireLogin()) return;
  createVisible.value = true;
}

async function submitPost() {
  if (!postForm.title || !postForm.content) {
    ElMessage.warning('请填写标题和内容');
    return;
  }
  creating.value = true;
  try {
    await createPost({ ...postForm, tags: splitTags(tagText.value) });
    Object.assign(postForm, { title: '', content: '', post_type: 'team' });
    tagText.value = '';
    createVisible.value = false;
    ElMessage.success('帖子已发布');
    await loadPosts();
  } finally {
    creating.value = false;
  }
}

async function openDetail(row: ForumPost) {
  currentPost.value = row;
  detailVisible.value = true;
  comments.value = await getComments(row.id);
}

async function submitComment() {
  if (!currentPost.value || !commentText.value) return;
  if (!requireLogin()) return;
  commenting.value = true;
  try {
    const comment = await createComment(currentPost.value.id, { content: commentText.value });
    comments.value = [...comments.value, comment];
    commentText.value = '';
  } finally {
    commenting.value = false;
  }
}

async function interest(row: ForumPost) {
  if (!requireLogin()) return;
  const { value } = await ElMessageBox.prompt('给对方留一句简短说明', '标记有意向', {
    confirmButtonText: '提交',
    cancelButtonText: '取消',
    inputPlaceholder: '例如：我擅长算法，希望加入队伍',
  });
  const result = await markInterest(row.id, { message: value });
  row.interested = true;
  row.interest_count = (row.interest_count || 0) + 1;
  ElMessage.success(`已标记意向，联系方式：${JSON.stringify(result.author_contact || {})}`);
}

async function loadPeople() {
  if (!requireLogin()) return;
  peopleLoading.value = true;
  try {
    people.value = await getMatchmakingUsers({ keyword: peopleKeyword.value, looking: onlyLooking.value ? '1' : '' });
  } finally {
    peopleLoading.value = false;
  }
}

watch(activeTab, (value) => {
  if (value === 'people' && people.value.length === 0 && auth.isAuthenticated) {
    loadPeople();
  }
});

onMounted(loadPosts);
</script>

<style scoped>
.forum-tabs {
  padding: 0 24px 24px;
}

.forum-toolbar {
  margin-bottom: 16px;
}

.forum-toolbar :deep(.el-input) {
  width: 300px;
}

.forum-toolbar :deep(.el-select) {
  width: 150px;
}

.full {
  width: 100%;
}

.link-title {
  border: 0;
  background: none;
  color: #1d4ed8;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  padding: 0;
}

.small {
  margin-top: 6px;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.people-grid {
  display: grid;
  gap: 12px;
}

.person-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
  border-top: 1px solid #edf2f7;
}

.person-row:first-child {
  border-top: 0;
}

.person-row strong,
.person-row span {
  display: block;
}

.person-row span {
  color: #65758b;
  margin-top: 4px;
}

.match-score {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border-radius: 8px;
  background: #ecfdf5;
  color: #047857;
  font-weight: 800;
}

.post-detail h2 {
  margin: 0 0 8px;
}

.author-line {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
}

.comment-list {
  display: grid;
  gap: 10px;
  margin: 14px 0;
}

.comment-item {
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.comment-item.premium {
  border-color: #86efac;
  background: #f0fdf4;
}

.comment-box {
  display: grid;
  gap: 10px;
}
</style>
