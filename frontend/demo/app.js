const API_BASE = '/api/v1';

const state = {
  token: localStorage.getItem('demo_token') || '',
  user: JSON.parse(localStorage.getItem('demo_user') || 'null'),
};

const titles = {
  overview: ['工作台', '查看接口状态、赛事数据和推荐结果。'],
  competitions: ['赛事查询', '检索、排序并订阅可参与的竞赛。'],
  recommendations: ['个性推荐', '基于用户画像、关注行为和赛事信息生成推荐。'],
  account: ['账号登录', '登录后可以加载个性化推荐。'],
};

function $(id) {
  return document.getElementById(id);
}

async function request(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
  const payload = await response.json();
  if (!response.ok || payload.code !== 0) {
    throw new Error(payload.message || '请求失败');
  }
  return payload.data;
}

function setView(view) {
  for (const name of Object.keys(titles)) {
    $(`${name}View`).classList.toggle('hidden', name !== view);
  }
  document.querySelectorAll('.nav button').forEach((button) => {
    button.classList.toggle('active', button.dataset.view === view);
  });
  $('viewTitle').textContent = titles[view][0];
  $('viewSubtitle').textContent = titles[view][1];
}

function updateUserMetric() {
  $('userMetric').textContent = state.user ? state.user.username : '未登录';
}

async function loadOverview() {
  try {
    const health = await request('/health');
    $('apiStatus').textContent = `API ${health.status}`;
    $('healthMetric').textContent = health.status;
    const competitions = await request('/competitions?page=1&page_size=10');
    $('competitionMetric').textContent = competitions.total;
    $('overviewMessage').textContent = '接口连接正常。';
    updateUserMetric();
  } catch (error) {
    $('apiStatus').textContent = 'API 未连接';
    $('overviewMessage').textContent = error.message;
  }
}

async function loadCompetitions() {
  const keyword = encodeURIComponent($('keywordInput').value.trim());
  const sort = encodeURIComponent($('sortSelect').value);
  const data = await request(`/competitions?page=1&page_size=20&keyword=${keyword}&sort=${sort}`);
  $('competitionRows').innerHTML = data.items
    .map(
      (item) => `
        <tr>
          <td><strong>${item.title}</strong><br /><span>${item.summary || ''}</span></td>
          <td>${item.category}</td>
          <td>${item.level}</td>
          <td>${item.organizer || '-'}</td>
          <td>${item.score}</td>
          <td><button class="secondary" data-subscribe="${item.id}">订阅</button></td>
        </tr>
      `,
    )
    .join('');
}

async function login(account = $('accountInput').value, password = $('passwordInput').value) {
  const data = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ account, password }),
  });
  state.token = data.access_token;
  state.user = data.user;
  localStorage.setItem('demo_token', state.token);
  localStorage.setItem('demo_user', JSON.stringify(state.user));
  $('accountMessage').textContent = `已登录：${state.user.username}`;
  updateUserMetric();
}

async function loadRecommendations() {
  if (!state.token) {
    $('recommendationRows').innerHTML = '<tr><td colspan="3">请先登录。</td></tr>';
    return;
  }
  const items = await request('/recommendations?limit=20');
  $('recommendationRows').innerHTML = items
    .map(
      (item) => `
        <tr>
          <td><strong>${item.title}</strong><br /><span>${item.category} / ${item.level}</span></td>
          <td>${item.recommend_score || 0}</td>
          <td>${(item.recommend_reasons || []).map((reason) => `<span class="tag">${reason}</span>`).join('')}</td>
        </tr>
      `,
    )
    .join('');
}

document.querySelectorAll('.nav button').forEach((button) => {
  button.addEventListener('click', () => setView(button.dataset.view));
});

$('refreshOverview').addEventListener('click', loadOverview);
$('quickLogin').addEventListener('click', async () => {
  await login('student', 'student123');
  await loadOverview();
});
$('searchCompetitions').addEventListener('click', loadCompetitions);
$('loginButton').addEventListener('click', () => login());
$('logoutButton').addEventListener('click', () => {
  state.token = '';
  state.user = null;
  localStorage.removeItem('demo_token');
  localStorage.removeItem('demo_user');
  $('accountMessage').textContent = '已退出。';
  updateUserMetric();
});
$('loadRecommendations').addEventListener('click', loadRecommendations);
$('competitionRows').addEventListener('click', async (event) => {
  const button = event.target.closest('[data-subscribe]');
  if (!button) return;
  if (!state.token) {
    alert('请先登录。');
    return;
  }
  await request(`/competitions/${button.dataset.subscribe}/subscribe`, {
    method: 'POST',
    body: JSON.stringify({ remind_days_before: 3 }),
  });
  button.textContent = '已订阅';
});

loadOverview();
loadCompetitions();
updateUserMetric();
