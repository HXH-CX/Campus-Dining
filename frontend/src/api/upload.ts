import { getToken } from './request'
import { compressImage, type CompressOptions, type CompressResult } from '@/utils/image'
import type { UploadResult } from '@/types'

export interface UploadOutcome extends UploadResult {
  /** 压缩明细；跳过压缩时 compressed=false */
  compress?: CompressResult
}

/**
 * 上传图片。**会先在浏览器端压缩**，再发 multipart。
 *
 * 走 XHR 而不是 axios：multipart 的 boundary 交给浏览器生成。
 * 压缩失败不影响上传（compressImage 内部会退回原图）。
 */
export async function uploadImage(file: File, options: CompressOptions = {}): Promise<UploadOutcome> {
  const compress = await compressImage(file, options)
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
