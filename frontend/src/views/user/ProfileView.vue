<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">个人中心</h1>
        <p class="page-subtitle">维护专业画像、竞赛经历、组队意向和 premium 指导人认证。</p>
      </div>
      <el-button type="primary" :icon="Check" :loading="loading" @click="save">保存画像</el-button>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="15">
        <div class="panel panel-body">
          <h2 class="section-title">基础画像</h2>
          <el-form :model="profile" label-width="110px">
            <el-form-item label="姓名">
              <el-input v-model="profile.real_name" placeholder="请输入姓名" />
            </el-form-item>
            <el-form-item label="学院">
              <el-input v-model="profile.college" placeholder="例如：信息学部" />
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
            <el-form-item label="兴趣技能">
              <el-input v-model="interestText" placeholder="用逗号分隔，例如：算法, Python, 数学建模" />
            </el-form-item>
          </el-form>
        </div>

        <div class="panel panel-body section-gap">
          <h2 class="section-title">获奖经历标签</h2>
          <div class="award-form">
            <el-input v-model="awardForm.competition" placeholder="赛事名称" />
            <el-select v-model="awardForm.category" placeholder="方向">
              <el-option label="数学建模" value="数学建模" />
              <el-option label="程序设计" value="程序设计" />
              <el-option label="计算机设计" value="计算机设计" />
              <el-option label="电子信息" value="电子信息" />
              <el-option label="创新创业" value="创新创业" />
            </el-select>
            <el-select v-model="awardForm.level" placeholder="级别">
              <el-option label="国一" value="国一" />
              <el-option label="国二" value="国二" />
              <el-option label="省一" value="省一" />
              <el-option label="省二" value="省二" />
              <el-option label="校级" value="校级" />
            </el-select>
            <el-input v-model="awardForm.year" placeholder="年份" />
            <el-button :icon="Plus" @click="addAward">添加</el-button>
          </div>

          <div class="award-list">
            <el-tag
              v-for="(award, index) in profile.competition_experiences"
              :key="`${award.competition}-${index}`"
              class="award-tag"
              :style="awardStyle(award)"
              closable
              @close="removeAward(index)"
            >
              {{ award.competition }} · {{ award.level }} · {{ award.year || '未填年份' }}
            </el-tag>
          </div>
        </div>

        <div class="panel panel-body section-gap">
          <h2 class="section-title">组队意向</h2>
          <el-form label-width="130px">
            <el-form-item label="寻找队友">
              <el-switch v-model="teamPreference.looking_for_teammates" />
            </el-form-item>
            <el-form-item label="目标赛事">
              <el-input v-model="targetCompetitionText" placeholder="用逗号分隔，例如：蓝桥杯, 计算机设计大赛" />
            </el-form-item>
            <el-form-item label="需要技能">
              <el-input v-model="requiredSkillText" placeholder="用逗号分隔，例如：算法, 建模, UI设计" />
            </el-form-item>
            <el-form-item label="期望奖项经历">
              <el-input v-model="requiredAwardText" placeholder="用逗号分隔，例如：数学建模省奖, 蓝桥杯省奖" />
            </el-form-item>
            <el-form-item label="联系方式说明">
              <el-input v-model="teamPreference.contact_preference" placeholder="例如：站内联系 / 邮箱 / 微信课后交换" />
            </el-form-item>
          </el-form>
        </div>
      </el-col>

      <el-col :xs="24" :lg="9">
        <div class="panel panel-body">
          <h2 class="section-title">认证申请</h2>
          <el-form label-position="top">
            <el-form-item label="认证类型">
              <el-select v-model="certForm.certification_type" class="full">
                <el-option label="premium 指导人" value="premium" />
                <el-option label="获奖经历" value="award" />
              </el-select>
            </el-form-item>
            <el-form-item label="材料说明">
              <el-input
                v-model="certForm.description"
                type="textarea"
                :rows="4"
                placeholder="填写奖项、等级、年份、可指导方向"
              />
            </el-form-item>
            <el-form-item label="证明材料链接">
              <el-input v-model="certForm.evidence_url" placeholder="可填写网盘、图片或证书链接" />
            </el-form-item>
            <el-button type="primary" class="full" :loading="certLoading" @click="submitCertification">提交认证</el-button>
          </el-form>

          <div class="cert-list">
            <div v-for="item in certifications" :key="item.id" class="cert-item">
              <el-tag :type="item.status === 'approved' ? 'success' : item.status === 'rejected' ? 'danger' : 'warning'">
                {{ statusLabel(item.status) }}
              </el-tag>
              <strong>{{ item.certification_type }}</strong>
              <p>{{ item.description }}</p>
            </div>
          </div>
        </div>

        <div class="panel panel-body section-gap">
          <h2 class="section-title">画像摘要</h2>
          <div class="profile-summary">
            <span>专业方向</span>
            <strong>{{ profile.major || '未填写' }}</strong>
          </div>
          <div class="profile-summary">
            <span>组队状态</span>
            <strong>{{ teamPreference.looking_for_teammates ? '正在寻找队友' : '暂不寻找队友' }}</strong>
          </div>
          <div class="profile-summary">
            <span>认证状态</span>
            <strong>{{ approvedCertifications.length ? 'premium/获奖认证已通过' : '暂无已通过认证' }}</strong>
          </div>
        </div>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { Check, Plus } from '@element-plus/icons-vue';
