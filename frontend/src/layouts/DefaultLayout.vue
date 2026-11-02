<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotifyStore } from '@/stores/notify'
import MobileTabBar from '@/components/MobileTabBar.vue'
import { ElMessage } from '@/utils/feedback'

const auth = useAuthStore()
const notify = useNotifyStore()
const router = useRouter()

const initial = computed(() => auth.user?.nickname?.slice(0, 1) || '食')
const quickKeyword = ref('')

// 登录态决定要不要轮询未读；退出登录时一并清掉角标，避免换了账号还挂着别人的红点
watch(
  () => auth.isLoggedIn,
  (loggedIn) => (loggedIn ? notify.start() : notify.stop()),
  { immediate: true },
)
onBeforeUnmount(() => notify.stop())

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

        <!-- 窄屏没有输入框的位置，留一个图标跳到搜索页（那一页本来就有完整输入框） -->
        <button class="search-btn" type="button" aria-label="搜索" @click="router.push({ name: 'search' })">
          🔍
        </button>

        <div class="actions">
          <template v-if="auth.isLoggedIn">
            <el-button class="write-btn" type="primary" round @click="router.push({ name: 'create' })">
              写食评
            </el-button>
            <router-link :to="{ name: 'notifications' }" class="bell" :title="notify.unread ? `${notify.unread} 条未读` : '通知'">
              <span class="bell-icon">🔔</span>
              <span v-if="notify.unread" class="bell-badge">{{ notify.unread > 99 ? '99+' : notify.unread }}</span>
            </router-link>
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

    <MobileTabBar />
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

/* 输入框在 900px 以下会被 .hide-sm 收掉，这时换成图标，保证搜索入口不消失 */
.search-btn {
  display: none;
  width: 32px;
  height: 32px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: none;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  flex-shrink: 0;
}

.search-btn:hover {
  background: var(--brand-soft);
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

.bell {
  position: relative;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  flex-shrink: 0;
  transition: background 0.15s;
}

.bell:hover {
  background: var(--brand-soft);
}

.bell-icon {
  font-size: 17px;
  line-height: 1;
}

/* 角标贴右上角，用 min-width 撑成胶囊，两位数（如 20）不会变成椭圆 */
.bell-badge {
  position: absolute;
  top: 0;
  right: -2px;
  min-width: 16px;
  padding: 0 4px;
  border-radius: 999px;
  background: #ff3b30;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
  box-shadow: 0 0 0 2px #fff;
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
 * 窄屏分两段：
 * - ≤900px：顶栏的搜索框换成图标，搜索入口不能凭空消失
 * - ≤560px：导航整体挪到底部 tabbar，顶栏退化成单行的「品牌 + 搜索 + 账号」，
 *   给内容留出高度。原先"导航换行 + 横向滚动"的写法在有了底部栏之后就重复了。
 */
@media (max-width: 900px) {
  .search-btn {
    display: grid;
    place-items: center;
    /* 靠右贴住账号区：贴品牌会看起来像 logo 的一部分 */
    margin-left: auto;
  }

  /* 搜索图标接管了 "推到右边" 的职责，账号区不再重复 */
  .actions {
    margin-left: 0;
  }
}

@media (max-width: 560px) {
  .topbar-inner {
    height: 52px;
    padding: 0 12px;
    gap: 6px;
  }

  .nav {
    display: none;
  }

  .brand-text {
    font-size: 15px;
  }

  .actions {
    gap: 4px;
  }

  /* 底部已有一个更大的发帖按钮，顶栏这个收起来，别让两个入口抢同一件事 */
  .write-btn {
    display: none;
  }

  /* 给底部固定栏让位，否则页面最后一行永远被挡住 */
  .shell {
    padding-bottom: calc(56px + env(safe-area-inset-bottom));
  }

  .footer {
    padding: 16px 12px 8px;
  }
}
</style>
