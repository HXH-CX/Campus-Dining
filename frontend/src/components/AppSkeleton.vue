<script setup lang="ts">
/**
 * 统一的加载骨架。
 *
 * 为什么不用 el-skeleton：它的 rows 是等宽文字条，和"卡片/表格/头像"完全不一个形状，
 * 数据到位时会明显跳一下。这里按内容形态做 7 种骨架，高度和真实内容接近，
 * 加载完成后布局不位移。
 */
withDefaults(
  defineProps<{
    /** post=信息流卡片；card=菜品/商家/食堂宫格；row=热榜/打分番；detail=详情页头图+宫格；profile=个人主页；form=表单；table=后台表格 */
    variant?: 'post' | 'card' | 'row' | 'detail' | 'profile' | 'form' | 'table'
    count?: number
  }>(),
  { variant: 'post', count: 3 },
)
</script>

<template>
  <div class="sk" :class="`sk-${variant}`" aria-busy="true" aria-live="polite">
    <!-- 信息流卡片 -->
    <template v-if="variant === 'post'">
      <div v-for="i in count" :key="i" class="sk-card sk-post">
        <div class="sk-head">
          <span class="sk-block sk-avatar" />
          <div class="sk-lines">
            <span class="sk-block w40" />
            <span class="sk-block w25 thin" />
          </div>
        </div>
        <span class="sk-block" />
        <span class="sk-block w70" />
        <div class="sk-dish">
          <span class="sk-block sk-dish-thumb" />
          <div class="sk-lines">
            <span class="sk-block w50" />
            <span class="sk-block w30 thin" />
          </div>
        </div>
        <span class="sk-block thin" style="width: 55%" />
      </div>
    </template>

    <!-- 宫格卡片 -->
    <div v-else-if="variant === 'card'" class="sk-grid">
      <div v-for="i in count" :key="i" class="sk-card sk-tile">
        <span class="sk-block sk-cover" />
        <span class="sk-block w70" />
        <span class="sk-block w40 thin" />
      </div>
    </div>

    <!-- 榜单 / 打分记录 -->
    <div v-else-if="variant === 'row'" class="sk-rows">
      <div v-for="i in count" :key="i" class="sk-row">
        <span class="sk-block sk-rank" />
        <div class="sk-lines">
          <span class="sk-block" :style="{ width: `${90 - i * 8}%` }" />
          <span class="sk-block w40 thin" />
        </div>
      </div>
    </div>

    <!-- 详情页：头图 + 宫格 -->
    <template v-else-if="variant === 'detail'">
      <div class="sk-card sk-hero">
        <span class="sk-block sk-hero-img" />
        <div class="sk-lines">
          <span class="sk-block w40" style="height: 18px" />
          <span class="sk-block w55 thin" />
          <span class="sk-block w30 thin" />
        </div>
      </div>
      <div class="sk-grid">
        <div v-for="i in count" :key="i" class="sk-card sk-tile">
          <span class="sk-block sk-cover" />
          <span class="sk-block w70" />
          <span class="sk-block w40 thin" />
        </div>
      </div>
    </template>

    <!-- 个人主页 -->
    <template v-else-if="variant === 'profile'">
      <div class="sk-card sk-hero">
        <span class="sk-block sk-avatar lg" />
        <div class="sk-lines">
          <span class="sk-block w40" style="height: 18px" />
          <span class="sk-block w25 thin" />
          <span class="sk-block w55 thin" />
        </div>
      </div>
      <div class="sk-card sk-post">
        <span class="sk-block" />
        <span class="sk-block w70" />
        <span class="sk-block thin" style="width: 45%" />
      </div>
      <div class="sk-card sk-post">
        <span class="sk-block" />
        <span class="sk-block w60" />
      </div>
    </template>

    <!-- 表单 -->
    <div v-else-if="variant === 'form'" class="sk-form">
      <div v-for="i in count" :key="i" class="sk-field">
        <span class="sk-block w20 thin" />
        <span class="sk-block sk-input" />
      </div>
    </div>

    <!-- 后台表格 -->
    <div v-else class="sk-card sk-table">
      <div class="sk-table-head">
        <span class="sk-block w20 thin" />
        <span class="sk-block w15 thin" />
        <span class="sk-block w15 thin" />
      </div>
      <div v-for="i in count" :key="i" class="sk-table-row">
        <span class="sk-block sk-thumb" />
        <span class="sk-block" :style="{ width: `${50 + (i % 3) * 8}%` }" />
        <span class="sk-block w15 thin" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.sk {
  display: grid;
  gap: 12px;
}

.sk-card {
  background: var(--card);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px 18px;
  display: grid;
  gap: 10px;
}

.sk-block {
  display: block;
  height: 12px;
  border-radius: 6px;
  background: linear-gradient(90deg, #f3ece5 25%, #faf5f0 37%, #f3ece5 63%);
  background-size: 400% 100%;
  animation: sk-shimmer 1.4s ease infinite;
}

.sk-block.thin {
  height: 9px;
}

.w15 {
  width: 15%;
}
.w20 {
  width: 20%;
}
.w25 {
  width: 25%;
}
.w30 {
  width: 30%;
}
.w40 {
  width: 40%;
}
.w50 {
  width: 50%;
}
.w55 {
  width: 55%;
}
.w60 {
  width: 60%;
}
.w70 {
  width: 70%;
}

/* 信息流 */
.sk-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sk-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
}

.sk-avatar.lg {
  width: 64px;
  height: 64px;
}

.sk-lines {
  display: grid;
  gap: 7px;
  flex: 1;
}

.sk-dish {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: #fdf8f3;
  border-radius: 10px;
}

.sk-dish-thumb {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  flex-shrink: 0;
}

/* 宫格 */
.sk-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 14px;
}

.sk-tile {
  padding: 12px;
}

.sk-cover {
  height: 110px;
  border-radius: 10px;
}

/* 榜单 */
.sk-rows {
  display: grid;
  gap: 14px;
  padding: 4px 0;
}

.sk-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sk-rank {
  width: 20px;
  height: 20px;
  border-radius: 6px;
  flex-shrink: 0;
}

/* 详情 / 主页 */
.sk-hero {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 14px;
}

.sk-hero-img {
  width: 110px;
  height: 110px;
  border-radius: 12px;
  flex-shrink: 0;
}

/* 表单 */
.sk-form {
  display: grid;
  gap: 18px;
}

.sk-field {
  display: grid;
  gap: 8px;
}

.sk-input {
  height: 34px;
  border-radius: 10px;
}

/* 表格 */
.sk-table {
  gap: 14px;
}

.sk-table-head {
  display: flex;
  gap: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}

.sk-table-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.sk-thumb {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  flex-shrink: 0;
}

@keyframes sk-shimmer {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0 50%;
  }
}

/* 尊重"减少动效"偏好 */
@media (prefers-reduced-motion: reduce) {
  .sk-block {
    animation: none;
  }
}
</style>
