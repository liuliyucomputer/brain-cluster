import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { fetchEyesTools, type EyesToolsData, type EyesTool } from '../lib/api'

const COLOR_MAP: Record<string, string> = {
  indigo:  'var(--brand-indigo)',
  cyan:    'var(--brand-cyan)',
  emerald: 'var(--success)',
  violet:  'var(--brand-violet)',
}

const BG_MAP: Record<string, string> = {
  indigo:  'rgba(99,102,241,0.08)',
  cyan:    'rgba(34,211,238,0.06)',
  emerald: 'rgba(16,185,129,0.06)',
  violet:  'rgba(168,85,247,0.06)',
}

const STATUS_CLS: Record<string, string> = {
  success: 'bg-success/10 text-success',
  warning: 'bg-warning/10 text-warning',
  danger:  'bg-danger/10 text-danger',
}

export function ToolsPanel() {
  const [data, setData] = useState<EyesToolsData | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [hovered, setHovered] = useState<string | null>(null)
  const [expandedTool, setExpandedTool] = useState<EyesTool | null>(null)

  useEffect(() => {
    fetchEyesTools().then(setData).catch(() => {})
  }, [])

  if (!data) {
    return <div className="surface-card p-4 text-center text-text-tertiary text-xs">加载工具库...</div>
  }

  const { tools, categories, status_labels } = data
  const categoryKeys = Object.keys(categories)
  const filtered = selectedCategory
    ? tools.filter(t => t.category === selectedCategory)
    : tools

  const statusCount = (status: string) => tools.filter(t => t.status === status).length

  return (
    <div className="surface-card p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-2xs font-medium text-text-tertiary uppercase tracking-wider">
          Eyes 工具库 / Tools
        </h2>
        <div className="flex items-center gap-2 text-2xs text-text-tertiary">
          <span className="flex items-center gap-1">
            <span className="status-dot online" /> {statusCount('verified')} 可用
          </span>
          <span className="flex items-center gap-1">
            <span className="status-dot busy" /> {statusCount('docker') + statusCount('cloudflare')} 待依赖
          </span>
          <span className="flex items-center gap-1">
            <span className="status-dot offline" /> {statusCount('gpu')} 需GPU
          </span>
        </div>
      </div>

      {/* Category filter tabs */}
      <div className="flex gap-1.5 mb-3 flex-wrap">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`text-2xs px-2 py-1 rounded border transition-all ${
            selectedCategory === null
              ? 'border-brand-indigo/40 bg-brand-indigo/10 text-brand-indigo'
              : 'border-border-default hover:border-border-hover text-text-tertiary hover:text-text-secondary'
          }`}
        >
          全部 ({tools.length})
        </button>
        {categoryKeys.map(cat => {
          const count = tools.filter(t => t.category === cat).length
          return (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`text-2xs px-2 py-1 rounded border transition-all ${
                selectedCategory === cat
                  ? 'border-brand-indigo/40 bg-brand-indigo/10 text-brand-indigo'
                  : 'border-border-default hover:border-border-hover text-text-tertiary hover:text-text-secondary'
              }`}
            >
              {categories[cat].zh} ({count})
            </button>
          )
        })}
      </div>

      {/* Tool cards grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
        {filtered.map((tool, i) => (
          <ToolCard
            key={tool.name}
            tool={tool}
            statusLabel={status_labels[tool.status]}
            index={i}
            isHovered={hovered === tool.name}
            onHover={(v) => setHovered(v ? tool.name : null)}
            onClick={() => setExpandedTool(tool)}
          />
        ))}
      </div>

      {/* Expanded modal */}
      {expandedTool && (
        <ToolDetailModal
          tool={expandedTool}
          statusLabel={status_labels[expandedTool.status]}
          category={categories[expandedTool.category]}
          onClose={() => setExpandedTool(null)}
        />
      )}
    </div>
  )
}

