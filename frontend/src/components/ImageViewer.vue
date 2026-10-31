<script setup lang="ts">
/**
 * 图片大图预览。
 *
 * 为什么不用 el-image-viewer：它要额外引一份样式和 popper 依赖，而我们只需要
 * 「铺满屏幕 + 左右翻页 + 关闭」三件事。帖子列表里每张卡片都挂这个组件，
 * 用自绘遮罩更划算，包体也几乎不增加。
 */
import { computed, onBeforeUnmount, watch } from 'vue'

const props = defineProps<{
  images: string[]
  index: number
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'update:index', value: number): void
}>()

const total = computed(() => props.images.length)
const current = computed(() => props.images[props.index] ?? '')
const hasNav = computed(() => total.value > 1)
/** 种子数据用 SVG 占位图，矢量放多大都清晰；位图则保持原始尺寸，避免糊 */
const isVector = computed(() => current.value.toLowerCase().endsWith('.svg'))

function close(): void {
  emit('update:visible', false)
}

function step(delta: number): void {
  if (!hasNav.value) return
  emit('update:index', (props.index + delta + total.value) % total.value)
}

function onKey(event: KeyboardEvent): void {
  if (event.key === 'Escape') close()
  else if (event.key === 'ArrowLeft') step(-1)
  else if (event.key === 'ArrowRight') step(1)
}

watch(
  () => props.visible,
  (open) => {
    // 打开时锁住背景滚动，否则手机上滑图片会带着整页走
    document.body.style.overflow = open ? 'hidden' : ''
    if (open) window.addEventListener('keydown', onKey)
    else window.removeEventListener('keydown', onKey)
  },
)

onBeforeUnmount(() => {
  document.body.style.overflow = ''
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="viewer" @click.self="close">
      <button class="close" aria-label="关闭" @click="close">✕</button>

      <button v-if="hasNav" class="nav prev" aria-label="上一张" @click.stop="step(-1)">‹</button>
      <img class="pic" :class="{ vector: isVector }" :src="current" alt="" @click.stop />
      <button v-if="hasNav" class="nav next" aria-label="下一张" @click.stop="step(1)">›</button>

      <div v-if="hasNav" class="counter">{{ index + 1 }} / {{ total }}</div>
    </div>
  </Teleport>
</template>

<style scoped>
.viewer {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(24, 16, 10, 0.88);
  display: grid;
  place-items: center;
  padding: 40px 56px;
  animation: fade 0.16s ease-out;
}

@keyframes fade {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.pic {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 10px;
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.45);
  cursor: default;
}

/* 矢量图放大不糊，就让占位图铺开一点；位图维持原尺寸，放大反而难看 */
.pic.vector {
  width: min(88vw, 860px);
  height: auto;
}

.close,
.nav {
  position: absolute;
  border: none;
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  border-radius: 50%;
  cursor: pointer;
  display: grid;
  place-items: center;
  font-family: inherit;
  transition: background 0.15s ease;
}

.close:hover,
.nav:hover {
  background: rgba(255, 255, 255, 0.28);
}

.close {
  top: 16px;
  right: 16px;
  width: 36px;
  height: 36px;
  font-size: 16px;
}

.nav {
  top: 50%;
  transform: translateY(-50%);
  width: 44px;
  height: 44px;
  font-size: 26px;
  line-height: 1;
  padding-bottom: 3px;
}

.prev {
  left: 12px;
}

.next {
  right: 12px;
}

.counter {
  position: absolute;
  bottom: 18px;
  left: 50%;
  transform: translateX(-50%);
  padding: 3px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  font-size: 12px;
}

@media (max-width: 560px) {
  .viewer {
    padding: 52px 12px;
  }

  .nav {
    width: 36px;
    height: 36px;
    font-size: 20px;
  }
}
</style>
