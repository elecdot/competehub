<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">个人中心</h1>
        <p class="page-subtitle">维护专业画像、获奖经历、认证材料和标准化组队意向。</p>
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
              <el-select v-model="profile.interests" multiple filterable class="wide" placeholder="选择统一技能标签">
                <el-option v-for="skill in options.skills" :key="skill" :label="skill" :value="skill" />
              </el-select>
            </el-form-item>
          </el-form>
        </div>

        <div class="panel panel-body section-gap">
          <h2 class="section-title">获奖经历标签</h2>
          <div class="award-form">
            <el-select v-model="awardForm.competition" filterable placeholder="官方赛事名称">
              <el-option v-for="item in options.competitions" :key="item.id" :label="item.title" :value="item.title" />
            </el-select>
            <el-select v-model="awardForm.category" placeholder="方向">
              <el-option v-for="item in awardCategories" :key="item" :label="item" :value="item" />
            </el-select>
            <el-select v-model="awardForm.level" placeholder="级别">
              <el-option label="国一" value="国一" />
              <el-option label="国二" value="国二" />
              <el-option label="国三" value="国三" />
              <el-option label="省一" value="省一" />
              <el-option label="省二" value="省二" />
              <el-option label="省三" value="省三" />
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
              <el-select v-model="teamPreference.target_competitions" multiple filterable class="wide" placeholder="选择官方规范赛事名称">
                <el-option v-for="item in options.competitions" :key="item.id" :label="item.title" :value="item.title" />
              </el-select>
            </el-form-item>
            <el-form-item label="需要技能">
              <el-select v-model="teamPreference.required_skills" multiple filterable class="wide" placeholder="选择技能模块">
                <el-option v-for="skill in options.skills" :key="skill" :label="skill" :value="skill" />
              </el-select>
            </el-form-item>
            <el-form-item label="期望奖项经历">
              <el-select v-model="teamPreference.required_awards" multiple class="wide" placeholder="选择奖项等级要求">
                <el-option label="国家级奖项" value="国家级奖项" />
                <el-option label="省部级奖项" value="省部级奖项" />
                <el-option label="校级奖项" value="校级奖项" />
                <el-option label="相关参赛经历" value="相关参赛经历" />
              </el-select>
            </el-form-item>
            <el-form-item label="联系方式说明">
              <el-input v-model="teamPreference.contact_preference" placeholder="例如：先站内联系，通过后交换微信" />
            </el-form-item>
          </el-form>
        </div>
      </el-col>

      <el-col :xs="24" :lg="9">
        <div class="panel panel-body">
          <h2 class="section-title">获奖认证申请</h2>
          <el-alert
            title="提交国家级奖项认证后，审核通过会自动获得 premium 指导人身份。"
            type="info"
            :closable="false"
            class="cert-alert"
          />
          <el-form label-position="top">
            <el-form-item label="认证赛事">
              <el-select v-model="certForm.competition" filterable class="full" placeholder="选择官方赛事名称">
                <el-option v-for="item in options.competitions" :key="item.id" :label="item.title" :value="item.title" />
              </el-select>
            </el-form-item>
            <el-form-item label="获奖等级">
              <el-select v-model="certForm.level" class="full">
                <el-option label="国一" value="国一" />
                <el-option label="国二" value="国二" />
                <el-option label="国三" value="国三" />
                <el-option label="省一" value="省一" />
                <el-option label="省二" value="省二" />
                <el-option label="省三" value="省三" />
                <el-option label="校级" value="校级" />
              </el-select>
            </el-form-item>
            <el-form-item label="证明材料链接">
              <el-input v-model="certForm.evidence_url" placeholder="填写证书图片、网盘或可访问材料链接" />
            </el-form-item>
            <el-form-item label="补充说明">
              <el-input v-model="certForm.note" type="textarea" :rows="3" placeholder="填写年份、赛道、可指导方向" />
            </el-form-item>
            <el-button type="primary" class="full" :loading="certLoading" @click="submitCertification">提交获奖认证</el-button>
          </el-form>

          <div class="cert-list">
            <div v-for="item in certifications" :key="item.id" class="cert-item">
              <el-tag :type="item.status === 'approved' ? 'success' : item.status === 'rejected' ? 'danger' : 'warning'">
                {{ statusLabel(item.status) }}
              </el-tag>
              <strong>{{ item.certification_type === 'premium' ? 'premium 指导人' : '获奖经历' }}</strong>
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
            <strong>{{ approvedCertifications.length ? '已有认证通过' : '暂无已通过认证' }}</strong>
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
import { getCompetitionOptions } from '@/api/competition';
import { createCertification, getMe, updateProfile } from '@/api/user';
import type { AwardExperience, CertificationRequest, CompetitionOptions, TeamPreference, UserProfile } from '@/api/types';

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
const awardForm = reactive<AwardExperience>({ competition: '', category: '', level: '', year: '' });
const certForm = reactive({ competition: '', level: '省一', evidence_url: '', note: '' });
const options = reactive<CompetitionOptions>({ competitions: [], categories: [], levels: [], tags: [], skills: [], forum_tags: [] });

