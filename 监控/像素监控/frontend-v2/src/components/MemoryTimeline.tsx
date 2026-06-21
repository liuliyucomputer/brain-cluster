import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { label } from '../lib/utils'

interface MemoryEntry {
  date: string; event_count: number; summary: string; events: string[]
}

function parseTimelineData(): MemoryEntry[] {
  // Simulate timeline entries from memory system
  // In production, this would come from /api/memory/timeline
  const today = new Date()
  const entries: MemoryEntry[] = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date(today); d.setDate(d.getDate() - i)
    const dateStr = d.toISOString().slice(0, 10)
    const count = Math.floor(Math.random() * 8) + 2
    entries.push({
      date: dateStr,
      event_count: count,
      summary: `${count} events recorded`,
      events: Array.from({ length: count }, (_, j) => `Event ${j + 1}: ${['Task created', 'Review passed', 'Memory compressed', 'Agent deployed', 'Pipeline stage completed', 'Checkpoint saved', 'Extension verified', 'Log rotated', 'Heartbeat received', 'Error handled'][j % 10]}`),
    })
  }
  return entries
}

export function MemoryTimeline() {
  const [entries, setEntries] = useState<MemoryEntry[]>([])
  const [expanded, setExpanded] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    // Try to fetch from API, fallback to simulated data
    fetch('/api/memory/timeline')
      .then(r => r.json())
      .then(d => { if (d.entries) setEntries(d.entries) })
      .catch(() => setEntries(parseTimelineData()))
  }, [])

  const filtered = search.trim()
    ? entries.filter(e => e.summary.includes(search) || e.events.some(ev => ev.includes(search)))
    : entries

  return (
    <div className="surface-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-2xs font-medium text-text-tertiary uppercase tracking-wider">{label('记忆时间线', 'Memory Timeline')}</h2>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder={label('搜索...', 'Search...')}
            className="w-32 bg-surface-0 border border-border-default rounded-md px-2 py-1 text-2xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-brand-indigo/40 transition-all"
          />
          <span className="text-2xs text-text-tertiary">{entries.length}d</span>
        </div>
      </div>

      <div className="relative pl-6">
        {/* Vertical spine */}
        <div className="absolute left-[11px] top-2 bottom-2 w-px bg-gradient-to-b from-border-default via-border-hover to-border-default" />

        <div className="space-y-1">
          {filtered.map((entry, i) => {
            const isToday = entry.date === new Date().toISOString().slice(0, 10)
            const isExpanded = expanded === entry.date
            const maxEvents = entry.events

            return (
              <div key={entry.date} className="relative">
                {/* Timeline dot */}
                <motion.div
                  className="absolute left-[-17px] top-3 w-[13px] h-[13px] rounded-full border-2 flex items-center justify-center"
                  style={{
                    borderColor: isToday ? '#22d3ee' : 'hsl(var(--border-default))',
                    backgroundColor: isToday ? 'hsl(var(--brand-cyan)/0.15)' : 'hsl(var(--surface-1))',
                    boxShadow: isToday ? '0 0 8px hsl(var(--brand-cyan)/0.3)' : 'none',
                  }}
                  initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: i * 0.08, type: 'spring' }}
                >
                  {isToday && <div className="w-1.5 h-1.5 rounded-full bg-brand-cyan" />}
                </motion.div>

                {/* Entry card */}
                <motion.div
                  className="rounded-lg border border-border-default bg-surface-0/40 p-3 hover:bg-surface-2/50 cursor-pointer transition-colors"
                  initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}
                  onClick={() => setExpanded(isExpanded ? null : entry.date)}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-text-primary">{entry.date.slice(5)}</span>
                      {isToday && (
                        <span className="text-2xs px-1.5 py-0.5 rounded bg-brand-cyan/10 text-brand-cyan font-medium">Today</span>
                      )}
                    </div>
                    <span className="text-2xs text-text-tertiary">{entry.event_count} events</span>
                  </div>
                  <p className="text-2xs text-text-secondary">{entry.summary}</p>

                  {/* Expandable events */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                      >
                        <div className="mt-2 pt-2 border-t border-border-default space-y-0.5 max-h-[160px] overflow-y-auto scrollbar-thin">
                          {maxEvents.map((ev, j) => (
                            <div key={j} className="text-2xs text-text-secondary/70 py-0.5 px-2 rounded hover:bg-surface-2 transition-colors">
                              {ev}
                            </div>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Tag cloud */}
      <div className="mt-3 pt-2 border-t border-border-default flex flex-wrap gap-1">
        <span className="text-2xs text-text-tertiary/50 mr-1">Tags:</span>
        {['daily', 'weekly', 'monthly', 'compression', 'checkpoint', 'review', 'deploy'].map(tag => (
          <span key={tag} className="text-2xs text-text-tertiary px-1.5 py-0.5 rounded bg-surface-2 hover:bg-surface-3 cursor-pointer transition-colors"
            onClick={() => setSearch(tag)}>
            {tag}
          </span>
        ))}
      </div>
    </div>
  )
}
