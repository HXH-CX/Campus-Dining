<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchCanteens } from '@/api/catalog'
import AppSkeleton from '@/components/AppSkeleton.vue'
import ErrorState from '@/components/ErrorState.vue'
import type { Canteen } from '@/types'

const router = useRouter()
const canteens = ref<Canteen[]>([])
const loading = ref(true)
const error = ref<unknown>(null)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    canteens.value = await fetchCanteens()
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1 class="page-title">食堂导航</h1>
    <p class="muted sub">挑一个食堂，看看里面有哪些商家</p>

    <AppSkeleton v-if="loading" variant="card" :count="4" />

    <ErrorState v-else-if="error" :error="error" title="食堂列表没加载出来" @retry="load" />

    <div v-else-if="!canteens.length" class="card empty">还没有录入食堂，等管理员开张</div>

    <div v-else class="grid">
      <div
        v-for="canteen in canteens"
        :key="canteen.id"
        class="card canteen"
        @click="router.push({ name: 'canteen-merchants', params: { id: canteen.id } })"
      >
        <div class="icon">🏫</div>
        <div>
          <div class="name">{{ canteen.name }}</div>
          <div class="tiny">{{ canteen.merchant_count }} 个商家</div>
        </div>
        <span class="arrow">→</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title {
  margin: 0 0 4px;
  font-size: 22px;
}

.sub {
  margin: 0 0 20px;
  font-size: 13px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}

.canteen {
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.canteen:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(120, 80, 50, 0.12);
}

.icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--brand-soft);
  display: grid;
  place-items: center;
  font-size: 22px;
}

.name {
  font-weight: 700;
  font-size: 16px;
}

.arrow {
  margin-left: auto;
  color: var(--text-3);
}
</style>
