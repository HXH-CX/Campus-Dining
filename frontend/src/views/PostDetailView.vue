<script setup lang="ts">
/**
 * 帖子详情页。
 *
 * 存在的意义：帖子原本只能"在列表里刷到"，没法分享、没法直达。
 * 这里把一条食评做成独立 URL（/posts/:id），评论也从弹窗改成页内，方便长评论展开。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from '@/utils/feedback'
import { addComment, deleteComment, fetchComments, fetchPost } from '@/api/post'
import { isNotFound } from '@/api/request'
import { useAuthStore } from '@/stores/auth'
import { timeAgo } from '@/utils/format'
import PostCard from '@/components/PostCard.vue'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import type { Comment, Post } from '@/types'

const props = defineProps<{ id: string }>()
const router = useRouter()
const auth = useAuthStore()

const post = ref<Post | null>(null)
const comments = ref<Comment[]>([])
const commentTotal = ref(0)
const commentPage = ref(1)
const pageSize = 20
const loading = ref(true)
const error = ref<unknown>(null)
const loadingMore = ref(false)
const draft = ref('')
const sending = ref(false)
const removing = ref<number | null>(null)
const commentBox = ref<HTMLElement | null>(null)

const postId = computed(() => Number(props.id))
const canSend = computed(() => draft.value.trim().length > 0 && !sending.value)

async function loadPost(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const [p, c] = await Promise.all([fetchPost(postId.value), fetchComments(postId.value, 1, pageSize)])
    post.value = p
    comments.value = c.items
    commentTotal.value = c.total
    commentPage.value = 1
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

async function loadMoreComments(): Promise<void> {
  if (loadingMore.value) return
  loadingMore.value = true
  try {
    const data = await fetchComments(postId.value, commentPage.value + 1, pageSize)
    comments.value = [...comments.value, ...data.items]
    commentPage.value += 1
  } catch {
    // 拦截器已提示，保留已有评论
  } finally {
    loadingMore.value = false
  }
}

async function submit(): Promise<void> {
  if (!auth.isLoggedIn) {
    ElMessage.warning('登录后才能评论')
    void router.push({ name: 'login', query: { redirect: `/posts/${postId.value}` } })
    return
  }
  const content = draft.value.trim()
  if (!content || sending.value) return
  sending.value = true
  try {
    const comment = await addComment(postId.value, content)
    comments.value.push(comment)
    commentTotal.value += 1
    draft.value = ''
    if (post.value) post.value.comment_count = commentTotal.value
    ElMessage.success('评论已发表')
  } catch {
    // 拦截器已提示，保留草稿
  } finally {
    sending.value = false
  }
}

/** 本人可删自己的，管理员可删任意 */
function canRemove(comment: Comment): boolean {
  return auth.user?.id === comment.author.id || auth.isAdmin
}

async function removeComment(comment: Comment): Promise<void> {
  if (removing.value) return
  removing.value = comment.id
  try {
    const result = await deleteComment(postId.value, comment.id)
    comments.value = comments.value.filter((item) => item.id !== comment.id)
    commentTotal.value = result.comment_count
    if (post.value) post.value.comment_count = result.comment_count
    ElMessage.success('评论已删除')
  } catch {
    // 拦截器已提示
  } finally {
    removing.value = null
  }
}

function onLiked(payload: { id: number; liked: boolean; like_count: number }): void {
  if (!post.value) return
  post.value.is_liked = payload.liked
  post.value.like_count = payload.like_count
}

function onDeleted(): void {
  ElMessage.success('已删除')
  void router.replace({ name: 'home' })
}

