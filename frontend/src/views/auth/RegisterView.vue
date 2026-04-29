<template>
  <main class="auth-page">
    <section class="auth-panel">
      <h1>注册账号</h1>
      <p>创建账号后可维护画像、收藏赛事并获取推荐。</p>
      <el-form :model="form" label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-button type="primary" class="full" :loading="loading" @click="submit">注册</el-button>
        <el-button class="full secondary" @click="$router.push('/login')">返回登录</el-button>
      </el-form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { register } from '@/api/auth';

const router = useRouter();
const loading = ref(false);
const form = reactive({ username: '', email: '', password: '', role: 'student' });

async function submit() {
  loading.value = true;
  try {
    await register(form);
    ElMessage.success('注册成功，请登录');
    router.push('/login');
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
