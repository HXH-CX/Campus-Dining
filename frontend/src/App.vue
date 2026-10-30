<script setup lang="ts">
import { useRoute } from 'vue-router'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import ErrorBoundary from '@/components/ErrorBoundary.vue'

const route = useRoute()
</script>

<template>
  <!-- 按需引入后不再 app.use(ElementPlus)，语言包通过 ConfigProvider 下发（分页"共 X 条"、弹窗按钮文案靠它） -->
  <el-config-provider :locale="zhCn">
    <!-- 换页时自动清掉上一页的崩溃状态 -->
    <ErrorBoundary :reset-key="route.fullPath">
      <router-view />
    </ErrorBoundary>
  </el-config-provider>
</template>
