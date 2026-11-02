import { getToken } from './request'
import { compressImage, type CompressOptions, type CompressResult } from '@/utils/image'
import type { UploadResult } from '@/types'

export interface UploadOutcome extends UploadResult {
  /** 压缩明细；跳过压缩时 compressed=false */
  compress?: CompressResult
}

/**
 * 服务端单张上限，**与后端 `UPLOAD_MAX_MB` 保持一致**（默认 10）。
 *
 * 改这里的同时要改 `backend/app/core/config.py` 和 `.env`，否则会出现
 * "前端放行、后端 400"或"前端误拦"。
 */
export const UPLOAD_MAX_MB = 10
export const UPLOAD_MAX_BYTES = UPLOAD_MAX_MB * 1024 * 1024

/**
 * 上传图片。**会先在浏览器端压缩**，再发 multipart。
 *
 * 走 XHR 而不是 axios：multipart 的 boundary 交给浏览器生成。
 * 压缩失败不影响上传（compressImage 内部会退回原图）。
 */
export async function uploadImage(file: File, options: CompressOptions = {}): Promise<UploadOutcome> {
  const compress = await compressImage(file, options)
  // 不管压缩成功与否，只看最终要传的那个文件：超了就提前拦下，
  // 别让用户等一个注定 400 的请求（压缩"成功"但体积仍超标是可能的，比如扫描件 PNG 转 WebP）
  if (compress.file.size > UPLOAD_MAX_BYTES) {
    const mb = (compress.file.size / 1024 / 1024).toFixed(1)
    throw new Error(
      compress.compressed
        ? `这张图压缩后还有 ${mb}MB，超过了 ${UPLOAD_MAX_MB}MB 上限，请裁剪后再试`
        : `图片有 ${mb}MB，超过了 ${UPLOAD_MAX_MB}MB 上限，请裁剪后再试`,
    )
  }
  const payload = await postFile(compress.file)
  return { ...payload, compress }
}

function postFile(file: File): Promise<UploadResult> {
  return new Promise((resolve, reject) => {
    const form = new FormData()
    form.append('file', file)

    const xhr = new XMLHttpRequest()
    xhr.open('POST', '/api/v1/uploads/images')
    const token = getToken()
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)

    xhr.onload = () => {
      try {
        const body = JSON.parse(xhr.responseText)
        if (body.code === 0) resolve(body.data as UploadResult)
        else reject(new Error(body.message || '上传失败'))
      } catch {
        reject(new Error('上传失败'))
      }
    }
    xhr.onerror = () => reject(new Error('网络异常，上传失败'))
    xhr.send(form)
  })
}
