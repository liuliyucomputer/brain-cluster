import { motion } from 'framer-motion'
import { label } from '../lib/utils'
import type { ClusterStatsV2 } from '../lib/api'

interface Props {
  current: ClusterStatsV2
  previous: ClusterStatsV2
  onClose: () => void
}

function DiffBadge({ cur, prev }: { cur: number; prev: number }) {
  const diff = cur - prev
  if (diff === 0) return <span className="text-2xs text-text-tertiary">{'\u2194'} 0</span>
  const up = diff > 0
  return (
    <span className={`text-2xs font-semibold ${up ? 'text-success' : 'text-danger'}`}>
      {up ? '\u2191' : '\u2193'} {Math.abs(diff)}
    </span>
  )
}

export function ComparisonView({ current, previous, onClose }: Props) {
  const cur = current.overview
  const prev = previous.overview

  const comparisons = [
    { label: label('总任务', 'Tasks'),     cur: cur.total,        prev: prev.total },
    { label: label('活跃', 'Active'),      cur: cur.active,       prev: prev.active },
    { label: label('已完成', 'Done'),      cur: cur.done,         prev: prev.done },
    { label: label('今日完成', 'Today'),   cur: cur.done_today,   prev: prev.done_today },
    { label: label('均耗时', 'Avg time'),  cur: cur.avg_duration, prev: prev.avg_duration, format: (v: number) => `${v}s` },
    { label: '24h 创建',                   cur: current.timeline.created_24h, prev: previous.timeline.created_24h },
    { label: '24h 完成',                   cur: current.timeline.completed_24h, prev: previous.timeline.completed_24h },
    { label: 'Letta Sync',                 cur: current.letta_sync_files, prev: previous.letta_sync_files },
  ]

  const pipelineStages = Object.keys(current.pipeline)

  return (
    <motion.div className="max-w-[1600px] mx-auto px-6 py-4"
      initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xs font-semibold text-text-primary">
          {label('对比视图', 'Comparison View')}
          <span className="text-text-tertiary font-normal ml-2 text-2xs">
            {label('当前 vs 上次采样', 'Current vs Previous Sample')}
          </span>
        </h2>
        <button onClick={onClose} className="text-2xs text-text-tertiary hover:text-text-secondary transition-colors px-2 py-1 rounded border border-border-default hover:border-border-hover">
          {label('关闭对比', 'Close')}
        </button>
      </div>

      {/* KPI comparison grid */}
      <div className="grid grid-cols-4 gap-2 mb-4">
        {comparisons.map((item, i) => (
          <div key={i} className="surface-card p-3">
            <div className="text-2xs text-text-tertiary mb-1">{item.label}</div>
            <div className="flex items-baseline justify-between">
              <span className="text-lg font-semibold stat-value text-text-primary">
                {item.format ? item.format(item.cur) : item.cur}
              </span>
              <span className="text-xs text-text-tertiary tabular-nums">
                {item.format ? item.format(item.prev) : item.prev}
              </span>
            </div>
            <div className="flex items-center gap-1.5 mt-1">
              <DiffBadge cur={item.cur as number} prev={item.prev as number} />
              <div className="flex-1 h-0.5 rounded-full bg-surface-2 overflow-hidden">
                <motion.div className="h-full rounded-full"
                  style={{ backgroundColor: (item.cur as number) >= (item.prev as number) ? '#10b981' : '#ef4444' }}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(Math.abs(((item.cur as number) - (item.prev as number)) / Math.max(item.prev as number || 1, 1)) * 100, 100)}%` }}
                  transition={{ duration: 0.8, delay: i * 0.1 }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Pipeline comparison */}
      <div className="surface-card p-4">
        <h3 className="text-2xs font-medium text-text-tertiary uppercase tracking-wider mb-3">
          Pipeline {label('对比', 'Comparison')}
        </h3>
        <div className="grid grid-cols-5 gap-2">
          {pipelineStages.map(stage => {
            const c = current.pipeline[stage]?.count ?? 0
            const p = previous.pipeline[stage]?.count ?? 0
            const max = Math.max(c, p, 1)
            const cRatio = (c / max) * 80
            const pRatio = (p / max) * 80
            const diff = c - p
            return (
              <div key={stage} className="text-center">
                <div className="text-2xs text-text-primary mb-2">{stage}</div>
                <div className="flex items-end justify-center gap-2 h-[90px] mb-1">
                  <div className="flex flex-col items-center gap-0.5">
                    <span className="text-2xs text-text-tertiary">{c}</span>
                    <motion.div className="w-8 rounded-t-md"
                      style={{ backgroundColor: diff >= 0 ? '#10b981' : '#ef4444', opacity: 0.4 }}
                      initial={{ height: 0 }} animate={{ height: cRatio }} transition={{ duration: 0.6, delay: 0.2 }}
                    />
                  </div>
                  <div className="flex flex-col items-center gap-0.5">
                    <span className="text-2xs text-text-tertiary">{p}</span>
                    <motion.div className="w-8 rounded-t-md"
                      style={{ backgroundColor: 'hsl(var(--text-tertiary))', opacity: 0.2 }}
                      initial={{ height: 0 }} animate={{ height: pRatio }} transition={{ duration: 0.6 }}
                    />
                  </div>
                </div>
                <DiffBadge cur={c} prev={p} />
              </div>
            )
          })}
        </div>
      </div>
    </motion.div>
  )
}
