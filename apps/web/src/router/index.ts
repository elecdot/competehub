import { createRouter, createWebHistory } from 'vue-router'

import AdminHomePage from '@/pages/AdminHomePage.vue'
import HomePage from '@/pages/HomePage.vue'
import RecommendationPage from '@/pages/RecommendationPage.vue'
import AccountStatusPage from '@/pages/AccountStatusPage.vue'
import { useAuthStore } from '@/stores/auth_store'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    {
      path: '/competitions',
      name: 'competitions',
      component: () => import('@/pages/CompetitionListPage.vue'),
    },
    {
      path: '/competitions/:id',
      name: 'competition-detail',
      component: () => import('@/pages/CompetitionDetailPage.vue'),
    },
    {
      path: '/recommendations',
      name: 'recommendations',
      component: RecommendationPage,
    },
    {
      path: '/me',
      name: 'account-status',
      component: AccountStatusPage,
    },
    {
      path: '/me/calendar',
      name: 'calendar',
      component: () => import('@/pages/CalendarPage.vue'),
    },
    {
      path: '/me/messages',
      name: 'messages',
      component: () => import('@/pages/MessageCenterPage.vue'),
    },
    {
      path: '/admin',
      name: 'admin-home',
      component: AdminHomePage,
      meta: { requiresAdmin: true },
    },
    {
      path: '/admin/recommendation-rule-sets',
      name: 'admin-recommendation-rule-sets',
      component: () => import('@/pages/AdminRecommendationRuleSetsPage.vue'),
      meta: { requiresAdmin: true },
    },
  ],
})

router.beforeEach(async (to) => {
  if (!to.meta.requiresAdmin) {
    return true
  }

  const auth = useAuthStore()
  // A browser cookie can be replaced by another tab after the application
  // initialized. Revalidate before every protected navigation so a stale
  // administrator snapshot cannot mount an administrator route.
  await auth.revalidateCurrentUser()
  if (!auth.isAdmin) {
    return { name: 'competitions' }
  }
  return true
})
