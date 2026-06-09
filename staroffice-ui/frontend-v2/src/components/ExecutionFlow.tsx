import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { ClusterStatsV2, MonitorData } from '../lib/api'

interface StageConfig {
  key: string; num: number; zh: string; en: string; color: string; desc: string
}

const STAGES: StageConfig[] = [
  { key: 'trigger',  num: 1, zh: '触发入队', en: 'TRIGGER',  color: '#6366f1', desc: '用户CLI / Cron \u2192 Kanban DB' },
  { key: 'dispatch', num: 2, zh: '状态调度', en: 'DISPATCH',  color: '#3b82f6', desc: 'Gateway 60s轮询 \u2192 启动Agent' },
  { key: 'strategy', num: 3, zh: '智能路由', en: 'STRATEGY',  color: '#f59e0b', desc: 'Strategist 任务分解 \u2192 分配' },
  { key: 'execute',  num: 4, zh: '并行执行', en: 'EXECUTE',   color: '#10b981', desc: 'A/B/C 三路并行创作' },
  { key: 'review',   num: 5, zh: '双审仲裁', en: 'REVIEW',    color: '#a855f7', desc: '双审 \u2192 三路分支 \u2192 仲裁' },
  { key: 'memory',   num: 6, zh: '记忆沉淀', en: 'MEMORY',    color: '#22d3ee', desc: '蒸馏 \u2192 固化 \u2192 长期知识' },
]

const MODULES = [
  { name: 'execution_flow.py',     role: '策略路由+双审判定', status: 'ready' as const },
  { name: 'pipeline_orchestrator.py', role: '30秒后台守护',   status: 'ready' as const },
  { name: 'memory_bridge.py',      role: 'kanban\u2192日志同步',status: 'ready' as const },
  { name: 'memory_engine.py',      role: 'Letta记忆CRUD',     status: 'ready' as const },
  { name: 'extension_bridge.py',   role: '6条扩展线管理',     status: 'ready' as const },
  { name: 'stats_api.py',          role: 'Grafana数据源 :19999',status: 'running' as const },
  { name: 'paths.py',              role: '全项目路径管理',     status: 'ready' as const },
  { name: 'log_manager.py',        role: '日志写入+轮转',     status: 'ready' as const },
]

interface Props {
  stats: ClusterStatsV2
  monitor: MonitorData | null
}

