<script setup lang="ts">
/**
 * 「今天吃什么」——随机一顿。
 *
 * 存在的意义：高分榜解决的是"什么好吃"，解决不了"我现在选不出来"。
 * 这个弹窗把选择权交给骰子：抽一道菜，不满意就再摇一次，满意就直接跳详情。
 *
 * 两个池子：
 * - 随便抽（默认）：后端先取高分池，池空退回全部在售菜品；
 * - 从想吃里抽：只在我自己攒的清单里挑，抽不到不偷偷换池子。
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchRandomDish } from '@/api/catalog'
import { fetchUserWants } from '@/api/user'
import ErrorState from '@/components/ErrorState.vue'
import RatingStars from '@/components/RatingStars.vue'
import { useAuthStore } from '@/stores/auth'
import type { RandomDishResult } from '@/types'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void }>()

const router = useRouter()
const auth = useAuthStore()

/** 骰子至少转这么久：秒出结果没有"抽"的感觉，眼睛也跟不上 */
const MIN_ROLL_MS = 640

const result = ref<RandomDishResult | null>(null)
const drawing = ref(false)
const error = ref<unknown>(null)
/** 每次抽中 +1，用作结果卡的 key，让揭晓动画能重播 */
const rolled = ref(0)
/** auto = 随便抽（高分池优先），wants = 只在想吃清单里抽 */
const source = ref<'auto' | 'wants'>('auto')
const wantsTotal = ref(0)
const wantsKnown = ref(false)
/** 失败重试时要不要继续避开当前这道 */
let wantExclude = false
let timer: number | undefined

const canUseWants = computed(() => auth.isLoggedIn && (!wantsKnown.value || wantsTotal.value > 0))

async function draw(excludeCurrent = false): Promise<void> {
  if (drawing.value) return
  if (source.value === 'wants' && !canUseWants.value) return
  drawing.value = true
  error.value = null
  wantExclude = excludeCurrent
  const startedAt = Date.now()
  try {
    const excludeId = excludeCurrent && result.value ? result.value.dish.id : undefined
    const data = await fetchRandomDish({
      source: source.value,
      ...(excludeId ? { exclude_id: excludeId } : {}),
    })
    const rest = MIN_ROLL_MS - (Date.now() - startedAt)
    if (rest > 0) {
      await new Promise<void>((resolve) => {
        timer = window.setTimeout(resolve, rest)
      })
    }
    result.value = data
    rolled.value += 1
  } catch (e) {
    error.value = e
  } finally {
    drawing.value = false
  }
}

/** 想吃清单有多少道：用于文案和"能不能从这儿抽"，只取 total 所以要最小分页 */
async function loadWantsTotal(): Promise<void> {
  if (!auth.user?.id) return
  try {
    const data = await fetchUserWants(auth.user.id, 1, 1)
    wantsTotal.value = data.total
  } catch {
    wantsTotal.value = 0
  } finally {
    wantsKnown.value = true
  }
}

function pickSource(next: 'auto' | 'wants'): void {
  if (source.value === next || drawing.value) return
  if (next === 'wants' && !canUseWants.value) return
  source.value = next
  result.value = null
  void draw(false)
}

function close(): void {
  emit('update:modelValue', false)
}

// 每次打开都回到"随便抽"并重新抽：关掉再打开就该是新的运气
watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    source.value = 'auto'
    void draw(false)
    if (auth.isLoggedIn) void loadWantsTotal()
  },
)

onBeforeUnmount(() => window.clearTimeout(timer))

/** 候选池只剩一道时，换也换不出别的，按钮直接禁掉别骗点击 */
const canReroll = (): boolean => !drawing.value && (result.value?.pool_size ?? 0) > 1

