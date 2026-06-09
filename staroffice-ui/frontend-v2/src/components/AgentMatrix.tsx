import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface AgentInfo {
  pending: number; in_progress: number; done: number; failed: number
  total: number; last_title: string | null; last_status: string
}

interface Props {
  agents: Record<string, AgentInfo> | null
}

const AGENT_NAMES: Record<string, [string, string]> = {
  strategist:       ['\u7b56\u7565', '#6366f1'],
  'executor-a':     ['\u6587\u6848', '#22d3ee'],
  'executor-b':     ['PPT',  '#a855f7'],
  'executor-c':     ['\u6570\u636e', '#f59e0b'],
  monitor:          ['\u76d1\u63a7', '#c084fc'],
  'reviewer-strict':  ['\u4e25\u5ba1', '#f87171'],
  'reviewer-creative':['\u521b\u5ba1', '#fb923c'],
  arbiter:          ['\u4ef2\u88c1', '#6366f1'],
  learner:          ['\u5b66\u4e60', '#10b981'],
}

function heatColor(load: number): string {
  if (load >= 6) return '#ef4444'
  if (load >= 4) return '#f59e0b'
  if (load >= 2) return '#22d3ee'
  return 'hsl(var(--border-default))'
}

export function AgentMatrix({ agents }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null)

  if (!agents || Object.keys(agents).length === 0) return (
    <div className="surface-card p-4 text-center text-text-tertiary text-xs">\u6682\u65e0\u667a\u80fd\u4f53\u6570\u636e</div>
  )

  const entries = Object.entries(agents).sort(([, a], [, b]) => b.total - a.total)
  const maxLoad = Math.max(...entries.map(([, a]) => a.total), 1)
  const avgHours = entries.reduce((s, [, a]) => s + (a.total > 0 ? a.done / Math.max(a.total, 1) : 0), 0) / entries.length * 100

  return (
    <div className="surface-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-2xs font-medium text-text-tertiary uppercase tracking-wider">
          \u667a\u80fd\u4f53\u8d1f\u8f7d / Agent Load
        </h2>
        <span className="text-2xs text-text-tertiary">
          avg success {avgHours.toFixed(0)}%
        </span>
      </div>

      <div className="grid grid-cols-3 gap-1.5">
        {entries.map(([name, a], i) => {
          const [zhName, color] = AGENT_NAMES[name] || [name, '#6b7280']
          const isActive = a.in_progress > 0
          const load = a.total
          const heatBg = heatColor(load)

          return (
            <motion.div
              key={name}
              className="rounded-lg border border-border-default p-2.5 cursor-pointer relative overflow-hidden transition-all"
              style={{
                backgroundColor: `hsl(var(--surface-0) / 0.4)`,
                borderColor: expanded === name ? `${color}40` : 'hsl(var(--border-default))',
                boxShadow: expanded === name ? `0 0 12px ${color}20` : 'none',
              }}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              whileHover={{ y: -2 }}
              onClick={() => setExpanded(expanded === name ? null : name)}
            >
              {/* Agent header */}
              <div className="flex items-center gap-1.5 mb-1.5">
                <span className={`status-dot ${isActive ? 'online' : ''}`}
                  style={{ backgroundColor: color, boxShadow: isActive ? `0 0 6px ${color}80` : 'none', animation: isActive ? 'status-pulse 2s ease-in-out infinite' : 'none' }} />
                <span className="text-xs font-semibold" style={{ color }}>{zhName}</span>
              </div>

              {/* Load heat bar */}
              <div className="w-full h-1.5 bg-surface-2 rounded-full overflow-hidden mb-1.5">
                <motion.div className="h-full rounded-full"
                  style={{ backgroundColor: heatBg }}
                  initial={{ width: 0 }}
                  animate={{ width: `${((load / maxLoad) * 100).toFixed(0)}%` }}
                  transition={{ duration: 0.6, delay: i * 0.05 }}
                />
              </div>

              {/* Stats row */}
              <div className="flex items-center gap-1.5 text-2xs">
                <span className="text-success/80" title="done">\u2713{a.done}</span>
                <span className="text-warning/80" title="active">{a.in_progress}</span>
                <span className="text-danger/70" title="failed">{a.failed}</span>
                <span className="text-text-secondary ml-auto font-semibold" title="total" style={{ color: heatBg }}>{a.total}</span>
              </div>

              {/* Expanded detail */}
              <AnimatePresence>
                {expanded === name && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-2 pt-2 border-t border-border-default space-y-1">
                      <div className="flex justify-between text-2xs">
                        <span className="text-text-tertiary">Success rate</span>
                        <span className="text-text-secondary">{a.total > 0 ? ((a.done / a.total) * 100).toFixed(0) : 0}%</span>
                      </div>
                      <div className="flex justify-between text-2xs">
                        <span className="text-text-tertiary">Queue depth</span>
                        <span className="text-text-secondary">{a.pending + a.in_progress}</span>
                      </div>
                      <div className="flex justify-between text-2xs">
                        <span className="text-text-tertiary">Failures</span>
                        <span className={a.failed > 0 ? 'text-danger/80' : 'text-text-secondary'}>{a.failed}</span>
                      </div>
                      {a.last_title && (
                        <div className="text-2xs text-text-tertiary/60 truncate pt-1 border-t border-border-default/50">
                          Last: {a.last_title.slice(0, 40)}
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
