/**
 * 上传前压缩。
 *
 * 手机拍的食物照通常 3-5MB / 4000px 宽，而卡片里最宽只显示到 600px 左右，
 * 原样上传既慢又浪费磁盘。这里在浏览器端按最长边缩放后重编码成 WebP。
 *
 * 三条原则：
 * 1. 任何一步失败都退回原图 —— 压缩是优化，不是前置条件，不能因为它传不上去。
 * 2. 压完反而更大就不用（小图、已优化过的图会出现这种情况）。
 * 3. 文件名后缀跟着实际编码走 —— 后端会校验扩展名与文件头魔数是否一致。
 */

export interface CompressOptions {
  /** 最长边像素，默认 1600 */
  maxEdge?: number
  /** 编码质量 0-1，默认 0.82 */
  quality?: number
}

export interface CompressResult {
  /** 实际要上传的文件（可能是原图） */
  file: File
  originalSize: number
  size: number
  /** 原图尺寸；解码失败时为 0 */
  width: number
  height: number
  compressed: boolean
}

const DEFAULT_MAX_EDGE = 1600
const DEFAULT_QUALITY = 0.82
/** 小于这个体积且尺寸不超标就原样上传，再压可能变大 */
const SKIP_BELOW_BYTES = 300 * 1024

const SUPPORTED = /^image\/(jpeg|png|webp)$/
const EXT_BY_MIME: Record<string, string> = {
  'image/webp': '.webp',
  'image/jpeg': '.jpg',
  'image/png': '.png',
}

interface Decoded {
  source: CanvasImageSource
  width: number
  height: number
  release: () => void
}

/** 解码成可画进 canvas 的源。优先 createImageBitmap，它不占 DOM 且能处理 EXIF 方向。 */
async function decode(file: File): Promise<Decoded> {
  if (typeof createImageBitmap === 'function') {
    try {
      // imageOrientation: 'from-image' 让竖拍照片按 EXIF 摆正，否则会躺倒 90°
      const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
      return { source: bitmap, width: bitmap.width, height: bitmap.height, release: () => bitmap.close() }
    } catch {
      // 老浏览器不认这个选项，往下走 <img>
    }
  }

  const url = URL.createObjectURL(file)
  try {
    const img = new Image()
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve()
      img.onerror = () => reject(new Error('图片解码失败'))
      img.src = url
    })
    return { source: img, width: img.naturalWidth, height: img.naturalHeight, release: () => URL.revokeObjectURL(url) }
  } catch (error) {
    URL.revokeObjectURL(url)
    throw error
  }
}

function toBlob(canvas: HTMLCanvasElement, type: string, quality: number): Promise<Blob | null> {
  return new Promise((resolve) => canvas.toBlob(resolve, type, quality))
}

/** 换后缀：后端靠扩展名判断类型，编码成 webp 后还叫 .jpg 会被魔数校验拒掉 */
function renameWithExt(name: string, mime: string): string {
  const base = name.replace(/\.[^./\\]+$/, '') || 'image'
  return `${base}${EXT_BY_MIME[mime] ?? '.jpg'}`
}

export async function compressImage(file: File, options: CompressOptions = {}): Promise<CompressResult> {
  const maxEdge = options.maxEdge ?? DEFAULT_MAX_EDGE
  const quality = options.quality ?? DEFAULT_QUALITY
  const untouched: CompressResult = {
    file,
    originalSize: file.size,
    size: file.size,
    width: 0,
    height: 0,
    compressed: false,
  }

  if (!SUPPORTED.test(file.type)) return untouched

  let decoded: Decoded
  try {
    decoded = await decode(file)
  } catch {
    return untouched
  }

  const { source, width, height } = decoded
  try {
    if (file.size <= SKIP_BELOW_BYTES && Math.max(width, height) <= maxEdge) {
      return { ...untouched, width, height }
    }

    const scale = Math.min(1, maxEdge / Math.max(width, height))
    const targetWidth = Math.max(1, Math.round(width * scale))
    const targetHeight = Math.max(1, Math.round(height * scale))

    const canvas = document.createElement('canvas')
    canvas.width = targetWidth
    canvas.height = targetHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return { ...untouched, width, height }

    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'
    // 铺白底：PNG 透明区域转 JPEG 时会变黑，WebP 支持透明但先铺底更稳
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, targetWidth, targetHeight)
    ctx.drawImage(source, 0, 0, targetWidth, targetHeight)

    const blob = (await toBlob(canvas, 'image/webp', quality)) ?? (await toBlob(canvas, 'image/jpeg', quality))
    if (!blob) return { ...untouched, width, height }
    if (blob.size >= file.size) return { ...untouched, width, height }

    return {
      file: new File([blob], renameWithExt(file.name, blob.type), { type: blob.type, lastModified: Date.now() }),
      originalSize: file.size,
      size: blob.size,
      width: targetWidth,
      height: targetHeight,
      compressed: true,
    }
  } catch {
    return { ...untouched, width, height }
  } finally {
    decoded.release()
  }
}

/** 字节数转成给人看的形式：2.4 MB / 380 KB */
export function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