export function ExecutionFlow({ stats, monitor }: Props) {
  const [playbackStage, setPlaybackStage] = useState(-1)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (playing) {
      const interval = 1000 / speed
      timerRef.current = setInterval(() => {
        setPlaybackStage(s => (s + 1) % 6)
      }, interval)
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [playing, speed])

  const pipeline = stats.pipeline
  const pending = pipeline.pending?.count || 0
  const inProgress = pipeline.in_progress?.count || 0
  const done = pipeline.done?.count || 0
  const archived = pipeline.archived?.count || 0
  const review = pipeline.review?.count || 0
  const total = pending + inProgress + review + done + archived

  const activeStage = pending > 0 ? 0 : inProgress > 0 ? 3 : review > 0 ? 4 : done > 0 ? 5 : 5

  const memoryLayers = monitor?.memory?.layers ?? {}
  const memoryTotal = Object.values(memoryLayers).reduce((s: number, l: any) => s + (l?.files || 0), 0)

  return (
    <div className="surface-card p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xs font-medium text-text-tertiary uppercase tracking-wider">执行流</h2>
        <div className="flex items-center gap-2">
          {/* Playback controls */}
          <button onClick={() => { setPlaying(!playing); if (!playing) setPlaybackStage(0) }}
            className={`text-2xs px-1.5 py-0.5 rounded border transition-all ${playing ? 'border-brand-cyan/40 text-brand-cyan bg-brand-cyan/10' : 'border-border-default text-text-tertiary hover:text-text-secondary'}`}>
            {playing ? '\u23f8\u23f8 Pause' : '\u25b6 Play'}
          </button>
          <button onClick={() => setPlaybackStage(-1)}
            className="text-2xs text-text-tertiary hover:text-text-secondary px-1">\u23f9</button>
          {[1, 2, 5].map(s => (
            <button key={s} onClick={() => setSpeed(s)}
              className={`text-2xs px-1 rounded ${speed === s ? 'text-brand-indigo' : 'text-text-tertiary/50'}`}>{s}x</button>
          ))}
          <span className="text-text-tertiary/30">|</span>
          <div className="flex items-center gap-3 text-2xs text-text-tertiary">
            <span>{total} 任务</span>
            <span className={activeStage < 3 ? 'text-warning' : activeStage < 5 ? 'text-success' : 'text-brand-violet'}>
              {STAGES[activeStage].zh}
            </span>
          </div>
        </div>
      </div>

      {/* 6-STAGE PIPELINE */}
      <div className="mb-5">
        <div className="flex items-stretch gap-0 relative">
          {STAGES.map((stage, i) => {
              const isActive = playing ? i <= playbackStage : i <= activeStage
              const isCurrent = playing ? i === playbackStage : i === activeStage
            const opacity = isActive ? 1 : 0.3

            const counts: Record<number, number> = {
              0: pending, 1: 0, 2: 0, 3: inProgress, 4: review, 5: done + archived,
            }
            const count = counts[i] || 0
            const maxCount = total > 0 ? Math.max(inProgress, review, done + archived, pending, 1) : 1
            const barHeight = total > 0 ? Math.max((count / maxCount) * 48, count > 0 ? 4 : 0) : 0

            return (
              <div key={stage.key} className="flex-1 flex flex-col items-center relative min-w-[100px]" style={{ opacity }}>
                {i > 0 && (
                  <div className="absolute left-0 top-[68px] w-full h-0.5 -translate-x-1/2" style={{
                    background: isActive
                      ? `linear-gradient(90deg, ${STAGES[i-1].color}60, ${stage.color}60)`
                      : 'hsl(var(--border-default))',
                  }}>
                    {isActive && (
                      <motion.div
                        className="absolute top-1/2 w-2 h-2 rounded-full -translate-y-1/2"
                        style={{ backgroundColor: stage.color, boxShadow: `0 0 8px ${stage.color}` }}
                        animate={{ left: ['0%', '100%'] }}
                        transition={{ duration: 2.5, repeat: Infinity, ease: 'linear' }}
                      />
                    )}
                  </div>
                )}

                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center text-2xs font-bold mb-1.5 relative"
                  style={{
                    backgroundColor: isCurrent ? `${stage.color}20` : isActive ? `${stage.color}10` : 'hsl(var(--surface-2))',
                    border: `2px solid ${isCurrent ? stage.color : isActive ? `${stage.color}40` : 'hsl(var(--border-default))'}`,
                    color: isCurrent ? stage.color : isActive ? 'hsl(var(--text-secondary))' : 'hsl(var(--text-tertiary))',
                  }}
                >
                  {stage.num}
                  {isCurrent && (
                    <motion.div
                      className="absolute inset-0 rounded-full"
                      style={{ border: `2px solid ${stage.color}40` }}
                      animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                    />
                  )}
                </div>

                <div className="w-full max-w-[60px] h-[48px] rounded-lg relative overflow-hidden mb-1.5" style={{
                  backgroundColor: 'hsl(var(--surface-2))',
                  border: `1px solid ${isActive ? stage.color + '20' : 'hsl(var(--border-default))'}`,
                }}>
                  <motion.div
                    className="absolute bottom-0 left-0 right-0 rounded-t-lg"
                    style={{ backgroundColor: stage.color }}
                    initial={{ height: 0 }}
                    animate={{ height: barHeight }}
                    transition={{ duration: 0.8, ease: 'easeOut', delay: i * 0.1 }}
                  />
                  {count > 0 && (
                    <span className="absolute inset-0 flex items-center justify-center text-xs font-bold"
                      style={{ color: '#fff', textShadow: '0 1px 2px rgba(0,0,0,0.8)' }}>
                      {count}
                    </span>
                  )}
                </div>

                <div className="text-center">
                  <div className="text-xs font-medium" style={{
                    color: isCurrent ? stage.color : isActive ? 'hsl(var(--text-primary))' : 'hsl(var(--text-tertiary))',
                  }}>
                    {stage.zh}
                  </div>
                  <div className="text-2xs text-text-tertiary/50 mt-0.5 max-w-[80px] text-center leading-tight">
                    {stage.desc}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* THREE-COLUMN DETAIL */}
      <div className="grid grid-cols-3 gap-3">
        {/* Executors */}
        <div className="rounded-lg border border-border-default bg-surface-0/40 p-3">
          <h3 className="text-2xs font-medium text-text-tertiary mb-2">执行器 / Executors</h3>
          <div className="space-y-1.5">
            {[
              { name: 'executor-a', zh: '文案创作', color: '#10b981' },
              { name: 'executor-b', zh: 'PPT设计',  color: '#22d3ee' },
              { name: 'executor-c', zh: '数据分析', color: '#f97316' },
            ].map(ex => {
              const agent = monitor?.agents?.[ex.name]
              const hasTasks = (agent?.total || 0) > 0
              return (
                <div key={ex.name} className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-surface-2/50 transition-colors">
                  <span className={`status-dot ${hasTasks ? 'online' : ''}`}
                    style={{
                      backgroundColor: ex.color,
                      boxShadow: hasTasks ? `0 0 6px ${ex.color}80` : 'none',
                      animation: hasTasks ? 'status-pulse 2s ease-in-out infinite' : 'none',
                    }} />
                  <span className="text-xs text-text-secondary flex-1">{ex.zh}</span>
                  {agent && (
                    <span className="text-2xs text-text-tertiary">{agent.done || 0} done / {agent.total} total</span>
                  )}
                  {hasTasks && (
                    <motion.div className="w-12 h-1 bg-surface-2 rounded-full overflow-hidden">
                      <motion.div className="h-full rounded-full" style={{ backgroundColor: ex.color }}
                        animate={{ width: `${((agent?.done || 0) / Math.max(agent?.total || 1, 1)) * 100}%` }}
                        transition={{ duration: 0.5 }} />
                    </motion.div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Review Chain */}
        <div className="rounded-lg border border-border-default bg-surface-0/40 p-3">
          <h3 className="text-2xs font-medium text-text-tertiary mb-2">审查链 / Review Chain</h3>
          <div className="space-y-1.5">
            {[
              { name: 'reviewer-strict',   zh: '严格审查 (\u226560)', color: '#f87171' },
              { name: 'reviewer-creative', zh: '创意审查 (\u226550)', color: '#fb923c' },
              { name: 'arbiter',           zh: '仲裁裁决',           color: '#fbbf24' },
            ].map(r => {
              const agent = monitor?.agents?.[r.name]
              return (
                <div key={r.name} className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-surface-2/50 transition-colors">
                  <span className="status-dot" style={{ backgroundColor: r.color }} />
                  <span className="text-xs text-text-secondary flex-1">{r.zh}</span>
                  {agent && <span className="text-2xs text-text-tertiary">tasks: {agent.total}</span>}
                </div>
              )
            })}
          </div>

          <div className="mt-3 pt-2 border-t border-border-default">
            <h3 className="text-2xs font-medium text-text-tertiary mb-1.5">分支判定</h3>
            <div className="grid grid-cols-3 gap-1">
              {[
                { label: 'PASS',  color: '#10b981', cond: 'S\u226560 & C\u226550' },
                { label: 'SPLIT', color: '#fbbf24', cond: '一个通过' },
                { label: 'FAIL',  color: '#f87171', cond: '均不通过' },
              ].map(b => (
                <div key={b.label} className="text-center rounded p-1.5" style={{ backgroundColor: `${b.color}08` }}>
                  <div className="text-2xs font-bold" style={{ color: b.color }}>{b.label}</div>
                  <div className="text-2xs text-text-tertiary/50">{b.cond}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Memory Pipeline */}
        <div className="rounded-lg border border-border-default bg-surface-0/40 p-3">
          <h3 className="text-2xs font-medium text-text-tertiary mb-2">管道记忆 / Pipeline Memory</h3>

          <div className="flex items-center gap-2 mb-2 pb-2 border-b border-border-default">
            <span className="text-xs">{'\ud83d\uddc4'}</span>
            <span className="text-xs text-text-secondary">kanban.db</span>
            <span className="text-2xs text-text-tertiary ml-auto">{monitor?.memory?.kanban_mb ?? 0} MB</span>
          </div>

          <div className="space-y-1">
            {[
              { label: 'daily 日志快照', key: 'daily',   color: '#a855f7', desc: '每4小时同步' },
              { label: 'weekly 周度固化', key: 'weekly',  color: '#6366f1', desc: '每日02:00' },
              { label: 'monthly 策略库', key: 'monthly', color: '#c084fc', desc: 'reputation + AB' },
              { label: 'vector 长期沉淀', key: 'vector', color: '#22d3ee', desc: '每周一03:00' },
            ].map(m => {
              const info = memoryLayers[m.key] as any
              const files = info?.files || 0
              const kb = info?.size_kb || 0
              const pct = files > 0 ? Math.min((files / 5) * 100, 100) : 0
              return (
                <motion.div key={m.key} className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-surface-2/50 transition-colors"
                  initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}
                >
                  <span className="status-dot" style={{ backgroundColor: m.color }} />
                  <div className="flex flex-col flex-1 min-w-0">
                    <span className="text-xs text-text-secondary">{m.label}</span>
                    <span className="text-2xs text-text-tertiary/50">{m.desc}</span>
                  </div>
                  {files > 0 ? (
                    <div className="flex items-center gap-1.5">
                      <span className="text-2xs text-text-tertiary">{files}f / {kb}KB</span>
                      <div className="w-10 h-1 bg-surface-2 rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ backgroundColor: m.color, width: `${pct}%` }} />
                      </div>
                    </div>
                  ) : (
                    <span className="text-2xs text-text-tertiary/40">未创建</span>
                  )}
                </motion.div>
              )
            })}
          </div>

          {/* Module status */}
          <div className="mt-3 pt-2 border-t border-border-default">
            <h3 className="text-2xs font-medium text-text-tertiary mb-1.5">
              核心模块
              <span className="text-text-tertiary/50 ml-1">
                {MODULES.filter(m => m.status === 'running').length}/{MODULES.length} 在线
              </span>
            </h3>
            <div className="grid grid-cols-2 gap-1">
              {MODULES.map(m => (
                <div key={m.name} className="flex items-center gap-1.5 py-0.5 group">
                  <span className={`status-dot ${m.status === 'running' ? 'online' : ''}`}
                    style={{ animation: m.status === 'running' ? 'status-pulse 2s ease-in-out infinite' : 'none' }} />
                  <span className="text-2xs text-text-tertiary truncate">{m.role}</span>
                  <span className="text-2xs text-text-tertiary/30 truncate opacity-0 group-hover:opacity-100 transition-opacity">{m.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Current node indicator */}
      <motion.div className="mt-3 pt-3 border-t border-border-default flex items-center gap-2 text-2xs">
        <span className="text-text-tertiary">当前阶段:</span>
        <motion.span
          className="px-2 py-0.5 rounded font-medium"
          style={{
            backgroundColor: `${STAGES[activeStage].color}15`,
            color: STAGES[activeStage].color,
          }}
          animate={{ opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          {STAGES[activeStage].zh}
        </motion.span>
        <span className="text-text-tertiary/50">
          {activeStage === 0 && '等待新任务触发入队'}
          {activeStage === 3 && `Strategist 调度中 \u00b7 ${inProgress} 个任务并行执行中`}
          {activeStage === 4 && `${review} 个任务等待双审裁决`}
          {activeStage >= 5 && '流程完成 \u2192 记忆沉淀 + 知识固化'}
        </span>
      </motion.div>
    </div>
  )
}
