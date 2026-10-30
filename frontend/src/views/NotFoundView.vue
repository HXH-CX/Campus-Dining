<template>
  <div class="notfound">
    <div class="emoji">🍽️</div>
    <h1>这道菜没找到</h1>
    <p class="muted">页面可能已经被撤下了</p>
    <router-link :to="{ name: 'home' }">
      <el-button type="primary" round>回首页</el-button>
    </router-link>
  </div>
</template>

<style scoped>
.notfound {
  min-height: 70vh;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 6px;
  text-align: center;
}

.emoji {
  font-size: 56px;
}

h1 {
  margin: 6px 0 0;
  font-size: 22px;
}

.muted {
  margin: 0 0 18px;
}
</style>
