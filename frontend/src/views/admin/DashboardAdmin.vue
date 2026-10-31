<script setup lang="ts">
/**
 * 后台数据概览。
 *
 * 后台此前只有 4 张 CRUD 表：能改数据，但看不出"这站今天怎么样"。
 * 这里补齐三件事：总量 + 今日新增、近 7 天发帖趋势、以及三条需要人工关注的问题
 * （新菜没人评 / 商家没有在售菜品 / 已下架菜品）。
 *
 * 所有数字都是查询时现算的只读数据，没有统计表，也不需要定时任务。
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { adminOverview } from '@/api/admin'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import type { AdminOverview } from '@/types'

const router = useRouter()

const data = ref<AdminOverview | null>(null)
const loading = ref(true)
const error = ref<unknown>(null)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    data.value = await adminOverview()
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

onMounted(load)

const cards = computed(() => {
  const d = data.value
  if (!d) return []
  return [
    { label: '用户', value: d.users, today: d.today_users, hint: '包括管理员' },
    { label: '帖子', value: d.posts, today: d.today_posts, hint: '食评条数' },
    { label: '评论', value: d.comments, today: d.today_comments, hint: '含帖子下的回复' },
    { label: '想吃', value: d.wants, today: null, hint: '未去吃的标记' },
  ]
})

/** 柱状图高度：全为 0 时也留一点底座，否则整张图会"消失" */
const barMax = computed(() => Math.max(1, ...(data.value?.posts_by_day ?? []).map((d) => d.count)))

function barHeight(count: number): string {
  return `${Math.max(4, Math.round((count / barMax.value) * 100))}%`
}

function dayLabel(date: string, index: number, total: number): string {
  if (index === total - 1) return '今天'
  return date.slice(5) // MM-DD
}

function goDish(id: number): void {
  router.push({ name: 'dish', params: { id } })
}

function goMerchant(id: number): void {
  router.push({ name: 'merchant', params: { id } })
}
</script>

<template>
  <div>
    <header class="head">
      <div>
        <h1>数据概览</h1>
        <p class="tiny">实时统计，刷新即最新</p>
      </div>
      <el-button round :loading="loading" @click="load">刷新</el-button>
    </header>

    <ErrorState v-if="error" :error="error" title="概览没加载出来" @retry="load" />

    <AppSkeleton v-else-if="loading && !data" variant="card" :count="3" />

    <template v-else-if="data">
      <div class="stats">
        <div v-for="card in cards" :key="card.label" class="stat card">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-foot tiny">
            <span v-if="card.today !== null" :class="{ up: card.today > 0 }">今日 +{{ card.today }}</span>
            <span v-else>{{ card.hint }}</span>
          </div>
        </div>
      </div>

      <section class="card trend">
        <header class="sec-head">
          <h2>近 7 天发帖</h2>
          <span class="tiny">共 {{ data.posts_by_day.reduce((sum, d) => sum + d.count, 0) }} 条</span>
        </header>

        <div class="bars">
          <div v-for="(day, index) in data.posts_by_day" :key="day.date" class="bar-col" :title="`${day.date}：${day.count} 条`">
            <span class="bar-num tiny">{{ day.count }}</span>
            <div class="bar-track">
              <div class="bar" :style="{ height: barHeight(day.count) }"></div>
            </div>
            <span class="tiny bar-label">{{ dayLabel(day.date, index, data.posts_by_day.length) }}</span>
          </div>
        </div>
      </section>

      <div class="grid2">
        <section class="card">
          <header class="sec-head">
            <h2>上架但没人评</h2>
            <span class="pill">{{ data.untasted_total }}</span>
          </header>
          <p class="tiny desc">新菜缺一条能让人下手的食评，可以去发帖引导一下</p>

          <div v-if="!data.untasted_dishes.length" class="ok">上架的菜都有人评过了</div>
          <ul v-else class="list">
            <li v-for="dish in data.untasted_dishes" :key="dish.id" @click="goDish(dish.id)">
              <span class="name">{{ dish.name }}</span>
              <span class="tiny">{{ dish.merchant_name }}</span>
            </li>
          </ul>
          <p v-if="data.untasted_total > data.untasted_dishes.length" class="tiny more">
            还有 {{ data.untasted_total - data.untasted_dishes.length }} 道没列出
          </p>
        </section>

        <section class="card">
          <header class="sec-head">
            <h2>没有在售菜品的商家</h2>
            <span class="pill">{{ data.empty_merchant_total }}</span>
          </header>
          <p class="tiny desc">用户点进去会看到空列表，补菜品或先下架商家</p>

          <div v-if="!data.empty_merchants.length" class="ok">每个商家都有在售菜品</div>
          <ul v-else class="list">
            <li v-for="merchant in data.empty_merchants" :key="merchant.id" @click="goMerchant(merchant.id)">
              <span class="name">{{ merchant.name }}</span>
              <span class="tiny">{{ merchant.canteen_name }}</span>
            </li>
          </ul>
        </section>
      </div>

      <section class="card meta">
        <span>食堂 <b>{{ data.canteens }}</b></span>
        <span>商家 <b>{{ data.merchants }}</b></span>
        <span>菜品 <b>{{ data.dishes }}</b></span>
        <span>评分记录 <b>{{ data.ratings }}</b></span>
        <span class="warn">已下架菜品 <b>{{ data.unavailable_dishes }}</b></span>
      </section>
    </template>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

