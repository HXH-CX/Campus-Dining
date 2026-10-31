import { get } from './request'
import type { Canteen, Dish, Merchant, PageData } from '@/types'

export function fetchCanteens() {
  return get<Canteen[]>('/canteens')
}

export function fetchCanteenMerchants(canteenId: number) {
  return get<Merchant[]>(`/canteens/${canteenId}/merchants`)
}

export function fetchMerchant(merchantId: number) {
  return get<Merchant>(`/merchants/${merchantId}`)
}

export function fetchMerchantDishes(merchantId: number, includeUnavailable = false) {
  return get<Dish[]>(`/merchants/${merchantId}/dishes`, { include_unavailable: includeUnavailable })
}

export function fetchDish(dishId: number) {
  return get<Dish>(`/dishes/${dishId}`)
}

/** 高分榜：够分且够人评的菜品，按均分倒序 */
export function fetchTopDishes(params: { min_rating?: number; min_count?: number; limit?: number } = {}) {
  return get<Dish[]>('/dishes/top', { ...params })
}

/** 按菜名或商家名模糊搜索；keyword 为空则返回全部上架菜品 */
export function searchDishes(keyword: string, page = 1, pageSize = 20) {
  return get<PageData<Dish>>('/dishes', { keyword, page, page_size: pageSize })
}

export function fetchDishRatings(dishId: number, page = 1, pageSize = 10) {
  return get<PageData<{ user_id: number; nickname: string; avatar_url: string | null; score: number; updated_at: string }>>(
    `/dishes/${dishId}/ratings`,
    { page, page_size: pageSize },
  )
}
