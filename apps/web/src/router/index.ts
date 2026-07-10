import { createRouter, createWebHistory } from 'vue-router'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/pages/HomePage.vue') },
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
      component: () => import('@/pages/RecommendationPage.vue'),
    },
    {
      path: '/me/calendar',
      name: 'calendar',
      component: () => import('@/pages/CalendarPage.vue'),
    },
    {
      path: '/admin',
      name: 'admin-home',
      component: () => import('@/pages/AdminHomePage.vue'),
    },
  ],
})
