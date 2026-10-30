<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    value: number
    size?: 'small' | 'default' | 'large'
    showScore?: boolean
    text?: boolean
  }>(),
  { size: 'small', showScore: false, text: true },
)

// el-rate 的 size 只认 small/default/large，这里保持一致
const stars = computed(() => Math.round(props.value || 0))
</script>

<template>
  <span class="rating">
    <el-rate
      :model-value="stars"
      disabled
      allow-half
      :size="size"
      :show-score="false"
      disabled-void-color="#eee4da"
      :colors="['#ffb400', '#ff9500', '#ff6b35']"
    />
    <span v-if="showScore" class="score">{{ value ? value.toFixed(1) : '暂无' }}</span>
  </span>
</template>

<style scoped>
.rating {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.rating :deep(.el-rate) {
  height: 18px;
  line-height: 18px;
}

.score {
  font-weight: 700;
  color: var(--brand-dark);
  font-size: 13px;
}
</style>
