<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from '@/utils/feedback'
import { adminCanteens, adminCreateCanteen, adminDeleteCanteen, adminUpdateCanteen } from '@/api/admin'
import ErrorState from '@/components/ErrorState.vue'
import AppSkeleton from '@/components/AppSkeleton.vue'
import type { Canteen } from '@/types'

const rows = ref<Canteen[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const error = ref<unknown>(null)

const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ name: '' })
const submitting = ref(false)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const data = await adminCanteens(page.value, pageSize)
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
  dialogVisible.value = true
}

function openEdit(row: Canteen): void {
  editingId.value = row.id
  form.name = row.name
  dialogVisible.value = true
}

async function submit(): Promise<void> {
  if (!form.name.trim()) {
    ElMessage.warning('食堂名称不能为空')
    return
  }
  submitting.value = true
  try {
    if (editingId.value) {
      await adminUpdateCanteen(editingId.value, form.name.trim())
      ElMessage.success('已保存')
    } else {
      await adminCreateCanteen(form.name.trim())
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    await load()
  } finally {
    submitting.value = false
  }
}

async function remove(row: Canteen): Promise<void> {
  try {
    await ElMessageBox.confirm(`确认删除「${row.name}」？`, '删除食堂', { type: 'warning' })
  } catch {
    return
  }
  try {
    await adminDeleteCanteen(row.id)
    ElMessage.success('已删除')
    await load()
  } catch {
    // 有商家时后端返回 40901，拦截器已提示
  }
}

onMounted(load)
</script>

<template>
  <div>
    <header class="head">
      <div>
        <h1>食堂管理</h1>
        <p class="tiny">删除前需保证该食堂下没有商家</p>
      </div>
      <el-button type="primary" round @click="openCreate">新建食堂</el-button>
    </header>

    <ErrorState v-if="error" :error="error" title="食堂列表没加载出来" @retry="load" />

    <AppSkeleton v-else-if="loading && !rows.length" variant="table" :count="6" />

    <el-table v-else v-loading="loading" :data="rows" class="table">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="食堂名称" min-width="200" />
      <el-table-column prop="merchant_count" label="商家数" width="110" />
      <el-table-column label="操作" width="160" align="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row as Canteen)">改名</el-button>
          <el-button link type="danger" @click="remove(row as Canteen)">删除</el-button>
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

    <el-dialog v-model="dialogVisible" :title="editingId ? '修改食堂' : '新建食堂'" width="420px">
      <el-form label-position="top">
        <el-form-item label="食堂名称">
          <el-input v-model="form.name" maxlength="100" show-word-limit @keyup.enter="submit" />
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
</style>
