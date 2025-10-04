import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, LoginCredentials, RegisterData, AuthResponse } from '@/types/auth'
import { authApi } from '@/api/auth'

const STORAGE_KEY = 'access_token'

const persistToken = (value: string | null) => {
  if (value) {
    localStorage.setItem(STORAGE_KEY, value)
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
}

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem(STORAGE_KEY))
  const isLoading = ref(false)

  // Getters
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  const applyAuthResponse = (response: AuthResponse) => {
    token.value = response.accessToken
    user.value = response.user
    persistToken(response.accessToken)
    return response
  }

  // Actions
  async function login(credentials: LoginCredentials) {
    isLoading.value = true
    try {
      const response = await authApi.login(credentials)
      return applyAuthResponse(response)
    } catch (error) {
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function register(userData: RegisterData) {
    isLoading.value = true
    try {
      const response = await authApi.register(userData)
      return applyAuthResponse(response)
    } catch (error) {
      throw error
    } finally {
      isLoading.value = false
    }
  }

  function logout() {
    user.value = null
    token.value = null
    persistToken(null)
  }

  async function fetchUser() {
    if (!token.value) return

    try {
      const response = await authApi.getCurrentUser()
      applyAuthResponse(response)
      return response
    } catch (error) {
      logout()
      throw error
    }
  }

  async function initialize() {
    if (!token.value) {
      return
    }

    try {
      await fetchUser()
    } catch (error) {
      console.error('Failed to initialize auth:', error)
      logout()
    }
  }

  async function updateProfile(userData: Partial<User>) {
    if (!user.value) return

    try {
      const response = await authApi.updateProfile(userData)
      user.value = { ...user.value, ...response }
      return response
    } catch (error) {
      throw error
    }
  }

  return {
    // State
    user,
    token,
    isLoading,

    // Getters
    isAuthenticated,
    isAdmin,

    // Actions
    login,
    register,
    logout,
    fetchUser,
    initialize,
    updateProfile
  }
})
