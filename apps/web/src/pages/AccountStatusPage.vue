<script setup lang="ts">
import { ReloadOutlined, UserOutlined } from '@ant-design/icons-vue'
import {
  Alert as AAlert,
  Button as AButton,
  Descriptions as ADescriptions,
  DescriptionsItem as ADescriptionsItem,
  Result as AResult,
  Skeleton as ASkeleton,
  Tag as ATag,
} from 'ant-design-vue'
import { computed, onMounted, ref } from 'vue'

import { fetchCurrentProfile } from '@/api/client'
import { useAuthStore } from '@/stores/auth_store'
import type { StudentProfile } from '@/types/auth'

const auth = useAuthStore()
const profile = ref<StudentProfile | null>(null)
const profileLoading = ref(false)
const profileError = ref('')

const missingFieldLabels: Record<string, string> = {
  college: '学院',
  major: '专业',
  grade: '年级',
  interest_tags: '兴趣标签',
}

const displayName = computed(() => auth.currentUser?.displayName || `用户 ${auth.currentUser?.id}`)
const capabilities = computed(() => auth.currentUser?.capabilities ?? [])
const missingFields = computed(() =>
  (profile.value?.missing_fields ?? []).map((field) => missingFieldLabels[field] ?? field),
)

async function loadProfile() {
  if (auth.currentUser?.role !== 'student') {
    profile.value = null
    return
  }
  profileLoading.value = true
  profileError.value = ''
  try {
    profile.value = await fetchCurrentProfile()
  } catch {
    profile.value = null
    profileError.value = 'profile_load_failed'
  } finally {
    profileLoading.value = false
  }
}

async function reload() {
  await auth.loadCurrentUser()
  await loadProfile()
}

onMounted(reload)
</script>

<template>
  <section class="account-page">
    <div class="page-heading">
      <div>
        <h1 class="page-title">账号状态</h1>
        <p class="page-description">当前会话、角色权限和学生画像就绪状态。</p>
      </div>
      <AButton :loading="auth.loading || profileLoading" @click="reload">
        <template #icon><ReloadOutlined /></template>
        刷新
      </AButton>
    </div>

    <ASkeleton v-if="auth.loading && !auth.currentUser" active />

    <AResult
      v-else-if="!auth.currentUser"
      class="state-panel"
      status="403"
      title="未登录"
      sub-title="当前浏览器没有有效会话。"
    />

    <div v-else class="status-layout">
      <section class="status-section" aria-labelledby="account-heading">
        <div class="section-title-row">
          <UserOutlined />
          <h2 id="account-heading">当前用户</h2>
        </div>
        <ADescriptions bordered :column="1" size="small">
          <ADescriptionsItem label="显示名">{{ displayName }}</ADescriptionsItem>
          <ADescriptionsItem label="角色">
            <ATag color="green">{{ auth.currentUser.role }}</ATag>
          </ADescriptionsItem>
          <ADescriptionsItem label="Capabilities">
            <span v-if="capabilities.length" class="inline-tags">
              <ATag v-for="capability in capabilities" :key="capability" color="blue">
                {{ capability }}
              </ATag>
            </span>
            <span v-else>[]</span>
          </ADescriptionsItem>
        </ADescriptions>
      </section>

      <section
        v-if="auth.currentUser.role === 'student'"
        class="status-section"
        aria-labelledby="profile-heading"
      >
        <h2 id="profile-heading">学生画像</h2>
        <ASkeleton v-if="profileLoading" active />
        <AAlert
          v-else-if="profileError"
          type="error"
          message="画像状态加载失败"
          show-icon
        />
        <ADescriptions v-else-if="profile" bordered :column="1" size="small">
          <ADescriptionsItem label="状态">
            <ATag :color="profile.profile_status === 'recommendation_ready' ? 'green' : 'orange'">
              {{ profile.profile_status }}
            </ATag>
          </ADescriptionsItem>
          <ADescriptionsItem label="缺少字段">
            <span v-if="missingFields.length" class="inline-tags">
              <ATag v-for="field in missingFields" :key="field" color="orange">
                {{ field }}
              </ATag>
            </span>
            <span v-else>[]</span>
          </ADescriptionsItem>
          <ADescriptionsItem label="学院">{{ profile.college ?? '未填写' }}</ADescriptionsItem>
          <ADescriptionsItem label="专业">{{ profile.major ?? '未填写' }}</ADescriptionsItem>
          <ADescriptionsItem label="年级">{{ profile.grade ?? '未填写' }}</ADescriptionsItem>
          <ADescriptionsItem label="兴趣标签">
            <span v-if="profile.interest_tags.length" class="inline-tags">
              <ATag v-for="tag in profile.interest_tags" :key="tag">{{ tag }}</ATag>
            </span>
            <span v-else>[]</span>
          </ADescriptionsItem>
        </ADescriptions>
      </section>
    </div>
  </section>
</template>
