import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

interface ServiceInfo {
  running: boolean; port: number; zh: string; pid: number | null
}

const MANAGEABLE = ['Dashboard', 'StatsAPI']
const MONITORED = ['Gateway', 'Grafana', 'StarOfficeUI']

export function ServicePanel() {
  const [services, setServices] = useState<Record<string, ServiceInfo>>({})
  const [loading, setLoading] = useState<Record<string, boolean>>({})
  const [expanded, setExpanded] = useState(false)

  const fetchStatus = async () => {
    try { const r = await fetch('/api/services/status'); setServices(await r.json()) } catch {}
  }

  useEffect(() => { fetchStatus(); const id = setInterval(fetchStatus, 5000); return () => clearInterval(id) }, [])

  const startService = async (name: string) => {
    setLoading(prev => ({ ...prev, [name]: true }))
    await fetch(`/api/services/start/${name}`, { method: 'POST' }).catch(() => {})
    setTimeout(fetchStatus, 2500)
    setTimeout(() => setLoading(prev => ({ ...prev, [name]: false })), 3000)
  }

  const stopService = async (name: string) => {
    setLoading(prev => ({ ...prev, [name]: true }))
    await fetch(`/api/services/stop/${name}`, { method: 'POST' }).catch(() => {})
    setTimeout(fetchStatus, 1500)
    setTimeout(() => setLoading(prev => ({ ...prev, [name]: false })), 2000)
  }

  const allServices = [...MONITORED, ...MANAGEABLE]
  const upCount = allServices.filter(n => services[n]?.running).length

  return (
    <div className="surface-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-2xs font-medium text-text-tertiary uppercase tracking-wider">服务控制 / Services</h2>
        <div className="flex items-center gap-2">
          <button onClick={() => setExpanded(!expanded)} className="text-2xs text-text-tertiary hover:text-text-secondary transition-colors">
            {expanded ? '收起' : '详情'}
          </button>
          <span className="text-2xs text-text-tertiary">{upCount}/{allServices.length} up</span>
        </div>
      </div>

      <div className="space-y-1">
        {MONITORED.map((name, i) => {
          const info = services[name]; const isUp = info?.running ?? false
          return (
            <motion.div
              key={name}
              className="flex items-center justify-between py-1.5 rounded-lg hover:bg-surface-2/50 px-1.5 -mx-1.5 transition-colors"
              initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
            >
              <div className="flex items-center gap-2">
                <span className={`status-dot ${isUp ? 'online' : 'offline'}`} />
                <div className="flex flex-col">
                  <span className="text-xs text-text-primary">{name}</span>
                  {expanded && info && <span className="text-2xs text-text-tertiary">{info.zh} :{info.port}</span>}
                </div>
              </div>
              <span className={`text-2xs ${isUp ? 'text-success/60' : 'text-danger/60'}`}>
                {isUp ? 'UP' : 'DOWN'}
              </span>
            </motion.div>
          )
        })}

        <div className="border-b border-border-default my-1" />

        {MANAGEABLE.map((name, i) => {
          const info = services[name]; const isUp = info?.running ?? false; const isLoading = loading[name]
          return (
            <motion.div
              key={name}
              className="flex items-center justify-between py-1.5 group rounded-lg hover:bg-surface-2/50 px-1.5 -mx-1.5 transition-colors"
              initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: (MONITORED.length + i) * 0.05 }}
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <span className={`status-dot ${isUp ? 'online' : 'offline'}`} />
                <div className="flex flex-col min-w-0">
                  <span className="text-xs text-text-primary truncate">{name}</span>
                  {expanded && info && <span className="text-2xs text-text-tertiary">{info.zh} :{info.port}</span>}
                </div>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                {isUp ? (
                  <button onClick={() => stopService(name)} disabled={isLoading}
                    className="text-2xs text-danger/60 hover:text-danger/80 transition-colors px-1.5 py-0.5 rounded border border-danger/15 hover:border-danger/40 opacity-0 group-hover:opacity-100">
                    {isLoading ? '...' : 'Stop'}
                  </button>
                ) : (
                  <button onClick={() => startService(name)} disabled={isLoading}
                    className="text-2xs text-success/60 hover:text-success/80 transition-colors px-1.5 py-0.5 rounded border border-success/15 hover:border-success/40">
                    {isLoading ? '...' : 'Start'}
                  </button>
                )}
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
