import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
      },
      {
        path: 'profile',
        name: 'profile',
        component: () => import('@/views/user/ProfileView.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'competitions',
        name: 'competitions',
        component: () => import('@/views/competition/CompetitionListView.vue'),
      },
      {
        path: 'competitions/:id',
        name: 'competition-detail',
        component: () => import('@/views/competition/CompetitionDetailView.vue'),
      },
      {
        path: 'recommendations',
        name: 'recommendations',
        component: () => import('@/views/recommendation/RecommendationView.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'calendar',
        name: 'calendar',
        component: () => import('@/views/reminder/ReminderCalendarView.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'forum',
        name: 'forum',
        component: () => import('@/views/forum/ForumListView.vue'),
      },
      {
        path: 'admin',
        name: 'admin',
        component: () => import('@/views/dashboard/AdminDashboardView.vue'),
        meta: { requiresAuth: true, roles: ['admin'] },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

function currentUserRole() {
  try {
    const user = JSON.parse(localStorage.getItem('current_user') || 'null') as { role?: string } | null;
    return user?.role || 'guest';
  } catch {
    localStorage.removeItem('current_user');
    return 'guest';
  }
}

router.beforeEach((to) => {
  const token = localStorage.getItem('access_token');

  if (to.meta.requiresAuth && !token) {
    return { name: 'login', query: { redirect: to.fullPath } };
  }

  const roles = to.meta.roles as string[] | undefined;
  if (roles?.length && !roles.includes(currentUserRole())) {
    return { name: 'dashboard' };
  }

  return true;
});

export default router;
