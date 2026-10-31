import { del, get, post, put } from './request'
import type { Comment, LikeResult, PageData, Post } from '@/types'

export interface FeedQuery {
  sort?: 'latest' | 'hot'
  page?: number
  page_size?: number
  keyword?: string
}

export function fetchFeed(query: FeedQuery = {}) {
  return get<PageData<Post>>('/posts/feed', { ...query })
}

export function fetchHot() {
  return get<Post[]>('/posts/hot')
}

export function fetchPost(postId: number) {
  return get<Post>(`/posts/${postId}`)
}

export function createPost(payload: {
  dish_id: number
  score: number
  content?: string
  images?: string[]
}) {
  return post<Post>('/posts', payload)
}

export function updatePost(postId: number, payload: { content?: string | null; images?: string[] }) {
  return put<Post>(`/posts/${postId}`, payload)
}

export function deletePost(postId: number) {
  return del<null>(`/posts/${postId}`)
}

export function toggleLike(postId: number) {
  return post<LikeResult>(`/posts/${postId}/like`)
}

export function fetchComments(postId: number, page = 1, pageSize = 20) {
  return get<PageData<Comment>>(`/posts/${postId}/comments`, { page, page_size: pageSize })
}

export function addComment(postId: number, content: string) {
  return post<Comment>(`/posts/${postId}/comments`, { content })
}

export function deleteComment(postId: number, commentId: number) {
  return del<{ comment_count: number }>(`/posts/${postId}/comments/${commentId}`)
}

export function fetchMerchantPosts(merchantId: number, page = 1, pageSize = 10) {
  return get<PageData<Post>>(`/merchants/${merchantId}/posts`, { page, page_size: pageSize })
}

export function fetchDishPosts(dishId: number, page = 1, pageSize = 10) {
  return get<PageData<Post>>(`/dishes/${dishId}/posts`, { page, page_size: pageSize })
}
