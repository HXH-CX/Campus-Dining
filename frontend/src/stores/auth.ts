import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { apiLogin, apiLogout, apiRegister } from '@/api/auth'
import { fetchMe } from '@/api/user'
import { clearToken, getToken, setToken } from '@/api/request'
import type { User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(getToken())
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => Boolean(token.value))
  const isAdmin = computed(() => user.value?.is_admin === true)
  const displayName = computed(() => user.value?.nickname || '未登录')

  function applyToken(newToken: string): void {
    token.value = newToken
    setToken(newToken)
  }

  function clear(): void {
    token.value = ''
    user.value = null
    clearToken()
  }

  async function login(username: string, password: string): Promise<void> {
    const data = await apiLogin(username, password)
    applyToken(data.access_token)
    user.value = data.user
  }

  async function register(username: string, nickname: string, password: string): Promise<void> {
    const data = await apiRegister(username, nickname, password)
    applyToken(data.access_token)
    user.value = data.user
  }

  /** 刷新用户信息（同时会触发后端称号的懒更新） */
  async function refreshMe(): Promise<void> {
    if (!token.value) return
    loading.value = true
    try {
      user.value = await fetchMe()
    } catch {
      // token 失效的情况由 request 拦截器统一处理，这里静默即可
    } finally {
      loading.value = false
    }
  }

  async function logout(): Promise<void> {
    // 先通知后端把令牌版本 +1，让这枚 token 在别处也立刻失效；
    // 拿不到后端（断网 / token 已过期）也必须把本地清干净，所以失败不阻断
    try {
      await apiLogout()
    } catch {
      // 静默：本地登出是用户意图，不能因为一次请求失败就把人卡在登录态
    } finally {
      clear()
    }
  }

  return {
    token,
    user,
    loading,
    isLoggedIn,
    isAdmin,
    displayName,
    login,
    register,
    refreshMe,
    logout,
    clear,
  }
})
