/**
 * 未读通知数（铃铛角标）。
 *
 * 单独放一个 store 而不是塞进 auth：角标刷新频率和用户信息不一样，
 * 而且发帖、点赞这些操作不该顺手把用户对象一起拉一遍。
 *
 * 轮询间隔 60s，标签页不可见时跳过——食堂门口掏手机看一眼就够了，
 * 做成 WebSocket 对这个体量的项目不划算。
 */
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { fetchUnreadCount } from '@/api/notification'

const POLL_MS = 60 * 1000

export const useNotifyStore = defineStore('notify', () => {
  const unread = ref(0)
  let timer: number | undefined

  async function refresh(): Promise<void> {
    try {
      unread.value = (await fetchUnreadCount()).count
    } catch {
      // 角标失败不该弹提示：后端短暂不可用不代表用户要处理什么
    }
  }

  function start(): void {
    if (timer !== undefined) return
    void refresh()
    timer = window.setInterval(() => {
      if (!document.hidden) void refresh()
    }, POLL_MS)
  }

  function stop(): void {
    if (timer !== undefined) {
      window.clearInterval(timer)
      timer = undefined
    }
    unread.value = 0
  }

  /** 本地先减，避免"已读点完角标还挂着"的滞后感；下一次轮询会校准 */
  function decrease(by = 1): void {
    unread.value = Math.max(0, unread.value - by)
  }

  function reset(): void {
    unread.value = 0
  }

  return { unread, refresh, start, stop, decrease, reset }
})
