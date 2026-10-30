/**
 * Element Plus 函数式组件的统一出口。
 *
 * 为什么不直接 `import { ElMessage } from 'element-plus'`：
 * 包的根入口 `es/index.mjs` 里有 `makeInstaller([...全部组件])`，引用它会把所有组件
 * 一起打进 bundle（实测 940KB，按需引入完全失效）。走子路径能只打包用到的两个组件。
 *
 * 样式在 main.ts 里显式引入（函数式组件走不到组件解析，不会自动带样式）。
 */
export { ElMessage } from 'element-plus/es/components/message/index'
export { ElMessageBox } from 'element-plus/es/components/message-box/index'
