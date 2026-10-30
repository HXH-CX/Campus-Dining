<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchMerchant, fetchMerchantDishes } from '@/api/catalog'
import { fetchMerchantPosts } from '@/api/post'
import { isNotFound } from '@/api/request'
import PostCard from '@/components/PostCard.vue'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import type { Dish, Merchant, Post } from '@/types'

const props = defineProps<{ id: string }>()
const router = useRouter()

const merchant = ref<Merchant | null>(null)
const dishes = ref<Dish[]>([])
const posts = ref<Post[]>([])
const postTotal = ref(0)
const postPage = ref(1)
const tab = ref<'dishes' | 'posts'>('dishes')
const loading = ref(true)
const postLoading = ref(false)
const error = ref<unknown>(null)

const merchantId = computed(() => Number(props.id))

async function loadPosts(page = 1): Promise<void> {
  postLoading.value = true
  try {
    const data = await fetchMerchantPosts(merchantId.value, page, 10)
    posts.value = page === 1 ? data.items : [...posts.value, ...data.items]
    postTotal.value = data.total
    postPage.value = page
  } finally {
    postLoading.value = false
  }
}

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const [m, d] = await Promise.all([fetchMerchant(merchantId.value), fetchMerchantDishes(merchantId.value)])
    merchant.value = m
    dishes.value = d
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
watch(merchantId, load)

watch(tab, (value) => {
  if (value === 'posts' && !posts.value.length) void loadPosts(1)
})

function onLiked(payload: { id: number; liked: boolean; like_count: number }): void {
  const target = posts.value.find((item) => item.id === payload.id)
  if (target) {
    target.is_liked = payload.liked
    target.like_count = payload.like_count
  }
}
</script>

<template>
  <div class="page">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item :to="{ name: 'canteens' }">食堂导航</el-breadcrumb-item>
      <el-breadcrumb-item :to="{ name: 'canteen-merchants', params: { id: merchant?.canteen_id } }">
        {{ merchant?.canteen_name || '食堂' }}
      </el-breadcrumb-item>
      <el-breadcrumb-item>{{ merchant?.name || '加载中' }}</el-breadcrumb-item>
    </el-breadcrumb>

    <AppSkeleton v-if="loading" variant="detail" :count="4" />

    <ErrorState v-else-if="error" :error="error" title="商家信息没加载出来" @retry="load" />

    <template v-else-if="merchant">
      <header class="card header">
        <div class="thumb img-fallback">🏪</div>
        <div class="info">
          <h1>{{ merchant.name }}</h1>
          <div class="tiny">{{ merchant.canteen_name }}</div>
          <div class="stats">
            <span class="big">{{ merchant.overall_rating ? merchant.overall_rating.toFixed(1) : '暂无' }}</span>
            <span class="tiny">综合评分 · {{ merchant.dish_count }} 道菜</span>
          </div>
        </div>
        <el-button type="primary" round @click="router.push({ name: 'create' })">去写食评</el-button>
      </header>

      <el-tabs v-model="tab" class="tabs">
        <el-tab-pane label="菜品" name="dishes">
          <div v-if="!dishes.length" class="card empty">这个商家还没有上架菜品</div>
          <div v-else class="grid">
            <div
              v-for="dish in dishes"
              :key="dish.id"
              class="card dish"
              @click="router.push({ name: 'dish', params: { id: dish.id } })"
            >
              <img v-if="dish.image_url" :src="dish.image_url" :alt="dish.name" class="cover" />
              <div v-else class="cover img-fallback">{{ dish.name.slice(0, 1) }}</div>
              <div class="dish-name">{{ dish.name }}</div>
              <div class="row">
                <span class="score">{{ dish.avg_rating ? dish.avg_rating.toFixed(1) : '暂无' }}</span>
                <span class="tiny">{{ dish.rating_count }} 人评</span>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane :label="`相关帖子${postTotal ? ` ${postTotal}` : ''}`" name="posts">
          <AppSkeleton v-if="postLoading && !posts.length" variant="post" :count="2" />
          <div v-else-if="!posts.length" class="card empty">还没有人点评这家店</div>
          <template v-else>
            <PostCard v-for="post in posts" :key="post.id" :post="post" @liked="onLiked" />
            <div class="more">
              <el-button v-if="posts.length < postTotal" :loading="postLoading" round @click="loadPosts(postPage + 1)">
                加载更多
              </el-button>
            </div>
          </template>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  gap: 18px;
  margin: 14px 0 6px;
}

.thumb {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  font-size: 28px;
  flex-shrink: 0;
}

.info {
  flex: 1;
}

h1 {
  margin: 0;
  font-size: 22px;
}

.stats {
  margin-top: 6px;
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.big {
  font-size: 24px;
  font-weight: 800;
  color: var(--brand-dark);
}

.tabs {
  margin-top: 10px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 14px;
}

.dish {
  padding: 10px;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.dish:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(120, 80, 50, 0.12);
}

.cover {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  border-radius: 10px;
  font-size: 26px;
}

.dish-name {
  font-weight: 600;
  margin: 8px 0 2px;
}

.row {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.score {
  color: var(--brand-dark);
  font-weight: 700;
}

.more {
  text-align: center;
  padding: 6px 0 20px;
}
</style>
