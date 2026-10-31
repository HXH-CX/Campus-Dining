import { get, post } from './request'
import type { NotificationItem, PageData } from '@/types'

/** 通知列表，unread_only 时只看未读 */
export function fetchNotifications(
  params: { page?: number; page_size?: number; unread_only?: boolean } = {},
) {
  return get<PageData<NotificationItem>>('/notifications', { ...params })
}

/** 铃铛角标用，比拉列表便宜得多 */
export function fetchUnreadCount() {
  return get<{ count: number }>('/notifications/unread-count')
}

export function markAllRead() {
  return post<{ updated: number; unread: number }>('/notifications/read')
}

export function markRead(id: number) {
  return post<{ updated: number; unread: number }>(`/notifications/${id}/read`)
}
