import { useMemo } from 'react'
import { motion } from 'framer-motion'
import type { ActivityItem } from '../lib/api'

interface Props {
  label: string
  value: number | string
  color: string
  trend?: number       // percentage change (positive = up, negative = down)
  trendLabel?: string  // "vs yesterday" etc.
  sparklineData?: ActivityItem[] // to generate mini sparkline
  sparklineColor?: string
}

function generateSparkline(activities: ActivityItem[], barCount = 18): (number | null)[] {
  if (!activities.length) return Array(barCount).fill(null)
  // Build histogram: group by hour for last 24h
  const now = Date.now()
  const buckets = new Array(barCount).fill(0)
  const oneHour = 3600 * 1000

  for (const a of activities) {
    const age = now - a.time * 1000
    const bucket = Math.floor(age / oneHour)
    if (bucket >= 0 && bucket < barCount) {
      buckets[barCount - 1 - bucket]++
    }
  }
  const max = Math.max(...buckets, 1)
  return buckets.map(v => v / max)
}

export function StatCard({ label, value, color, trend, trendLabel, sparklineData, sparklineColor }: Props) {
  const bars = useMemo(() => sparklineData ? generateSparkline(sparklineData) : [], [sparklineData])

  return (
    <motion.div
      className="surface-card interactive p-3 cursor-default group"
      variants={{ hidden: { opacity: 0, y: 6 }, show: { opacity: 1, y: 0 } }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* Label row */}
      <div className="flex items-center justify-between mb-0.5">
        <span className="text-2xs text-text-tertiary">{label}</span>
        {trend !== undefined && (
          <span
            className={`text-2xs font-semibold ${trend >= 0 ? 'text-success' : 'text-danger'}`}
          >
            {trend >= 0 ? '\u2191' : '\u2193'} {Math.abs(trend)}%
          </span>
        )}
      </div>

      {/* Value */}
      <div className="flex items-end gap-2 mb-1">
        <span
          className="text-lg font-semibold stat-value leading-none"
          style={{ color: `hsl(${color})` }}
        >
          {value}
        </span>
        {trendLabel && (
          <span className="text-2xs text-text-tertiary/50 pb-0.5">{trendLabel}</span>
        )}
      </div>

      {/* Mini sparkline */}
      {bars.some(b => b !== null) && (
        <div className="flex items-end gap-px h-[28px] mt-1">
          {bars.map((pct, i) => (
            <div key={i} className="flex-1" style={{ height: '100%', display: 'flex', alignItems: 'flex-end' }}>
              <motion.div
                className="w-full rounded-t-sm"
                style={{
                  backgroundColor: sparklineColor || `hsl(var(--brand-cyan))`,
                  opacity: (pct ?? 0.01) * 0.8 + 0.1,
                }}
                initial={{ height: 0 }}
                animate={{ height: `${(pct ?? 0) * 100}%` }}
                transition={{ duration: 0.6, delay: i * 0.03, ease: 'easeOut' }}
              />
            </div>
          ))}
        </div>
      )}

      {/* Trend arrow indicator */}
      {trend !== undefined && (
        <div className="mt-1 flex items-center gap-1">
          <div className="flex-1 h-0.5 rounded-full bg-surface-2 overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{ backgroundColor: trend >= 0 ? '#10b981' : '#ef4444' }}
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(Math.abs(trend), 100)}%` }}
              transition={{ duration: 0.8, delay: 0.2 }}
            />
          </div>
          <span className={`text-2xs ${trend >= 0 ? 'text-success/60' : 'text-danger/60'}`}>
            {trend >= 0 ? '+' : ''}{trend}%
          </span>
        </div>
      )}
    </motion.div>
  )
}
