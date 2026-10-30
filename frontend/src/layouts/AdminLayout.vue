<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const menus = [
  { name: 'admin-canteens', label: '食堂管理', icon: '🏫' },
  { name: 'admin-merchants', label: '商家管理', icon: '🏪' },
  { name: 'admin-dishes', label: '菜品管理', icon: '🍲' },
  { name: 'admin-posts', label: '帖子管理', icon: '📝' },
]

const activeName = computed(() => route.name as string)
</script>

<template>
  <div class="admin">
    <aside class="side">
      <div class="side-brand">🍜 校园食光</div>
      <div class="side-sub">管理后台</div>

      <nav class="side-nav">
        <button
          v-for="menu in menus"
          :key="menu.name"
          class="side-link"
          :class="{ active: activeName === menu.name }"
          @click="router.push({ name: menu.name })"
        >
          <span>{{ menu.icon }}</span>
          {{ menu.label }}
        </button>
      </nav>

      <div class="side-foot">
        <div class="who">{{ auth.displayName }}</div>
        <el-button text size="small" @click="router.push({ name: 'home' })">← 返回前台</el-button>
      </div>
    </aside>

    <section class="main">
      <router-view />
    </section>
  </div>
</template>

<style scoped>
.admin {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 208px 1fr;
  background: var(--bg);
}

.side {
  background: #fff;
  border-right: 1px solid var(--line);
  padding: 22px 14px;
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: 100vh;
}

.side-brand {
  font-weight: 800;
  font-size: 16px;
}

.side-sub {
  font-size: 12px;
  color: var(--text-3);
  margin: 2px 0 22px;
  letter-spacing: 2px;
}

.side-nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.side-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: none;
  background: transparent;
  border-radius: 10px;
  font-size: 14px;
  color: var(--text-2);
  cursor: pointer;
  text-align: left;
  font-family: inherit;
}

.side-link:hover {
  background: var(--brand-soft);
}

.side-link.active {
  background: var(--brand-soft);
  color: var(--brand-dark);
  font-weight: 600;
}

.side-foot {
  border-top: 1px solid var(--line);
  padding-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.who {
  font-size: 12px;
  color: var(--text-3);
}

.main {
  padding: 26px 30px 60px;
  max-width: 1100px;
  width: 100%;
}
</style>
