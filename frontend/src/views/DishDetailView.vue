<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchDish, fetchDishRatings } from '@/api/catalog'
import { fetchDishPosts } from '@/api/post'
import { isNotFound } from '@/api/request'
import PostCard from '@/components/PostCard.vue'
import RatingStars from '@/components/RatingStars.vue'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import { timeAgo } from '@/utils/format'
import type { Dish, Post } from '@/types'

const props = defineProps<{ id: string }>()
const router = useRouter()

const dish = ref<Dish | null>(null)
const posts = ref<Post[]>([])
const postTotal = ref(0)
const postPage = ref(1)
const ratings = ref<{ user_id: number; nickname: string; score: number; updated_at: string }[]>([])
const ratingTotal = ref(0)
const tab = ref<'posts' | 'ratings'>('posts')
const loading = ref(true)
const postLoading = ref(false)
const error = ref<unknown>(null)

const dishId = computed(() => Number(props.id))

async function loadPosts(page = 1): Promise<void> {
  postLoading.value = true
  try {
    const data = await fetchDishPosts(dishId.value, page, 10)
    posts.value = page === 1 ? data.items : [...posts.value, ...data.items]
    postTotal.value = data.total
    postPage.value = page
  } finally {
    postLoading.value = false
  }
}

async function loadRatings(): Promise<void> {
  const data = await fetchDishRatings(dishId.value, 1, 50)
  ratings.value = data.items
  ratingTotal.value = data.total
}

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const [d, p] = await Promise.all([fetchDish(dishId.value), fetchDishPosts(dishId.value, 1, 10)])
    dish.value = d
    posts.value = p.items
    postTotal.value = p.total
    await loadRatings()
  } catch (e) {
    if (isNotFound(e)) {
      void router.replace({ name: 'not-found' })
      return
    }
    error.value = e
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(dishId, load)

function onLiked(payload: { id: number; liked: boolean; like_count: number }): void {
  const target = posts.value.find((item) => item.id === payload.id)
  if (target) {
    target.is_liked = payload.liked
    target.like_count = payload.like_count
  }
}

function onDeleted(id: number): void {
  posts.value = posts.value.filter((item) => item.id !== id)
  postTotal.value -= 1
}
</script>

<template>
  <div class="page">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item :to="{ name: 'canteens' }">食堂导航</el-breadcrumb-item>
      <el-breadcrumb-item :to="{ name: 'merchant', params: { id: dish?.merchant_id } }">
        {{ dish?.merchant_name || '商家' }}
      </el-breadcrumb-item>
      <el-breadcrumb-item>{{ dish?.name || '菜品' }}</el-breadcrumb-item>
    </el-breadcrumb>

    <AppSkeleton v-if="loading" variant="detail" :count="4" />

    <ErrorState v-else-if="error" :error="error" title="菜品信息没加载出来" @retry="load" />

    <template v-else-if="dish">
      <header class="card header">
        <img v-if="dish.image_url" :src="dish.image_url" :alt="dish.name" class="cover" />
        <div v-else class="cover img-fallback">{{ dish.name.slice(0, 1) }}</div>

        <div class="info">
          <h1>{{ dish.name }}</h1>
          <div class="tiny">{{ dish.merchant_name }} · {{ dish.canteen_name }}</div>
          <div class="rating-row">
            <span class="big">{{ dish.avg_rating ? dish.avg_rating.toFixed(1) : '暂无' }}</span>
            <div>
              <RatingStars :value="dish.avg_rating" size="default" />
              <div class="tiny">{{ dish.rating_count }} 人打过分</div>
            </div>
          </div>
          <el-tag v-if="!dish.is_available" type="info" size="small">已下架</el-tag>
        </div>

        <el-button
          v-if="dish.is_available"
          type="primary"
          round
          @click="router.push({ name: 'create', query: { dish_id: dish.id } })"
        >
          我也来评一句
        </el-button>
      </header>

      <el-tabs v-model="tab" class="tabs">
        <el-tab-pane :label="`食评 ${postTotal}`" name="posts">
          <div v-if="!posts.length" class="card empty">这道菜还没有人发帖，做第一个吧</div>
          <template v-else>
            <PostCard v-for="post in posts" :key="post.id" :post="post" @liked="onLiked" @deleted="onDeleted" />
            <div class="more">
              <el-button v-if="posts.length < postTotal" :loading="postLoading" round @click="loadPosts(postPage + 1)">
                加载更多
              </el-button>
            </div>
          </template>
        </el-tab-pane>

        <el-tab-pane :label="`打分记录 ${ratingTotal}`" name="ratings">
          <div v-if="!ratings.length" class="card empty">还没有打分记录</div>
          <div v-else class="card">
            <div v-for="item in ratings" :key="`${item.user_id}-${item.updated_at}`" class="rating-item">
              <span class="avatar">{{ item.nickname.slice(0, 1) }}</span>
              <span class="name">{{ item.nickname }}</span>
              <RatingStars :value="item.score" />
              <span class="tiny time">{{ timeAgo(item.updated_at) }}</span>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<style scoped>
.header {
  display: flex;
  gap: 18px;
  align-items: center;
  margin: 14px 0 6px;
}

.cover {
  width: 116px;
  height: 96px;
  border-radius: 14px;
  object-fit: cover;
  font-size: 34px;
  flex-shrink: 0;
}

.info {
  flex: 1;
}

h1 {
  margin: 0;
  font-size: 22px;
}

.rating-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 8px 0 4px;
}

.big {
  font-size: 26px;
  font-weight: 800;
  color: var(--brand-dark);
  line-height: 1;
}

.tabs {
  margin-top: 10px;
}

.more {
  text-align: center;
  padding: 6px 0 20px;
}

.rating-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 0;
  border-bottom: 1px dashed var(--line);
}

.rating-item:last-child {
  border-bottom: none;
}

.avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ffb27a, #ff6b35);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 700;
}

.name {
  font-size: 13px;
  font-weight: 600;
  min-width: 80px;
}

.time {
  margin-left: auto;
}
</style>
