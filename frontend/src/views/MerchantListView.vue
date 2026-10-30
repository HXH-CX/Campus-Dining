<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchCanteenMerchants, fetchCanteens } from '@/api/catalog'
import { isNotFound } from '@/api/request'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import type { Canteen, Merchant } from '@/types'

const props = defineProps<{ id: string }>()
const router = useRouter()

const merchants = ref<Merchant[]>([])
const canteen = ref<Canteen | null>(null)
const loading = ref(true)
const error = ref<unknown>(null)

const canteenId = computed(() => Number(props.id))

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const [list, canteens] = await Promise.all([fetchCanteenMerchants(canteenId.value), fetchCanteens()])
    merchants.value = list
    canteen.value = canteens.find((item) => item.id === canteenId.value) || null
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

onMounted(load)
watch(canteenId, load)
</script>

<template>
  <div class="page">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item :to="{ name: 'canteens' }">食堂导航</el-breadcrumb-item>
      <el-breadcrumb-item>{{ canteen?.name || '加载中' }}</el-breadcrumb-item>
    </el-breadcrumb>

    <h1 class="page-title">{{ canteen?.name }}</h1>
    <p class="muted sub">共 {{ merchants.length }} 个商家</p>

    <AppSkeleton v-if="loading" variant="card" :count="6" />

    <ErrorState v-else-if="error" :error="error" title="商家列表没加载出来" @retry="load" />

    <div v-else-if="!merchants.length" class="card empty">这个食堂还没有录入商家</div>

    <div v-else class="grid">
      <div
        v-for="merchant in merchants"
        :key="merchant.id"
        class="card merchant"
        @click="router.push({ name: 'merchant', params: { id: merchant.id } })"
      >
        <div class="top">
          <span class="name">{{ merchant.name }}</span>
          <span class="score">{{ merchant.overall_rating ? merchant.overall_rating.toFixed(1) : '暂无' }}</span>
        </div>
        <div class="tiny">{{ merchant.dish_count }} 道菜 · 综合评分</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title {
  margin: 14px 0 4px;
  font-size: 22px;
}

.sub {
  margin: 0 0 20px;
  font-size: 13px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}

.merchant {
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.merchant:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(120, 80, 50, 0.12);
}

.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.name {
  font-weight: 700;
  font-size: 16px;
}

.score {
  color: var(--brand-dark);
  font-weight: 800;
  font-size: 18px;
}
</style>
