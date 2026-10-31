import { del, get, patch, post, put } from './request'
import type { AdminOverview, Canteen, Dish, Merchant, PageData, Post } from '@/types'

// ---- 概览
export function adminOverview() {
  return get<AdminOverview>('/admin/overview')
}

// ---- 食堂
export function adminCanteens(page = 1, pageSize = 20) {
  return get<PageData<Canteen>>('/admin/canteens', { page, page_size: pageSize })
}
export function adminCreateCanteen(name: string) {
  return post<Canteen>('/admin/canteens', { name })
}
export function adminUpdateCanteen(id: number, name: string) {
  return put<Canteen>(`/admin/canteens/${id}`, { name })
}
export function adminDeleteCanteen(id: number) {
  return del<null>(`/admin/canteens/${id}`)
}

// ---- 商家
export function adminMerchants(page = 1, pageSize = 20, canteenId?: number) {
  return get<PageData<Merchant>>('/admin/merchants', {
    page,
    page_size: pageSize,
    ...(canteenId ? { canteen_id: canteenId } : {}),
  })
}
export function adminCreateMerchant(name: string, canteenId: number) {
  return post<Merchant>('/admin/merchants', { name, canteen_id: canteenId })
}
export function adminUpdateMerchant(id: number, payload: { name?: string; canteen_id?: number }) {
  return put<Merchant>(`/admin/merchants/${id}`, payload)
}
export function adminDeleteMerchant(id: number) {
  return del<null>(`/admin/merchants/${id}`)
}

// ---- 菜品
export function adminDishes(page = 1, pageSize = 20, merchantId?: number) {
  return get<PageData<Dish>>('/admin/dishes', {
    page,
    page_size: pageSize,
    include_unavailable: true,
    ...(merchantId ? { merchant_id: merchantId } : {}),
  })
}
export function adminCreateDish(payload: { name: string; merchant_id: number; image_url?: string | null }) {
  return post<Dish>('/admin/dishes', payload)
}
export function adminUpdateDish(
  id: number,
  payload: { name?: string; merchant_id?: number; image_url?: string | null },
) {
  return put<Dish>(`/admin/dishes/${id}`, payload)
}
export function adminSetDishAvailability(id: number, isAvailable: boolean) {
  return patch<Dish>(`/admin/dishes/${id}/availability`, { is_available: isAvailable })
}
export function adminDeleteDish(id: number) {
  return del<null>(`/admin/dishes/${id}`)
}

// ---- 帖子（应急删除，非审核流程）
export function adminPosts(page = 1, pageSize = 20, keyword?: string) {
  return get<PageData<Post>>('/admin/posts', {
    page,
    page_size: pageSize,
    ...(keyword ? { keyword } : {}),
  })
}
export function adminDeletePost(id: number) {
  return del<null>(`/admin/posts/${id}`)
}
