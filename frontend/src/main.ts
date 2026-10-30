import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { ElLoading } from 'element-plus/es/components/loading/index'
import { ElMessage } from '@/utils/feedback'
// 模板里的 el-* 组件由 unplugin-vue-components 按需引入（连样式一起）。
// 但 ElMessage / ElMessageBox / v-loading 是"函数/指令"，走不到组件解析，样式得手动引。
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
import 'element-plus/es/components/loading/style/css'

import App from './App.vue'
import router from './router'
import { setUnauthorizedHandler } from './api/request'
import { useAuthStore } from './stores/auth'
import './assets/global.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
// v-loading 指令（后台表格在用）
app.use(ElLoading)

// token 失效时统一登出并跳登录页，避免每个接口单独处理
setUnauthorizedHandler(() => {
  const auth = useAuthStore()
  auth.clear()
  if (router.currentRoute.value.name !== 'login') {
    router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
  }
})

/**
 * 渲染阶段的兜底：ErrorBoundary 只包了 router-view 内部，
 * 这里接住布局层/根组件抛出的异常，至少别让用户面对纯白页面。
 */
app.config.errorHandler = (error, _instance, info) => {
  console.error('[全局异常]', info, error)
  ElMessage.error('页面出现异常，请刷新重试')
}

/**
 * 未处理的 Promise 拒绝通常是"请求没写 catch"。
 * axios 的错误已被拦截器提示过，这里只记录，不再二次弹窗。
 */
window.addEventListener('unhandledrejection', (event) => {
  const reason = event.reason as { isAxiosError?: boolean } | undefined
  if (reason?.isAxiosError) return
  console.error('[未处理的异步异常]', event.reason)
})

// 带着 token 刷新页面时，先把用户信息捞回来，导航栏才不会闪成未登录
const auth = useAuthStore()
if (auth.isLoggedIn) {
  void auth.refreshMe()
}

app.mount('#app')
