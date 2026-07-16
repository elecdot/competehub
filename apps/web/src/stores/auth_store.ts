import { defineStore } from 'pinia'
import { computed, readonly, ref } from 'vue'

import {
  fetchAuthCapabilities,
  fetchCurrentUser,
  loginCurrentUser,
  logoutCurrentUser,
} from '@/api/client'
import type {
  AuthCapabilities,
  CurrentUser,
  CurrentUserResponse,
  LoginPayload,
} from '@/types/auth'

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
  const capabilities = ref<AuthCapabilities>({
    public_email_registration_enabled: false,
  })
  const capabilitiesLoaded = ref(false)
  const initialized = ref(false)
  const loading = ref(false)
  const errorMessage = ref('')
  const isAuthenticated = computed(() => currentUser.value !== null)
  const isAdmin = computed(() => currentUser.value?.role === 'admin')
  const publicEmailRegistrationEnabled = computed(
    () => capabilities.value.public_email_registration_enabled,
  )

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

  async function loadAuthCapabilities() {
    try {
      capabilities.value = await fetchAuthCapabilities()
    } catch {
      capabilities.value = { public_email_registration_enabled: false }
    } finally {
      capabilitiesLoaded.value = true
    }
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

  async function logout() {
    sessionGeneration.value += 1
    currentUserRequest = null
    loading.value = true
    errorMessage.value = ''
    try {
      await logoutCurrentUser()
    } finally {
      currentUser.value = null
      initialized.value = true
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
    capabilities,
    capabilitiesLoaded,
    initialized,
    loading,
    errorMessage,
    isAuthenticated,
    isAdmin,
    publicEmailRegistrationEnabled,
    sessionGeneration: readonly(sessionGeneration),
    loadAuthCapabilities,
    loadCurrentUser,
    ensureCurrentUser,
    login,
    logout,
    clearCurrentUser,
  }
})
