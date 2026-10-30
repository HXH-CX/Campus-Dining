/** 时间格式化。后端返回的是不带时区的 "2026-10-30T15:31:46"，本地开发直接按本地时间解析即可。 */

export function parseTime(value: string | null | undefined): Date | null {
  if (!value) return null
  const normalized = value.includes('T') ? value : value.replace(' ', 'T')
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

export function timeAgo(value: string | null | undefined): string {
  const date = parseTime(value)
  if (!date) return ''
  const diff = Date.now() - date.getTime()
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (diff < minute) return '刚刚'
  if (diff < hour) return `${Math.floor(diff / minute)} 分钟前`
  if (diff < day) return `${Math.floor(diff / hour)} 小时前`
  if (diff < 7 * day) return `${Math.floor(diff / day)} 天前`
  return formatDate(value)
}

export function formatDate(value: string | null | undefined): string {
  const date = parseTime(value)
  if (!date) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

/** 评分保留一位小数，0 分显示"暂无" */
export function formatRating(value: number | null | undefined): string {
  if (!value) return '暂无'
  return value.toFixed(1)
}
