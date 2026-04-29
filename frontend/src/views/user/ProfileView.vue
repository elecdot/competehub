<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">个人中心</h1>
        <p class="page-subtitle">维护专业、年级、兴趣方向和能力阶段，提升筛选与推荐准确性。</p>
      </div>
      <el-button type="primary" :icon="Check" :loading="loading" @click="save">保存画像</el-button>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="16">
        <div class="panel panel-body">
          <h2 class="section-title">基础画像</h2>
          <el-form :model="profile" label-width="96px">
            <el-form-item label="姓名">
              <el-input v-model="profile.real_name" placeholder="请输入姓名" />
            </el-form-item>
            <el-form-item label="学院">
              <el-input v-model="profile.college" placeholder="例如：计算机学院" />
            </el-form-item>
            <el-form-item label="专业">
              <el-input v-model="profile.major" placeholder="例如：计算机科学与技术" />
            </el-form-item>
            <el-form-item label="年级">
              <el-select v-model="profile.grade" placeholder="请选择年级" class="wide">
                <el-option label="大一" value="大一" />
                <el-option label="大二" value="大二" />
                <el-option label="大三" value="大三" />
                <el-option label="大四" value="大四" />
              </el-select>
            </el-form-item>
            <el-form-item label="能力阶段">
              <el-segmented v-model="profile.ability_level" :options="abilityOptions" />
            </el-form-item>
          </el-form>
        </div>
      </el-col>

      <el-col :xs="24" :lg="8">
        <div class="panel panel-body">
          <h2 class="section-title">推荐依据</h2>
          <div class="profile-summary">
            <span>专业方向</span>
            <strong>{{ profile.major || '未填写' }}</strong>
          </div>
          <div class="profile-summary">
            <span>当前年级</span>
            <strong>{{ profile.grade || '未填写' }}</strong>
          </div>
          <div class="profile-summary">
            <span>能力阶段</span>
            <strong>{{ abilityLabel }}</strong>
          </div>
        </div>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { Check } from '@element-plus/icons-vue';
import { getMe, updateProfile } from '@/api/user';

const loading = ref(false);
const profile = reactive({
  real_name: '',
  college: '',
  major: '',
  grade: '',
  ability_level: 'beginner',
});

const abilityOptions = [
  { label: '新手', value: 'beginner' },
  { label: '进阶', value: 'intermediate' },
  { label: '冲刺', value: 'advanced' },
];

const abilityLabel = computed(() => abilityOptions.find((item) => item.value === profile.ability_level)?.label || '未设置');

async function load() {
  const data = (await getMe()) as { profile?: Record<string, string> };
  Object.assign(profile, data.profile || {});
}

async function save() {
  loading.value = true;
  try {
    await updateProfile({ ...profile });
    ElMessage.success('个人画像已保存');
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.wide {
  width: 260px;
}

.profile-summary {
  padding: 14px 0;
  border-top: 1px solid #edf2f7;
}

.profile-summary:first-of-type {
  border-top: 0;
}

.profile-summary span {
  display: block;
  color: #65758b;
  font-size: 13px;
}

.profile-summary strong {
  display: block;
  margin-top: 6px;
  font-size: 18px;
}
</style>
