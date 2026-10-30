<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchHot } from '@/api/post'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import type { Post } from '@/types'

const router = useRouter()
const posts = ref<Post[]>([])
const loading = ref(true)
const error = ref<unknown>(null)

async function reload(): Promise<void> {
  try {
    posts.value = await fetchHot()
    error.value = null
  } catch (e) {
    // 榜单是"锦上添花"，失败不该让首页整体挂掉，退化成一个可点重试的小块
    error.value = e
  }
}

onMounted(async () => {
  try {
    await reload()
  } finally {
    loading.value = false
  }
})

// 点赞/评论后由父组件调用，让榜单反映最新权重
defineExpose({ reload })

function go(post: Post): void {
  router.push({ name: 'dish', params: { id: post.dish.id } })
}
</script>

<template>
  <aside class="hot card">
    <h3 class="section-title">🔥 今日热榜</h3>
    <p class="tiny hint">近 24 小时 · 点赞 + 评论×2</p>

    <AppSkeleton v-if="loading" variant="row" :count="5" />

    <ErrorState v-else-if="error" :error="error" title="热榜没拉下来" compact @retry="reload" />

    <div v-else-if="!posts.length" class="empty">今天还没人上榜，快去发第一条</div>

    <ol v-else class="list">
      <li v-for="(post, index) in posts" :key="post.id" class="item" @click="go(post)">
        <span class="rank" :class="`r${index + 1}`">{{ index + 1 }}</span>
        <div class="body">
          <div class="dish">{{ post.dish.name }}</div>
          <div class="meta tiny">
            {{ post.merchant.name }} · {{ post.author.nickname }}
          </div>
        </div>
        <span class="hits tiny">{{ post.like_count }}👍</span>
      </li>
    </ol>
  </aside>
</template>

<style scoped>
.hot {
  position: sticky;
  top: 78px;
}

/* 窄屏时右栏会折到内容下方，此时不该再吸顶 */
@media (max-width: 900px) {
  .hot {
    position: static;
  }
}

.hint {
  margin: -8px 0 12px;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 4px;
  border-bottom: 1px dashed var(--line);
  cursor: pointer;
}

.item:last-child {
  border-bottom: none;
}

.item:hover .dish {
  color: var(--brand-dark);
}

.rank {
  width: 20px;
  height: 20px;
  border-radius: 6px;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 700;
  background: #f4ece4;
  color: var(--text-3);
  flex-shrink: 0;
}

.rank.r1 {
  background: #ffe3d3;
  color: #d94a12;
}

.rank.r2 {
  background: #ffe9c9;
  color: #b7791f;
}

.rank.r3 {
  background: #fff2d6;
  color: #a8863a;
}

.body {
  flex: 1;
  min-width: 0;
}

.dish {
  font-weight: 600;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.meta {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hits {
  flex-shrink: 0;
}
</style>
