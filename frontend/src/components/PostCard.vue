<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from '@/utils/feedback'
import { toggleLike, deletePost } from '@/api/post'
import { adminDeletePost } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import { timeAgo } from '@/utils/format'
import RatingStars from './RatingStars.vue'
import CommentDialog from './CommentDialog.vue'
import type { Post } from '@/types'

const props = defineProps<{ post: Post; detail?: boolean }>()
const emit = defineEmits<{
  (e: 'liked', payload: { id: number; liked: boolean; like_count: number }): void
  (e: 'commented', payload: { id: number; comment_count: number }): void
  (e: 'deleted', id: number): void
  /** 详情页用：点"评论"滚到下方评论区，而不是再弹一个框 */
  (e: 'comment'): void
}>()

const auth = useAuthStore()
const router = useRouter()

const busy = ref(false)
const commentOpen = ref(false)
const initial = computed(() => props.post.author.nickname.slice(0, 1))
const images = computed(() => props.post.images || [])

function onCommented(payload: { id: number; comment_count: number }): void {
  props.post.comment_count = payload.comment_count
  emit('commented', payload)
}

function goDish(): void {
  router.push({ name: 'dish', params: { id: props.post.dish.id } })
}

/** 列表里整张卡片可点进详情；详情页自己就是详情，不再嵌套跳转 */
function goDetail(): void {
  if (props.detail) return
  router.push({ name: 'post', params: { id: props.post.id } })
}

function onCommentClick(): void {
  if (props.detail) emit('comment')
  else commentOpen.value = true
}

function goAuthor(): void {
  router.push({ name: 'user', params: { id: props.post.author.id } })
}

async function handleLike(): Promise<void> {
  if (!auth.isLoggedIn) {
    ElMessage.warning('登录后才能点赞')
    router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  if (busy.value) return
  busy.value = true
  try {
    const result = await toggleLike(props.post.id)
    emit('liked', { id: props.post.id, liked: result.liked, like_count: result.like_count })
  } finally {
    busy.value = false
  }
}

async function handleDelete(): Promise<void> {
  try {
    // 自己的帖子走用户接口；管理员删别人的走后台应急接口
    if (isOwner.value) await deletePost(props.post.id)
    else await adminDeletePost(props.post.id)
    ElMessage.success('已删除')
    emit('deleted', props.post.id)
  } catch {
    // 拦截器已提示
  }
}

const isOwner = computed(() => auth.user?.id === props.post.author.id)
const canDelete = computed(() => isOwner.value || auth.isAdmin)
const deleteLabel = computed(() => (isOwner.value ? '删除这条' : '管理员删除'))
</script>

<template>
  <article class="postcard" :class="{ clickable: !detail }" @click="goDetail">
    <header class="head">
      <img
        v-if="post.author.avatar_url"
        :src="post.author.avatar_url"
        class="avatar avatar-img"
        alt=""
        @click.stop="goAuthor"
      />
      <span v-else class="avatar" @click.stop="goAuthor">{{ initial }}</span>
      <div class="who">
        <div class="name-row">
          <span class="name" @click.stop="goAuthor">{{ post.author.nickname }}</span>
          <span class="title-badge">{{ post.author.title_emoji }} {{ post.author.title_name }}</span>
        </div>
        <div class="tiny">{{ timeAgo(post.created_at) }}</div>
      </div>
      <span v-if="canDelete" @click.stop>
        <el-dropdown trigger="click">
          <span class="more">···</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="handleDelete">{{ deleteLabel }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </span>
    </header>

    <div class="dish-line" @click.stop="goDish">
      <span class="dish-name">🍽 {{ post.dish.name }}</span>
      <span class="tiny">{{ post.merchant.name }} · {{ post.merchant.canteen_name }}</span>
      <RatingStars v-if="post.author_score" :value="post.author_score" />
    </div>

    <p v-if="post.content" class="content">{{ post.content }}</p>

    <div v-if="images.length" class="thumbs" :class="[`n${images.length}`, { bigger: detail }]">
      <img v-for="(src, index) in images" :key="index" :src="src" :alt="post.dish.name" loading="lazy" />
    </div>

    <footer class="foot">
      <button class="action" :class="{ liked: post.is_liked }" :disabled="busy" @click.stop="handleLike">
        <span class="icon">{{ post.is_liked ? '❤️' : '🤍' }}</span>
        {{ post.like_count }}
      </button>
      <button class="action" @click.stop="onCommentClick">
        <span class="icon">💬</span>
        {{ post.comment_count }}
      </button>
      <span class="tiny dish-stat">菜品均分 {{ post.dish.avg_rating ? post.dish.avg_rating.toFixed(1) : '暂无' }} · {{ post.dish.rating_count }} 人评</span>
    </footer>

    <CommentDialog
      v-if="!detail"
      v-model="commentOpen"
      :post-id="post.id"
      :dish-name="post.dish.name"
      @commented="onCommented"
    />
  </article>
</template>

<style scoped>
.postcard {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px 18px;
  margin-bottom: 14px;
}

/* 列表里整卡可点进详情 */
.postcard.clickable {
  cursor: pointer;
  transition: box-shadow 0.15s ease;
}

.postcard.clickable:hover {
  box-shadow: 0 6px 20px rgba(84, 60, 40, 0.1);
}

.postcard.clickable:hover .content {
  color: var(--brand-dark);
}

.head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ffb27a, #ff6b35);
  color: #fff;
  display: grid;
  place-items: center;
  font-weight: 700;
  cursor: pointer;
  flex-shrink: 0;
}

.avatar-img {
  object-fit: cover;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px var(--line);
}

.who {
  flex: 1;
  min-width: 0;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.name {
  font-weight: 600;
  cursor: pointer;
}

.name:hover {
  color: var(--brand-dark);
}

.title-badge {
  font-size: 11px;
  background: var(--brand-soft);
  color: var(--brand-dark);
  padding: 1px 8px;
  border-radius: 999px;
  white-space: nowrap;
}

.more {
  color: var(--text-3);
  cursor: pointer;
  padding: 0 6px;
  font-weight: 700;
  letter-spacing: 1px;
}

.dish-line {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin: 12px 0 8px;
  padding: 8px 12px;
  background: var(--brand-soft);
  border-radius: 10px;
  cursor: pointer;
}

.dish-name {
  font-weight: 600;
  color: var(--brand-dark);
}

.content {
  margin: 8px 0;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text);
}

.thumbs {
  display: grid;
  gap: 6px;
  margin: 10px 0;
}

.thumbs.n1 {
  grid-template-columns: minmax(0, 320px);
}

.thumbs.n2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.thumbs.n3,
.thumbs.n4 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.thumbs img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  border-radius: 10px;
  background: #faf3ec;
}

/* 详情页图片更大：单图铺满，多图仍两列 */
.thumbs.bigger.n1 {
  grid-template-columns: minmax(0, 1fr);
}

.thumbs.bigger img {
  aspect-ratio: 3 / 2;
}

.foot {
  display: flex;
  align-items: center;
  gap: 16px;
  border-top: 1px solid var(--line);
  padding-top: 10px;
  margin-top: 10px;
}

.action {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: none;
  background: transparent;
  color: var(--text-2);
  font-size: 13px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 8px;
  font-family: inherit;
}

.action:hover {
  background: var(--brand-soft);
}

.action.liked {
  color: #e8452c;
  font-weight: 600;
}

.icon {
  font-size: 14px;
}

.dish-stat {
  margin-left: auto;
}
</style>
