import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { motion } from 'framer-motion'

const AGENT_ZH: Record<string, string> = { strategist: '\u7b56\u7565', 'executor-a': '\u6587\u6848', 'executor-b': 'PPT', 'executor-c': '\u6570\u636e', monitor: '\u76d1\u63a7', 'reviewer-strict': '\u4e25\u5ba1', 'reviewer-creative': '\u521b\u5ba1', arbiter: '\u4ef2\u88c1', learner: '\u5b66\u4e60' }

const TABS = [
  { key: 'alerts', label: '\u544a\u8b66' },
  { key: 'system', label: '\u7cfb\u7edf' },
  { key: 'app', label: '\u9762\u677f' },
  { key: 'gateway', label: '\u7f51\u5173' },
  { key: 'commander', label: '\u6307\u6325\u5b98' },
  ...Object.entries(AGENT_ZH).map(([key, label]) => ({ key, label })),
]

const LEVEL_FILTERS = ['ALL', 'ERROR', 'WARN', 'INFO'] as const
type LevelFilter = typeof LEVEL_FILTERS[number]

function clusterLines(lines: string[]): { line: string; count: number }[] {
  const clusters: Map<string, number> = new Map()
  const clustered: { line: string; count: number }[] = []
  for (const line of lines) {
    const stripped = line.replace(/\d{2}:\d{2}:\d{2}/, '').replace(/\d+\.\d+\.\d+\.\d+/, '').trim()
    if (clusters.has(stripped)) {
      clusters.set(stripped, clusters.get(stripped)! + 1)
    } else {
      clusters.set(stripped, 1)
      clustered.push({ line, count: 1 })
    }
  }
  return clustered.map(c => ({ ...c, count: clusters.get(c.line.replace(/\d{2}:\d{2}:\d{2}/, '').replace(/\d+\.\d+\.\d+\.\d+/, '').trim()) ?? 1 }))
}