function ToolCard({ tool, statusLabel, index, isHovered, onHover, onClick }: {
  tool: EyesTool
  statusLabel: { zh: string; en: string; cls: string }
  index: number
  isHovered: boolean
  onHover: (v: boolean) => void
  onClick: () => void
}) {
  const color = COLOR_MAP[tool.color] || 'var(--brand-indigo)'
  const bg = BG_MAP[tool.color] || 'rgba(99,102,241,0.08)'

  return (
    <motion.div
      className="relative rounded-lg border border-border-default p-3 cursor-default transition-all overflow-hidden group"
      style={{ background: bg }}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
      onClick={onClick}
    >
      {/* Left accent bar */}
      <div
        className="absolute left-0 top-0 bottom-0 w-0.5 rounded-r transition-all duration-300"
        style={{ background: color, opacity: isHovered ? 1 : 0.3 }}
      />

      {/* Top row: name + stars */}
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-text-primary truncate pr-1">{tool.zh}</span>
        <span className="text-2xs text-text-tertiary shrink-0 stat-value">{tool.stars}</span>
      </div>

      {/* Description */}
      <p className="text-2xs text-text-tertiary leading-relaxed mb-2 line-clamp-2">{tool.desc}</p>

      {/* Bottom: status badge + name */}
      <div className="flex items-center justify-between">
        <span className={`text-2xs px-1.5 py-0.5 rounded ${STATUS_CLS[statusLabel.cls] || 'bg-success/10 text-success'}`}>
          {statusLabel.zh}
        </span>
        <span className="text-2xs text-text-tertiary/50 truncate ml-1 max-w-[60px]">{tool.name}</span>
      </div>

      {/* Hover glow */}
      <div
        className="absolute inset-0 rounded-lg pointer-events-none transition-opacity duration-300"
        style={{
          opacity: isHovered ? 0.15 : 0,
          background: `radial-gradient(circle at 50% 0%, ${color}, transparent 70%)`,
        }}
      />
    </motion.div>
  )
}

function ToolDetailModal({ tool, statusLabel, category, onClose }: {
  tool: EyesTool
  statusLabel: { zh: string; en: string; cls: string }
  category: { zh: string; en: string }
  onClose: () => void
}) {
  const color = COLOR_MAP[tool.color] || 'var(--brand-indigo)'
  const bg = BG_MAP[tool.color] || 'rgba(99,102,241,0.08)'

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      <motion.div
        className="relative w-full max-w-lg rounded-2xl border border-border-default overflow-hidden"
        style={{ background: 'hsl(240,6%,10%)' }}
        initial={{ scale: 0.9, opacity: 0, y: 20 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.9, opacity: 0, y: 20 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header gradient */}
        <div className="relative h-32" style={{ background: bg }}>
          <div
            className="absolute inset-0"
            style={{
              background: `radial-gradient(circle at 30% 50%, ${color}15, transparent 60%)`,
            }}
          />
          <button
            onClick={onClose}
            className="absolute top-3 right-3 w-8 h-8 rounded-full flex items-center justify-center text-white/40 hover:text-white/80 hover:bg-white/10 transition-all"
          >
            ✕
          </button>
          <div className="absolute bottom-4 left-6">
            <span
              className="text-2xs px-2 py-0.5 rounded-full border mb-2 inline-block"
              style={{ borderColor: `${color}30`, color, background: `${color}10` }}
            >
              {category?.zh || tool.category}
            </span>
            <h2 className="text-xl font-bold text-white/90">{tool.zh}</h2>
            <p className="text-xs text-white/40 mt-0.5">{tool.name}</p>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Description */}
          <div>
            <h3 className="text-2xs font-medium text-white/30 uppercase tracking-wider mb-1.5">介绍</h3>
            <p className="text-sm text-white/70 leading-relaxed">{tool.desc}</p>
          </div>

          {/* Status & Stars */}
          <div className="flex items-center gap-3">
            <span className={`text-xs px-2.5 py-1 rounded-full ${STATUS_CLS[statusLabel.cls] || 'bg-success/10 text-success'}`}>
              {statusLabel.zh}
            </span>
            <span className="text-xs text-white/30">
              ⭐ {tool.stars}
            </span>
            <span className="text-xs text-white/30">
              📦 {tool.category}
            </span>
          </div>

          {/* Color indicator */}
          <div className="flex items-center gap-2">
            <span className="text-2xs text-white/30">主题色:</span>
            <span
              className="w-4 h-4 rounded-full border border-white/10"
              style={{ background: color }}
            />
            <span className="text-2xs text-white/40">{tool.color}</span>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}