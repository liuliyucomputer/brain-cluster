import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface CommandItem {
  id: string
  category: 'quick' | 'agents' | 'tasks' | 'commands' | 'navigation' | 'memory'
  title: string
  description?: string
  shortcut?: string
  icon?: string
  action: () => void
}

interface Props {
  isOpen: boolean
  onClose: () => void
}

const CATEGORY_ORDER: { key: CommandItem['category']; zh: string }[] = [
  { key: 'quick',  zh: '\u5feb\u6377\u6307\u4ee4' },
  { key: 'agents',  zh: 'Agent \u667a\u80fd\u4f53' },
  { key: 'tasks',   zh: '\u4efb\u52a1\u64cd\u4f5c' },
  { key: 'commands',zh: '\u7cfb\u7edf\u547d\u4ee4' },
  { key: 'navigation', zh: '\u5bfc\u822a' },
  { key: 'memory',  zh: '\u8bb0\u5fc6\u7ba1\u7406' },
]

const CATEGORY_ICONS: Record<string, string> = {
  quick: '\u26a1', agents: '\ud83e\udd16', tasks: '\u2705', commands: '\u2328', navigation: '\ud83d\udccd', memory: '\ud83e\udde0',
}

// LRU — store last 5 used commands
const lruKey = 'brain-cmd-palette-lru'
function getRecent(): string[] { try { return JSON.parse(localStorage.getItem(lruKey) || '[]') } catch { return [] } }
function pushRecent(id: string) { const rec = getRecent().filter(r => r !== id); rec.unshift(id); localStorage.setItem(lruKey, JSON.stringify(rec.slice(0, 5))) }

