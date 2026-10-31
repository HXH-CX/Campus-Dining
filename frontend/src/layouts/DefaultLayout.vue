<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from '@/utils/feedback'

const auth = useAuthStore()
const router = useRouter()

const initial = computed(() => auth.user?.nickname?.slice(0, 1) || '食')
const quickKeyword = ref('')

function goSearch(): void {
  const kw = quickKeyword.value.trim()
  router.push({ name: 'search', query: kw ? { kw } : {} })
}

function handleCommand(command: string): void {
  if (command === 'logout') {
    auth.logout()
    ElMessage.success('已退出登录')
    router.push({ name: 'home' })
    return
  }
  if (command === 'me') {
    router.push({ name: 'me' })
    return
  }
  if (command === 'admin') {
    router.push({ name: 'admin-dashboard' })
  }
}
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <div class="topbar-inner">
        <router-link :to="{ name: 'home' }" class="brand">
          <span class="brand-mark">🍜</span>
          <span class="brand-text">校园食光</span>
        </router-link>

        <nav class="nav">
          <router-link :to="{ name: 'home' }" class="nav-link" exact-active-class="active">首页</router-link>
          <router-link :to="{ name: 'canteens' }" class="nav-link" active-class="active">食堂导航</router-link>
          <router-link :to="{ name: 'create' }" class="nav-link" active-class="active">发帖</router-link>
        </nav>

        <div class="quick-search hide-sm">
          <el-input
            v-model="quickKeyword"
            size="small"
            placeholder="搜菜名 / 商家"
            clearable
            @keyup.enter="goSearch"
            @clear="quickKeyword = ''"
          >
            <template #prefix>🔍</template>
          </el-input>
        </div>

        <div class="actions">
          <template v-if="auth.isLoggedIn">
            <el-button type="primary" round @click="router.push({ name: 'create' })">写食评</el-button>
            <el-dropdown trigger="click" @command="handleCommand">
              <div class="me">
                <span class="avatar">{{ initial }}</span>
                <span class="me-name hide-sm">{{ auth.displayName }}</span>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="me">个人中心</el-dropdown-item>
                  <el-dropdown-item v-if="auth.isAdmin" command="admin">管理后台</el-dropdown-item>
                  <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <router-link :to="{ name: 'login' }">
              <el-button round>登录</el-button>
            </router-link>
            <router-link :to="{ name: 'register' }">
              <el-button type="primary" round>注册</el-button>
            </router-link>
          </template>
        </div>
      </div>
    </header>

    <main>
      <router-view />
    </main>

    <footer class="footer">
      <span>校园食光 · 今天吃什么，交给同学们决定</span>
    </footer>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--line);
}

.topbar-inner {
  max-width: 1080px;
  margin: 0 auto;
  height: 60px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  gap: 24px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 800;
  font-size: 17px;
  letter-spacing: 0.5px;
  flex-shrink: 0;
  white-space: nowrap;
}

.brand-mark {
  font-size: 22px;
}

.nav {
  display: flex;
  gap: 4px;
  flex: 1;
}

.nav-link {
  padding: 6px 14px;
  border-radius: 999px;
  color: var(--text-2);
  font-weight: 500;
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}

.nav-link:hover {
  background: var(--brand-soft);
  color: var(--brand-dark);
}

.nav-link.active {
  background: var(--brand-soft);
  color: var(--brand-dark);
  font-weight: 600;
}

.actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.quick-search {
  width: 180px;
}

.me {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px 4px 4px;
  border-radius: 999px;
}

.me:hover {
  background: var(--brand-soft);
}

.avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ff8a5c, #ff5f2e);
  color: #fff;
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 13px;
}

.me-name {
  font-size: 13px;
  color: var(--text-2);
  max-width: 96px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

main {
  flex: 1;
}

.footer {
  border-top: 1px solid var(--line);
  padding: 20px 16px 28px;
  text-align: center;
  color: var(--text-3);
  font-size: 12px;
}

/*
 * 窄屏：品牌和导航挤在一行会把「食堂导航」挤成竖排（每个字一行）。
 * 这里让导航整体换到第二行并允许横向滚动，比缩字号更耐看。
 */
@media (max-width: 560px) {
  .topbar-inner {
    height: auto;
    padding: 8px 12px;
    gap: 8px;
    flex-wrap: wrap;
  }

  .nav {
    order: 3;
    flex: 1 0 100%;
    gap: 2px;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .nav::-webkit-scrollbar {
    display: none;
  }

  .nav-link {
    padding: 5px 10px;
    font-size: 13px;
  }

  .brand-text {
    font-size: 15px;
  }

  .actions {
    margin-left: auto;
  }
}
</style>
