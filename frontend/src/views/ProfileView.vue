<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { UploadRequestOptions, UploadUserFile } from 'element-plus'
import { ElMessage } from '@/utils/feedback'
import { fetchFollowers, fetchFollowing, fetchUser, fetchUserPosts, fetchUserRatings, toggleFollow, updateMe } from '@/api/user'
import { isNotFound } from '@/api/request'
import { uploadImage } from '@/api/upload'
import { useAuthStore } from '@/stores/auth'
import PostCard from '@/components/PostCard.vue'
import RatingStars from '@/components/RatingStars.vue'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import { formatDate, timeAgo } from '@/utils/format'
import type { Post, RatingItem, User, UserCard } from '@/types'

const props = defineProps<{ id?: string }>()
const router = useRouter()
const auth = useAuthStore()

const user = ref<User | null>(null)
const posts = ref<Post[]>([])
const ratings = ref<RatingItem[]>([])
const followers = ref<UserCard[]>([])
const following = ref<UserCard[]>([])
// 计数用后端返回的 total，而不是当前页条数
const totals = ref({ posts: 0, ratings: 0, followers: 0, following: 0 })
const tab = ref<'posts' | 'ratings' | 'following' | 'followers'>('posts')
const loading = ref(true)
const error = ref<unknown>(null)

const userId = computed(() => (props.id ? Number(props.id) : auth.user?.id || 0))
const isSelf = computed(() => auth.user?.id === user.value?.id)

