import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from '@/utils/feedback'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: '/',
      component: () => import('@/layouts/DefaultLayout.vue'),
      children: [
        { path: '', name: 'home', component: () => import('@/views/HomeView.vue') },
        { path: 'canteens', name: 'canteens', component: () => import('@/views/CanteenListView.vue') },
        { path: 'search', name: 'search', component: () => import('@/views/SearchView.vue') },
        {
          path: 'canteens/:id',
          name: 'canteen-merchants',
          component: () => import('@/views/MerchantListView.vue'),
          props: true,
        },
        {
          path: 'merchants/:id',
          name: 'merchant',
          component: () => import('@/views/MerchantDetailView.vue'),
          props: true,
        },
        { path: 'dishes/:id', name: 'dish', component: () => import('@/views/DishDetailView.vue'), props: true },
        {
          path: 'create',
          name: 'create',
          component: () => import('@/views/CreatePostView.vue'),
          meta: { requiresAuth: true },
        },
        { path: 'users/:id', name: 'user', component: () => import('@/views/ProfileView.vue'), props: true },
        {
          path: 'me',
          name: 'me',
          component: () => import('@/views/ProfileView.vue'),
          meta: { requiresAuth: true },
        },
      ],
    },
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
    { path: '/register', name: 'register', component: () => import('@/views/RegisterView.vue') },
    {
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        { path: '', redirect: { name: 'admin-canteens' } },
        { path: 'canteens', name: 'admin-canteens', component: () => import('@/views/admin/CanteenAdmin.vue') },
        { path: 'merchants', name: 'admin-merchants', component: () => import('@/views/admin/MerchantAdmin.vue') },
        { path: 'dishes', name: 'admin-dishes', component: () => import('@/views/admin/DishAdmin.vue') },
        { path: 'posts', name: 'admin-posts', component: () => import('@/views/admin/PostAdmin.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue') },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.requiresAdmin) {
    if (!auth.user) await auth.refreshMe()
    if (!auth.isAdmin) return { name: 'home' }
  }

  return true
})

/**
 * 发版后 index.html 里的 chunk hash 变了，用户停留在旧页面点导航会
 * 404 / 加载失败。这里做一次"强制刷新"，把新 index.html 拉下来。
 * 用一个 sessionStorage 标记防止无限刷新。
 */
const CHUNK_RELOAD_FLAG = 'cf_chunk_reloaded'

router.onError((error, to) => {
  const message = String((error as Error)?.message || error)
  const isChunkError = /dynamically imported module|Importing a module script|Loading chunk/i.test(message)

  if (!isChunkError) {
    console.error('[路由异常]', message)
    ElMessage.error('页面加载失败，请重试')
    return
  }

  if (sessionStorage.getItem(CHUNK_RELOAD_FLAG)) {
    // 刷新过一次还是失败：别死循环，老实报错
    sessionStorage.removeItem(CHUNK_RELOAD_FLAG)
    ElMessage.error('页面资源加载失败，请检查网络后手动刷新')
    return
  }

  sessionStorage.setItem(CHUNK_RELOAD_FLAG, '1')
  window.location.assign(to.fullPath || '/')
})

// 导航成功说明资源是好的，清掉标记，下次发版还能再自动刷新一次
router.afterEach(() => {
  sessionStorage.removeItem(CHUNK_RELOAD_FLAG)
})

export default router
