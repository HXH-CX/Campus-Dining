<script setup lang="ts">
/**
 * 首页「高分榜」。
 *
 * 存在的意义：首页的帖子流回答不了「今天吃什么」——那是按时间/热度排的，
 * 一条 5 星帖可能只是某个人第一次吃。这里改成按菜品聚合：
 * 够分（均分门槛）+ 够人评（至少 N 人）才上榜，避免"一人打五星就登顶"。
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchTopDishes } from '@/api/catalog'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import type { Dish } from '@/types'

const MIN_RATING = 4
const MIN_COUNT = 2

const router = useRouter()
const dishes = ref<Dish[]>([])
const loading = ref(true)
const error = ref<unknown>(null)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    dishes.value = await fetchTopDishes({ min_rating: MIN_RATING, min_count: MIN_COUNT, limit: 6 })
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

onMounted(load)

function go(dishId: number): void {
  router.push({ name: 'dish', params: { id: dishId } })
}

const RANK = ['🥇', '🥈', '🥉']
</script>

<template>
  <section class="card board">
    <header class="head">
      <h2>高分榜</h2>
      <span class="tiny rule">均分 {{ MIN_RATING }} 以上 · 至少 {{ MIN_COUNT }} 人评过</span>
    </header>

    <AppSkeleton v-if="loading" variant="card" :count="3" />

    <ErrorState v-else-if="error" :error="error" title="高分榜没拉下来" compact @retry="load" />

    <div v-else-if="!dishes.length" class="empty">
      还没有菜品够格上榜，多几个人打分就会出现
    </div>

    <div v-else class="items">
      <div v-for="(dish, index) in dishes" :key="dish.id" class="item" @click="go(dish.id)">
        <img v-if="dish.image_url" :src="dish.image_url" class="thumb" :alt="dish.name" loading="lazy" />
        <span v-else class="thumb fallback">{{ dish.name.slice(0, 1) }}</span>

        <div class="info">
          <div class="name">
            <span v-if="index < 3" class="rank">{{ RANK[index] }}</span>{{ dish.name }}
          </div>
          <div class="tiny sub">{{ dish.merchant_name }} · {{ dish.canteen_name }}</div>
        </div>

        <div class="score">
          <b>{{ dish.avg_rating.toFixed(1) }}</b>
          <span class="tiny">{{ dish.rating_count }} 人评</span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.board {
  margin-bottom: 18px;
}

.head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 12px;
}

.head h2 {
  margin: 0;
  font-size: 16px;
}

.rule {
  margin-left: auto;
}

/* 两列而不是三列：三列时菜名和商家名会被截成「麻辣烫（微…」，反而看不出是哪道菜 */
.items {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 12px;
  background: #fffaf5;
  border: 1px solid var(--line);
  cursor: pointer;
  transition: border-color 0.15s ease, transform 0.15s ease;
}

.item:hover {
  border-color: var(--brand);
  transform: translateY(-1px);
}

.rank {
  margin-right: 2px;
}

.thumb {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  object-fit: cover;
  flex-shrink: 0;
}

.fallback {
  display: grid;
  place-items: center;
  background: var(--brand-soft);
  color: var(--brand-dark);
  font-weight: 700;
}

.info {
  flex: 1;
  min-width: 0;
}

.name {
  font-weight: 600;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 食堂名长的会把两行撑开、高度参差，统一单行截断 */
.sub {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.score {
  text-align: right;
  flex-shrink: 0;
}

.score b {
  color: #e8452c;
  font-size: 16px;
}

.score .tiny {
  display: block;
}

@media (max-width: 560px) {
  .items {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