// Build commands with real API-calling quick actions
function buildCommands(onClose: () => void): CommandItem[] {
  const closeAfter = (fn: () => Promise<void>) => async () => { try { await fn() } finally { onClose() } }
  const apiCall = (url: string, method = 'POST') => fetch(`/api${url}`, { method }).then(r => r.json())

  const recent = getRecent()
  const allCmds: CommandItem[] = [
    // Quick actions
    { id: 'quick-restart', category: 'quick', title: '\u91cd\u542f\u670d\u52a1', description: '\u91cd\u542f Dashboard + StatsAPI', shortcut: '\u2318\u21E72', icon: '\ud83d\udd04',
      action: closeAfter(() => apiCall('/services/restart-all', 'POST')) },
    { id: 'quick-compress', category: 'quick', title: '\u89e6\u53d1\u8bb0\u5fc6\u538b\u7f29', description: '\u8fd0\u884c dreaming_compressor.py \u4e09\u9636\u6bb5\u538b\u7f29', shortcut: '\u2318M', icon: '\ud83d\udce6',
      action: closeAfter(() => apiCall('/memory/compress', 'POST')) },
    { id: 'quick-checkpoint', category: 'quick', title: '\u4fdd\u5b58\u5feb\u7167', description: '\u8fd0\u884c checkpoint.py \u4fdd\u5b58\u5f53\u524d\u72b6\u6001', shortcut: '\u2318\u21E7S', icon: '\ud83d\udcf8',
      action: closeAfter(() => apiCall('/checkpoint/save', 'POST')) },
    { id: 'quick-cleanup', category: 'quick', title: '\u6e05\u7406\u65e5\u5fd7', description: 'Rotate \u8fc7\u671f\u65e5\u5fd7\u6587\u4ef6', icon: '\ud83e\uddf9',
      action: closeAfter(() => apiCall('/logs/rotate', 'POST')) },
    { id: 'quick-sync-kanban', category: 'quick', title: '\u5f3a\u5236\u540c\u6b65 kanban', description: '\u4ece kanban.db \u62c9\u53d6\u6700\u65b0\u4efb\u52a1\u72b6\u6001', icon: '\ud83d\udce1',
      action: closeAfter(() => apiCall('/sync/kanban', 'POST')) },
    { id: 'quick-health-check', category: 'quick', title: '\u5168\u9762\u5065\u5eb7\u68c0\u67e5', description: '\u8fd0\u884c\u5168\u90e8 E2E \u81ea\u68c0', icon: '\ud83c\udfe5',
      action: closeAfter(() => apiCall('/health/full', 'POST')) },

    ...recent.filter(id => allCmds.find(c => c.id === id)).map(id => ({ ...allCmds.find(c => c.id === id)!, category: 'quick' as const })),

    // Agents
    { id: 'agent-strategist', category: 'agents', title: '\u7b56\u7565 Agent', description: 'Strategist \u2014 \u4efb\u52a1\u5206\u89e3\u4e0e\u5206\u914d', shortcut: 'Alt+1', icon: '\ud83c\udfaf', action: onClose },
    { id: 'agent-executor-a', category: 'agents', title: '\u6267\u884c\u5668 A', description: '\u6587\u6848\u521b\u4f5c \u2014 executor-a', shortcut: 'Alt+2', icon: '\u270f\ufe0f', action: onClose },
    { id: 'agent-executor-b', category: 'agents', title: '\u6267\u884c\u5668 B', description: 'PPT\u8bbe\u8ba1 \u2014 executor-b', shortcut: 'Alt+3', icon: '\ud83c\udfa8', action: onClose },
    { id: 'agent-executor-c', category: 'agents', title: '\u6267\u884c\u5668 C', description: '\u6570\u636e\u5206\u6790 \u2014 executor-c', shortcut: 'Alt+4', icon: '\ud83d\udcca', action: onClose },
    { id: 'agent-arbiter', category: 'agents', title: '\u4ef2\u88c1 Agent', description: 'Arbiter \u2014 \u53cc\u5ba1\u89e3\u51b3', shortcut: 'Alt+5', icon: '\u2696\ufe0f', action: onClose },

    // Tasks
    { id: 'task-create', category: 'tasks', title: '\u53d1\u5e03\u4efb\u52a1', description: '\u521b\u5efa\u65b0\u4efb\u52a1\u5e76\u5206\u914d Agent', shortcut: '\u2318N', icon: '\u2795', action: onClose },
    { id: 'task-view-all', category: 'tasks', title: '\u67e5\u770b\u6240\u6709\u4efb\u52a1', description: '\u4efb\u52a1\u5217\u8868\u4e0e\u72b6\u6001\u7b5b\u9009', shortcut: '\u2318T', icon: '\ud83d\udccb', action: onClose },

    // Commands
    { id: 'cmd-refresh', category: 'commands', title: '\u5237\u65b0\u6570\u636e', description: '\u5f3a\u5236\u62c9\u53d6\u6700\u65b0\u96c6\u7fa4\u72b6\u6001', shortcut: '\u2318R', icon: '\ud83d\udd04', action: onClose },
    { id: 'cmd-export-report', category: 'commands', title: '\u5bfc\u51fa\u62a5\u544a', description: '\u751f\u6210 CSV/JSON \u62a5\u544a\u6587\u4ef6', icon: '\ud83d\udcc4', action: onClose },

    // Navigation
    { id: 'nav-dashboard', category: 'navigation', title: '\u4e3b\u63a7\u9762\u677f', description: 'Brain Cluster \u5b9e\u65f6\u76d1\u63a7', shortcut: '\u23181', icon: '\ud83d\udfe6', action: onClose },
    { id: 'nav-logs', category: 'navigation', title: '\u65e5\u5fd7\u9762\u677f', description: '\u641c\u7d22\u4e0e\u5206\u6790\u65e5\u5fd7', shortcut: '\u23182', icon: '\ud83d\udcdc', action: onClose },

    // Memory
    { id: 'mem-view-daily', category: 'memory', title: '\u6bcf\u65e5\u8bb0\u5fc6', description: '\u67e5\u770b daily \u5de5\u4f5c\u65e5\u5fd7', icon: '\ud83d\udcc5', action: onClose },
    { id: 'mem-view-weekly', category: 'memory', title: '\u5468\u5ea6\u56fa\u5316', description: '\u67e5\u770b weekly \u84b8\u998f', icon: '\ud83d\udcca', action: onClose },
  ]
  return allCmds
}

