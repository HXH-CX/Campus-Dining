<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from '@/utils/feedback'
import { fetchDish, fetchDishRatings, fetchMerchantDishes, toggleWant } from '@/api/catalog'
import { fetchDishPosts } from '@/api/post'
import { isNotFound } from '@/api/request'
import PostCard from '@/components/PostCard.vue'
import RatingStars from '@/components/RatingStars.vue'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import ImageViewer from '@/components/ImageViewer.vue'
import { useAuthStore } from '@/stores/auth'
import { timeAgo } from '@/utils/format'
import type { Dish, Post } from '@/types'

const props = defineProps<{ id: string }>()
const router = useRouter()
const auth = useAuthStore()

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
const wanting = ref(false)
const coverOpen = ref(false)
/**
 * 同店其他菜。
 *
 * 看完一道菜，下一个念头几乎必然是"这家还有什么"——此前只能回退到商家页，
 * 多两次点击。放在页面底部而不是塞进 Tab：它是"顺便看看"，不该和食评抢位置。
 * 只取 6 道，剩下的引导去商家页。
 */
const siblings = ref<Dish[]>([])

async function loadSiblings(merchantId: number): Promise<void> {
  try {
    const list = await fetchMerchantDishes(merchantId)
    siblings.value = list
      // 接口已经只返在售菜品，这里去掉当前这道
      .filter((item) => item.id !== dishId.value)
      // 均分高的在前，同分看人数（3 人 4.67 比 1 人 5.0 可信），没人评过的沉底
      .sort((a, b) => b.avg_rating - a.avg_rating || b.rating_count - a.rating_count)
      .slice(0, 6)
  } catch {
    // 附加信息，拿不到就不显示，绝不能因为它影响菜品主体和食评
    siblings.value = []
  }
}

/** 想吃：一个接口翻转状态，返回最新的想吃人数，不需要前端猜 */
async function handleWant(): Promise<void> {
  if (!dish.value || wanting.value) return
  if (!auth.isLoggedIn) {
    ElMessage.warning('登录后才能加入想吃清单')
    router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  wanting.value = true
  try {
    const result = await toggleWant(dish.value.id)
    dish.value.is_wanted = result.wanted
    dish.value.want_count = result.want_count
    ElMessage.success(result.wanted ? '已加入想吃清单' : '已移出想吃清单')
  } catch {
    // 拦截器已提示
  } finally {
    wanting.value = false
  }
}

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
    // 同店其他菜要等拿到 merchant_id 才能查，所以是第二跳；和打分记录并行发
    await Promise.all([loadRatings(), loadSiblings(d.merchant_id)])
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
        <img
          v-if="dish.image_url"
          :src="dish.image_url"
          :alt="dish.name"
          class="cover"
          @click="coverOpen = true"
        />
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

        <div class="acts">
          <el-button round class="want-btn" :class="{ on: dish.is_wanted }" :loading="wanting" @click="handleWant">
            {{ dish.is_wanted ? '已想吃' : '想吃' }}
            <span v-if="dish.want_count" class="want-count">{{ dish.want_count }}</span>
          </el-button>
          <el-button
            v-if="dish.is_available"
            type="primary"
            round
            @click="router.push({ name: 'create', query: { dish_id: dish.id } })"
          >
            我也来评一句
          </el-button>
        </div>
      </header>

      <ImageViewer
        v-model:visible="coverOpen"
        :index="0"
        :images="dish.image_url ? [dish.image_url] : []"
      />

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

      <section v-if="siblings.length" class="siblings">
        <div class="sib-head">
          <h2>这家还有</h2>
          <router-link
            class="tiny more-link"
            :to="{ name: 'merchant', params: { id: dish.merchant_id } }"
          >
            看全部 →
          </router-link>
        </div>
        <div class="sib-scroll">
          <div
            v-for="item in siblings"
            :key="item.id"
            class="card sib"
            @click="router.push({ name: 'dish', params: { id: item.id } })"
          >
            <img v-if="item.image_url" :src="item.image_url" :alt="item.name" loading="lazy" />
            <div v-else class="sib-fallback">{{ item.name.slice(0, 1) }}</div>
            <div class="sib-name">{{ item.name }}</div>
            <div class="tiny sib-score">
              <template v-if="item.rating_count">
                {{ item.avg_rating.toFixed(1) }} · {{ item.rating_count }} 人
              </template>
              <template v-else>还没人评</template>
            </div>
          </div>
        </div>
      </section>
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
  cursor: zoom-in;
}

.info {
  flex: 1;
  min-width: 0;
}

.acts {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* Element Plus 给相邻按钮加 margin-left，这里已经用 gap，去掉避免间距翻倍 */
.acts :deep(.el-button + .el-button) {
  margin-left: 0;
}

/* 已想吃用浅底强调：不抢主按钮（我也来评一句）的视觉权重 */
.want-btn.on {
  color: var(--brand-dark);
  border-color: var(--brand);
  background: var(--brand-soft);
}

.want-count {
  margin-left: 6px;
  font-size: 12px;
  opacity: 0.75;
}

@media (max-width: 560px) {
  .header {
    flex-wrap: wrap;
  }

  .acts {
    width: 100%;
  }

  .acts :deep(.el-button) {
    flex: 1;
  }
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
  /* 窄屏下 "暂无" 会被挤成竖排两个字，锁死不换行 */
  white-space: nowrap;
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

/* ---- 同店其他菜 ---- */
.siblings {
  margin: 22px 0 8px;
}

.sib-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}

.sib-head h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}

.more-link {
  color: var(--brand-dark);
  text-decoration: none;
}

/* 横向滚动而不是换行：手机上一行滑动比堆三行更好点，也不会把页面拉得很长 */
.sib-scroll {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 4px;
  scrollbar-width: thin;
}

.sib {
  flex: 0 0 128px;
  padding: 8px;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.sib:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(120, 72, 30, 0.12);
}

.sib img,
.sib-fallback {
  width: 100%;
  aspect-ratio: 4 / 3;
  border-radius: 10px;
  object-fit: cover;
  background: #faf3ec;
}

.sib-fallback {
  display: grid;
  place-items: center;
  font-size: 24px;
  color: #c8a68b;
  font-weight: 700;
}

.sib-name {
  margin-top: 6px;
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sib-score {
  color: var(--text-3);
}
</style>
