<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { UploadRequestOptions, UploadUserFile } from 'element-plus'
import { ElMessage } from '@/utils/feedback'
import { fetchCanteens, fetchCanteenMerchants, fetchMerchantDishes, fetchTopDishes } from '@/api/catalog'
import { createPost } from '@/api/post'
import { UPLOAD_MAX_MB, uploadImage } from '@/api/upload'
import { humanSize } from '@/utils/image'
import ErrorState from '@/components/ErrorState.vue'
import AppSkeleton from '@/components/AppSkeleton.vue'
import PostResultPanel from '@/components/PostResultPanel.vue'
import { useAuthStore } from '@/stores/auth'
import type { Post } from '@/types'

interface Option {
  value: number
  label: string
  children?: Option[]
}

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const options = ref<Option[]>([])
const cascaderValue = ref<number[]>([])
const form = reactive({ score: 0, content: '' })
const images = ref<string[]>([])
const fileList = ref<UploadUserFile[]>([])
const treeLoading = ref(true)
const treeError = ref<unknown>(null)
const submitting = ref(false)
/** 发布成功后的结果面板；非空时整个表单被替换掉 */
const done = ref<Post | null>(null)
const rank = ref<number | null>(null)
const rankLoading = ref(false)
/** 累计压缩成效，用于在表单下方给一条轻提示 */
const saved = reactive({ before: 0, after: 0, count: 0 })

const dishId = computed(() => Number(cascaderValue.value[2] || 0))
const dishLabel = computed(() => {
  if (!cascaderValue.value.length) return ''
  const canteen = options.value.find((item) => item.value === cascaderValue.value[0])
  const merchant = canteen?.children?.find((item) => item.value === cascaderValue.value[1])
  const dish = merchant?.children?.find((item) => item.value === cascaderValue.value[2])
  return [canteen?.label, merchant?.label, dish?.label].filter(Boolean).join(' / ')
})

/** 数据量很小（2 食堂 / 6 商家 / 20 菜品），一次性把三级树拉全，级联选择器才能预设值 */
async function loadTree(): Promise<Option[]> {
  const canteens = await fetchCanteens()
  return Promise.all(
    canteens.map(async (canteen) => {
      const merchants = await fetchCanteenMerchants(canteen.id)
      return {
        value: canteen.id,
        label: canteen.name,
        children: await Promise.all(
          merchants.map(async (merchant) => {
            const dishes = await fetchMerchantDishes(merchant.id)
            return {
              value: merchant.id,
              label: merchant.name,
              children: dishes.map((dish) => ({ value: dish.id, label: dish.name })),
            }
          }),
        ),
      }
    }),
  )
}

/** 从菜品详情页跳过来时带上 dish_id，自动把三级都选好 */
function preselect(targetDishId: number): void {
  for (const canteen of options.value) {
    for (const merchant of canteen.children || []) {
      const dish = (merchant.children || []).find((item) => item.value === targetDishId)
      if (dish) {
        cascaderValue.value = [canteen.value, merchant.value, dish.value]
        return
      }
    }
  }
}

async function load(): Promise<void> {
  treeLoading.value = true
  treeError.value = null
  try {
    options.value = await loadTree()
    const fromQuery = Number(route.query.dish_id || 0)
    if (fromQuery) preselect(fromQuery)
  } catch (e) {
    // 三级树拉不到就没法选菜，表单不该显示成"空的可选项"
    treeError.value = e
  } finally {
    treeLoading.value = false
  }
}

onMounted(load)

const savedText = computed(() => {
  if (!saved.count) return ''
  const ratio = saved.before ? Math.round((1 - saved.after / saved.before) * 100) : 0
  return `已自动压缩 ${saved.count} 张：${humanSize(saved.before)} → ${humanSize(saved.after)}（省 ${ratio}%）`
})

function customUpload(uploadOptions: UploadRequestOptions): Promise<unknown> {
  return uploadImage(uploadOptions.file as File)
    .then((result) => {
      images.value.push(result.url)
      if (result.compress?.compressed) {
        saved.count += 1
        saved.before += result.compress.originalSize
        saved.after += result.compress.size
      }
      uploadOptions.onSuccess(result)
    })
    .catch((error: Error) => {
      ElMessage.error(error.message || '上传失败')
      uploadOptions.onError(error as never)
    })
}

function onRemove(file: UploadUserFile): void {
  const url = (file.response as { url?: string } | undefined)?.url
  if (url) images.value = images.value.filter((item) => item !== url)
  fileList.value = fileList.value.filter((item) => item.uid !== file.uid)
}

function beforeUpload(file: File): boolean {
  const allowed = ['image/jpeg', 'image/png', 'image/webp']
  if (!allowed.includes(file.type)) {
    ElMessage.warning('只支持 jpg / png / webp')
    return false
  }
  // 原图上限直接取服务端限制（10MB），选之前就拦住，不用等压缩完才发现传不上去。
  // 压缩后一般只有几百 KB，这个数字只对"压缩失败退回原图"和"误选了视频"有意义。
  if (file.size > UPLOAD_MAX_MB * 1024 * 1024) {
    ElMessage.warning(`单张图片不能超过 ${UPLOAD_MAX_MB}MB，可以先在相册里裁剪一下`)
    return false
  }
  return true
}

