<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { searchDishes } from '@/api/catalog'
import { fetchFeed } from '@/api/post'
import PostCard from '@/components/PostCard.vue'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import type { Dish, Post } from '@/types'

const route = useRoute()
const router = useRouter()

const keyword = ref(String(route.query.kw || ''))
const tab = ref<'dishes' | 'posts'>('dishes')
const dishes = ref<Dish[]>([])
const dishTotal = ref(0)
const posts = ref<Post[]>([])
const postTotal = ref(0)
const loading = ref(false)
const searched = ref(false)
const error = ref<unknown>(null)

async function search(): Promise<void> {
  const kw = keyword.value.trim()
  // 只同步地址栏，不重复触发（watch 里做了对比）
  if (String(route.query.kw || '') !== kw) {
    await router.replace({ name: 'search', query: kw ? { kw } : {} })
  }

  loading.value = true
  error.value = null
  try {
    const [dishPage, postPage] = await Promise.all([
      searchDishes(kw, 1, 24),
      fetchFeed({ keyword: kw, page: 1, page_size: 10 }),
    ])
    dishes.value = dishPage.items
    dishTotal.value = dishPage.total
    posts.value = postPage.items
    postTotal.value = postPage.total
    searched.value = true
    // 菜品没结果但帖子有时，自动切到帖子页，避免看到空页面
    if (!dishPage.total && postPage.total) tab.value = 'posts'
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

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

watch(
  () => route.query.kw,
  (value) => {
    const next = String(value || '')
    if (next !== keyword.value) {
      keyword.value = next
      void search()
    }
  },
)

onMounted(search)
</script>

<template>
  <div class="page">
    <div class="searchbar">
      <el-input
        v-model="keyword"
        size="large"
        placeholder="搜菜名或商家，例如「拉面」「麻辣烫」"
        clearable
        @keyup.enter="search"
      >
        <template #append>
          <el-button @click="search">搜索</el-button>
        </template>
      </el-input>
    </div>

    <el-tabs v-model="tab" class="tabs">
      <el-tab-pane :label="`菜品 ${dishTotal}`" name="dishes">
        <AppSkeleton v-if="loading" variant="card" :count="6" />
        <ErrorState v-else-if="error" :error="error" title="搜索失败了" @retry="search" />
        <div v-else-if="!dishes.length" class="card empty">
          {{ searched ? '没搜到相关菜品，换个词试试' : '输入关键词开始搜索' }}
        </div>
        <div v-else class="grid">
          <div
            v-for="dish in dishes"
            :key="dish.id"
            class="card dish"
            @click="router.push({ name: 'dish', params: { id: dish.id } })"
          >
            <img v-if="dish.image_url" :src="dish.image_url" :alt="dish.name" class="cover" loading="lazy" />
            <div v-else class="cover img-fallback">{{ dish.name.slice(0, 1) }}</div>
            <div class="dish-name">{{ dish.name }}</div>
            <div class="tiny">{{ dish.merchant_name }} · {{ dish.canteen_name }}</div>
            <div class="row">
              <span class="score">{{ dish.avg_rating ? dish.avg_rating.toFixed(1) : '暂无' }}</span>
              <span class="tiny">{{ dish.rating_count }} 人评</span>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane :label="`帖子 ${postTotal}`" name="posts">
        <AppSkeleton v-if="loading" variant="post" :count="2" />
        <ErrorState v-else-if="error" :error="error" title="搜索失败了" @retry="search" />
        <div v-else-if="!posts.length" class="card empty">没搜到相关帖子</div>
        <template v-else>
          <PostCard v-for="post in posts" :key="post.id" :post="post" @liked="onLiked" @deleted="onDeleted" />
        </template>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.searchbar {
  max-width: 620px;
  margin: 4px 0 18px;
}

.tabs {
  margin-top: 4px;
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
  margin-top: 2px;
}

.score {
  color: var(--brand-dark);
  font-weight: 700;
}
</style>
