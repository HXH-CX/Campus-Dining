<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchFeed } from '@/api/post'
import PostCard from '@/components/PostCard.vue'
import HotBoard from '@/components/HotBoard.vue'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import type { Post } from '@/types'

const router = useRouter()

const sort = ref<'latest' | 'hot'>('latest')
const posts = ref<Post[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const error = ref<unknown>(null)
const hotRef = ref<{ reload: () => Promise<void> } | null>(null)

/** page 只在请求成功后才推进，避免失败一次就永久错位 */
async function fetchPage(target: number, append: boolean): Promise<void> {
  if (loading.value) return
  loading.value = true
  if (!append) error.value = null
  try {
    const data = await fetchFeed({ sort: sort.value, page: target, page_size: pageSize })
    posts.value = append ? [...posts.value, ...data.items] : data.items
    total.value = data.total
    page.value = target
  } catch (e) {
    // "加载更多"失败时保留已有列表，只在首屏失败时整块替换成错误态
    if (!append) error.value = e
  } finally {
    loading.value = false
  }
}

function retry(): void {
  void fetchPage(1, false)
}

function loadMore(): void {
  void fetchPage(page.value + 1, true)
}

function onLiked(payload: { id: number; liked: boolean; like_count: number }): void {
  const target = posts.value.find((item) => item.id === payload.id)
  if (target) {
    target.is_liked = payload.liked
    target.like_count = payload.like_count
  }
  void hotRef.value?.reload()
}

function onDeleted(id: number): void {
  posts.value = posts.value.filter((item) => item.id !== id)
  total.value -= 1
  void hotRef.value?.reload()
}

watch(sort, () => void fetchPage(1, false))

onMounted(() => void fetchPage(1, false))
</script>

<template>
  <div class="page home-grid">
    <div>
      <div class="hero card">
        <div>
          <h1>今天吃什么？</h1>
          <p class="muted">看看同学们最近在食堂发现了什么好东西</p>
        </div>
        <el-button type="primary" round size="large" @click="router.push({ name: 'create' })">
          发一条食评
        </el-button>
      </div>

      <div class="tabs">
        <button class="tab" :class="{ active: sort === 'latest' }" @click="sort = 'latest'">最新</button>
        <button class="tab" :class="{ active: sort === 'hot' }" @click="sort = 'hot'">最热</button>
        <span class="tiny count">共 {{ total }} 条</span>
      </div>

      <AppSkeleton v-if="loading && !posts.length" variant="post" :count="3" />

      <ErrorState v-else-if="error" :error="error" title="信息流没加载出来" @retry="retry" />

      <div v-else-if="!posts.length" class="card empty">
        食堂还没人开张，去发第一条吧
      </div>

      <template v-else>
        <PostCard
          v-for="post in posts"
          :key="post.id"
          :post="post"
          @liked="onLiked"
          @deleted="onDeleted"
        />

        <div class="more">
          <el-button v-if="posts.length < total" :loading="loading" round @click="loadMore">
            加载更多（{{ posts.length }}/{{ total }}）
          </el-button>
          <span v-else class="tiny">已经到底啦</span>
        </div>
      </template>
    </div>

    <HotBoard ref="hotRef" />
  </div>
</template>

<style scoped>
.home-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 288px;
  gap: 22px;
  align-items: start;
}

.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
  background: linear-gradient(120deg, #fff6ef 0%, #ffffff 60%);
}

.hero h1 {
  margin: 0 0 4px;
  font-size: 22px;
}

.hero p {
  margin: 0;
  font-size: 13px;
}

.tabs {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.tab {
  border: none;
  background: transparent;
  padding: 6px 16px;
  border-radius: 999px;
  font-size: 14px;
  color: var(--text-2);
  cursor: pointer;
  font-family: inherit;
}

.tab.active {
  background: var(--brand);
  color: #fff;
  font-weight: 600;
}

.count {
  margin-left: auto;
}

.more {
  text-align: center;
  padding: 10px 0 30px;
}
</style>
