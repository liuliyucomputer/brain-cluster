export function cn(...inputs: (string | undefined | null | false)[]): string {
  return inputs.filter(Boolean).join(' ')
}

export function formatTime(date: Date): string {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function formatNumber(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)
}

export function percent(value: number, total: number): number {
  return total > 0 ? Math.round((value / total) * 100) : 0
}

export function formatDuration(seconds: number | null): string {
  if (seconds == null) return '--'
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}h ${m}m`
}

export function formatTimestamp(ts: number | null): string {
  if (!ts) return '--'
  const d = new Date(ts * 1000)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  
  if (diff < 60000) return 'just now / 刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago / ${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago / ${Math.floor(diff / 3600000)}小时前`
  if (diff < 172800000) return `yesterday / 昨天`
  
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

export function formatRelativeTimestamp(ts: number): string {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  const now = Date.now()
  const diff = now - d.getTime()
  
  if (diff < 60000) return '刚刚 / just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前 / ${Math.floor(diff / 60000)}m`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前 / ${Math.floor(diff / 3600000)}h`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

// Bilingual label helper
export function label(zh: string, en: string): string {
  return `${zh} / ${en}`
}

// Status colors
export const STATUS_COLORS: Record<string, string> = {
  pending: '#6366f1',
  in_progress: '#3b82f6',
  review: '#f59e0b',
  done: '#22c55e',
  archived: '#8b5cf6',
  error: '#ef4444',
}

export const STATUS_LABELS: Record<string, [string, string]> = {
  pending: ['待处理', 'Pending'],
  in_progress: ['执行中', 'Running'],
  review: ['审查中', 'Review'],
  done: ['已完成', 'Done'],
  archived: ['已归档', 'Archived'],
  error: ['错误', 'Error'],
}
