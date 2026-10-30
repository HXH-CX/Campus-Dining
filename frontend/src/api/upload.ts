import { getToken } from './request'
import type { UploadResult } from '@/types'

/** 走 XHR 而不是 axios：需要上传进度，且 multipart 由浏览器自己生成 boundary */
export function uploadImage(file: File): Promise<UploadResult> {
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
