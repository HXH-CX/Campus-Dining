<script setup lang="ts">
/**
 * 统一的错误态区块：图标 + 标题 + 说明 + 重试。
 * 用在"页面主数据加载失败"的位置，替代此前的白屏或只弹一个 toast。
 */
import { computed } from 'vue'
import { describeError } from '@/utils/error'

const props = defineProps<{
  error: unknown
  /** 覆盖默认标题，例如"帖子列表没加载出来" */
  title?: string
  /** 紧凑模式，用于侧栏/弹窗这种窄容器 */
  compact?: boolean
}>()

const emit = defineEmits<{ (e: 'retry'): void }>()

const info = computed(() => describeError(props.error))

const ICONS: Record<string, string> = {
  network: '📡',
  timeout: '⏳',
  server: '🛠️',
  notfound: '🔍',
  forbidden: '🔒',
  unauthorized: '🔑',
  unknown: '😵',
}

const icon = computed(() => ICONS[info.value.kind] || ICONS.unknown)

function reloadPage(): void {
  window.location.reload()
}
</script>

<template>
  <div class="err" :class="{ compact }">
    <div class="icon">{{ icon }}</div>
    <div class="title">{{ title || info.title }}</div>
    <p class="desc">{{ info.desc }}</p>
    <div class="acts">
      <el-button v-if="info.retryable" type="primary" round @click="emit('retry')">重试</el-button>
      <el-button round @click="reloadPage">刷新页面</el-button>
    </div>
  </div>
</template>

<style scoped>
.err {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 44px 20px;
  display: grid;
  justify-items: center;
  text-align: center;
  gap: 6px;
}

.err.compact {
  padding: 22px 14px;
}

.icon {
  font-size: 34px;
  line-height: 1;
}

.compact .icon {
  font-size: 24px;
}

.title {
  font-weight: 600;
  font-size: 15px;
}

.desc {
  margin: 0;
  font-size: 13px;
  color: var(--text-3);
  max-width: 420px;
  line-height: 1.6;
}

.acts {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}
</style>
