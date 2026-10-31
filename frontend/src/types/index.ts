// 与后端 Pydantic Schema 一一对应，改接口时两端一起改

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface PageData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Achievement {
  code: string
  name: string
  emoji: string
  description: string
  unlocked_at: string
}

export interface User {
  id: number
  username: string
  nickname: string
  avatar_url: string | null
  is_admin: boolean
  title_level: number
  title_name: string
  title_emoji: string
  follower_count: number
  following_count: number
  achievements: Achievement[]
  created_at: string
}

export interface UserCard {
  id: number
  nickname: string
  avatar_url: string | null
  title_level: number
  title_name: string
  title_emoji: string
  is_mutual: boolean
  followed_by_me: boolean
}

export interface Canteen {
  id: number
  name: string
  merchant_count: number
}

export interface Merchant {
  id: number
  name: string
  canteen_id: number
  canteen_name: string
  overall_rating: number
  dish_count: number
}

export interface Dish {
  id: number
  name: string
  image_url: string | null
  merchant_id: number
  merchant_name: string
  canteen_name: string
  avg_rating: number
  rating_count: number
  is_available: boolean
  /** 只有菜品详情接口会填真值，列表接口为 0 */
  want_count?: number
  is_wanted?: boolean
}

export interface DishBrief {
  id: number
  name: string
  image_url: string | null
  avg_rating: number
  rating_count: number
}

/** 「今天吃什么」的抽取结果 */
export interface RandomDishResult {
  dish: Dish
  /** 本次候选池大小，1 表示没得换 */
  pool_size: number
  /** top 高分池 / all 全部在售 / wants 我的想吃清单 */
  source: 'top' | 'all' | 'wants'
}

/** 想吃清单的操作结果 */
export interface WantResult {
  wanted: boolean
  want_count: number
}

export interface AuthorBrief {
  id: number
  nickname: string
  avatar_url: string | null
  title_level: number
  title_name: string
  title_emoji: string
}

export interface Post {
  id: number
  content: string | null
  images: string[]
  like_count: number
  comment_count: number
  created_at: string
  author: AuthorBrief
  dish: DishBrief & { is_available?: boolean }
  merchant: { id: number; name: string; canteen_name: string }
  author_score: number | null
  is_liked: boolean
}

export interface Comment {
  id: number
  content: string
  created_at: string
  author: AuthorBrief
}

export interface LikeResult {
  liked: boolean
  like_count: number
}

export interface RatingItem {
  dish: DishBrief
  score: number
  updated_at: string
}

/** 评论所属帖子（个人中心「我的评论」用） */
export interface CommentedPost {
  id: number
  dish_name: string
  excerpt: string | null
  image_url: string | null
}

export interface UserCommentItem {
  id: number
  content: string
  created_at: string
  post: CommentedPost
}

/** 管理后台概览（GET /admin/overview） */
export interface AdminOverview {
  users: number
  posts: number
  comments: number
  ratings: number
  dishes: number
  merchants: number
  canteens: number
  wants: number
  today_users: number
  today_posts: number
  today_comments: number
  posts_by_day: { date: string; count: number }[]
  untasted_total: number
  untasted_dishes: { id: number; name: string; merchant_name: string }[]
  empty_merchant_total: number
  empty_merchants: { id: number; name: string; canteen_name: string }[]
  unavailable_dishes: number
}

export interface LoginResult {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface UploadResult {
  url: string
  size: number
}
