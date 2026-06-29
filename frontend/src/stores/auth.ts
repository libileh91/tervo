/**
 * ResQ — Auth store (Pinia).
 *
 * Manages authentication state: token, user, login/logout.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi, type UserResponse } from '@/api/client'

const TOKEN_KEY = 'resq_access_token'
const REFRESH_KEY = 'resq_refresh_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const refreshToken = ref<string | null>(localStorage.getItem(REFRESH_KEY))
  const user = ref<UserResponse | null>(null)
  const loading = ref(false)

  async function login(username: string, password: string) {
    loading.value = true
    try {
      const res = await authApi.login({ username, password })
      token.value = res.access_token
      refreshToken.value = res.refresh_token
      localStorage.setItem(TOKEN_KEY, res.access_token)
      localStorage.setItem(REFRESH_KEY, res.refresh_token)

      // Fetch user profile
      await fetchUser()
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    if (!token.value) return
    user.value = await authApi.me(token.value)
  }

  function logout() {
    token.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
  }

  function isAuthenticated(): boolean {
    return token.value !== null
  }

  // Try to fetch user on init if token exists
  if (token.value) {
    fetchUser()
  }

  return {
    token,
    refreshToken,
    user,
    loading,
    login,
    logout,
    fetchUser,
    isAuthenticated,
  }
})