function scrollToComments(): void {
  commentBox.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/** 复制当前地址；非安全上下文（老浏览器/内网 http）下 clipboard 不可用，退回 execCommand */
async function share(): Promise<void> {
  const url = window.location.href
  try {
    await navigator.clipboard.writeText(url)
    ElMessage.success('链接已复制，去发给同学吧')
    return
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = url
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    try {
      document.execCommand('copy')
      ElMessage.success('链接已复制，去发给同学吧')
    } catch {
      ElMessage.warning(`复制失败，手动复制：${url}`)
    } finally {
      document.body.removeChild(textarea)
    }
  }
}

onMounted(loadPost)
watch(postId, loadPost)
</script>

<template>
  <div class="page narrow">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item :to="{ name: 'home' }">首页</el-breadcrumb-item>
      <el-breadcrumb-item v-if="post" :to="{ name: 'dish', params: { id: post.dish.id } }">
        {{ post.dish.name }}
      </el-breadcrumb-item>
      <el-breadcrumb-item>这条食评</el-breadcrumb-item>
    </el-breadcrumb>

    <AppSkeleton v-if="loading" variant="post" :count="1" />

    <ErrorState v-else-if="error" :error="error" title="这条食评没加载出来" @retry="loadPost" />

    <template v-else-if="post">
      <div class="bar">
        <el-button text @click="router.back()">← 返回</el-button>
        <el-button round @click="share">🔗 复制链接</el-button>
      </div>

      <PostCard :post="post" detail @liked="onLiked" @deleted="onDeleted" @comment="scrollToComments" />

      <section ref="commentBox" class="comments card">
        <h3 class="section-title">💬 评论 · {{ commentTotal }}</h3>

        <div class="editor">
          <el-input
            v-model="draft"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            :placeholder="auth.isLoggedIn ? '友善发言，说说你的看法' : '登录后可以参与讨论'"
            @keydown.ctrl.enter="submit"
          />
          <div class="send">
            <span class="tiny">Ctrl + Enter 快速发送</span>
            <el-button type="primary" round :loading="sending" :disabled="!canSend" @click="submit">
              {{ auth.isLoggedIn ? '发表' : '登录后发表' }}
            </el-button>
          </div>
        </div>

        <div v-if="!comments.length" class="empty">还没有评论，抢个沙发</div>

        <ul v-else class="list">
          <li v-for="comment in comments" :key="comment.id" class="item">
            <span class="avatar">{{ comment.author.nickname.slice(0, 1) }}</span>
            <div class="body">
              <div class="head">
                <router-link class="name" :to="{ name: 'user', params: { id: comment.author.id } }">
                  {{ comment.author.nickname }}
                </router-link>
                <span class="badge">{{ comment.author.title_emoji }} {{ comment.author.title_name }}</span>
                <span class="tiny time">{{ timeAgo(comment.created_at) }}</span>
                <button
                  v-if="canRemove(comment)"
                  class="del"
                  :disabled="removing === comment.id"
                  @click="removeComment(comment)"
                >
                  删除
                </button>
              </div>
              <p>{{ comment.content }}</p>
            </div>
          </li>
        </ul>

        <div v-if="comments.length < commentTotal" class="more">
          <el-button round :loading="loadingMore" @click="loadMoreComments">
            加载更多（{{ comments.length }}/{{ commentTotal }}）
          </el-button>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.narrow {
  max-width: 720px;
}

.bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 10px 0 12px;
}

.comments {
  margin-top: 6px;
}

.editor {
  padding-bottom: 14px;
  border-bottom: 1px solid var(--line);
}

.send {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.item {
  display: flex;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px dashed var(--line);
}

.item:last-child {
  border-bottom: none;
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ffb27a, #ff6b35);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}

.body {
  flex: 1;
  min-width: 0;
}

.head {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.name {
  font-weight: 600;
  font-size: 13px;
}

.name:hover {
  color: var(--brand-dark);
}

.badge {
  font-size: 11px;
  background: var(--brand-soft);
  color: var(--brand-dark);
  padding: 0 6px;
  border-radius: 999px;
}

.time {
  margin-left: auto;
}

.del {
  border: none;
  background: none;
  color: var(--text-3);
  font-size: 12px;
  cursor: pointer;
  padding: 0 2px;
  font-family: inherit;
}

.del:hover {
  color: #e8452c;
}

.del:disabled {
  opacity: 0.5;
  cursor: default;
}

p {
  margin: 4px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.empty {
  padding: 28px 0;
  text-align: center;
  color: var(--text-3);
}

.more {
  text-align: center;
  padding-top: 14px;
}
</style>
