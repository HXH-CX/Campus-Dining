<script setup lang="ts">
/**
 * 帖子编辑弹窗。
 *
 * 只改文案与配图：菜品和评分属于「我的看法」，要改就重新发帖（会覆盖评分），
 * 编辑一条历史帖子不该悄悄改掉菜品均分。
 */
import { ref, watch } from 'vue'
import type { UploadRequestOptions, UploadUserFile } from 'element-plus'
import { ElMessage } from '@/utils/feedback'
import { updatePost } from '@/api/post'
import { uploadImage } from '@/api/upload'
import type { Post } from '@/types'

const props = defineProps<{ modelValue: boolean; post: Post }>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved', post: Post): void
}>()

const content = ref('')
const images = ref<string[]>([])
const fileList = ref<UploadUserFile[]>([])
const saving = ref(false)

const visible = ref(props.modelValue)
watch(
  () => props.modelValue,
  (value) => {
    visible.value = value
    if (!value) return
    // 每次打开都从当前帖子重新取，避免上次取消留下的脏数据
    content.value = props.post.content || ''
    images.value = [...(props.post.images || [])]
    fileList.value = images.value.map((url, index) => ({ name: `图 ${index + 1}`, url }))
  },
)

function close(): void {
  visible.value = false
  emit('update:modelValue', false)
}

function customUpload(options: UploadRequestOptions): Promise<unknown> {
  return uploadImage(options.file as File)
    .then((result) => {
      images.value.push(result.url)
      options.onSuccess(result)
    })
    .catch((error: Error) => {
      ElMessage.error(error.message || '上传失败')
      options.onError(error as never)
    })
}

function onRemove(file: UploadUserFile): void {
  // 预填的老图没有 response，只能靠 file.url 识别
  const url = (file.response as { url?: string } | undefined)?.url || file.url
  if (url) images.value = images.value.filter((item) => item !== url)
  fileList.value = fileList.value.filter((item) => item.uid !== file.uid)
}

function beforeUpload(file: File): boolean {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    ElMessage.warning('只支持 jpg / png / webp')
    return false
  }
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.warning('单张图片不能超过 20MB')
    return false
  }
  return true
}

async function save(): Promise<void> {
  saving.value = true
  try {
    // 显式传空串会被后端 strip 成 null —— 清空文案就是有意为之
    const updated = await updatePost(props.post.id, {
      content: content.value.trim() || null,
      images: images.value,
    })
    ElMessage.success('已更新')
    emit('saved', updated)
    close()
  } catch {
    // 拦截器已提示
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog
    v-model="visible"
    title="编辑这条食评"
    width="560px"
    :close-on-click-modal="false"
    @close="emit('update:modelValue', false)"
  >
    <el-form label-position="top">
      <el-form-item label="说点什么（500 字以内）">
        <el-input
          v-model="content"
          type="textarea"
          :rows="5"
          maxlength="500"
          show-word-limit
          placeholder="好吃在哪？踩雷在哪？"
        />
      </el-form-item>

      <el-form-item label="图片（最多 4 张）">
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
      </el-form-item>
    </el-form>

    <p class="tiny note">菜品和评分不能在这里改：评分代表你现在的看法，要改请重新发一条（会覆盖原评分）。</p>

    <template #footer>
      <el-button round @click="close">取消</el-button>
      <el-button type="primary" round :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.plus {
  font-size: 22px;
  color: var(--text-3);
}

.note {
  margin: 0;
  color: var(--text-3);
  line-height: 1.5;
}
</style>