export function CommandPalette({ isOpen, onClose }: Props) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const commands = useRef<CommandItem[]>([])

  useEffect(() => {
    if (isOpen) {
      commands.current = buildCommands(onClose)
      setQuery('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen, onClose])

  // Listen for keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        if (!isOpen) onClose() // toggle handled by parent
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  const filtered = query.trim()
    ? commands.current.filter(c =>
        c.title.includes(query) ||
        c.description?.includes(query) ||
        c.id.includes(query.toLowerCase())
      )
    : commands.current

  // Group by category
  const grouped = new Map<string, CommandItem[]>()
  for (const item of filtered) {
    if (!grouped.has(item.category)) grouped.set(item.category, [])
    grouped.get(item.category)!.push(item)
  }

  const allItems = filtered
  const selectedItem = allItems[selectedIndex]

  const execute = useCallback((item: CommandItem) => {
    pushRecent(item.id)
    item.action()
  }, [])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIndex(i => Math.min(i + 1, allItems.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setSelectedIndex(i => Math.max(i - 1, 0)) }
    else if (e.key === 'Enter' && selectedItem) { e.preventDefault(); execute(selectedItem) }
    else if (e.key === 'Escape') { e.preventDefault(); onClose() }
  }, [allItems.length, selectedItem, execute, onClose])

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 z-[100]"
            style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            className="fixed z-[101] left-1/2 -translate-x-1/2 rounded-xl overflow-hidden border border-white/[0.06]"
            style={{
              top: '15%',
              width: '520px',
              maxWidth: '90vw',
              background: 'hsl(240 6% 12% / 0.92)',
              backdropFilter: 'blur(24px) saturate(180%)',
              WebkitBackdropFilter: 'blur(24px) saturate(180%)',
            }}
            initial={{ opacity: 0, scale: 0.96, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -8 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
          >
            {/* Top light leak */}
            <div className="absolute top-0 left-[10%] right-[10%] h-px bg-gradient-to-r from-transparent via-white/8 to-transparent pointer-events-none" />

            {/* Search */}
            <div className="px-4 pt-4 pb-2">
              <div className="flex items-center gap-3 px-3 py-2">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="opacity-30 shrink-0">
                  <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M11 11l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={e => { setQuery(e.target.value); setSelectedIndex(0) }}
                  onKeyDown={handleKeyDown}
                  placeholder="搜索 Agent\u3001\u4efb\u52a1\u3001\u547d\u4ee4..."
                  className="flex-1 bg-transparent border-none outline-none text-sm text-text-primary placeholder:text-text-tertiary/50"
                  style={{ fontFamily: 'var(--font-sans)' }}
                />
                <kbd className="text-2xs text-text-tertiary/50 px-1.5 py-0.5 rounded bg-surface-0 border border-border-default font-mono">
                  esc
                </kbd>
              </div>
              {/* Active search underline */}
              <div className="mx-3 h-px bg-gradient-to-r from-brand-indigo/40 via-brand-indigo/20 to-transparent" />
            </div>

            {/* Results */}
            <div className="max-h-[320px] overflow-y-auto scrollbar-thin px-2 pb-2">
              {filtered.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 gap-2">
                  <span className="text-2xl opacity-20">{'\ud83d\udc7b'}</span>
                  <span className="text-xs text-text-tertiary/50">\u65e0\u5339\u914d\u7ed3\u679c</span>
                </div>
              ) : (
                Array.from(grouped.entries()).map(([category, items]) => (
                  <div key={category}>
                    <div className="flex items-center gap-1.5 px-4 py-1.5">
                      <span className="text-2xs">{CATEGORY_ICONS[category] || '\u2022'}</span>
                      <span className="text-2xs font-medium text-text-tertiary uppercase tracking-wider">
                        {CATEGORY_ORDER.find(c => c.key === category)?.zh || category}
                      </span>
                    </div>
                    {items.map(item => {
                      const globalIndex = allItems.indexOf(item)
                      const isSelected = globalIndex === selectedIndex
                      return (
                        <motion.div
                          key={item.id}
                          className={`flex items-center gap-3 py-2 px-4 rounded-lg mx-1 cursor-pointer transition-colors ${
                            isSelected ? 'bg-brand-indigo/10 border-l-2 border-l-brand-indigo' : 'hover:bg-surface-2/50 border-l-2 border-l-transparent'
                          }`}
                          onClick={() => execute(item)}
                          onMouseEnter={() => setSelectedIndex(globalIndex)}
                        >
                          {item.icon ? (
                            <span className="text-sm shrink-0">{item.icon}</span>
                          ) : (
                            <div className="w-4 h-4 shrink-0" />
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="text-xs text-text-primary">{item.title}</div>
                            {item.description && (
                              <div className="text-2xs text-text-tertiary/60 truncate">{item.description}</div>
                            )}
                          </div>
                          {item.shortcut && (
                            <kbd className="text-2xs text-text-tertiary/40 font-mono shrink-0">{item.shortcut}</kbd>
                          )}
                        </motion.div>
                      )
                    })}
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-2 flex items-center gap-3 text-2xs text-text-tertiary/40 border-t border-border-default">
              <span><kbd className="px-1 py-0.5 rounded bg-surface-0 border border-border-default font-mono">\u2191\u2193</kbd> \u5bfc\u822a</span>
              <span><kbd className="px-1 py-0.5 rounded bg-surface-0 border border-border-default font-mono">\u21a9</kbd> \u9009\u62e9</span>
              <span><kbd className="px-1 py-0.5 rounded bg-surface-0 border border-border-default font-mono">esc</kbd> \u5173\u95ed</span>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
