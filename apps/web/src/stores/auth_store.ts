import { defineStore } from 'pinia'

import { fetchCurrentUser, loginCurrentUser, logoutCurrentUser } from '@/api/client'
import type { CurrentUser, CurrentUserResponse, LoginPayload } from '@/types/auth'

function mapCurrentUser(user: CurrentUserResponse): CurrentUser {
  return {
    id: user.id,
    displayName: user.display_name,
    role: user.role,
    capabilities: user.role === 'student' ? [] : user.capabilities,
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    currentUser: null as CurrentUser | null,
    loading: false,
    errorMessage: '',
  }),
  getters: {
    isAuthenticated: (state) => state.currentUser !== null,
    isAdmin: (state) => state.currentUser?.role === 'admin',
  },
  actions: {
    async loadCurrentUser() {
      this.loading = true
      this.errorMessage = ''
      try {
        this.currentUser = mapCurrentUser(await fetchCurrentUser())
      } catch {
        this.currentUser = null
        this.errorMessage = 'unauthorized'
      } finally {
        this.loading = false
      }
    },
    async login(payload: LoginPayload) {
      this.loading = true
      this.errorMessage = ''
      try {
        this.currentUser = mapCurrentUser(await loginCurrentUser(payload))
      } catch {
        this.currentUser = null
        this.errorMessage = 'unauthorized'
        throw new Error('login_failed')
      } finally {
        this.loading = false
      }
    },
    async logout() {
      this.loading = true
      this.errorMessage = ''
      try {
        await logoutCurrentUser()
      } finally {
        this.currentUser = null
        this.loading = false
      }
    },
    clearCurrentUser() {
      this.currentUser = null
      this.errorMessage = ''
    },
  },
})
