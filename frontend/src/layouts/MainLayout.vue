<template>
  <el-container class="app-shell">
    <el-aside width="248px" class="app-sidebar">
      <div class="brand">
        <div class="brand-mark">CH</div>
        <div>
          <strong>CompeteHub</strong>
          <span>竞赛服务平台</span>
        </div>
      </div>

      <el-menu router :default-active="$route.path" class="nav-menu">
        <el-menu-item index="/">
          <el-icon><DataBoard /></el-icon>
          <span>工作台</span>
        </el-menu-item>
        <el-menu-item index="/competitions">
          <el-icon><Search /></el-icon>
          <span>赛事查询</span>
        </el-menu-item>
        <el-menu-item index="/recommendations">
          <el-icon><Aim /></el-icon>
          <span>个性推荐</span>
        </el-menu-item>
        <el-menu-item index="/calendar">
          <el-icon><Calendar /></el-icon>
          <span>订阅日历</span>
        </el-menu-item>
        <el-menu-item index="/forum">
          <el-icon><ChatDotRound /></el-icon>
          <span>交流论坛</span>
        </el-menu-item>
        <el-menu-item index="/profile">
          <el-icon><User /></el-icon>
          <span>个人中心</span>
        </el-menu-item>
        <el-menu-item v-if="auth.role === 'admin'" index="/admin">
          <el-icon><Setting /></el-icon>
          <span>后台管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <div class="header-title">
          <strong>{{ routeTitle }}</strong>
          <span>赛事发现、推荐与运营管理</span>
        </div>
        <div class="user-actions">
          <el-tag v-if="auth.user" effect="plain">{{ roleLabel }}</el-tag>
          <span v-if="auth.user" class="username">{{ auth.user.username }}</span>
          <el-button v-if="auth.isAuthenticated" :icon="SwitchButton" text @click="logout">退出</el-button>
          <el-button v-else type="primary" @click="$router.push('/login')">登录</el-button>
        </div>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  Aim,
  Calendar,
  ChatDotRound,
  DataBoard,
  Search,
  Setting,
  SwitchButton,
  User,
} from '@element-plus/icons-vue';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const titles: Record<string, string> = {
  '/': '工作台',
  '/competitions': '赛事查询',
  '/recommendations': '个性推荐',
  '/calendar': '订阅日历',
  '/forum': '交流论坛',
  '/profile': '个人中心',
  '/admin': '后台管理',
};

const roleNames: Record<string, string> = {
  admin: '管理员',
  student: '学生',
  teacher: '教师',
  organizer: '组织者',
  verified: '认证用户',
  guest: '访客',
};

const routeTitle = computed(() => titles[route.path] || 'CompeteHub');
const roleLabel = computed(() => roleNames[auth.role] || auth.role);

function logout() {
  auth.logout();
  router.push('/login');
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.app-sidebar {
  border-right: 1px solid #e3e8f0;
  background: #fff;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  border-bottom: 1px solid #e3e8f0;
}

.brand-mark {
  display: grid;
  flex: 0 0 40px;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 8px;
  background: #1f2937;
  color: #fff;
  font-weight: 800;
}

.brand strong {
  display: block;
  font-size: 19px;
}

.brand span {
  color: #65758b;
  font-size: 13px;
}

.nav-menu {
  border-right: 0;
  padding: 10px;
}

.nav-menu :deep(.el-menu-item) {
  height: 42px;
  border-radius: 8px;
  margin-bottom: 4px;
}

.nav-menu :deep(.el-menu-item.is-active) {
  background: #eaf2ff;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 64px;
  border-bottom: 1px solid #e3e8f0;
  background: #fff;
}

.header-title {
  display: grid;
  gap: 2px;
}

.header-title strong {
  font-size: 16px;
}

.header-title span {
  color: #65758b;
  font-size: 12px;
}

.user-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.username {
  color: #334155;
  font-weight: 600;
}

.app-main {
  padding: 0;
  background: #f4f6fa;
}
</style>
