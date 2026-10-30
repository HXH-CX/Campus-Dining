<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from '@/utils/feedback'
import { addComment, fetchComments } from '@/api/post'
import AppSkeleton from '@/components/AppSkeleton.vue'
import { useAuthStore } from '@/stores/auth'
import { timeAgo } from '@/utils/format'
import type { Comment } from '@/types'

const props = defineProps<{ modelValue: boolean; postId: number; dishName: string }>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'commented', payload: { id: number; comment_count: number }): void
}>()

const auth = useAuthStore()
const router = useRouter()

const comments = ref<Comment[]>([])
const total = ref(0)
const loading = ref(false)
const draft = ref('')
const sending = ref(false)

async function load(): Promise<void> {
  loading.value = true
  try {
    const data = await fetchComments(props.postId, 1, 50)
    comments.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) void load()
  },
)

async function submit(): Promise<void> {
  if (!auth.isLoggedIn) {
    ElMessage.warning('登录后才能评论')
    emit('update:modelValue', false)
    router.push({ name: 'login', query: { redirect: `/dishes/${router.currentRoute.value.params.id}` } })
    return
  }
  const content = draft.value.trim()
  if (!content) {
    ElMessage.warning('说点什么吧')
    return
  }
  sending.value = true
  try {
    const comment = await addComment(props.postId, content)
    comments.value.push(comment)
    total.value += 1
    draft.value = ''
    emit('commented', { id: props.postId, comment_count: total.value })
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="`评论 · ${dishName}`"
    width="520px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <AppSkeleton v-if="loading" variant="row" :count="3" />

    <div v-else-if="!comments.length" class="empty">还没有评论，抢个沙发</div>

    <ul v-else class="list">
      <li v-for="comment in comments" :key="comment.id" class="item">
        <span class="avatar">{{ comment.author.nickname.slice(0, 1) }}</span>
        <div class="body">
          <div class="head">
            <span class="name">{{ comment.author.nickname }}</span>
            <span class="badge">{{ comment.author.title_emoji }} {{ comment.author.title_name }}</span>
            <span class="tiny time">{{ timeAgo(comment.created_at) }}</span>
          </div>
          <p>{{ comment.content }}</p>
        </div>
      </li>
    </ul>

    <div class="editor">
      <el-input
        v-model="draft"
        type="textarea"
        :rows="3"
        maxlength="500"
        show-word-limit
        placeholder="友善发言，说说你的看法"
      />
      <div class="send">
        <el-button type="primary" :loading="sending" @click="submit">发表</el-button>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 340px;
  overflow-y: auto;
}

.item {
  display: flex;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px dashed var(--line);
}

.avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ffb27a, #ff6b35);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 12px;
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

p {
  margin: 4px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.empty {
  padding: 28px 0;
}

.editor {
  margin-top: 14px;
  border-top: 1px solid var(--line);
  padding-top: 14px;
}

.send {
  margin-top: 10px;
  text-align: right;
}
</style>
