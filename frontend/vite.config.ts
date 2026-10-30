import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import type { ComponentResolver } from 'unplugin-vue-components/types'

/**
 * 不用官方 ElementPlusResolver 的原因：
 * 它对 1.1.0+ 的 Element Plus 统一从 `element-plus/es`（包根 barrel）导入，而那个 barrel 里有
 * `makeInstaller([...全部组件])`，摇树摇不掉 —— 实测打出来 944KB，和全量引入没区别。
 * 这里按组件目录逐个导入，才能只带上真正用到的组件。
 *
 * 子组件（ElTableColumn 之类）实际挂在父组件目录下，需要映射。
 */
const SUB_COMPONENT_DIR: Record<string, string> = {
  'table-column': 'table',
  'form-item': 'form',
  'tab-pane': 'tabs',
  'breadcrumb-item': 'breadcrumb',
  'dropdown-menu': 'dropdown',
  'dropdown-item': 'dropdown',
  option: 'select',
}

const toKebab = (name: string): string => name.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase()

const elementPlusComponentResolver: ComponentResolver = (name: string) => {
  if (!/^El[A-Z]/.test(name)) return
  const partial = toKebab(name.slice(2))
  const dir = SUB_COMPONENT_DIR[partial] ?? partial
  return {
    name,
    from: `element-plus/es/components/${dir}/index`,
    // 每个组件的 style/css 内部已经 import 了 base，这里只补自己那份
    sideEffects: `element-plus/es/components/${dir}/style/css`,
  }
}

// 开发期把 /api 与 /uploads 代理到后端，前端代码里不出现跨域地址
const backendDownHint = (proxy: {
  on: (event: string, fn: (...args: any[]) => void) => void
}): void => {
  // 后端没起时 Vite 默认吐一段 ECONNREFUSED 的 HTML，前端只能显示"服务器开小差了"。
  // 这里改成结构化 JSON，前端错误卡片就能直接说清是后端没启动。
  proxy.on('error', (_err: unknown, _req: unknown, res: any) => {
    if (!res || typeof res.writeHead !== 'function') return
    res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
    res.end(JSON.stringify({ code: 50200, message: '后端服务未启动，请先运行 uvicorn（127.0.0.1:8000）' }))
  })
}

export default defineConfig({
  plugins: [
    vue(),
    // 模板里的 el-* 组件按需引入（含各自的 css），不再 import 'element-plus' 整包
    Components({
      resolvers: [elementPlusComponentResolver],
      dts: 'src/components.d.ts',
    }),
  ],
  resolve: {
    // 用 /src 而不是 node:path/fileURLToPath，省掉 @types/node 这个额外依赖
    alias: { '@': '/src' },
  },
  server: {
    // 显式绑 127.0.0.1：Windows 上 localhost 会优先解析到 ::1，导致部分工具/预览面板连不上
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true, configure: backendDownHint },
      '/uploads': { target: 'http://127.0.0.1:8000', changeOrigin: true, configure: backendDownHint },
    },
  },
  build: {
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        // 注意：对象写法 manualChunks: { 'element-plus': ['element-plus'] } 会把整包拉进 chunk，
        // 等于废掉按需引入。函数写法只对"真正进了依赖图"的模块分组。
        // element-plus 故意不分组：让它在各路由 chunk 里按需出现，首屏只带导航栏用到的那几个组件。
        manualChunks(id: string) {
          if (!id.includes('node_modules')) return
          if (id.includes('/vue/') || id.includes('vue-router') || id.includes('/pinia/')) return 'vue'
        },
      },
    },
  },
})
