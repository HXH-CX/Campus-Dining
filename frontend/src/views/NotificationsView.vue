<script setup lang="ts">
/**
 * 通知中心：谁赞了、谁评论了、谁关注了。
 *
 * 点一条通知 = 标记已读 + 跳到"能看懂它指的是什么"的地方：
 * 赞和评论跳原帖，关注跳对方主页。不这样做的话，用户点完还在原地，
 * 只会觉得这是个死列表。
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchNotifications, markAllRead, markRead } from '@/api/notification'
import { useNotifyStore } from '@/stores/notify'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import { timeAgo } from '@/utils/format'
import { ElMessage } from '@/utils/feedback'
import type { NotificationItem } from '@/types'

const router = useRouter()
const notify = useNotifyStore()

const tab = ref<'all' | 'unread'>('all')
const items = ref<NotificationItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const error = ref<unknown>(null)
const marking = ref(false)

const emptyText = computed(() =>
  tab.value === 'unread' ? '没有未读通知，攒着吧' : '还没有人惊动你，去发条食评试试',
)

const ACTIONS: Record<NotificationItem['type'], string> = {
  like: '赞了你的食评',
  comment: '评论了你的食评',
  follow: '关注了你',
}

async function fetchPage(target: number, append: boolean): Promise<void> {
  if (loading.value) return
  loading.value = true
  if (!append) error.value = null
  try {
    const data = await fetchNotifications({
      page: target,
      page_size: pageSize,
      unread_only: tab.value === 'unread',
    })
    items.value = append ? [...items.value, ...data.items] : data.items
    total.value = data.total
    page.value = target
  } catch (e) {
    if (!append) error.value = e
  } finally {
    loading.value = false
  }
}

function switchTab(next: 'all' | 'unread'): void {
  if (tab.value === next) return
  tab.value = next
  // 先清空再请求：不清的话切换瞬间会看到上一个 tab 的内容
  items.value = []
  total.value = 0
  void fetchPage(1, false)
}

async function open(item: NotificationItem): Promise<void> {
  if (!item.is_read) {
    // 本地先置灰 + 减角标，等接口回来再校准；失败就让它留在未读
    item.is_read = true
    notify.decrease()
    try {
      await markRead(item.id)
    } catch {
      item.is_read = false
      void notify.refresh()
      return
    }
  }
  if (item.type === 'follow') {
    router.push({ name: 'user', params: { id: item.actor.id } })
    return
  }
  if (item.post) router.push({ name: 'post', params: { id: item.post.id } })
}

async function readAll(): Promise<void> {
  if (marking.value) return
  marking.value = true
  try {
    const data = await markAllRead()
    items.value.forEach((item) => (item.is_read = true))
    notify.reset()
    ElMessage.success(data.updated ? `已把 ${data.updated} 条标为已读` : '本来就没有未读')
    // 在"未读"页签下清空后列表就没内容了，退回全部更合理
    if (tab.value === 'unread') switchTab('all')
  } catch {
    // 拦截器已提示
  } finally {
    marking.value = false
  }
}

onMounted(() => void fetchPage(1, false))
</script>

<template>
  <div class="page narrow">
    <header class="head card">
      <div>
        <h1>通知</h1>
        <p class="tiny">被赞、被评论、被关注都会落在这里</p>
      </div>
      <el-button :disabled="!notify.unread" :loading="marking" round @click="readAll">全部已读</el-button>
    </header>

    <div class="tabs">
      <button class="tab" :class="{ active: tab === 'all' }" @click="switchTab('all')">全部</button>
      <button class="tab" :class="{ active: tab === 'unread' }" @click="switchTab('unread')">
        未读
        <span v-if="notify.unread" class="badge">{{ notify.unread > 99 ? '99+' : notify.unread }}</span>
      </button>
    </div>

    <AppSkeleton v-if="loading && !items.length" variant="row" :count="5" />

    <ErrorState v-else-if="error" :error="error" title="通知没加载出来" @retry="fetchPage(1, false)" />

    <div v-else-if="!items.length" class="card empty">{{ emptyText }}</div>

    <template v-else>
      <ul class="list card">
        <li
          v-for="item in items"
          :key="item.id"
          class="row"
          :class="{ unread: !item.is_read }"
          @click="open(item)"
        >
          <span class="dot" :class="{ on: !item.is_read }" />
          <span class="avatar">
            <img v-if="item.actor.avatar_url" :src="item.actor.avatar_url" :alt="item.actor.nickname" />
            <template v-else>{{ item.actor.nickname.slice(0, 1) }}</template>
          </span>

          <div class="body">
            <p class="line">
              <strong>{{ item.actor.nickname }}</strong>
              <span class="muted"> {{ ACTIONS[item.type] }}</span>
              <span v-if="item.post" class="dish">· {{ item.post.dish_name }}</span>
            </p>
            <p v-if="item.comment_content" class="excerpt">“{{ item.comment_content }}”</p>
            <p v-else-if="item.post?.content" class="excerpt">{{ item.post.content }}</p>
            <p class="tiny">{{ timeAgo(item.created_at) }}</p>
          </div>

          <img
            v-if="item.post?.image_url"
            class="thumb"
            :src="item.post.image_url"
            :alt="item.post.dish_name"
            loading="lazy"
          />
        </li>
      </ul>

      <div v-if="items.length < total" class="more">
        <el-button :loading="loading" round @click="fetchPage(page + 1, true)">
          加载更多（{{ items.length }} / {{ total }}）
        </el-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.narrow {
  max-width: 720px;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.head h1 {
  margin: 0 0 2px;
  font-size: 20px;
}

.head p {
  margin: 0;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  color: var(--text-2);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.tab.active {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
  font-weight: 600;
}

.badge {
  min-width: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: var(--brand);
  color: #fff;
  font-size: 11px;
  line-height: 18px;
  text-align: center;
}

.tab.active .badge {
  background: rgba(255, 255, 255, 0.28);
}

.list {
  list-style: none;
  margin: 0;
  padding: 6px;
}

.row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 10px;
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.15s;
}

.row + .row {
  border-top: 1px solid var(--line);
}

.row:hover {
  background: #fffaf5;
}

.row.unread {
  background: var(--brand-soft);
}

.dot {
  width: 7px;
  height: 7px;
  margin-top: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot.on {
  background: var(--brand);
}

.avatar {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--brand-soft);
  color: var(--brand-dark);
  font-weight: 700;
  overflow: hidden;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.body {
  flex: 1;
  min-width: 0;
}

.line {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
}

.dish {
  color: var(--brand-dark);
  font-weight: 600;
}

.excerpt {
  margin: 3px 0 2px;
  color: var(--text-2);
  font-size: 13px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.thumb {
  width: 56px;
  height: 56px;
  flex-shrink: 0;
  border-radius: 10px;
  object-fit: cover;
  background: #faf3ec;
}

.more {
  display: flex;
  justify-content: center;
  padding: 16px 0;
}

@media (max-width: 560px) {
  .head {
    align-items: flex-start;
  }

  .thumb {
    width: 44px;
    height: 44px;
  }
}
</style>