async function load(): Promise<void> {
  if (!userId.value) return
  loading.value = true
  error.value = null
  try {
    const [u, p, r, frs, fing] = await Promise.all([
      fetchUser(userId.value),
      fetchUserPosts(userId.value, 1, 20),
      fetchUserRatings(userId.value, 1, 20),
      fetchFollowers(userId.value, 1, 30),
      fetchFollowing(userId.value, 1, 30),
    ])
    user.value = u
    posts.value = p.items
    ratings.value = r.items
    followers.value = frs.items
    following.value = fing.items
    totals.value = {
      posts: p.total,
      ratings: r.total,
      followers: frs.total,
      following: fing.total,
    }
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

watch(() => props.id, load, { immediate: true })

// /me 路由下依赖 auth.user 才能拿到 id
watch(
  () => auth.user?.id,
  (id) => {
    if (!props.id && id) void load()
  },
)

async function handleFollow(): Promise<void> {
  if (!user.value) return
  if (!auth.isLoggedIn) {
    router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  const result = await toggleFollow(user.value.id)
  ElMessage.success(result.following ? '已关注' : '已取消关注')
  await load()
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
}

// ---- 编辑资料
const editVisible = ref(false)
const saving = ref(false)
const editForm = reactive({ nickname: '', avatar_url: '' })
const avatarList = ref<UploadUserFile[]>([])

function openEdit(): void {
  if (!user.value) return
  editForm.nickname = user.value.nickname
  editForm.avatar_url = user.value.avatar_url || ''
  avatarList.value = user.value.avatar_url ? [{ name: 'avatar', url: user.value.avatar_url }] : []
  editVisible.value = true
}

function uploadAvatar(options: UploadRequestOptions): Promise<unknown> {
  return uploadImage(options.file as File)
    .then((result) => {
      editForm.avatar_url = result.url
      options.onSuccess(result)
    })
    .catch((error: Error) => {
      ElMessage.error(error.message || '上传失败')
      options.onError(error as never)
    })
}

function removeAvatar(): void {
  editForm.avatar_url = ''
  avatarList.value = []
}

async function saveProfile(): Promise<void> {
  if (!editForm.nickname.trim()) {
    ElMessage.warning('昵称不能为空')
    return
  }
  saving.value = true
  try {
    // 传 null 表示清空头像，后端用 model_fields_set 区分"没传"和"清空"
    user.value = await updateMe({
      nickname: editForm.nickname.trim(),
      avatar_url: editForm.avatar_url || null,
    })
    await auth.refreshMe()
    ElMessage.success('已保存')
    editVisible.value = false
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page">
    <AppSkeleton v-if="loading" variant="profile" />

    <ErrorState v-else-if="error" :error="error" title="用户主页没加载出来" @retry="load" />

    <template v-else-if="user">
      <header class="card profile">
        <img v-if="user.avatar_url" :src="user.avatar_url" class="avatar avatar-img" alt="" />
        <span v-else class="avatar">{{ user.nickname.slice(0, 1) }}</span>

        <div class="info">
          <div class="name-row">
            <h1>{{ user.nickname }}</h1>
            <span class="title-badge">{{ user.title_emoji }} {{ user.title_name }}</span>
            <span v-for="ach in user.achievements" :key="ach.code" class="ach" :title="ach.description">
              {{ ach.emoji }} {{ ach.name }}
            </span>
          </div>
          <div class="tiny">@{{ user.username }} · 加入于 {{ formatDate(user.created_at) }}</div>

          <div class="counts">
            <span><b>{{ user.follower_count }}</b> 粉丝</span>
            <span><b>{{ user.following_count }}</b> 关注</span>
            <span><b>{{ totals.posts }}</b> 帖子</span>
            <span><b>{{ totals.ratings }}</b> 评价</span>
          </div>
        </div>

        <div v-if="isSelf" class="self-actions">
          <el-button round @click="openEdit">编辑资料</el-button>
          <el-button type="primary" round @click="router.push({ name: 'create' })">写食评</el-button>
        </div>
        <el-button v-else type="primary" round @click="handleFollow">关注 TA</el-button>
      </header>

      <el-tabs v-model="tab" class="tabs">
        <el-tab-pane :label="`${isSelf ? '我' : 'TA'}的帖子 ${totals.posts}`" name="posts">
          <div v-if="!posts.length" class="card empty">还没有发过帖子</div>
          <PostCard v-for="post in posts" :key="post.id" :post="post" @liked="onLiked" @deleted="onDeleted" />
        </el-tab-pane>

        <el-tab-pane :label="`${isSelf ? '我' : 'TA'}的评价 ${totals.ratings}`" name="ratings">
          <div v-if="!ratings.length" class="card empty">还没有给菜品打过分</div>
          <div v-else class="card">
            <div
              v-for="item in ratings"
              :key="item.dish.id"
              class="rating-item"
              @click="router.push({ name: 'dish', params: { id: item.dish.id } })"
            >
              <img v-if="item.dish.image_url" :src="item.dish.image_url" class="thumb" :alt="item.dish.name" />
              <span v-else class="thumb img-fallback">{{ item.dish.name.slice(0, 1) }}</span>
              <div class="r-body">
                <div class="r-name">{{ item.dish.name }}</div>
                <div class="tiny">菜品均分 {{ item.dish.avg_rating ? item.dish.avg_rating.toFixed(1) : '暂无' }}</div>
              </div>
              <RatingStars :value="item.score" show-score />
              <span class="tiny">{{ timeAgo(item.updated_at) }}</span>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane :label="`关注 ${following.length}`" name="following">
          <div v-if="!following.length" class="card empty">还没有关注任何人</div>
          <div v-else class="card">
            <div
              v-for="item in following"
              :key="item.id"
              class="user-item"
              @click="router.push({ name: 'user', params: { id: item.id } })"
            >
              <span class="avatar sm">{{ item.nickname.slice(0, 1) }}</span>
              <span class="u-name">{{ item.nickname }}</span>
              <span class="title-badge">{{ item.title_emoji }} {{ item.title_name }}</span>
              <el-tag v-if="item.is_mutual" size="small" type="success" effect="light">互关</el-tag>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane :label="`粉丝 ${followers.length}`" name="followers">
          <div v-if="!followers.length" class="card empty">还没有粉丝</div>
          <div v-else class="card">
            <div
              v-for="item in followers"
              :key="item.id"
              class="user-item"
              @click="router.push({ name: 'user', params: { id: item.id } })"
            >
              <span class="avatar sm">{{ item.nickname.slice(0, 1) }}</span>
              <span class="u-name">{{ item.nickname }}</span>
              <span class="title-badge">{{ item.title_emoji }} {{ item.title_name }}</span>
              <el-tag v-if="item.is_mutual" size="small" type="success" effect="light">互关</el-tag>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <el-dialog v-model="editVisible" title="编辑资料" width="420px">
        <el-form label-position="top">
          <el-form-item label="头像">
            <el-upload
              v-model:file-list="avatarList"
              list-type="picture-card"
              :limit="1"
              :http-request="uploadAvatar"
              :on-remove="removeAvatar"
              accept="image/jpeg,image/png,image/webp"
            >
              <span class="plus">＋</span>
            </el-upload>
          </el-form-item>
          <el-form-item label="昵称">
            <el-input v-model="editForm.nickname" maxlength="50" show-word-limit @keyup.enter="saveProfile" />
          </el-form-item>
          <p class="tiny">用户名 @{{ user.username }} 是登录凭据，不能修改；称号由发帖和获赞自动计算。</p>
        </el-form>
        <template #footer>
          <el-button round @click="editVisible = false">取消</el-button>
          <el-button type="primary" round :loading="saving" @click="saveProfile">保存</el-button>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<style scoped>
.profile {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 8px;
}

.avatar {
  width: 68px;
  height: 68px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ffb27a, #ff6b35);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 26px;
  font-weight: 700;
  flex-shrink: 0;
}

.avatar.sm {
  width: 32px;
  height: 32px;
  font-size: 13px;
}

.avatar-img {
  object-fit: cover;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px var(--line);
}

.info {
  flex: 1;
  min-width: 0;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

h1 {
  margin: 0;
  font-size: 20px;
}

.title-badge {
  font-size: 11px;
  background: var(--brand-soft);
  color: var(--brand-dark);
  padding: 1px 8px;
  border-radius: 999px;
}

.ach {
  font-size: 11px;
  background: #eef9e6;
  color: #4f8a2f;
  padding: 1px 8px;
  border-radius: 999px;
}

.counts {
  display: flex;
  gap: 16px;
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-2);
}

.counts b {
  color: var(--text);
}

.tabs {
  margin-top: 12px;
}

.rating-item,
.user-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px dashed var(--line);
  cursor: pointer;
}

.rating-item:last-child,
.user-item:last-child {
  border-bottom: none;
}

.rating-item:hover .r-name,
.user-item:hover .u-name {
  color: var(--brand-dark);
}

.thumb {
  width: 46px;
  height: 46px;
  border-radius: 10px;
  object-fit: cover;
  font-size: 18px;
}

.r-body {
  flex: 1;
}

.r-name {
  font-weight: 600;
}

.u-name {
  font-weight: 600;
  flex: 1;
}

.self-actions {
  display: flex;
  gap: 8px;
}

.plus {
  font-size: 20px;
  color: var(--text-3);
}
</style>