const awardCategories = ['数学建模', '程序设计', '计算机设计', '电子信息', '创新创业', '城市建设', '机械制造', '人文设计'];
const abilityOptions = [
  { label: '新手', value: 'beginner' },
  { label: '进阶', value: 'intermediate' },
  { label: '冲刺', value: 'advanced' },
];
const approvedCertifications = computed(() => certifications.value.filter((item) => item.status === 'approved'));

function awardStyle(award: AwardExperience) {
  const categoryColors: Record<string, string> = {
    数学建模: '30, 100, 210',
    程序设计: '22, 130, 90',
    计算机设计: '126, 58, 242',
    电子信息: '220, 88, 42',
    创新创业: '190, 120, 25',
    城市建设: '14, 116, 144',
    机械制造: '101, 85, 143',
    人文设计: '190, 70, 120',
  };
  const alphaMap: Record<string, number> = { 国一: 0.95, 国二: 0.78, 国三: 0.68, 省一: 0.56, 省二: 0.44, 省三: 0.34, 校级: 0.24 };
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
  Object.assign(options, await getCompetitionOptions());
  const data = (await getMe()) as {
    profile?: UserProfile;
    team_preference?: TeamPreference;
    certifications?: CertificationRequest[];
  };
  Object.assign(profile, data.profile || {});
  Object.assign(teamPreference, data.team_preference || {});
  profile.interests ||= [];
  profile.competition_experiences ||= [];
  teamPreference.target_competitions ||= [];
  teamPreference.required_skills ||= [];
  teamPreference.required_awards ||= [];
  certifications.value = data.certifications || [];
}

async function save() {
  loading.value = true;
  try {
    await updateProfile({ ...profile, team_preference: { ...teamPreference } });
    ElMessage.success('个人画像已保存');
  } finally {
    loading.value = false;
  }
}

async function submitCertification() {
  if (!certForm.competition || !certForm.level) {
    ElMessage.warning('请选择认证赛事和获奖等级');
    return;
  }
  certLoading.value = true;
  try {
    const isNational = certForm.level.startsWith('国');
    const description = `${certForm.competition} ${certForm.level}。${certForm.note || ''}`.trim();
    const record = await createCertification({
      certification_type: isNational ? 'premium' : 'award',
      description,
      evidence_url: certForm.evidence_url,
    });
    certifications.value = [record, ...certifications.value];
    Object.assign(certForm, { competition: '', level: '省一', evidence_url: '', note: '' });
    ElMessage.success(isNational ? '国家级获奖认证已提交，通过后自动获得 premium 身份' : '获奖认证已提交');
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
  grid-template-columns: 1.4fr 130px 110px 90px auto;
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

.cert-alert {
  margin-bottom: 14px;
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
