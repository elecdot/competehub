<template>
  <main class="auth-page">
    <section class="auth-panel">
      <h1>登录 CompeteHub</h1>
      <p>进入竞赛信息、推荐与订阅管理工作台。</p>
      <el-form :model="form" label-position="top" @submit.prevent="submit">
        <el-form-item label="账号">
          <el-input v-model="form.account" placeholder="用户名 / 邮箱 / 手机号 / 学号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-button type="primary" class="full" :loading="loading" @click="submit">登录</el-button>
        <el-button class="full secondary" @click="$router.push('/register')">注册账号</el-button>
      </el-form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const loading = ref(false);
const form = reactive({ account: '', password: '' });

async function submit() {
  loading.value = true;
  try {
    await auth.login(form);
    router.push((route.query.redirect as string) || '/');
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  background: #eef2f7;
}

.auth-panel {
  width: min(420px, calc(100vw - 32px));
  padding: 28px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.auth-panel h1 {
  margin: 0 0 8px;
}

.auth-panel p {
  margin: 0 0 24px;
  color: #64748b;
}

.full {
  width: 100%;
  margin: 8px 0 0;
}

.secondary {
  margin-left: 0;
}
</style>

