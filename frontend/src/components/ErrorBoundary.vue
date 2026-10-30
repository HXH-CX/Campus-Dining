<script setup lang="ts">
/**
 * 渲染异常边界：某个组件在 render/setup 里抛错时，接住它并显示错误页，
 * 而不是让整棵组件树卸载导致白屏。
 *
 * 注意：它拦不住异步请求里的错误（那些走 api 拦截器 + 页面的 error 态）。
 */
import { onErrorCaptured, ref, watch } from 'vue'
import ErrorState from './ErrorState.vue'

const props = defineProps<{
  /** 变化时自动清除错误，通常是 route.fullPath —— 换页了就别再显示上一页的崩溃 */
  resetKey?: unknown
}>()

const failed = ref<unknown>(null)
const attempt = ref(0)

onErrorCaptured((error, _instance, info) => {
  failed.value = error
  console.error('[渲染异常]', info, error)
  // 返回 false 阻止继续冒泡到 app.config.errorHandler，避免重复提示
  return false
})

watch(
  () => props.resetKey,
  () => {
    failed.value = null
  },
)

function retry(): void {
  failed.value = null
  attempt.value += 1
}
</script>

<template>
  <ErrorState v-if="failed" :error="failed" title="页面渲染出错了" @retry="retry" />
  <div v-else :key="attempt" class="boundary-inner">
    <slot />
  </div>
</template>

<style scoped>
/* display:contents 让这层包裹不产生额外盒模型，不影响布局 */
.boundary-inner {
  display: contents;
}
</style>
