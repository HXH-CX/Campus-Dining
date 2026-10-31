<script setup lang="ts">
/**
 * 发帖成功后的结果面板。
 *
 * 为什么不是"toast + 跳转"：评分是这个产品最重要的动作，发完却只说一句
 * "发布成功"就把人扔到菜品页，用户不知道自己这一票改变了什么。
 * 这里把三件事说清楚——我打了几分、这道菜现在几分、离高分榜还有多远。
 *
 * 组件只负责渲染，排名由页面查好传进来（查不到就不显示名次，不影响"发布成功"）。
 */
import { computed } from 'vue'
import RatingStars from '@/components/RatingStars.vue'
import type { Post } from '@/types'

const props = defineProps<{
  post: Post
  /** 榜单名次，null 表示没上榜；rankLoading 时先不显示这一行 */
  rank: number | null
  rankLoading: boolean
}>()

const emit = defineEmits<{ (e: 'again'): void; (e: 'home'): void }>()

/** 高分榜门槛，与后端 /dishes/top 默认值保持一致 */
const MIN_RATING = 4
const MIN_COUNT = 2

const dish = computed(() => props.post.dish)

/** 没上榜时给一句"还差什么"，比干巴巴的"未上榜"有用 */
const hint = computed(() => {
  if (props.rank !== null) return ''
  const count = dish.value.rating_count
  if (count < MIN_COUNT) {
    const left = MIN_COUNT - count
    return `再有 ${left} 位同学评过，就能进高分榜`
  }
  if (dish.value.avg_rating < MIN_RATING) {
    return `均分到 ${MIN_RATING.toFixed(1)} 才能上榜，现在还差 ${(MIN_RATING - dish.value.avg_rating).toFixed(1)} 分`
  }
  return '这次没挤进榜单前列，再攒几条评价'
})
</script>

<template>
  <div class="card done">
    <div class="badge">✓ 发布成功</div>

    <h2 class="title">{{ dish.name }}</h2>
    <p class="muted sub">这一票记在 {{ post.merchant.name }} · {{ post.merchant.canteen_name }}</p>

    <div class="scores">
      <div class="score-box mine">
        <span class="label">你打的</span>
        <RatingStars :value="post.author_score || 0" />
        <span class="num">{{ post.author_score }}.0</span>
      </div>
      <div class="arrow">→</div>
      <div class="score-box now">
        <span class="label">这道菜现在</span>
        <RatingStars :value="dish.avg_rating" />
        <span class="num">{{ dish.avg_rating.toFixed(1) }}</span>
        <span class="tiny">{{ dish.rating_count }} 人评过</span>
      </div>
    </div>

    <div class="rank">
      <template v-if="rankLoading">
        <span class="tiny">正在看榜单…</span>
      </template>
      <template v-else-if="rank !== null">
        <span class="rank-hit">🏆 目前排在高分榜第 {{ rank }} 位</span>
      </template>
      <template v-else>
        <span class="tiny">{{ hint }}</span>
      </template>
    </div>

    <div class="acts">
      <el-button type="primary" round @click="emit('again')">再发一条</el-button>
      <el-button round @click="$router.push({ name: 'dish', params: { id: dish.id } })">看这道菜</el-button>
      <el-button round text @click="emit('home')">回首页</el-button>
    </div>
  </div>
</template>

<style scoped>
.done {
  text-align: center;
  padding: 30px 22px 24px;
}

.badge {
  display: inline-block;
  padding: 4px 14px;
  border-radius: 999px;
  background: #eaf7ee;
  color: #1f9d55;
  font-size: 12px;
  font-weight: 700;
}

.title {
  margin: 12px 0 4px;
  font-size: 22px;
}

.sub {
  margin: 0 0 20px;
  font-size: 13px;
}

.scores {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-bottom: 16px;
}

.score-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex: 1;
  max-width: 190px;
  padding: 14px 10px;
  border-radius: 14px;
  background: #fffaf5;
  border: 1px solid var(--line);
}

.score-box.now {
  background: var(--brand-soft);
  border-color: #ffd8c4;
}

.label {
  font-size: 12px;
  color: var(--text-2);
}

.num {
  font-size: 20px;
  font-weight: 800;
  color: var(--brand-dark);
  line-height: 1.1;
}

.arrow {
  color: var(--text-3);
  font-size: 18px;
}

.rank {
  min-height: 22px;
  margin-bottom: 18px;
}

.rank-hit {
  color: var(--brand-dark);
  font-weight: 700;
  font-size: 14px;
}

.acts {
  display: flex;
  gap: 10px;
  justify-content: center;
  flex-wrap: wrap;
}

/* el-button + el-button 默认 margin-left，包在 flex 里会多出一段空隙 */
.acts :deep(.el-button + .el-button) {
  margin-left: 0;
}

@media (max-width: 480px) {
  .scores {
    gap: 8px;
  }

  .arrow {
    display: none;
  }

  .score-box {
    padding: 12px 6px;
  }
}
</style>
