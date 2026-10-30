/**
 * 把各种异常翻译成"用户看得懂 + 程序能判断"的结构。
 *
 * 目的：页面不再只靠 toast 报错（消息 3 秒就消失了，用户面对的是空白页），
 * 而是能把错误展示成一块可重试的区域。
 */
import axios from 'axios'

export type ErrorKind =
  | 'network'
  | 'timeout'
  | 'server'
  | 'notfound'
  | 'forbidden'
  | 'unauthorized'
  | 'unknown'

export interface ErrorInfo {
  kind: ErrorKind
  title: string
  desc: string
  /** 同样的请求重试有没有意义：404 之类重试也不会变好 */
  retryable: boolean
}

interface Envelope {
  code?: number
  message?: string
}

export function describeError(error: unknown): ErrorInfo {
  const isAxios = axios.isAxiosError(error)
  const status = isAxios ? error.response?.status : undefined
  const code = isAxios ? error.code : undefined
  const serverMsg = isAxios ? (error.response?.data as Envelope | undefined)?.message : undefined

  if (code === 'ECONNABORTED' || code === 'ETIMEDOUT') {
    return {
      kind: 'timeout',
      title: '请求超时',
      desc: '服务器响应太慢，检查一下网络再重试',
      retryable: true,
    }
  }

  // 没有 response 说明请求根本没到达后端：多半是后端没起或网络断了
  if (isAxios && !error.response) {
    return {
      kind: 'network',
      title: '连不上服务器',
      desc: '请确认后端已启动（默认 127.0.0.1:8000），或检查网络连接',
      retryable: true,
    }
  }

  if (status && status >= 500) {
    return {
      kind: 'server',
      title: '服务器开小差了',
      desc: serverMsg || '接口执行出错，稍后再试一次',
      retryable: true,
    }
  }

  if (status === 404) {
    return { kind: 'notfound', title: '内容不存在', desc: serverMsg || '它可能已经被删除了', retryable: false }
  }

  if (status === 403) {
    return { kind: 'forbidden', title: '没有权限', desc: serverMsg || '当前账号无权访问这里', retryable: false }
  }

  if (status === 401) {
    return { kind: 'unauthorized', title: '需要登录', desc: '登录状态已失效，请重新登录', retryable: false }
  }

  const message = serverMsg || (error instanceof Error ? error.message : '')
  return { kind: 'unknown', title: '加载失败', desc: message || '发生了未知错误，重试一下', retryable: true }
}
