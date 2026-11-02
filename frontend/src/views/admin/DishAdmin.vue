<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { UploadRequestOptions, UploadUserFile } from 'element-plus'
import { ElMessage, ElMessageBox } from '@/utils/feedback'
import {
  adminCreateDish,
  adminDeleteDish,
  adminDishes,
  adminMerchants,
  adminSetDishAvailability,
  adminUpdateDish,
} from '@/api/admin'
import { fetchDishTags } from '@/api/catalog'
import { uploadImage } from '@/api/upload'
import ErrorState from '@/components/ErrorState.vue'
import AppSkeleton from '@/components/AppSkeleton.vue'
import type { Dish, DishTag, Merchant } from '@/types'

const rows = ref<Dish[]>([])
const merchants = ref<Merchant[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const error = ref<unknown>(null)

const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<{
  name: string
  merchant_id: number | null
  image_url: string | null
  tags: string[]
}>({
  name: '',
  merchant_id: null,
  image_url: null,
  tags: [],
})
/** 标签白名单（后端定），0 道菜的也列出来——管理员可能正要给某道菜补上 */
const tagOptions = ref<DishTag[]>([])
const fileList = ref<UploadUserFile[]>([])
const submitting = ref(false)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const data = await adminDishes(page.value, pageSize)
    rows.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

/** 最多 4 个（与后端 MAX_TAGS_PER_DISH 一致），点满再点新标签给提示而不是静默忽略 */
const MAX_TAGS = 4

function toggleTag(name: string): void {
  const index = form.tags.indexOf(name)
  if (index >= 0) {
    form.tags.splice(index, 1)
    return
  }
  if (form.tags.length >= MAX_TAGS) {
    ElMessage.warning(`最多选 ${MAX_TAGS} 个标签`)
    return
  }
  form.tags.push(name)
}

function openCreate(): void {
  editingId.value = null
  form.name = ''
  form.merchant_id = merchants.value[0]?.id ?? null
  form.image_url = null
  form.tags = []
  fileList.value = []
  dialogVisible.value = true
}

function openEdit(row: Dish): void {
  editingId.value = row.id
  form.name = row.name
  form.merchant_id = row.merchant_id
  form.image_url = row.image_url
  // 复制一份，避免在弹窗里改到表格行上的原数组
  form.tags = [...(row.tags ?? [])]
  fileList.value = row.image_url ? [{ name: 'cover', url: row.image_url }] : []
  dialogVisible.value = true
}

function customUpload(options: UploadRequestOptions): Promise<unknown> {
  // 封面在列表里显示 ~200px，详情页 ~600px
  return uploadImage(options.file as File, { maxEdge: 1200 })
    .then((result) => {
      form.image_url = result.url
      options.onSuccess(result)
    })
    .catch((error: Error) => {
      ElMessage.error(error.message || '上传失败')
      options.onError(error as never)
    })
}

function onRemove(): void {
  form.image_url = null
}

async function submit(): Promise<void> {
  if (!form.name.trim()) {
    ElMessage.warning('菜品名称不能为空')
    return
  }
  if (!form.merchant_id) {
    ElMessage.warning('请选择所属商家')
    return
  }
  submitting.value = true
  try {
    if (editingId.value) {
      await adminUpdateDish(editingId.value, {
        name: form.name.trim(),
        merchant_id: form.merchant_id,
        image_url: form.image_url,
        tags: form.tags,
      })
      ElMessage.success('已保存')
    } else {
      await adminCreateDish({
        name: form.name.trim(),
        merchant_id: form.merchant_id,
        image_url: form.image_url,
        tags: form.tags,
      })
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    await load()
  } finally {
    submitting.value = false
  }
}

async function toggleAvailability(row: Dish): Promise<void> {
  const result = await adminSetDishAvailability(row.id, !row.is_available)
  row.is_available = result.is_available
  ElMessage.success(result.is_available ? '已上架' : '已下架')
}

async function remove(row: Dish): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认删除「${row.name}」？已有帖子或评分引用的菜品无法删除，只能下架。`,
      '删除菜品',
      { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await adminDeleteDish(row.id)
    ElMessage.success('已删除')
    await load()
  } catch {
    // 被引用时返回 40901
  }
}

onMounted(async () => {
  try {
    const data = await adminMerchants(1, 100)
    merchants.value = data.items
  } catch {
    // 商家下拉是新建菜品时才需要的，失败不阻塞列表
  }
  try {
    tagOptions.value = await fetchDishTags()
  } catch {
    // 标签选择器同样只影响弹窗，失败不阻塞列表
  }
  await load()
})
</script>

<template>
  <div>
    <header class="head">
      <div>
        <h1>菜品管理</h1>
        <p class="tiny">被帖子或评分引用过的菜品只能下架，不能删除</p>
      </div>
      <el-button type="primary" round @click="openCreate">新建菜品</el-button>
    </header>

    <ErrorState v-if="error" :error="error" title="菜品列表没加载出来" @retry="load" />

    <AppSkeleton v-else-if="loading && !rows.length" variant="table" :count="6" />

    <el-table v-else v-loading="loading" :data="rows" class="table">
      <el-table-column label="菜品" min-width="220">
        <template #default="{ row }">
          <div class="dish-cell">
            <img v-if="row.image_url" :src="row.image_url" class="thumb" :alt="row.name" />
            <span v-else class="thumb img-fallback">{{ row.name.slice(0, 1) }}</span>
            <div>
              <div class="name">{{ row.name }}</div>
              <div class="tiny">{{ row.merchant_name }} · {{ row.canteen_name }}</div>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="均分" width="90">
        <template #default="{ row }">
          <span class="score">{{ row.avg_rating ? row.avg_rating.toFixed(1) : '暂无' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="rating_count" label="评价数" width="90" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_available ? 'success' : 'info'" size="small" effect="light">
            {{ row.is_available ? '上架' : '已下架' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" align="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row as Dish)">编辑</el-button>
          <el-button link type="warning" @click="toggleAvailability(row as Dish)">
            {{ row.is_available ? '下架' : '上架' }}
          </el-button>
          <el-button link type="danger" @click="remove(row as Dish)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!error && rows.length" class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, total"
        @current-change="load"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑菜品' : '新建菜品'" width="480px">
      <el-form label-position="top">
        <el-form-item label="菜品名称">
          <el-input v-model="form.name" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="所属商家">
          <el-select v-model="form.merchant_id" placeholder="选择商家" filterable class="full">
            <el-option
              v-for="item in merchants"
              :key="item.id"
              :label="`${item.name}（${item.canteen_name}）`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="口味标签">
          <div class="tag-picker">
            <button
              v-for="item in tagOptions"
              :key="item.name"
              type="button"
              class="pick"
              :class="{ on: form.tags.includes(item.name) }"
              @click="toggleTag(item.name)"
            >
              {{ item.emoji }} {{ item.name }}
            </button>
          </div>
          <div class="hint">可不选，最多 4 个。学生搜「辣」「面食」时就靠它们</div>
        </el-form-item>
        <el-form-item label="菜品封面">
          <el-upload
            v-model:file-list="fileList"
            list-type="picture-card"
            :limit="1"
            :http-request="customUpload"
            :on-remove="onRemove"
            accept="image/jpeg,image/png,image/webp"
          >
            <span class="plus">＋</span>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button round @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" round :loading="submitting" @click="submit">保存</el-button>
      </template>
    </el-dialog>
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

.table {
  border-radius: var(--radius);
  overflow: hidden;
}

/* 标签选择：一排可点的小胶囊，比 el-checkbox 紧凑，且能一眼看清已选 */
.tag-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pick {
  padding: 4px 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  color: var(--text-2);
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.pick:hover {
  border-color: var(--brand);
  color: var(--brand-dark);
}

.pick.on {
  border-color: var(--brand);
  background: var(--brand);
  color: #fff;
  font-weight: 600;
}

.hint {
  width: 100%;
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-3);
}

.pager {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}

.dish-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.thumb {
  width: 42px;
  height: 42px;
  border-radius: 9px;
  object-fit: cover;
  font-size: 16px;
  flex-shrink: 0;
}

.name {
  font-weight: 600;
}

.score {
  color: var(--brand-dark);
  font-weight: 700;
}

.full {
  width: 100%;
}

.plus {
  font-size: 20px;
  color: var(--text-3);
}
</style>
