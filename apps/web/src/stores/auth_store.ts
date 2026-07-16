import { defineStore } from 'pinia'
import { computed, readonly, ref } from 'vue'

import { fetchCurrentUser, loginCurrentUser } from '@/api/client'
import type { CurrentUser, CurrentUserResponse, LoginPayload } from '@/types/auth'

function mapCurrentUser(user: CurrentUserResponse): CurrentUser {
  return {
    id: user.id,
    displayName: user.display_name,
    role: user.role,
    capabilities: user.role === 'student' ? [] : user.capabilities,
  }
}

export const useAuthStore = defineStore('auth', () => {
  const currentUser = ref<CurrentUser | null>(null)
  const initialized = ref(false)
  const loading = ref(false)
  const errorMessage = ref('')
  const isAuthenticated = computed(() => currentUser.value !== null)
  const isAdmin = computed(() => currentUser.value?.role === 'admin')

  let currentUserRequest: Promise<CurrentUserResponse> | null = null
  const sessionGeneration = ref(0)

  function fetchCurrentUserOnce() {
    currentUserRequest ??= fetchCurrentUser()
    return currentUserRequest
  }

  function sessionIdentity(user: CurrentUser | null) {
    return user === null ? '' : `${user.id}:${user.role}`
  }

  function acceptProbedCurrentUser(user: CurrentUser | null) {
    if (sessionIdentity(currentUser.value) !== sessionIdentity(user)) {
      sessionGeneration.value += 1
    }
    currentUser.value = user
    return sessionGeneration.value
  }

  async function loadCurrentUser() {
    let generation = sessionGeneration.value
    const request = fetchCurrentUserOnce()
    loading.value = true
    errorMessage.value = ''
    try {
      const user = mapCurrentUser(await request)
      if (generation === sessionGeneration.value) {
        generation = acceptProbedCurrentUser(user)
      }
    } catch {
      if (generation === sessionGeneration.value) {
        generation = acceptProbedCurrentUser(null)
        errorMessage.value = 'unauthorized'
      }
    } finally {
      if (currentUserRequest === request) currentUserRequest = null
      if (generation === sessionGeneration.value) {
        initialized.value = true
        loading.value = false
      }
    }
  }

  async function ensureCurrentUser() {
    if (!initialized.value) await loadCurrentUser()
  }

  async function revalidateCurrentUser() {
    const requestWasInFlight = currentUserRequest !== null
    await loadCurrentUser()
    if (requestWasInFlight) {
      // The shared request may have started before another tab replaced the
      // browser session. A security boundary needs one probe started after
      // revalidation began, even when ordinary callers can share requests.
      await loadCurrentUser()
    }
  }

  async function login(payload: LoginPayload) {
    sessionGeneration.value += 1
    currentUserRequest = null
    loading.value = true
    errorMessage.value = ''
    try {
      currentUser.value = mapCurrentUser(await loginCurrentUser(payload))
      initialized.value = true
    } catch {
      currentUser.value = null
      errorMessage.value = 'unauthorized'
      throw new Error('login_failed')
    } finally {
      loading.value = false
    }
  }

  function clearCurrentUser() {
    sessionGeneration.value += 1
    currentUserRequest = null
    currentUser.value = null
    initialized.value = true
    loading.value = false
    errorMessage.value = ''
  }

  return {
    currentUser,
    initialized,
    loading,
    errorMessage,
    isAuthenticated,
    isAdmin,
    sessionGeneration: readonly(sessionGeneration),
    loadCurrentUser,
    ensureCurrentUser,
    revalidateCurrentUser,
    login,
    clearCurrentUser,
  }
})