import { createCertification, getMe } from '@/api/user';
import { updateProfile } from '@/api/user';
import type { AwardExperience, CertificationRequest, TeamPreference, UserProfile } from '@/api/types';

const loading = ref(false);
const certLoading = ref(false);
const profile = reactive<UserProfile>({
  real_name: '',
  college: '',
  major: '',
  grade: '',
  ability_level: 'beginner',
  interests: [],
  competition_experiences: [],
  goals: [],
});
const teamPreference = reactive<TeamPreference>({
  looking_for_teammates: false,
  target_competitions: [],
  required_awards: [],
  required_skills: [],
  contact_preference: '',
});
const certifications = ref<CertificationRequest[]>([]);
const interestText = ref('');
const targetCompetitionText = ref('');
const requiredSkillText = ref('');
const requiredAwardText = ref('');
const awardForm = reactive<AwardExperience>({ competition: '', category: '', level: '', year: '' });
const certForm = reactive({ certification_type: 'premium', description: '', evidence_url: '' });

const abilityOptions = [
  { label: '新手', value: 'beginner' },
  { label: '进阶', value: 'intermediate' },
  { label: '冲刺', value: 'advanced' },
];

const approvedCertifications = computed(() => certifications.value.filter((item) => item.status === 'approved'));

function splitTags(value: string) {
  return value
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function syncTexts() {
  interestText.value = (profile.interests || []).join(', ');
  targetCompetitionText.value = (teamPreference.target_competitions || []).join(', ');
  requiredSkillText.value = (teamPreference.required_skills || []).join(', ');
  requiredAwardText.value = (teamPreference.required_awards || []).join(', ');
}

function awardStyle(award: AwardExperience) {
  const categoryColors: Record<string, string> = {
    数学建模: '30, 100, 210',
    程序设计: '22, 130, 90',
    计算机设计: '126, 58, 242',
    电子信息: '220, 88, 42',
    创新创业: '190, 120, 25',
  };
  const alphaMap: Record<string, number> = { 国一: 0.95, 国二: 0.76, 省一: 0.58, 省二: 0.42, 校级: 0.28 };
  const rgb = categoryColors[award.category || ''] || '75, 85, 99';
  const alpha = alphaMap[award.level || ''] || 0.32;
  return {
    backgroundColor: `rgba(${rgb}, ${alpha})`,
    borderColor: `rgba(${rgb}, ${Math.min(alpha + 0.2, 1)})`,
    color: alpha > 0.55 ? '#fff' : '#111827',
  };
}

function addAward() {
  if (!awardForm.competition || !awardForm.level) {
    ElMessage.warning('请填写赛事名称和获奖级别');
    return;
  }
  profile.competition_experiences = [...(profile.competition_experiences || []), { ...awardForm }];
  Object.assign(awardForm, { competition: '', category: '', level: '', year: '' });
}

function removeAward(index: number) {
  profile.competition_experiences = (profile.competition_experiences || []).filter((_, itemIndex) => itemIndex !== index);
}

async function load() {
  const data = (await getMe()) as {
    profile?: UserProfile;
    team_preference?: TeamPreference;
    certifications?: CertificationRequest[];
  };
  Object.assign(profile, data.profile || {});
  Object.assign(teamPreference, data.team_preference || {});
  certifications.value = data.certifications || [];
  syncTexts();
}

async function save() {
  loading.value = true;
  try {
    profile.interests = splitTags(interestText.value);
    teamPreference.target_competitions = splitTags(targetCompetitionText.value);
    teamPreference.required_skills = splitTags(requiredSkillText.value);
    teamPreference.required_awards = splitTags(requiredAwardText.value);
    await updateProfile({ ...profile, team_preference: { ...teamPreference } });
    ElMessage.success('个人画像已保存');
  } finally {
    loading.value = false;
  }
}

async function submitCertification() {
  if (!certForm.description) {
    ElMessage.warning('请填写认证说明');
    return;
  }
  certLoading.value = true;
  try {
    const record = await createCertification({ ...certForm });
    certifications.value = [record, ...certifications.value];
    Object.assign(certForm, { certification_type: 'premium', description: '', evidence_url: '' });
    ElMessage.success('认证申请已提交，等待管理员审核');
  } finally {
    certLoading.value = false;
  }
}

function statusLabel(status: string) {
  return { approved: '已通过', rejected: '已驳回', pending: '待审核' }[status] || status;
}

onMounted(load);
</script>

<style scoped>
.wide,
.full {
  width: 100%;
}

.section-gap {
  margin-top: 16px;
}

.award-form {
  display: grid;
  grid-template-columns: 1.2fr 130px 120px 100px auto;
  gap: 10px;
}

.award-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.award-tag {
  height: 30px;
  border-radius: 6px;
}

.cert-list {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.cert-item {
  padding: 12px 0;
  border-top: 1px solid #edf2f7;
}

.cert-item strong {
  margin-left: 8px;
}

.cert-item p {
  margin: 8px 0 0;
  color: #475569;
  line-height: 1.6;
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

@media (max-width: 960px) {
  .award-form {
    grid-template-columns: 1fr;
  }
}
</style>