export function LogPanel() {
  const [tab, setTab] = useState('alerts')
  const [lines, setLines] = useState<string[]>([])
  const [search, setSearch] = useState('')
  const [levelFilter, setLevelFilter] = useState<LevelFilter>('ALL')
  const [clusterMode, setClusterMode] = useState(false)
  const [contextIndex, setContextIndex] = useState<number | null>(null)

  const abortRef = useRef<AbortController | null>(null)

  const fetchLogs = useCallback(async (tabKey: string) => {
    // 取消之前的请求，避免竞态条件
    if (abortRef.current) {
      abortRef.current.abort()
    }
    abortRef.current = new AbortController()

    try {
      let url: string
      if (['gateway', 'grafana', 'staroffice', 'orchestrator', 'commander'].includes(tabKey)) url = `/api/logs/service/${tabKey}`
      else if (Object.keys(AGENT_ZH).includes(tabKey)) url = `/api/logs/agents/${tabKey}`
      else url = `/api/logs/${tabKey}`
      const r = await fetch(url, { signal: abortRef.current.signal })
      const d = await r.json()
      setLines(d.lines || [])
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setLines([])
      }
    }
  }, [])

  useEffect(() => { fetchLogs(tab) }, [tab, fetchLogs])
  useEffect(() => { const id = setInterval(() => fetchLogs(tab), 6000); return () => clearInterval(id) }, [tab, fetchLogs])

  const filtered = useMemo(() => {
    let result = lines
    if (search.trim()) result = result.filter(l => l.toLowerCase().includes(search.toLowerCase()))
    if (levelFilter !== 'ALL') result = result.filter(l => {
      if (levelFilter === 'ERROR') return l.includes('ERROR') || l.includes('FAIL') || l.includes('CRITICAL') || l.includes('\u274c')
      if (levelFilter === 'WARN') return l.includes('WARN') || l.includes('\u26a0')
      if (levelFilter === 'INFO') return l.includes('INFO') || l.includes('SUCCESS')
      return true
    })
    return result
  }, [lines, search, levelFilter])

  const displayed = useMemo(() => {
    return clusterMode ? clusterLines(filtered) : filtered.map(line => ({ line, count: 1 }))
  }, [filtered, clusterMode])

  const errorCount = lines.filter(l => l.includes('ERROR') || l.includes('FAIL') || l.includes('CRITICAL')).length
  const warnCount = lines.filter(l => l.includes('WARN')).length

  const getLineColor = (line: string) => {
    if (line.includes('ERROR') || line.includes('FAIL') || line.includes('\u274c') || line.includes('CRITICAL')) return 'text-danger/80'
    if (line.includes('WARN') || line.includes('\u26a0')) return 'text-amber-400/70'
    if (line.includes('INFO') || line.includes('SUCCESS')) return 'text-text-secondary/60'
    return 'text-text-tertiary/40'
  }

  return (
    <div className="surface-card p-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-2xs font-medium text-text-tertiary uppercase tracking-wider">\u65e5\u5fd7 / Logs</h2>
        <div className="flex items-center gap-1.5">
          {errorCount > 0 && <span className="text-2xs bg-danger/10 text-danger px-1.5 py-0.5 rounded">{errorCount} ERR</span>}
          {warnCount > 0 && <span className="text-2xs bg-warning/10 text-warning px-1.5 py-0.5 rounded">{warnCount} WRN</span>}
        </div>
      </div>

      {/* Search + Filter bar */}
      <div className="flex items-center gap-2 mb-2">
        <input
          type="text" value={search} onChange={e => setSearch(e.target.value)}
          placeholder="\u641c\u7d22\u65e5\u5fd7..."
          className="flex-1 bg-surface-0 border border-border-default rounded-md px-2 py-1 text-2xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-brand-indigo/40 transition-all"
        />
        <div className="flex gap-0.5">
          {LEVEL_FILTERS.map(l => (
            <button key={l} onClick={() => setLevelFilter(l)}
              className={`text-2xs px-1.5 py-0.5 rounded transition-colors ${
                levelFilter === l ? 'bg-brand-indigo/15 text-brand-indigo' : 'text-text-tertiary hover:text-text-secondary hover:bg-surface-2'
              }`}>
              {l}
            </button>
          ))}
        </div>
        <button onClick={() => setClusterMode(!clusterMode)}
          className={`text-2xs px-1.5 py-0.5 rounded transition-colors ${
            clusterMode ? 'bg-brand-cyan/15 text-brand-cyan' : 'text-text-tertiary hover:text-text-secondary hover:bg-surface-2'
          }`}>
          {clusterMode ? '\u5c55\u5f00' : '\u805a\u7c7b'}
        </button>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 mb-2 overflow-x-auto scrollbar-thin pb-1">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`text-2xs px-2 py-1 rounded whitespace-nowrap transition-colors ${
              tab === t.key ? 'bg-brand-indigo/15 text-brand-indigo' : 'text-text-tertiary hover:text-text-secondary hover:bg-surface-2/50'
            }`}>{t.label}</button>
        ))}
      </div>

      {/* Log content */}
      <motion.div key={tab} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        className="bg-black/30 rounded-lg p-3 font-mono text-xs leading-relaxed max-h-[240px] overflow-y-auto scrollbar-thin">
        {displayed.length === 0 ? (
          <span className="text-text-tertiary/30">{search.trim() ? '\u65e0\u5339\u914d\u7ed3\u679c' : '\u6682\u65e0\u65e5\u5fd7'}</span>
        ) : (
          displayed.map((item, i) => {
            const color = getLineColor(item.line)
            const isError = item.line.includes('ERROR') || item.line.includes('FAIL') || item.line.includes('CRITICAL')
            const showContext = contextIndex === i
            return (
              <div key={i}>
                <div className={`py-0.5 flex items-start gap-2 ${color} ${isError ? 'bg-danger/5 -mx-1.5 px-1.5 rounded' : ''}`}
                  onClick={() => isError && setContextIndex(showContext ? null : i)}>
                  {item.count > 1 && <span className="text-text-tertiary/40 shrink-0">[{item.count}\u00d7]</span>}
                  <span className="truncate flex-1">{item.line}</span>
                </div>
                {showContext && isError && (
                  <div className="pl-4 border-l border-danger/20 ml-2 py-0.5 space-y-0">
                    {filtered.slice(Math.max(0, filtered.indexOf(item.line) - 2), Math.min(filtered.length, filtered.indexOf(item.line) + 3)).map((ctx, j) => (
                      <div key={j} className={`text-2xs ${getLineColor(ctx)}`}
                        style={{ opacity: ctx === item.line ? 1 : 0.4 }}>{ctx}</div>
                    ))}
                  </div>
                )}
              </div>
            )
          })
        )}
      </motion.div>

      {search && (
        <div className="text-2xs text-text-tertiary/40 mt-1">\u663e\u793a {displayed.length}/{lines.length} \u884c</div>
      )}
    </div>
  )
}
