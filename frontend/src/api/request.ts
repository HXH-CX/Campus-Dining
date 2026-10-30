import axios, { type AxiosRequestConfig } from 'axios'
import { ElMessage } from '@/utils/feedback'
import { describeError } from '@/utils/error'

const TOKEN_KEY = 'cf_token'

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

// 40101 的统一处理由 main.ts 注册，避免这里 import router/store 造成循环依赖
let unauthorizedHandler: (() => void) | null = null
export function setUnauthorizedHandler(fn: () => void): void {
  unauthorizedHandler = fn
}

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

interface Envelope<T> {
  code: number
  message: string
  data: T
}

http.interceptors.response.use(
  (response) => {
    const body = response.data as Envelope<unknown>
    // 后端所有响应都包了一层，这里直接解包，业务代码只拿 data
    if (body && typeof body.code === 'number' && body.code !== 0) {
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message))
    }
    return body.data as never
  },
  (error) => {
    const status = error?.response?.status
    const body = error?.response?.data as Envelope<unknown> | undefined

    if (body?.code === 40101 || status === 401) {
      unauthorizedHandler?.()
      ElMessage.warning('登录已过期，请重新登录')
      return Promise.reject(error)
    }

    // 统一走错误分类，避免把 axios 的英文 "Network Error" 直接甩给用户
    ElMessage.error(describeError(error).desc)
    return Promise.reject(error)
  },
)

export function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  return http.get(url, { params }) as unknown as Promise<T>
}

export function post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return http.post(url, data, config) as unknown as Promise<T>
}

export function put<T>(url: string, data?: unknown): Promise<T> {
  return http.put(url, data) as unknown as Promise<T>
}

export function patch<T>(url: string, data?: unknown): Promise<T> {
  return http.patch(url, data) as unknown as Promise<T>
}

export function del<T>(url: string): Promise<T> {
  return http.delete(url) as unknown as Promise<T>
}

/** 供页面判断"资源不存在"，决定要不要跳 404 页 */
export function isNotFound(error: unknown): boolean {
  const status = (error as { response?: { status?: number } })?.response?.status
  return status === 404
}

export default http
