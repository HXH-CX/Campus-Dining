<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from '@/utils/feedback'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const form = reactive({ username: '', nickname: '', password: '', confirm: '' })
const submitting = ref(false)

async function submit(): Promise<void> {
  if (!/^[a-zA-Z0-9_]{3,50}$/.test(form.username)) {
    ElMessage.warning('用户名只支持 3-50 位字母、数字、下划线')
    return
  }
  if (form.password.length < 6 || form.password.length > 32) {
    ElMessage.warning('密码长度需在 6-32 位之间')
    return
  }
  if (form.password !== form.confirm) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }

  submitting.value = true
  try {
    await auth.register(form.username, form.nickname || form.username, form.password)
    ElMessage.success('注册成功，先去逛逛吧')
    router.replace('/')
  } catch {
    // 拦截器已提示
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth">
    <div class="panel">
      <div class="brand">🍜 校园食光</div>
      <h2>注册</h2>
      <p class="muted">注册即获得「🍚 干饭练习生」称号</p>

      <el-form label-position="top" @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="form.username" size="large" placeholder="字母 / 数字 / 下划线" />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" size="large" placeholder="同学们看到的名字" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" size="large" type="password" show-password placeholder="6-32 位" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input
            v-model="form.confirm"
            size="large"
            type="password"
            show-password
            placeholder="再输一次"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button type="primary" size="large" class="submit" :loading="submitting" @click="submit">
          注册并登录
        </el-button>
      </el-form>

      <div class="switch">
        已经有账号了？
        <router-link :to="{ name: 'login' }" class="link">去登录</router-link>
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
  margin: 0 0 18px;
  font-size: 13px;
}

.submit {
  width: 100%;
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
</style>
