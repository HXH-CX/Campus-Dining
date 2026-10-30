<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from '@/utils/feedback'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const form = reactive({ username: 'xiaoming', password: '123456' })
const submitting = ref(false)

async function submit(): Promise<void> {
  if (!form.username || !form.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  submitting.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('欢迎回来')
    const redirect = route.query.redirect as string | undefined
    router.replace(redirect || '/')
  } catch {
    // 拦截器已提示
  } finally {
    submitting.value = false
  }
}

function fill(username: string, password: string): void {
  form.username = username
  form.password = password
}
</script>

<template>
  <div class="auth">
    <div class="panel">
      <div class="brand">🍜 校园食光</div>
      <h2>登录</h2>
      <p class="muted">今天吃什么，看看同学们怎么说</p>

      <el-form label-position="top" @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="form.username" size="large" placeholder="学号或昵称" @keyup.enter="submit" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            size="large"
            type="password"
            show-password
            placeholder="至少 6 位"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button type="primary" size="large" class="submit" :loading="submitting" @click="submit">
          登录
        </el-button>
      </el-form>

      <div class="tips">
        <span class="tiny">演示账号：</span>
        <el-button link type="primary" size="small" @click="fill('xiaoming', '123456')">xiaoming</el-button>
        <el-button link type="primary" size="small" @click="fill('admin', 'admin123')">admin</el-button>
      </div>

      <div class="switch">
        还没有账号？
        <router-link :to="{ name: 'register' }" class="link">去注册</router-link>
        <span class="dot">·</span>
        <router-link :to="{ name: 'home' }" class="link">先随便逛逛</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: radial-gradient(circle at 30% 20%, #fff1e6, var(--bg) 60%);
  padding: 20px;
}

.panel {
  width: 100%;
  max-width: 380px;
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 12px 40px rgba(120, 80, 50, 0.12);
  padding: 32px 30px 26px;
}

.brand {
  font-weight: 800;
  color: var(--brand-dark);
}

h2 {
  margin: 10px 0 4px;
  font-size: 24px;
}

.muted {
  margin: 0 0 20px;
  font-size: 13px;
}

.submit {
  width: 100%;
  margin-top: 4px;
}

.tips {
  margin-top: 14px;
  display: flex;
  align-items: center;
  gap: 2px;
}

.switch {
  margin-top: 18px;
  text-align: center;
  font-size: 13px;
  color: var(--text-2);
}

.link {
  color: var(--brand-dark);
  font-weight: 600;
}

.dot {
  margin: 0 6px;
  color: var(--text-3);
}
</style>