function goEat(): void {
  if (!result.value) return
  const id = result.value.dish.id
  close()
  router.push({ name: 'dish', params: { id } })
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    width="min(440px, 92vw)"
    align-center
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #header>
      <div class="head">
        <h3>今天吃什么</h3>
        <p class="tiny">交给骰子，省下在食堂门口站着的十分钟</p>
      </div>
    </template>

    <div class="sources">
      <button class="chip" :class="{ on: source === 'auto' }" :disabled="drawing" @click="pickSource('auto')">
        随便抽
      </button>
      <button
        class="chip"
        :class="{ on: source === 'wants' }"
        :disabled="drawing || !canUseWants"
        @click="pickSource('wants')"
      >
        从想吃里抽<span v-if="wantsKnown && wantsTotal" class="chip-count">{{ wantsTotal }}</span>
      </button>
    </div>
    <p v-if="!auth.isLoggedIn" class="tiny hint">登录后可以只在「想吃」清单里抽</p>
    <p v-else-if="wantsKnown && !wantsTotal" class="tiny hint">想吃清单还是空的，去菜品页点「想吃」攒几道</p>

    <div v-if="drawing" class="rolling">
      <div class="dice">
        <span v-for="i in 3" :key="i" :style="{ animationDelay: `${(i - 1) * 0.13}s` }">🎲</span>
      </div>
      <p class="muted">正在翻菜单…</p>
      <p class="tiny">
        {{ source === 'wants' ? '只从你自己挑的清单里抽' : '优先从高分菜里挑，比闭眼指强一点' }}
      </p>
    </div>

    <ErrorState v-else-if="error" :error="error" title="这次没抽出来" compact @retry="draw(wantExclude)" />

    <div v-else-if="result" :key="rolled" class="result">
      <div class="pic">
        <img v-if="result.dish.image_url" :src="result.dish.image_url" :alt="result.dish.name" />
        <span v-else class="pic-fallback">{{ result.dish.name.slice(0, 1) }}</span>
      </div>

      <h2 class="name">{{ result.dish.name }}</h2>
      <p class="meta">{{ result.dish.merchant_name }} · {{ result.dish.canteen_name }}</p>

      <div class="rating">
        <RatingStars :value="result.dish.avg_rating" show-score />
        <span class="tiny">{{ result.dish.rating_count }} 人评过</span>
      </div>

      <p class="tiny pool">
        <template v-if="result.source === 'wants'">从你想吃的 {{ result.pool_size }} 道里抽的</template>
        <template v-else-if="result.source === 'top'">从 {{ result.pool_size }} 道高分菜里抽的</template>
        <template v-else>高分菜还没攒够，这次从全部 {{ result.pool_size }} 道在售菜里抽的</template>
      </p>
    </div>

    <template #footer>
      <div class="acts">
        <el-button
          round
          :disabled="!canReroll()"
          :title="(result?.pool_size ?? 0) <= 1 && !drawing ? '候选池就这一道，换不了' : ''"
          @click="draw(true)"
        >
          换一个
        </el-button>
        <el-button type="primary" round :disabled="drawing || !result" @click="goEat">就吃这个</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.head h3 {
  margin: 0 0 2px;
  font-size: 17px;
}

.head p {
  margin: 0;
}

.rolling {
  padding: 26px 0 22px;
  text-align: center;
}

/* 两个池子的切换：做成轻量 chip，不跟主按钮抢视线 */
.sources {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 8px;
}

.chip {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--text-2);
  border-radius: 999px;
  padding: 5px 14px;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.chip:hover:not(:disabled) {
  border-color: var(--brand);
  color: var(--brand-dark);
}

.chip.on {
  background: var(--brand-soft);
  border-color: var(--brand);
  color: var(--brand-dark);
  font-weight: 600;
}

.chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chip-count {
  margin-left: 5px;
  font-size: 11px;
  opacity: 0.75;
}

.hint {
  margin: 0 0 6px;
  text-align: center;
}

.dice {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-bottom: 10px;
}

.dice span {
  font-size: 38px;
  line-height: 1;
  display: inline-block;
  animation: tumble 0.62s linear infinite;
}

/* 三个骰子错开相位，看起来像在真的摇，而不是一起转的图标 */
@keyframes tumble {
  0% {
    transform: rotate(0deg) translateY(0);
  }
  50% {
    transform: rotate(180deg) translateY(-9px);
  }
  100% {
    transform: rotate(360deg) translateY(0);
  }
}

.result {
  text-align: center;
  animation: reveal 0.32s cubic-bezier(0.2, 0.9, 0.3, 1.25) both;
}

@keyframes reveal {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.pic {
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 12px;
  overflow: hidden;
  background: var(--brand-soft);
  margin-bottom: 12px;
}

.pic img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.pic-fallback {
  display: grid;
  place-items: center;
  height: 100%;
  font-size: 44px;
  font-weight: 700;
  color: var(--brand-dark);
}

.name {
  margin: 0;
  font-size: 20px;
}

.meta {
  margin: 4px 0 8px;
  font-size: 13px;
  color: var(--text-2);
}

.rating {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.pool {
  margin: 10px 0 0;
}

.acts {
  display: flex;
  justify-content: center;
  gap: 10px;
}
</style>
