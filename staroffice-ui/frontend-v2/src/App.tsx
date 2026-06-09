import { useState, useCallback, useEffect } from 'react'
import { motion } from 'framer-motion'
import { fetchStatsV2, fetchMonitor, type ClusterStatsV2, type MonitorData } from './lib/api'
import { formatTime } from './lib/utils'
import { PipelineFlow } from './components/PipelineFlow'
import { AgentMatrix } from './components/AgentMatrix'
import { EventStream } from './components/EventStream'
import { ServicePanel } from './components/ServicePanel'
import { ExtensionsPanel } from './components/ExtensionsPanel'
import { LogPanel } from './components/LogPanel'
import { ExecutionFlow } from './components/ExecutionFlow'
import { TaskCreator } from './components/TaskCreator'
import { MemoryManager } from './components/MemoryManager'

const EMPTY_STATS: ClusterStatsV2 = {
  overview: { total: 0, active: 0, done: 0, done_today: 0, avg_duration: 0 },
  services: {}, agents: {}, pipeline: {}, activity: [],
  timeline: { created_24h: 0, completed_24h: 0, active_24h: 0 },
  letta_sync_files: 0, kanban: { by_status: {}, by_agent: {} }, extensions: null,
}

export default function App() {
  const [stats, setStats] = useState<ClusterStatsV2>(EMPTY_STATS)
  const [monitor, setMonitor] = useState<MonitorData | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const [connected, setConnected] = useState(true)

  const updateStats = useCallback((data: ClusterStatsV2) => {
    setStats(data); setLastUpdate(new Date()); setLoading(false); setConnected(true)
  }, [])

  useEffect(() => {
    fetchStatsV2().then(updateStats).catch(() => { setLoading(false); setConnected(false) })
    fetchMonitor().then(setMonitor).catch(() => {})
  }, [updateStats])

  useEffect(() => {
    const id = setInterval(() => {
      fetchStatsV2().then(updateStats).catch(() => setConnected(false))
      fetchMonitor().then(setMonitor).catch(() => {})
    }, 3000)
    return () => clearInterval(id)
  }, [updateStats])

  const { overview } = stats
  const health = monitor?.health
  const servicesMon = monitor?.services
  const serviceUp = servicesMon ? [servicesMon.staroffice, servicesMon.grafana, servicesMon.dashboard].filter(Boolean).length : 0
  const extVerified = Object.values(stats.extensions?.lines ?? {}).filter((e: any) => e?.verified).length

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'hsl(240,8%,4.5%)' }}>
        <div className="flex flex-col items-center gap-4">
          <div className="relative w-14 h-14">
            <div className="absolute inset-0 rounded-full border-2 border-indigo-500/30 animate-ping" />
            <div className="absolute inset-1 rounded-full bg-indigo-500/20" style={{ animation: 'heartbeat 1.5s ease-in-out infinite' }} />
          </div>
          <p className="text-sm text-blue-200/60 font-medium">加载脑集群...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen" style={{ background: 'hsl(240,8%,4.5%)', color: '#e0e2f0' }}>
      {/* Header */}
      <header className="border-b border-white/[0.05]" style={{ background: 'hsla(240,8%,5%,0.92)', backdropFilter: 'blur(20px)' }}>
        <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-indigo-400" style={{ boxShadow: '0 0 14px rgba(99,102,241,0.5)', animation: 'heartbeat 2s ease-in-out infinite' }} />
            <h1 className="text-sm font-bold tracking-tight">
              <span className="text-white/90">Brain Cluster</span>
              <span className="text-white/25 font-normal ml-2 text-[10px]">脑集群 · 实时动态监控</span>
            </h1>
            {health && (
              <span
                className="text-[10px] px-2 py-0.5 rounded-full font-semibold"
                style={{
                  background: health.score >= 100 ? 'rgba(34,197,94,0.12)' : 'rgba(245,158,11,0.12)',
                  color: health.score >= 100 ? '#4ade80' : '#fbbf24',
                }}
              >
                健康 {health.score}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 text-[10px]">
            <span className="flex items-center gap-1.5 text-white/35">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: connected ? '#4ade80' : '#fbbf24', boxShadow: connected ? '0 0 6px rgba(74,222,128,0.5)' : 'none' }} />
              {connected ? '实时' : '轮询'}
            </span>
            <span className="text-white/25 tabular-nums">{formatTime(lastUpdate)}</span>
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="max-w-[1600px] mx-auto px-6 py-3 space-y-3">

        {/* === STATS ROW === */}
        <div className="grid grid-cols-7 gap-2">
          {[
            { label: '总任务', val: overview.total, color: '#818cf8' },
            { label: '活跃中', val: overview.active, color: '#fbbf24' },
            { label: '已完成', val: overview.done, color: '#4ade80' },
            { label: 'Letta', val: stats.letta_sync_files, color: '#818cf8' },
            { label: '服务在线', val: `${serviceUp}/3`, color: serviceUp >= 3 ? '#4ade80' : '#fbbf24' },
            { label: '扩展已验证', val: extVerified, color: '#c084fc' },
            { label: '24h完成', val: stats.timeline.completed_24h, color: '#22d3ee' },
          ].map((s, i) => (
            <motion.div
              key={i}
              className="card-depth rounded-xl p-3 text-center"
              style={{ background: 'hsl(240,6%,10%)', border: '1px solid rgba(255,255,255,0.05)' }}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04, duration: 0.35 }}
            >
              <div className="text-[10px] text-white/35 mb-0.5">{s.label}</div>
              <div className="text-xl font-bold tabular-nums" style={{ color: s.color }}>{s.val}</div>
            </motion.div>
          ))}
        </div>

        {/* === EXECUTION FLOW — "血脉" === */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <ExecutionFlow stats={stats} monitor={monitor} />
        </motion.div>

        {/* === 3-COLUMN DETAIL === */}
        <div className="grid grid-cols-3 gap-3">

          {/* COL 1: Agents + Extensions */}
          <div className="space-y-3">
            <AgentMatrix agents={monitor?.agents ?? null} />
            <ExtensionsPanel extensions={stats.extensions?.lines ?? null} />
          </div>

          {/* COL 2: Events + Task Creator */}
          <div className="space-y-3">
            <EventStream events={monitor?.recent_events ?? []} />
            <TaskCreator />
          </div>

          {/* COL 3: Services + Memory + Logs */}
          <div className="space-y-3">
            <ServicePanel />
            <MemoryManager />
            <LogPanel />
          </div>

        </div>
      </div>
    </div>
  )
}