async function submit(): Promise<void> {
  if (!dishId.value) {
    ElMessage.warning('先选好吃的是哪家的哪道菜')
    return
  }
  if (!form.score) {
    ElMessage.warning('给这道菜打个分吧')
    return
  }
  submitting.value = true
  try {
    const post = await createPost({
      dish_id: dishId.value,
      score: form.score,
      content: form.content.trim() || undefined,
      images: images.value,
    })
    done.value = post
    void loadRank(post)
  } catch {
    // 拦截器已提示；留在表单上让用户重试，输入内容不能丢
  } finally {
    submitting.value = false
  }
}

/** 发完一条，把"这道菜现在几分、离高分榜还差多远"算出来 */
async function loadRank(post: Post): Promise<void> {
  // 不达标的菜不必查榜：省一次请求，也避免前端自己判断门槛和后端漂移
  if (post.dish.avg_rating < 4 || post.dish.rating_count < 2) {
    rank.value = null
    return
  }
  rankLoading.value = true
  try {
    const top = await fetchTopDishes({ limit: 20 })
    const index = top.findIndex((item) => item.id === post.dish.id)
    rank.value = index >= 0 ? index + 1 : null
  } catch {
    // 榜单查不到不影响"发布成功"这件事本身
    rank.value = null
  } finally {
    rankLoading.value = false
  }
}

/** 再发一条：清干净表单，但保留刚才选的三级联动，通常是在同一家店连着发 */
function again(): void {
  done.value = null
  rank.value = null
  rankLoading.value = false
  form.score = 0
  form.content = ''
  images.value = []
  fileList.value = []
  saved.before = 0
  saved.after = 0
  saved.count = 0
}
</script>

<template>
  <div class="page narrow">
    <PostResultPanel
      v-if="done"
      :post="done"
      :rank="rank"
      :rank-loading="rankLoading"
      @again="again"
      @home="router.push({ name: 'home' })"
    />

    <template v-else>
      <h1 class="page-title">发一条食评</h1>
      <p class="muted sub">
        当前身份：{{ auth.user?.title_emoji }} {{ auth.displayName }} · {{ auth.user?.title_name }}
      </p>

    <div class="card">
      <AppSkeleton v-if="treeLoading" variant="form" :count="3" />

      <ErrorState v-else-if="treeError" :error="treeError" title="菜品列表没加载出来" @retry="load" />

      <el-form v-else label-position="top">
        <el-form-item label="吃什么（食堂 / 商家 / 菜品）" required>
          <el-cascader
            v-model="cascaderValue"
            :options="options"
            :props="{ expandTrigger: 'hover' }"
            placeholder="按顺序选：食堂 → 商家 → 菜品"
            clearable
            filterable
            class="full"
          />
          <div v-if="dishLabel" class="tiny chosen">已选：{{ dishLabel }}</div>
        </el-form-item>

        <el-form-item label="给这道菜打分" required>
          <div class="rate-row">
            <el-rate v-model="form.score" :max="5" size="large" />
            <span class="tiny">{{ form.score ? `${form.score} 星` : '1-5 星，必选' }}</span>
          </div>
        </el-form-item>

        <el-form-item label="说点什么（选填，500 字以内）">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="5"
            maxlength="500"
            show-word-limit
            placeholder="好吃在哪？踩雷在哪？给同学们一点参考"
          />
        </el-form-item>

        <el-form-item label="图片（选填，最多 4 张）">
          <el-upload
            v-model:file-list="fileList"
            list-type="picture-card"
            :limit="4"
            :http-request="customUpload"
            :before-upload="beforeUpload"
            :on-remove="onRemove"
            accept="image/jpeg,image/png,image/webp"
          >
            <span class="plus">＋</span>
          </el-upload>
          <div v-if="savedText" class="tiny saved">{{ savedText }}</div>
        </el-form-item>

        <div class="actions">
          <el-button round @click="router.back()">取消</el-button>
          <el-button type="primary" round :loading="submitting" @click="submit">发布</el-button>
        </div>
      </el-form>
    </div>

    <p class="tiny note">
      提示：同一道菜重复打分不会新增记录，会覆盖你之前的评分（评分代表你当前的看法）。
    </p>
    </template>
  </div>
</template>

<style scoped>
.narrow {
  max-width: 720px;
}

.page-title {
  margin: 0 0 4px;
  font-size: 22px;
}

.sub {
  margin: 0 0 18px;
  font-size: 13px;
}

.full {
  width: 100%;
}

.chosen {
  margin-top: 6px;
  color: var(--brand-dark);
}

.rate-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.plus {
  font-size: 22px;
  color: var(--text-3);
}

.saved {
  margin-top: 6px;
  color: #4f8a2f;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}

.note {
  margin-top: 12px;
  text-align: center;
}
</style>
