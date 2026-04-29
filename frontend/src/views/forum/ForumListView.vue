<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">交流论坛</h1>
        <p class="page-subtitle">发帖找队友、浏览同好名单、向认证指导人咨询。</p>
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

          <div class="post-grid" v-loading="loading">
            <article v-for="row in items" :key="row.id" class="post-card" @click="openDetail(row.id)">
              <div class="post-head">
                <div>
                  <h2>{{ row.title }}</h2>
                  <span>{{ row.author?.username || '-' }}</span>
                </div>
                <el-tag v-if="row.author?.premium" type="success">premium 指导人</el-tag>
              </div>
              <p>{{ row.content }}</p>
              <div class="tag-list">
                <el-tag v-for="tag in row.tags || []" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
              </div>
              <div class="post-meta">
                <span>赞 {{ row.like_count || 0 }}</span>
                <span>评 {{ row.comment_count || 0 }}</span>
                <span>意向 {{ row.interest_count || 0 }}</span>
                <span>{{ formatDateTime(row.created_at) }}</span>
              </div>
            </article>
          </div>
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
            <button v-for="item in people" :key="item.user.id" class="person-row" @click="openPerson(item)">
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
            </button>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="createVisible" title="发布帖子" width="660px">
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
        <el-form-item label="关联赛事">
          <el-select v-model="selectedCompetitionTitle" filterable clearable class="full" placeholder="选择官方规范赛事名称">
            <el-option v-for="item in options.competitions" :key="item.id" :label="item.title" :value="item.title" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="selectedTags" multiple filterable class="full" placeholder="从统一标签中选择">
            <el-option v-for="tag in options.forum_tags" :key="tag" :label="tag" :value="tag" />
          </el-select>
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

    <el-dialog v-model="personVisible" title="同好资料" width="620px">
      <div v-if="currentPerson" class="person-detail">
        <h2>{{ currentPerson.profile.real_name || currentPerson.user.username }}</h2>
        <p>{{ currentPerson.profile.major || '未填写专业' }} · {{ currentPerson.profile.grade || '未填写年级' }}</p>
        <div class="tag-list">
          <el-tag v-for="skill in currentPerson.team_preference?.required_skills || []" :key="skill">{{ skill }}</el-tag>
          <el-tag v-for="competition in currentPerson.team_preference?.target_competitions || []" :key="competition" type="success">
            {{ competition }}
          </el-tag>
        </div>
        <div class="cert-box" v-if="currentPerson.certifications?.length">
          <strong>认证经历</strong>
          <p v-for="cert in currentPerson.certifications" :key="cert.id">{{ cert.description }}</p>
        </div>
        <el-input v-model="contactMessage" type="textarea" :rows="3" placeholder="给对方留一句联系说明" />
      </div>
      <template #footer>
        <el-button @click="personVisible = false">关闭</el-button>
        <el-button type="primary" :loading="contactLoading" @click="sendContact">发送到对方收件箱</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { EditPen, Search } from '@element-plus/icons-vue';
import { getCompetitionOptions } from '@/api/competition';
import { createPost, getPosts } from '@/api/forum';
import { contactUser, getMatchmakingUsers } from '@/api/user';
import type { CompetitionOptions, ForumPost, MatchmakingUser } from '@/api/types';
import { useAuthStore } from '@/stores/auth';
import { formatDateTime } from '@/utils/format';

const router = useRouter();
const auth = useAuthStore();
const activeTab = ref('posts');
const keyword = ref('');
const postType = ref('');
const loading = ref(false);
const items = ref<ForumPost[]>([]);
const createVisible = ref(false);
const creating = ref(false);
const selectedTags = ref<string[]>([]);
const selectedCompetitionTitle = ref('');
const postForm = reactive({ title: '', content: '', post_type: 'team' });
const peopleKeyword = ref('');
const onlyLooking = ref(true);
const peopleLoading = ref(false);
const people = ref<MatchmakingUser[]>([]);
const personVisible = ref(false);
const currentPerson = ref<MatchmakingUser | null>(null);
const contactMessage = ref('');
const contactLoading = ref(false);
const options = reactive<CompetitionOptions>({ competitions: [], categories: [], levels: [], tags: [], skills: [], forum_tags: [] });

function requireLogin() {
  if (auth.isAuthenticated) return true;
  ElMessage.warning('请先登录后再操作');
  router.push('/login');
  return false;
}

async function loadOptions() {
  Object.assign(options, await getCompetitionOptions());
}

async function loadPosts() {
  loading.value = true;
  try {
    const data = await getPosts({ keyword: keyword.value, post_type: postType.value, page: 1, page_size: 50 });
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
    const tags = Array.from(new Set([...selectedTags.value, selectedCompetitionTitle.value].filter(Boolean)));
    await createPost({ ...postForm, tags });
    Object.assign(postForm, { title: '', content: '', post_type: 'team' });
    selectedTags.value = [];
    selectedCompetitionTitle.value = '';
    createVisible.value = false;
    ElMessage.success('帖子已发布');
    await loadPosts();
  } finally {
    creating.value = false;
  }
}

function openDetail(id: number) {
  router.push(`/forum/posts/${id}`);
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

function openPerson(item: MatchmakingUser) {
  currentPerson.value = item;
  contactMessage.value = `我对你的组队方向感兴趣，希望交流 ${item.team_preference?.target_competitions?.[0] || '竞赛组队'}。`;
  personVisible.value = true;
}

async function sendContact() {
  if (!currentPerson.value) return;
  contactLoading.value = true;
  try {
    await contactUser(currentPerson.value.user.id, { message: contactMessage.value });
    ElMessage.success('已发送到对方收件箱');
    personVisible.value = false;
  } finally {
    contactLoading.value = false;
  }
}

watch(activeTab, (value) => {
  if (value === 'people' && people.value.length === 0 && auth.isAuthenticated) {
    loadPeople();
  }
});

onMounted(async () => {
  await loadOptions();
  await loadPosts();
});
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

.post-grid {
  display: grid;
  gap: 14px;
}

.post-card {
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.post-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.post-head,
.post-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.post-head h2 {
  margin: 0 0 6px;
  font-size: 17px;
}

.post-head span,
.post-card p,
.post-meta {
  color: #64748b;
}

.post-card p {
  line-height: 1.7;
}

.post-meta {
  justify-content: flex-start;
  margin-top: 12px;
  font-size: 13px;
}

.people-grid {
  display: grid;
  gap: 12px;
}

.person-row {
  display: flex;
  width: 100%;
  justify-content: space-between;
  gap: 16px;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  text-align: left;
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

.person-detail h2 {
  margin: 0 0 8px;
}

.person-detail p {
  color: #475569;
  line-height: 1.7;
}

.cert-box {
  margin: 14px 0;
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
}
</style>
