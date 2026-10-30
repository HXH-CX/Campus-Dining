<script setup lang="ts">
/**
 * 帖子管理（应急手段，不是审核流程）。
 *
 * PRD 2.2 定稿：MVP 不做审核/举报/封禁，只保留管理员"发现明显违规内容时直接删帖"这一个口子，
 * 所以这里只有列表 + 删除，没有状态流转。删除会连带评论与点赞（外键级联），
 * 但不删评分——评分属于用户对菜品的看法，和帖子是两件事。
 */
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from '@/utils/feedback'
import { adminDeletePost, adminPosts } from '@/api/admin'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import { timeAgo } from '@/utils/format'
import type { Post } from '@/types'

const rows = ref<Post[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const keyword = ref('')
const loading = ref(false)
const error = ref<unknown>(null)
const deletingId = ref<number | null>(null)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const data = await adminPosts(page.value, pageSize, keyword.value.trim() || undefined)
    rows.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

function doSearch(): void {
  page.value = 1
  void load()
}

function resetSearch(): void {
  keyword.value = ''
  page.value = 1
  void load()
}

async function remove(row: Post): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `将删除「${row.author.nickname}」对「${row.dish.name}」的这条食评，同时清空它的 ${row.comment_count} 条评论和 ${row.like_count} 个赞。\n\n该评分记录会保留在菜品里，删除后无法恢复。`,
      '应急删除帖子',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '再想想' },
    )
  } catch {
    return
  }

  deletingId.value = row.id
  try {
    await adminDeletePost(row.id)
    ElMessage.success('已删除')
    // 删掉当前页最后一条时回退一页，避免停在空页
    if (rows.value.length === 1 && page.value > 1) page.value -= 1
    await load()
  } catch {
    // 拦截器已提示
  } finally {
    deletingId.value = null
  }
}

function openDish(row: Post): void {
  const url = `/dishes/${row.dish.id}`
  window.open(url, '_blank')
}

function summary(content: string | null): string {
  if (!content) return '（无文字，仅图片）'
  return content.length > 60 ? `${content.slice(0, 60)}…` : content
}

onMounted(load)
</script>

<template>
  <div>
    <header class="head">
      <div>
        <h1>帖子管理</h1>
        <p class="tiny">仅用于处理明显违规内容，删除不可恢复；日常不干预用户发言</p>
      </div>
      <div class="search">
        <el-input
          v-model="keyword"
          placeholder="搜帖子内容"
          clearable
          style="width: 220px"
          @keyup.enter="doSearch"
          @clear="resetSearch"
        />
        <el-button type="primary" round @click="doSearch">查询</el-button>
      </div>
    </header>

    <AppSkeleton v-if="loading && !rows.length" variant="table" :count="6" />

    <ErrorState v-else-if="error" :error="error" title="帖子列表没加载出来" @retry="load" />

    <template v-else>
      <el-table v-loading="loading" :data="rows" class="table" row-key="id">
        <el-table-column label="内容" min-width="300">
          <template #default="{ row }">
            <div class="cell">
              <img v-if="row.images?.length" :src="row.images[0]" class="thumb" alt="" />
              <img v-else-if="row.dish.image_url" :src="row.dish.image_url" class="thumb" alt="" />
              <div v-else class="thumb fallback">{{ row.dish.name.slice(0, 1) }}</div>
              <div class="text">
                <div class="content">{{ summary(row.content) }}</div>
                <div class="tiny">{{ row.images?.length ? `${row.images.length} 张图 · ` : '' }}ID {{ row.id }}</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="作者" width="140">
          <template #default="{ row }">
            <div class="author">
              <span class="title">{{ row.author.title_emoji }}</span>
              <span>{{ row.author.nickname }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="菜品 / 商家" min-width="180">
          <template #default="{ row }">
            <div>{{ row.dish.name }}</div>
            <div class="tiny">{{ row.merchant.name }} · {{ row.merchant.canteen_name }}</div>
          </template>
        </el-table-column>

        <el-table-column label="作者评分" width="96" align="center">
          <template #default="{ row }">
            <span>{{ row.author_score ? `${row.author_score} 星` : '—' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="互动" width="110" align="center">
          <template #default="{ row }">
            <span class="tiny">{{ row.like_count }} 赞 · {{ row.comment_count }} 评</span>
          </template>
        </el-table-column>

        <el-table-column label="发布" width="110">
          <template #default="{ row }">
            <span class="tiny">{{ timeAgo(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="140" align="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDish(row as Post)">查看菜品</el-button>
            <el-button link type="danger" :loading="deletingId === row.id" @click="remove(row as Post)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!rows.length" class="card empty">没有匹配的帖子</div>

      <div class="pager">
        <span class="tiny">共 {{ total }} 条</span>
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="load"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

h1 {
  margin: 0;
  font-size: 20px;
}

.tiny {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--text-3);
}

.search {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.table {
  border-radius: var(--radius);
  overflow: hidden;
}

.cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.thumb {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  object-fit: cover;
  flex-shrink: 0;
  background: var(--brand-soft);
}

.thumb.fallback {
  display: grid;
  place-items: center;
  font-weight: 700;
  color: var(--brand-dark);
}

.text {
  min-width: 0;
}

.content {
  font-size: 13px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.author {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}

.pager {
  margin-top: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
