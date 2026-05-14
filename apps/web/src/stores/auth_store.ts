import { defineStore } from 'pinia'

type Role = 'student' | 'admin' | 'teacher' | 'organizer'

interface CurrentUser {
  id: number
  displayName: string
  role: Role
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    currentUser: null as CurrentUser | null,
  }),
  getters: {
    isAuthenticated: (state) => state.currentUser !== null,
    isAdmin: (state) => state.currentUser?.role === 'admin',
  },
})
