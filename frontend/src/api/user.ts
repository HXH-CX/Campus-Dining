import { get, post, put } from './request'
import type { PageData, Post, RatingItem, User, UserCard } from '@/types'

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

export function fetchFollowers(userId: number, page = 1, pageSize = 12) {
  return get<PageData<UserCard>>(`/users/${userId}/followers`, { page, page_size: pageSize })
}

export function fetchFollowing(userId: number, page = 1, pageSize = 12) {
  return get<PageData<UserCard>>(`/users/${userId}/following`, { page, page_size: pageSize })
}

export function toggleFollow(userId: number) {
  return post<{ following: boolean }>(`/users/${userId}/follow`)
}