h1 {
  margin: 0;
  font-size: 20px;
}

.tiny {
  margin: 4px 0 0;
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 14px;
}

.stat {
  padding: 16px 18px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-2);
}

.stat-value {
  font-size: 28px;
  font-weight: 800;
  line-height: 1.3;
  color: var(--text);
}

.stat-foot {
  margin: 0;
  min-height: 18px;
}

/* 今日有新增时用品牌色标出来，0 就保持灰，不制造噪音 */
.stat-foot .up {
  color: var(--brand-dark);
  font-weight: 600;
}

.sec-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.sec-head h2 {
  margin: 0;
  font-size: 15px;
}

.sec-head .tiny {
  margin: 0 0 0 auto;
}

.trend {
  margin-bottom: 14px;
}

.bars {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 10px;
  align-items: end;
  margin-top: 14px;
}

.bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.bar-num {
  margin: 0;
  font-weight: 600;
  color: var(--text-2);
}

.bar-track {
  width: 100%;
  height: 108px;
  display: flex;
  align-items: flex-end;
  background: linear-gradient(180deg, rgba(255, 107, 53, 0.04), rgba(255, 107, 53, 0.1));
  border-radius: 8px;
}

.bar {
  width: 100%;
  border-radius: 8px;
  background: linear-gradient(180deg, #ff9a6a, #ff6b35);
  transition: height 0.35s ease;
}

.bar-label {
  margin: 0;
}

.grid2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 14px;
  /* 两侧内容长度不一样，别把空卡片拉成一整列高度 */
  align-items: start;
}

.pill {
  margin-left: auto;
  min-width: 26px;
  padding: 1px 9px;
  border-radius: 999px;
  background: var(--brand-soft);
  color: var(--brand-dark);
  font-size: 12px;
  font-weight: 700;
  text-align: center;
}

.desc {
  margin: 2px 0 10px;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.list li {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 7px 0;
  border-bottom: 1px dashed var(--line);
  cursor: pointer;
}

.list li:last-child {
  border-bottom: none;
}

.list li:hover .name {
  color: var(--brand-dark);
}

.name {
  font-weight: 600;
  font-size: 13px;
}

.ok {
  padding: 14px 0 6px;
  color: var(--text-3);
  font-size: 13px;
}

.more {
  margin: 6px 0 0;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  padding: 14px 18px;
  color: var(--text-2);
  font-size: 13px;
}

.meta b {
  color: var(--text);
}

.meta .warn b {
  color: #e8452c;
}

@media (max-width: 1100px) {
  .stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .grid2 {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
