import { get, post, put } from './request'
import type { Dish, PageData, Post, RatingItem, User, UserCard, UserCommentItem } from '@/types'

export function fetchMe() {
  return get<User>('/users/me')
}

/** 只允许改昵称和头像 */
export function updateMe(payload: { nickname?: string; avatar_url?: string | null }) {
  return put<User>('/users/me', payload)
}

export function fetchUser(userId: number) {
  return get<User>(`/users/${userId}`)
}

export function fetchUserPosts(userId: number, page = 1, pageSize = 10) {
  return get<PageData<Post>>(`/users/${userId}/posts`, { page, page_size: pageSize })
}

export function fetchUserRatings(userId: number, page = 1, pageSize = 10) {
  return get<PageData<RatingItem>>(`/users/${userId}/ratings`, { page, page_size: pageSize })
}

export function fetchUserComments(userId: number, page = 1, pageSize = 20) {
  return get<PageData<UserCommentItem>>(`/users/${userId}/comments`, { page, page_size: pageSize })
}

export function fetchFollowers(userId: number, page = 1, pageSize = 12) {
  return get<PageData<UserCard>>(`/users/${userId}/followers`, { page, page_size: pageSize })
}

export function fetchFollowing(userId: number, page = 1, pageSize = 12) {
  return get<PageData<UserCard>>(`/users/${userId}/following`, { page, page_size: pageSize })
}

/** 按昵称搜人。登录后返回的 followed_by_me / is_mutual 都相对当前用户 */
export function searchUsers(keyword: string, page = 1, pageSize = 12) {
  return get<PageData<UserCard>>('/users', { keyword, page, page_size: pageSize })
}

/** 我赞过的帖子（仅本人可看），按点赞时间倒序 */
export function fetchLikedPosts(userId: number, page = 1, pageSize = 10) {
  return get<PageData<Post>>(`/users/${userId}/liked-posts`, { page, page_size: pageSize })
}

/** 想吃清单：最近加的在前，已下架的菜也会返回（前端标灰） */
export function fetchUserWants(userId: number, page = 1, pageSize = 20) {
  return get<PageData<Dish>>(`/users/${userId}/wants`, { page, page_size: pageSize })
}

export function toggleFollow(userId: number) {
  return post<{ following: boolean }>(`/users/${userId}/follow`)
}
