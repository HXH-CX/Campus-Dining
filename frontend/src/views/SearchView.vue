<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchDishTags, searchDishes, searchMerchants } from '@/api/catalog'
import { fetchFeed } from '@/api/post'
import { searchUsers, toggleFollow } from '@/api/user'
import PostCard from '@/components/PostCard.vue'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from '@/utils/feedback'
import type { Dish, DishTag, Merchant, Post, UserCard } from '@/types'

type Tab = 'dishes' | 'posts' | 'merchants' | 'users'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const keyword = ref(String(route.query.kw || ''))
/** 当前选中的标签；空串表示不限 */
const activeTag = ref(String(route.query.tag || ''))
const tags = ref<DishTag[]>([])
const tab = ref<Tab>('dishes')
const dishes = ref<Dish[]>([])
const dishTotal = ref(0)
const posts = ref<Post[]>([])
const postTotal = ref(0)
const merchants = ref<Merchant[]>([])
const merchantTotal = ref(0)
const users = ref<UserCard[]>([])
const userTotal = ref(0)
const loading = ref(false)
const searched = ref(false)
const error = ref<unknown>(null)
/** 正在关注/取关的用户 id，避免连点 */
const followBusy = ref<number | null>(null)

async function search(): Promise<void> {
  const kw = keyword.value.trim()
  // 只同步地址栏，不重复触发（watch 里做了对比）
  const nextQuery: Record<string, string> = {}
  if (kw) nextQuery.kw = kw
  if (activeTag.value) nextQuery.tag = activeTag.value
  if (route.query.kw !== nextQuery.kw || route.query.tag !== nextQuery.tag) {
    await router.replace({ name: 'search', query: nextQuery })
  }

  loading.value = true
  error.value = null
  try {
    // 四个页签一次并行拿完：菜/帖子本来就各查一次，商家和用户各加一个轻查询，
    // 分成"点页签再查"会让每次切页签都闪一次骨架屏，得不偿失。
    const [dishPage, postPage, merchantPage, userPage] = await Promise.all([
      searchDishes(kw, 1, 24, activeTag.value),
      fetchFeed({ keyword: kw, page: 1, page_size: 10 }),
      searchMerchants(kw, 1, 12),
      searchUsers(kw, 1, 12),
    ])
    dishes.value = dishPage.items
    dishTotal.value = dishPage.total
    posts.value = postPage.items
    postTotal.value = postPage.total
    merchants.value = merchantPage.items
    merchantTotal.value = merchantPage.total
    users.value = userPage.items
    userTotal.value = userPage.total
    searched.value = true

    // 菜品没结果时自动切到第一个有内容的页签，避免用户对着空页面以为搜错了
    if (!dishPage.total) {
      const totals: Record<Exclude<Tab, 'dishes'>, number> = {
        posts: postPage.total,
        merchants: merchantPage.total,
        users: userPage.total,
      }
      const fallback = (Object.keys(totals) as Exclude<Tab, 'dishes'>[]).find((key) => totals[key] > 0)
      if (fallback) tab.value = fallback
    }
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

async function onFollow(user: UserCard): Promise<void> {
  if (!auth.isLoggedIn) {
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  if (followBusy.value !== null) return
  followBusy.value = user.id
  try {
    const result = await toggleFollow(user.id)
    user.followed_by_me = result.following
    // 粉丝数本地加减，省一次列表重拉；下一次搜索会校准
    user.follower_count = Math.max(0, user.follower_count + (result.following ? 1 : -1))
    ElMessage.success(result.following ? `已关注 ${user.nickname}` : '已取消关注')
  } catch {
    // 拦截器已提示
  } finally {
    followBusy.value = null
  }
}

async function loadTags(): Promise<void> {
  try {
    tags.value = await fetchDishTags()
  } catch {
    // 标签是筛选增强，拿不到就不显示这排 chip，不影响搜索本身
    tags.value = []
  }
}

function pickTag(name: string): void {
  // 再点一次同一个标签 = 取消筛选
  activeTag.value = activeTag.value === name ? '' : name
  void search()
}

function clearTag(): void {
  if (!activeTag.value) return
  activeTag.value = ''
  void search()
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
  () => [route.query.kw, route.query.tag],
  ([kw, tag]) => {
    const nextKw = String(kw || '')
    const nextTag = String(tag || '')
    if (nextKw === keyword.value && nextTag === activeTag.value) return
    keyword.value = nextKw
    activeTag.value = nextTag
    void search()
  },
)

onMounted(() => {
  void loadTags()
  void search()
})
</script>

<template>
  <div class="page">
    <div class="searchbar">
      <el-input
        v-model="keyword"
        size="large"
        placeholder="搜菜名、商家或同学，例如「拉面」「红红」"
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
        <!-- 标签筛选：一排常驻，0 道菜的标签灰掉但仍可见（用户能知道"这类菜还没人录"） -->
        <div v-if="tags.length" class="tag-filter">
          <button type="button" class="chip" :class="{ on: !activeTag }" @click="clearTag">全部</button>
          <button
            v-for="item in tags"
            :key="item.name"
            type="button"
            class="chip"
            :class="{ on: activeTag === item.name, off: !item.count && activeTag !== item.name }"
            :disabled="!item.count && activeTag !== item.name"
            @click="pickTag(item.name)"
          >
            {{ item.emoji }} {{ item.name }}
            <span class="n">{{ item.count }}</span>
          </button>
        </div>

        <AppSkeleton v-if="loading" variant="card" :count="6" />
        <ErrorState v-else-if="error" :error="error" title="搜索失败了" @retry="search" />
        <div v-else-if="!dishes.length" class="card empty">
          <template v-if="activeTag">「{{ activeTag }}」这个标签下还没有菜，换个标签看看</template>
          <template v-else>{{ searched ? '没搜到相关菜品，换个词试试' : '输入关键词开始搜索' }}</template>
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

      <el-tab-pane :label="`商家 ${merchantTotal}`" name="merchants">
        <AppSkeleton v-if="loading" variant="card" :count="6" />
        <ErrorState v-else-if="error" :error="error" title="搜索失败了" @retry="search" />
        <div v-else-if="!merchants.length" class="card empty">没搜到相关商家</div>
        <div v-else class="grid">
          <div
            v-for="merchant in merchants"
            :key="merchant.id"
            class="card dish"
            @click="router.push({ name: 'merchant', params: { id: merchant.id } })"
          >
            <div class="mark">{{ merchant.name.slice(0, 1) }}</div>
            <div class="dish-name">{{ merchant.name }}</div>
            <div class="tiny">{{ merchant.canteen_name }}</div>
            <div class="row">
              <span class="score">{{ merchant.overall_rating ? merchant.overall_rating.toFixed(1) : '暂无' }}</span>
              <span class="tiny">{{ merchant.dish_count }} 道在售</span>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane :label="`用户 ${userTotal}`" name="users">
        <AppSkeleton v-if="loading" variant="row" :count="4" />
        <ErrorState v-else-if="error" :error="error" title="搜索失败了" @retry="search" />
        <div v-else-if="!users.length" class="card empty">没搜到相关同学</div>
        <ul v-else class="card people">
          <li
            v-for="user in users"
            :key="user.id"
            class="person"
            @click="router.push({ name: 'user', params: { id: user.id } })"
          >
            <span class="avatar">
              <img v-if="user.avatar_url" :src="user.avatar_url" :alt="user.nickname" />
              <template v-else>{{ user.nickname.slice(0, 1) }}</template>
            </span>
            <div class="who">
              <p class="nick">
                {{ user.nickname }}
                <span v-if="user.is_mutual" class="mutual">互关</span>
              </p>
              <p class="tiny">{{ user.title_emoji }} {{ user.title_name }} · {{ user.follower_count }} 粉丝</p>
            </div>
            <el-button
              v-if="auth.user?.id !== user.id"
              :type="user.followed_by_me ? 'default' : 'primary'"
              size="small"
              round
              :loading="followBusy === user.id"
              @click.stop="onFollow(user)"
            >
              {{ user.followed_by_me ? '已关注' : '关注' }}
            </el-button>
          </li>
        </ul>
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

/* ---- 标签筛选 ---- */
.tag-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.chip {
  padding: 5px 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  color: var(--text-2);
  font-family: inherit;
  font-size: 13px;
  line-height: 1.4;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.chip:hover:not(:disabled) {
  border-color: var(--brand);
  color: var(--brand-dark);
}

.chip.on {
  border-color: var(--brand);
  background: var(--brand);
  color: #fff;
  font-weight: 600;
}

/* 灰掉但仍可读：说明"这个标签存在，只是暂时没菜" */
.chip.off {
  color: var(--text-3);
  cursor: not-allowed;
}

.chip .n {
  margin-left: 2px;
  font-size: 11px;
  opacity: 0.7;
}

/* 商家卡片没有真实 logo，用首字占位，比空白方块像样 */
.mark {
  width: 100%;
  aspect-ratio: 4 / 3;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: linear-gradient(135deg, #ffe6d6, #ffd0b5);
  color: var(--brand-dark);
  font-size: 34px;
  font-weight: 800;
}

.people {
  list-style: none;
  margin: 0;
  padding: 6px;
}

.person {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 10px;
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.15s;
}

.person + .person {
  border-top: 1px solid var(--line);
}

.person:hover {
  background: #fffaf5;
}

.avatar {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #ff8a5c, #ff5f2e);
  color: #fff;
  font-weight: 700;
  overflow: hidden;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.who {
  flex: 1;
  min-width: 0;
}

.nick {
  margin: 0;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.who p.tiny {
  margin: 0;
}

.mutual {
  padding: 0 6px;
  border-radius: 6px;
  background: var(--brand-soft);
  color: var(--brand-dark);
  font-size: 11px;
  font-weight: 600;
}
</style>
