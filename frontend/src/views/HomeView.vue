<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchFeed } from '@/api/post'
import PostCard from '@/components/PostCard.vue'
import HotBoard from '@/components/HotBoard.vue'
import TopDishBoard from '@/components/TopDishBoard.vue'
import RandomDishDialog from '@/components/RandomDishDialog.vue'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import { useAuthStore } from '@/stores/auth'
import type { Post } from '@/types'

const router = useRouter()
const auth = useAuthStore()

const TABS = [
  { key: 'latest', label: '最新' },
  { key: 'hot', label: '最热' },
  { key: 'following', label: '关注' },
] as const

type SortKey = (typeof TABS)[number]['key']

const sort = ref<SortKey>('latest')
const posts = ref<Post[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const error = ref<unknown>(null)
const hotRef = ref<{ reload: () => Promise<void> } | null>(null)
const randomOpen = ref(false)

/** 关注流未登录时的清空动作：不打注定 401 的请求，页面直接给登录引导 */
function clearForGuest(): void {
  posts.value = []
  total.value = 0
  error.value = null
  loading.value = false
  page.value = 1
}

/** page 只在请求成功后才推进，避免失败一次就永久错位 */
async function fetchPage(target: number, append: boolean): Promise<void> {
  if (sort.value === 'following' && !auth.isLoggedIn) {
    clearForGuest()
    return
  }
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

function goLogin(): void {
  router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
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

watch(sort, () => {
  // 切 tab 先清空：否则新 tab 加载时还挂着上一个 tab 的帖子，顺序和内容都对不上
  posts.value = []
  total.value = 0
  void fetchPage(1, false)
})

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
        <div class="hero-acts">
          <el-button round size="large" @click="randomOpen = true">
            <span class="dice">🎲</span>帮我选
          </el-button>
          <el-button type="primary" round size="large" @click="router.push({ name: 'create' })">
            发一条食评
          </el-button>
        </div>
      </div>

      <TopDishBoard />

      <div class="tabs">
        <button
          v-for="tab in TABS"
          :key="tab.key"
          class="tab"
          :class="{ active: sort === tab.key }"
          @click="sort = tab.key"
        >
          {{ tab.label }}
          <span v-if="tab.key === 'following' && auth.user?.following_count" class="tab-count">
            {{ auth.user.following_count }}
          </span>
        </button>
        <span v-if="!(sort === 'following' && !auth.isLoggedIn)" class="tiny count">共 {{ total }} 条</span>
      </div>

      <AppSkeleton v-if="loading && !posts.length" variant="post" :count="3" />

      <ErrorState v-else-if="error" :error="error" title="信息流没加载出来" @retry="retry" />

      <div v-else-if="sort === 'following' && !auth.isLoggedIn" class="card empty follow-empty">
        <p class="empty-title">登录后才能看关注动态</p>
        <p class="tiny">关注的人发了什么，集中在这里，不用在信息流里翻</p>
        <el-button type="primary" round @click="goLogin">去登录</el-button>
      </div>

      <div v-else-if="!posts.length && sort === 'following'" class="card empty follow-empty">
        <template v-if="!auth.user?.following_count">
          <p class="empty-title">还没关注任何人</p>
          <p class="tiny">点开任意一条帖子，进作者主页就能关注；之后他们的新帖会出现在这里</p>
          <el-button round @click="sort = 'latest'">先去逛逛</el-button>
        </template>
        <template v-else>
          <p class="empty-title">关注的人还没发帖</p>
          <p class="tiny">你关注了 {{ auth.user.following_count }} 人，他们发帖后会出现在这里</p>
          <el-button round @click="sort = 'latest'">看看全站</el-button>
        </template>
      </div>

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

    <RandomDishDialog v-model="randomOpen" />
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

.hero-acts {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

/* Element Plus 默认给相邻按钮加 margin-left，这里已经用 gap 了，去掉避免间距翻倍 */
.hero-acts :deep(.el-button + .el-button) {
  margin-left: 0;
}

/* 只抖骰子图标，不抖整颗按钮：整颗转起来像误触 */
.dice {
  display: inline-block;
  margin-right: 5px;
  animation: nudge 4.2s ease-in-out infinite;
}

@keyframes nudge {
  0%,
  88%,
  100% {
    transform: rotate(0deg);
  }
  90% {
    transform: rotate(-6deg);
  }
  93% {
    transform: rotate(6deg);
  }
  96% {
    transform: rotate(-3deg);
  }
}

@media (max-width: 620px) {
  .hero {
    flex-direction: column;
    align-items: stretch;
  }

  .hero-acts :deep(.el-button) {
    flex: 1;
  }
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

/* 关注人数跟在 tab 后面，比单独写一行"你关注了 3 人"省地方 */
.tab-count {
  margin-left: 4px;
  font-size: 11px;
  opacity: 0.7;
}

/* 关注流的三条空态（未登录 / 没关注人 / 关注的人没发帖）共用一套排版 */
.follow-empty {
  display: grid;
  justify-items: center;
  gap: 6px;
  padding: 40px 20px;
}

.empty-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}

.follow-empty .tiny {
  margin: 0;
  max-width: 400px;
  line-height: 1.7;
}

.follow-empty :deep(.el-button) {
  margin-top: 8px;
}

.count {
  margin-left: auto;
}

.more {
  text-align: center;
  padding: 10px 0 30px;
}
</style>
