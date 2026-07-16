import { createRouter, createWebHistory } from 'vue-router'

import AdminHomePage from '@/pages/AdminHomePage.vue'
import CalendarPage from '@/pages/CalendarPage.vue'
import HomePage from '@/pages/HomePage.vue'
import RecommendationPage from '@/pages/RecommendationPage.vue'
import AccountStatusPage from '@/pages/AccountStatusPage.vue'

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
      name: 'personal-info',
      component: AccountStatusPage,
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/pages/LoginPage.vue'),
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/pages/RegisterPage.vue'),
    },
    {
      path: '/me/calendar',
      name: 'calendar',
      component: CalendarPage,
    },
    {
      path: '/admin',
      name: 'admin-home',
      component: AdminHomePage,
    },
    {
      path: '/admin/recommendation-rule-sets',
      name: 'admin-recommendation-rule-sets',
      component: () => import('@/pages/AdminRecommendationRuleSetsPage.vue'),
    },
  ],
})
