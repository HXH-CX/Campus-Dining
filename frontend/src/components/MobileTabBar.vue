<script setup lang="ts">
/**
 * 移动端底部导航。
 *
 * 只在窄屏出现（≤560px）。存在理由：这个产品的主场景是站在食堂门口掏手机，
 * 而顶栏在手机上要折成两行，发帖入口被挤到第二行的横向滚动条里，很难找。
 *
 * 五项定死：首页 / 食堂 / 发帖(中间主按钮) / 通知 / 我的。
 * 搜索不放这里——顶栏给了一个搜索图标，点进搜索页本身就有大输入框，
 * 不必把一个"要输入"的动作塞进 tab。
 *
 * 未登录时三个"需要身份"的入口统一跳登录并带回跳地址，不在 tab 上做禁用态：
 * 禁用态会让人以为功能不存在，跳登录至少说明"登录就能用"。
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotifyStore } from '@/stores/notify'

const auth = useAuthStore()
const notify = useNotifyStore()
const route = useRoute()
const router = useRouter()

/** 发帖是个按钮不是链接（要登录才能进），高亮只能自己判断 */
const createActive = computed(() => route.name === 'create')

function requireLogin(target: string): boolean {
  if (auth.isLoggedIn) return false
  router.push({ name: 'login', query: { redirect: target } })
  return true
}

function goCreate(): void {
  if (requireLogin('/create')) return
  router.push({ name: 'create' })
}

function goNotifications(): void {
  if (requireLogin('/notifications')) return
  router.push({ name: 'notifications' })
}

function goMe(): void {
  if (requireLogin('/me')) return
  router.push({ name: 'me' })
}
</script>

<template>
  <nav class="tabbar" aria-label="主导航">
    <router-link :to="{ name: 'home' }" class="tab" exact-active-class="on">
      <span class="ico">🏠</span>
      <span class="txt">首页</span>
    </router-link>

    <router-link :to="{ name: 'canteens' }" class="tab" active-class="on">
      <span class="ico">🏫</span>
      <span class="txt">食堂</span>
    </router-link>

    <button class="tab tab-publish" :class="{ on: createActive }" type="button" @click="goCreate">
      <span class="plus">＋</span>
      <span class="txt">发帖</span>
    </button>

    <button class="tab" type="button" @click="goNotifications">
      <span class="ico">
        🔔
        <span v-if="notify.unread" class="dot">{{ notify.unread > 99 ? '99+' : notify.unread }}</span>
      </span>
      <span class="txt">通知</span>
    </button>

    <button class="tab" type="button" @click="goMe">
      <span class="ico">👤</span>
      <span class="txt">我的</span>
    </button>
  </nav>
</template>

<style scoped>
.tabbar {
  display: none;
}

@media (max-width: 560px) {
  .tabbar {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 18;
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    align-items: end;
    height: calc(56px + env(safe-area-inset-bottom));
    padding-bottom: env(safe-area-inset-bottom);
    background: rgba(255, 255, 255, 0.96);
    backdrop-filter: blur(10px);
    border-top: 1px solid var(--line);
  }

  .tab {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    height: 56px;
    padding: 0;
    border: none;
    background: none;
    color: var(--text-3);
    font-family: inherit;
    cursor: pointer;
  }

  .ico {
    position: relative;
    font-size: 19px;
    line-height: 1;
    /* 未选中压暗一档，选中时再提亮：emoji 本身不能改色，只能靠滤镜 */
    filter: grayscale(0.7);
    opacity: 0.75;
    transition: filter 0.15s, opacity 0.15s, transform 0.15s;
  }

  .txt {
    font-size: 11px;
    line-height: 1;
  }

  .tab.on {
    color: var(--brand-dark);
    font-weight: 600;
  }

  .tab.on .ico {
    filter: none;
    opacity: 1;
    transform: translateY(-1px);
  }

  /* 发帖是主按钮：抬起来做成圆角方块，和四个 tab 拉开层级。
     按钮用绝对定位而不是挤在流里 —— 否则文字会被顶得和其他 tab 不齐。 */
  .tab-publish {
    position: relative;
    justify-content: center;
  }

  .tab-publish .plus {
    position: absolute;
    left: 50%;
    bottom: 33px;
    display: grid;
    place-items: center;
    width: 42px;
    height: 42px;
    border-radius: 14px;
    background: linear-gradient(135deg, #ff8a5c, #ff5f2e);
    color: #fff;
    font-size: 22px;
    font-weight: 700;
    line-height: 1;
    transform: translateX(-50%);
    box-shadow: 0 6px 16px rgba(255, 95, 46, 0.35);
  }

  .tab-publish.on .plus {
    box-shadow: 0 6px 22px rgba(255, 95, 46, 0.55);
  }

  /* 其它 tab 的文字被上面的图标顶低了 (图标 19 + 间距 2) / 2 ≈ 10px，
     这里补回来，五个文字才在同一水平线上 */
  .tab-publish .txt {
    transform: translateY(10px);
  }

  /* 角标：和顶栏铃铛同一套写法 */
  .dot {
    position: absolute;
    top: -3px;
    right: -7px;
    min-width: 15px;
    padding: 0 4px;
    border-radius: 999px;
    background: #ff3b30;
    color: #fff;
    font-size: 10px;
    font-weight: 700;
    line-height: 15px;
    text-align: center;
    filter: none;
  }
}
</style>
