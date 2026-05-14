import { createRouter, createWebHistory } from 'vue-router'

import AdminHomePage from '@/pages/AdminHomePage.vue'
import CalendarPage from '@/pages/CalendarPage.vue'
import CompetitionDetailPage from '@/pages/CompetitionDetailPage.vue'
import CompetitionListPage from '@/pages/CompetitionListPage.vue'
import HomePage from '@/pages/HomePage.vue'
import RecommendationPage from '@/pages/RecommendationPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    { path: '/competitions', name: 'competitions', component: CompetitionListPage },
    { path: '/competitions/:id', name: 'competition-detail', component: CompetitionDetailPage },
    { path: '/recommendations', name: 'recommendations', component: RecommendationPage },
    { path: '/me/calendar', name: 'calendar', component: CalendarPage },
    { path: '/admin', name: 'admin-home', component: AdminHomePage },
  ],
})
