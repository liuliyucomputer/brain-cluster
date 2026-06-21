import { motion } from 'framer-motion'
import { label } from '../lib/utils'

interface Props {
  health: { gateway_ok: boolean; ports_ok: number; score: number } | undefined
  services: Record<string, boolean> | undefined
}

const DIMENSIONS = [
  { key: 'gateway',   label: 'Gateway',  angle: 0 },
  { key: 'services',  label: 'Services', angle: 72 },
  { key: 'pipeline',  label: 'Pipeline', angle: 144 },
  { key: 'memory',    label: 'Memory',   angle: 216 },
  { key: 'agents',    label: 'Agents',   angle: 288 },
]

const DIM_COLORS = ['#22d3ee', '#10b981', '#6366f1', '#a855f7', '#f59e0b']

function computeScore(key: string, health: Props['health'], services: Props['services']): number {
  if (!health) return 0
  switch (key) {
    case 'gateway':   return health.gateway_ok ? 100 : 0
    case 'services':  return services ? (Object.values(services).filter(Boolean).length / Math.max(Object.keys(services).length, 1)) * 100 : 0
    case 'pipeline':  return health.score * 0.8
    case 'memory':    return health.ports_ok > 2 ? 85 : health.ports_ok > 1 ? 60 : 30
    case 'agents':    return health.score * 0.7
    default: return 50
  }
}

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number): [number, number] {
  const rad = ((angleDeg - 90) * Math.PI) / 180
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)]
}

export function HealthRadar({ health, services }: Props) {
  if (!health) return (
    <div className="surface-card p-4 text-center text-text-tertiary text-xs">健康数据不可用</div>
  )

  const cx = 80; const cy = 80; const r = 64
  const levels = [19, 38, 58]

  const points = DIMENSIONS.map((d, i) => {
    const score = computeScore(d.key, health, services) / 100
    return polarToCartesian(cx, cy, r * score, d.angle)
  })

  const polygonPath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ') + 'Z'

  return (
    <div className="surface-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-2xs font-medium text-text-tertiary uppercase tracking-wider">{label('健康雷达', 'Health Radar')}</h2>
        <span className={`text-2xs px-2 py-0.5 rounded font-semibold ${
          health.score >= 100 ? 'bg-success/10 text-success' : health.score >= 60 ? 'bg-warning/10 text-warning' : 'bg-danger/10 text-danger'
        }`}>
          {health.score} pts
        </span>
      </div>

      <svg viewBox="0 0 160 160" className="w-full max-w-[200px] mx-auto">
        {/* Grid rings */}
        {levels.map(l => (
          <g key={l}>
            <polygon
              points={DIMENSIONS.map(d => { const p = polarToCartesian(cx, cy, l, d.angle); return `${p[0]},${p[1]}` }).join(' ')}
              fill="none" stroke="hsl(var(--border-default))" strokeWidth="0.5" opacity="0.5"
            />
            {l === levels[2] && DIMENSIONS.map((d, i) => {
              const p = polarToCartesian(cx, cy, r, d.angle)
              const lp = polarToCartesian(cx, cy, r + 4, d.angle)
              return (
                <g key={d.key}>
                  <line x1={cx} y1={cy} x2={lp[0]} y2={lp[1]} stroke="hsl(var(--border-default))" strokeWidth="0.5" opacity="0.3" />
                  <text x={lp[0]} y={lp[1]} textAnchor="middle" dominantBaseline="middle"
                    fill="hsl(var(--text-tertiary))" fontSize="6" fontFamily="var(--font-sans)" fontWeight="500">
                    {d.label}
                  </text>
                </g>
              )
            })}
          </g>
        ))}

        {/* Data glow ring */}
        <polygon
          points={DIMENSIONS.map(d => { const p = polarToCartesian(cx, cy, r * 0.97, d.angle); return `${p[0]},${p[1]}` }).join(' ')}
          fill="none" stroke="hsl(var(--brand-indigo)/0.15)" strokeWidth="1"
        />

        {/* Score polygon with glow */}
        <defs>
          <filter id="radarGlow">
            <feGaussianBlur stdDeviation="1.5" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <polygon points={polygonPath} fill="hsl(var(--brand-indigo)/0.12)" stroke="hsl(var(--brand-indigo))" strokeWidth="1.5" filter="url(#radarGlow)" />

        {/* Score dots */}
        {points.map((p, i) => (
          <motion.circle
            key={i} cx={p[0]} cy={p[1]} r="3"
            fill={DIM_COLORS[i]} stroke="hsl(var(--surface-1))" strokeWidth="1"
            initial={{ r: 0 }} animate={{ r: 3 }} transition={{ delay: i * 0.15, type: 'spring' }}
          />
        ))}

        {/* Center dot */}
        <circle cx={cx} cy={cy} r="2" fill="hsl(var(--text-tertiary))" opacity="0.3" />
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-y-1 gap-x-3 justify-center mt-2">
        {DIMENSIONS.map((d, i) => (
          <div key={d.key} className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: DIM_COLORS[i] }} />
            <span className="text-2xs text-text-tertiary">{d.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
