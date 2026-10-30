<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from '@/utils/feedback'
import {
  adminCreateMerchant,
  adminDeleteMerchant,
  adminMerchants,
  adminUpdateMerchant,
} from '@/api/admin'
import { fetchCanteens } from '@/api/catalog'
import ErrorState from '@/components/ErrorState.vue'
import AppSkeleton from '@/components/AppSkeleton.vue'
import type { Canteen, Merchant } from '@/types'

const rows = ref<Merchant[]>([])
const canteens = ref<Canteen[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const error = ref<unknown>(null)

const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<{ name: string; canteen_id: number | null }>({ name: '', canteen_id: null })
const submitting = ref(false)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const data = await adminMerchants(page.value, pageSize)
    rows.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  editingId.value = null
  form.name = ''
  form.canteen_id = canteens.value[0]?.id ?? null
  dialogVisible.value = true
}

function openEdit(row: Merchant): void {
  editingId.value = row.id
  form.name = row.name
  form.canteen_id = row.canteen_id
  dialogVisible.value = true
}

async function submit(): Promise<void> {
  if (!form.name.trim()) {
    ElMessage.warning('商家名称不能为空')
    return
  }
  if (!form.canteen_id) {
    ElMessage.warning('请选择所属食堂')
    return
  }
  submitting.value = true
  try {
    if (editingId.value) {
      await adminUpdateMerchant(editingId.value, { name: form.name.trim(), canteen_id: form.canteen_id })
      ElMessage.success('已保存')
    } else {
      await adminCreateMerchant(form.name.trim(), form.canteen_id)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    await load()
  } finally {
    submitting.value = false
  }
}

async function remove(row: Merchant): Promise<void> {
  try {
    await ElMessageBox.confirm(`确认删除「${row.name}」？`, '删除商家', { type: 'warning' })
  } catch {
    return
  }
  try {
    await adminDeleteMerchant(row.id)
    ElMessage.success('已删除')
    await load()
  } catch {
    // 有菜品时返回 40901
  }
}

onMounted(async () => {
  try {
    canteens.value = await fetchCanteens()
  } catch {
    // 食堂列表只用于下拉选择，失败不影响列表展示，拦截器已提示
  }
  await load()
})
</script>

<template>
  <div>
    <header class="head">
      <div>
        <h1>商家管理</h1>
        <p class="tiny">删除前需先清空该商家下的菜品</p>
      </div>
      <el-button type="primary" round @click="openCreate">新建商家</el-button>
    </header>

    <ErrorState v-if="error" :error="error" title="商家列表没加载出来" @retry="load" />

    <AppSkeleton v-else-if="loading && !rows.length" variant="table" :count="6" />

    <el-table v-else v-loading="loading" :data="rows" class="table">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="商家" min-width="180" />
      <el-table-column prop="canteen_name" label="所属食堂" width="140" />
      <el-table-column label="综合评分" width="110">
        <template #default="{ row }">
          <span class="score">{{ row.overall_rating ? row.overall_rating.toFixed(1) : '暂无' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="dish_count" label="菜品数" width="90" />
      <el-table-column label="操作" width="160" align="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row as Merchant)">编辑</el-button>
          <el-button link type="danger" @click="remove(row as Merchant)">删除</el-button>
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

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑商家' : '新建商家'" width="440px">
      <el-form label-position="top">
        <el-form-item label="商家名称">
          <el-input v-model="form.name" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="所属食堂">
          <el-select v-model="form.canteen_id" placeholder="选择食堂" class="full">
            <el-option v-for="item in canteens" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
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

.pager {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}

.score {
  color: var(--brand-dark);
  font-weight: 700;
}

.full {
  width: 100%;
}
</style>
